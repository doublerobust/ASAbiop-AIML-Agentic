#!/usr/bin/env python3
"""TC-001 Ground Truth: Kaplan-Meier Median PFS Estimation (Python)

Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark.

Cross-validated against: R survival::survfit(), SAS PROC LIFETEST
Dependencies: pandas, numpy, lifelines (>= 0.29.0)
Usage: python tc_001_km_median.py --seed 42 --n 200 --output results.json
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from lifelines import KaplanMeierFitter

from common.data_generation import generate_adtte


def compute_km_median(
    adtte: pd.DataFrame,
    arm: int = 1,
    population: str = "ITT",
    conf_type: str = "log-log",
    seed: int = 42,
) -> dict:
    """Compute KM median PFS for a single treatment arm.

    Args:
        adtte: ADTTE-like DataFrame with AVAL, CNSR, TRT01PN, ITTFL columns
        arm: Treatment arm to analyze (default: 1)
        population: Population filter (default: "ITT")
        conf_type: Confidence interval method (default: "log-log")
        seed: Random seed for provenance

    Returns:
        dict with structured benchmark output
    """
    # Population filter
    if population == "ITT":
        data = adtte[(adtte["ITTFL"] == "Y") & (adtte["TRT01PN"] == arm)].copy()
    else:
        data = adtte[adtte["TRT01PN"] == arm].copy()

    if len(data) == 0:
        raise ValueError(f"No subjects in arm {arm} for population {population}")

    n_total = len(data)
    n_events = int((1 - data["CNSR"]).sum())

    # Kaplan-Meier fit
    # lifelines uses log-log transform for CI by default (alpha=0.05 → 95% CI)
    kmf = KaplanMeierFitter()
    kmf.fit(
        durations=data["AVAL"],
        event_observed=1 - data["CNSR"],
        alpha=0.05,
    )

    # Extract median and CI
    median_pfs = kmf.median_survival_time_

    # CI extraction: lifelines provides median_ at the 0.5 quantile
    # Use the confidence_interval_ at the median
    ci = kmf.confidence_interval_
    surv = kmf.survival_function_

    # Find index where survival crosses 0.5
    below_half = surv["KM_estimate"] <= 0.5
    if below_half.any():
        median_idx = below_half.idxmax()
        ci_lower = float(ci.loc[median_idx, "KM_estimate_lower_0.95"])
        ci_upper = float(ci.loc[median_idx, "KM_estimate_upper_0.95"])
        estimable = True
    else:
        ci_lower = None
        ci_upper = None
        estimable = False

    result = {
        "test_case_id": "TC-001",
        "variant_id": f"v{seed}",
        "language": "Python",
        "package": "lifelines",
        "package_version": "0.29.0",
        "median_pfs": round(float(median_pfs), 4) if estimable else None,
        "ci_lower": round(float(ci_lower), 4) if estimable else None,
        "ci_upper": round(float(ci_upper), 4) if estimable else None,
        "n_events": n_events,
        "n_total": n_total,
        "ci_method": conf_type,
        "estimable": estimable,
        "seed": seed,
    }

    return result


def main():
    parser = argparse.ArgumentParser(
        description="TC-001: KM Median PFS Estimation (Python)"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--n", type=int, default=200, help="Number of subjects")
    parser.add_argument("--arm", type=int, default=1, help="Treatment arm")
    parser.add_argument("--output", type=str, default=None, help="Output JSON path")
    args = parser.parse_args()

    print(f"TC-001: KM Median PFS (Python) — seed={args.seed}, n={args.n}, arm={args.arm}")

    # Generate synthetic ADTTE
    adtte = generate_adtte(seed=args.seed, n_subjects=args.n, n_arms=2)
    print(f"Generated ADTTE with {len(adtte)} subjects")

    # Compute KM median
    result = compute_km_median(adtte, arm=args.arm, seed=args.seed)

    # Print result
    print("\n" + "─" * 50)
    if result["estimable"]:
        print(f"Median PFS:     {result['median_pfs']:.1f} months")
        print(f"95% CI:         ({result['ci_lower']:.1f}, {result['ci_upper']:.1f})")
    else:
        print("Median PFS:     Not estimable (survival never crosses 0.5)")
    print(f"Events:         {result['n_events']} / {result['n_total']} "
          f"({100 * result['n_events'] / result['n_total']:.1f}%)")
    print(f"CI method:      {result['ci_method']}")
    print(f"Python lifelines v{result['package_version']}")
    print("─" * 50)

    # Structured JSON output
    print("\n=== BENCHMARK OUTPUT ===")
    print(json.dumps(result, indent=2))
    print("=== END OUTPUT ===")

    # Write to file if requested
    if args.output:
        outpath = Path(args.output)
        outpath.parent.mkdir(parents=True, exist_ok=True)
        with open(outpath, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Wrote output to: {outpath}")


if __name__ == "__main__":
    main()
