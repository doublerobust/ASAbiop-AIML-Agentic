#!/usr/bin/env python3
"""TC-002 Ground Truth: Baseline Demographics Table (Python)

Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark.

Cross-validated against: R dplyr + Tplyr, SAS PROC FREQ + PROC MEANS
Dependencies: pandas, numpy
Usage: python tc_002_demographics.py --seed 42 --n 400 --output results.json
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from common.data_generation import get_adsl


def compute_demographics(adsl: pd.DataFrame, population: str = "SAFETY",
                         seed: int = None) -> dict:
    """Compute baseline demographics summary by treatment arm.

    Args:
        adsl: ADSL-like DataFrame
        population: Population filter ("SAFETY" or "ITT")

    Returns:
        dict with structured benchmark output
    """
    # Population filter
    if population == "SAFETY":
        data = adsl[adsl["SAFFL"] == "Y"].copy()
    elif population == "ITT":
        data = adsl[adsl["ITTFL"] == "Y"].copy()
    else:
        data = adsl.copy()

    n_total = len(data)

    if n_total == 0:
        raise ValueError("No subjects in the specified population")

    # ── Continuous: AGE ──
    age_stats = (
        data.groupby(["TRT01PN", "TRT01P"])["AGE"]
        .agg(["count", "mean", "std", "median", "min", "max"])
        .round(2)
        .reset_index()
    )

    # ── Categorical variables ──
    def compute_cat_freq(df, var, var_name):
        """Compute frequency table for a categorical variable by arm."""
        freq = (
            df.groupby(["TRT01PN", "TRT01P", var])
            .size()
            .reset_index(name="n")
        )
        freq["pct"] = (
            freq.groupby(["TRT01PN", "TRT01P"])["n"]
            .transform(lambda x: round(100 * x / x.sum(), 1))
        )
        freq["variable"] = var_name
        freq = freq.rename(columns={var: "level"})
        return freq

    cat_vars = {
        "SEX": "Sex",
        "RACE": "Race",
        "REGION1": "Region",
        "ECOG": "ECOG",
    }

    cat_tables = []
    for var, name in cat_vars.items():
        if var in data.columns:
            cat_tables.append(compute_cat_freq(data, var, name))

    cat_all = pd.concat(cat_tables, ignore_index=True)

    # ── Overall totals ──
    total_age = data["AGE"].agg(["count", "mean", "std", "median", "min", "max"]).round(2)

    # ── Build result ──
    result = {
        "test_case_id": "TC-002",
        "variant_id": (f"v{seed}" if seed is not None else None),
        "language": "Python",
        "package": "pandas",
        "package_version": pd.__version__,
        "population": population,
        "n_total": n_total,
        "age_by_arm": age_stats.to_dict(orient="records"),
        "categorical_by_arm": cat_all.to_dict(orient="records"),
        "total_age": total_age.to_dict(),
        "seed": seed,
    }

    return result


def main():
    parser = argparse.ArgumentParser(
        description="TC-002: Baseline Demographics Table (Python)"
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n", type=int, default=400)
    parser.add_argument("--data", type=str, default=None,
                        help="Shared ADSL CSV (for cross-language verification)")
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    print(f"TC-002: Baseline Demographics (Python) — seed={args.seed}, n={args.n}")

    # Obtain ADSL: shared CSV (cross-language) or in-language generation (smoke)
    adsl = get_adsl(data_path=args.data, seed=args.seed, n_subjects=args.n, n_arms=2)
    print(f"{'Loaded shared' if args.data else 'Generated'} ADSL with {len(adsl)} subjects")

    # Compute demographics
    result = compute_demographics(adsl, population="SAFETY", seed=args.seed)

    # Print summary
    print("\n" + "─" * 50)
    print(f"Population: {result['population']} (N={result['n_total']})")
    print("\n— Age by Arm —")
    for row in result["age_by_arm"]:
        print(f"  Arm {row['TRT01PN']}: n={row['count']}, "
              f"mean={row['mean']}, sd={row['std']}, "
              f"median={row['median']}, range=({row['min']}, {row['max']})")

    print("\n— Categorical by Arm —")
    for row in result["categorical_by_arm"]:
        print(f"  {row['variable']}: {row['level']} (Arm {row['TRT01PN']}): "
              f"{row['n']} ({row['pct']}%)")
    print("─" * 50)

    # Structured JSON
    print("\n=== BENCHMARK OUTPUT ===")
    print(json.dumps(result, indent=2, default=str))
    print("=== END OUTPUT ===")

    if args.output:
        outpath = Path(args.output)
        outpath.parent.mkdir(parents=True, exist_ok=True)
        with open(outpath, "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"Wrote output to: {outpath}")


if __name__ == "__main__":
    main()
