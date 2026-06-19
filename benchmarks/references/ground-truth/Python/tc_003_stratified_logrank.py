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
import lifelines
from scipy import stats

from common.data_generation import get_adtte


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

    data = data.reset_index(drop=True)
    event = (1 - data["CNSR"]).astype(int)
    groups = sorted(data["TRT01PN"].unique())
    df = len(groups) - 1

    # -------------------------------------------------------------------
    # Stratified log-rank computed manually to MATCH R survival::survdiff().
    # BUGFIX: lifelines.multivariate_logrank_test has NO `strata=` argument
    # (the previous code passed one, causing a TypeError) and lifelines
    # provides no built-in stratified log-rank. The stratified Mantel-Haenszel
    # log-rank sums each stratum's observed-minus-expected vector and variance
    # matrix, then forms chi^2 = (sum O-E)' (sum V)^- (sum O-E). For a two-arm
    # comparison this reduces to (sum(O1-E1))^2 / sum(V1), with equal weight
    # per stratum — identical to R's default strata() behaviour.
    # -------------------------------------------------------------------
    def stratum_logrank_oe_v(times, ev, grp, ref_group):
        """Return (O-E, V) for `ref_group` within one stratum (log-rank)."""
        oe = 0.0
        var = 0.0
        for t in np.unique(times[ev == 1]):
            at_risk = times >= t
            n = int(at_risk.sum())
            d = int(((times == t) & (ev == 1)).sum())
            if n <= 1 or d == 0:
                continue
            n_ref = int((at_risk & (grp == ref_group)).sum())
            d_ref = int(((times == t) & (ev == 1) & (grp == ref_group)).sum())
            exp_ref = d * n_ref / n
            oe += d_ref - exp_ref
            # Hypergeometric variance of the count in ref group
            var += (d * (n_ref / n) * (1 - n_ref / n) * (n - d) / (n - 1))
        return oe, var

    strata_key = data[strata_vars].astype(str).agg("|".join, axis=1)
    ref_group = groups[0]
    total_oe = 0.0
    total_var = 0.0
    n_strata_total = 0
    n_strata_with_events = 0

    for _, idx in data.groupby(strata_key).groups.items():
        n_strata_total += 1
        s_times = data.loc[idx, "AVAL"].to_numpy()
        s_event = event.loc[idx].to_numpy()
        s_group = data.loc[idx, "TRT01PN"].to_numpy()
        if s_event.sum() == 0:
            continue  # stratum with no events contributes nothing (matches R)
        n_strata_with_events += 1
        oe, var = stratum_logrank_oe_v(s_times, s_event, s_group, ref_group)
        total_oe += oe
        total_var += var

    chi_square = (total_oe ** 2) / total_var if total_var > 0 else 0.0
    p_value = float(stats.chi2.sf(chi_square, df))

    output = {
        "test_case_id": "TC-003",
        "variant_id": f"v{seed}",
        "language": "Python",
        "package": "lifelines+scipy",
        "package_version": lifelines.__version__,
        "chi_square": round(float(chi_square), 4),
        "df": int(df),
        "p_value": round(float(p_value), 6),
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
    parser.add_argument("--data", type=str, default=None,
                       help="Shared ADTTE CSV (for cross-language verification)")
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    strata_vars = [v.strip() for v in args.strata.split(",")]
    seed = args.seed

    print(f"TC-003: Stratified Log-Rank Test (Python) — seed={seed}, n={args.n}")
    print(f"Strata: {', '.join(strata_vars)}")

    # Obtain ADTTE: shared CSV (cross-language) or in-language generation (smoke)
    adtte = get_adtte(data_path=args.data, seed=seed, n_subjects=args.n, n_arms=2, hr=0.75)
    print(f"{'Loaded shared' if args.data else 'Generated'} ADTTE with {len(adtte)} subjects")

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
