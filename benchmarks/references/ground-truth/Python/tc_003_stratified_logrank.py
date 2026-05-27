#!/usr/bin/env python3
"""TC-003 Ground Truth: Stratified Log-Rank Test (Python)

Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark.

Cross-validated against: R survival::survdiff(), SAS PROC LIFETEST STRATA
Dependencies: pandas, numpy, lifelines (>= 0.29.0)
Usage: python tc_003_stratified_logrank.py --seed 42 --n 400 --output results.json
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from lifelines import multivariate_logrank_test

from common.data_generation import generate_adtte


def compute_stratified_logrank(
    adtte: pd.DataFrame,
    strata_vars: list = None,
    population: str = "ITT",
    seed: int = 42,
) -> dict:
    """Perform stratified log-rank test comparing two treatment arms.

    Args:
        adtte: ADTTE-like DataFrame
        strata_vars: List of stratification variable column names
        population: Population filter
        seed: Random seed for provenance

    Returns:
        dict with structured benchmark output
    """
    if strata_vars is None:
        strata_vars = ["SEX", "ECOG"]

    # Population filter
    if population == "ITT":
        data = adtte[adtte["ITTFL"] == "Y"].copy()
    else:
        data = adtte.copy()

    if len(data) == 0:
        raise ValueError("No subjects in the specified population")

    # Check both arms exist
    arms = sorted(data["TRT01PN"].unique())
    if len(arms) < 2:
        raise ValueError(f"Need 2 arms for comparison; found: {arms}")

    n_total = len(data)
    n_events = int((1 - data["CNSR"]).sum())

    # Create strata interaction column (combine all strata variables)
    # lifelines multivariate_logrank_test handles strata natively
    # but we need to ensure proper stratification
    data = data.reset_index(drop=True)

    # For lifelines, we pass the strata variables; it handles equal weighting
    result = multivariate_logrank_test(
        durations=data["AVAL"],
        groups=data["TRT01PN"],
        event_observed=1 - data["CNSR"],
        strata=data[strata_vars],
    )

    # Count non-empty strata
    strata_combos = data.groupby(strata_vars).size()
    n_strata_total = len(strata_combos)
    n_strata_with_events = data.groupby(strata_vars).apply(
        lambda x: (1 - x["CNSR"]).sum() > 0
    ).sum()

    output = {
        "test_case_id": "TC-003",
        "variant_id": f"v{seed}",
        "language": "Python",
        "package": "lifelines",
        "package_version": "0.29.0",
        "chi_square": round(float(result.test_statistic), 4),
        "df": int(result.degrees_of_freedom),
        "p_value": round(float(result.p_value), 6),
        "n_total": n_total,
        "n_events": n_events,
        "strata_variables": strata_vars,
        "n_strata_total": int(n_strata_total),
        "n_strata_with_events": int(n_strata_with_events),
        "stratification_method": "equal_weight_per_stratum",
        "seed": seed,
    }

    return output


def main():
    parser = argparse.ArgumentParser(
        description="TC-003: Stratified Log-Rank Test (Python)"
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n", type=int, default=400)
    parser.add_argument("--strata", type=str, default="SEX,ECOG",
                       help="Comma-separated stratification variables")
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    strata_vars = [v.strip() for v in args.strata.split(",")]
    seed = args.seed

    print(f"TC-003: Stratified Log-Rank Test (Python) — seed={seed}, n={args.n}")
    print(f"Strata: {', '.join(strata_vars)}")

    # Generate synthetic ADTTE (2 arms, HR=0.75)
    adtte = generate_adtte(seed=seed, n_subjects=args.n, n_arms=2, hr=0.75)
    print(f"Generated ADTTE with {len(adtte)} subjects")

    # Compute stratified log-rank
    result = compute_stratified_logrank(
        adtte, strata_vars=strata_vars, seed=seed
    )

    # Print result
    print("\n" + "─" * 50)
    print("Method: Stratified log-rank test")
    print(f"Stratification: {', '.join(result['strata_variables'])}")
    print(f"Chi-square:     {result['chi_square']:.4f}")
    print(f"DF:             {result['df']}")
    print(f"p-value:        {result['p_value']:.6f}")
    print(f"Total N:        {result['n_total']} ({result['n_events']} events)")
    print(f"Strata:         {result['n_strata_total']} total, "
          f"{result['n_strata_with_events']} with events")
    print(f"Method:         {result['stratification_method']}")
    print(f"Python lifelines v{result['package_version']}")
    print("─" * 50)

    # Structured JSON
    print("\n=== BENCHMARK OUTPUT ===")
    print(json.dumps(result, indent=2))
    print("=== END OUTPUT ===")

    if args.output:
        outpath = Path(args.output)
        outpath.parent.mkdir(parents=True, exist_ok=True)
        with open(outpath, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Wrote output to: {outpath}")


if __name__ == "__main__":
    main()
