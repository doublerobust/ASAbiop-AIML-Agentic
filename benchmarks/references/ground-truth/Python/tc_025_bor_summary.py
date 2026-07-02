#!/usr/bin/env python3
"""TC-025 Ground Truth: Best Overall Response (BOR) Summary Table

Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark.

BOR per RECIST 1.1: CR, PR, SD, PD, NE (Not Evaluable)
This test case evaluates:
  1. Correct BOR distribution by treatment arm
  2. Response rates (ORR = CR+PR, DCR = CR+PR+SD)
  3. Difference in response proportions (Fisher exact / chi-square)
  4. 95% CI for response rates (Clopper-Pearson exact)

Dependencies: numpy, pandas, scipy, statsmodels (optional)
Usage: python tc_025_bor_summary.py --seed 42 --n 200 --output results.json
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


# ─────────────────────────────────────────────────────
# Argument parsing
# ─────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="TC-025 BOR Summary Table")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--data", type=str, default=None)
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--ars-output", type=str, default=None)
    return parser.parse_args()


# ─────────────────────────────────────────────────────
# Generate BOR data
# ─────────────────────────────────────────────────────

def generate_bor_data(seed=42, n_subjects=200):
    """Generate synthetic BOR data per RECIST 1.1."""
    rng = np.random.default_rng(seed)
    trt = rng.integers(0, 2, size=n_subjects)

    bor = []
    for a in trt:
        if a == 0:
            # Control: CR 2%, PR 18%, SD 45%, PD 30%, NE 5%
            bor.append(rng.choice(
                ["CR", "PR", "SD", "PD", "NE"],
                p=[0.02, 0.18, 0.45, 0.30, 0.05]
            ))
        else:
            # Active: CR 8%, PR 35%, SD 35%, PD 15%, NE 7%
            bor.append(rng.choice(
                ["CR", "PR", "SD", "PD", "NE"],
                p=[0.08, 0.35, 0.35, 0.15, 0.07]
            ))

    sex = rng.choice(["M", "F"], size=n_subjects, p=[0.55, 0.45])
    age = np.round(rng.normal(58, 12, size=n_subjects)).astype(int)
    agegr1 = np.where(age < 65, "<65", ">=65")
    ecog = rng.choice([0, 1], size=n_subjects, p=[0.6, 0.4])

    df = pd.DataFrame({
        "USUBJID": [f"SUBJ-{i+1:04d}" for i in range(n_subjects)],
        "STUDYID": "BENCHMARK-001",
        "TRT01PN": trt,
        "TRT01P": np.where(trt == 0, "Placebo", "Active"),
        "BOR": bor,
        "ITTFL": np.where(rng.random(n_subjects) < 0.95, "Y", "N"),
        "SAFFL": np.where(rng.random(n_subjects) < 0.98, "Y", "N"),
        "SEX": sex,
        "AGEGR1": agegr1,
        "ECOG": ecog,
    })
    return df


# ─────────────────────────────────────────────────────
# Clopper-Pearson exact CI
# ─────────────────────────────────────────────────────

def clopper_pearson_ci(x, n, conf=0.95):
    """Compute Clopper-Pearson exact binomial CI."""
    from scipy.stats import beta
    alpha = 1 - conf
    lower = 0.0 if x == 0 else beta.ppf(alpha / 2, x, n - x + 1)
    upper = 1.0 if x == n else beta.ppf(1 - alpha / 2, x + 1, n - x)
    return lower, upper


# ─────────────────────────────────────────────────────
# TC-025 Core Computation
# ─────────────────────────────────────────────────────

def compute_bor_summary(data):
    """Compute BOR summary: distribution, ORR, DCR, difference tests."""
    data_itt = data[data["ITTFL"] == "Y"].copy()

    results = {}
    for arm in [0, 1]:
        arm_data = data_itt[data_itt["TRT01PN"] == arm]
        n_total = len(arm_data)

        n_cr = int((arm_data["BOR"] == "CR").sum())
        n_pr = int((arm_data["BOR"] == "PR").sum())
        n_sd = int((arm_data["BOR"] == "SD").sum())
        n_pd = int((arm_data["BOR"] == "PD").sum())
        n_ne = int((arm_data["BOR"] == "NE").sum())

        n_eval = n_total - n_ne

        n_orr = n_cr + n_pr
        orr_rate = n_orr / n_total if n_total > 0 else 0
        orr_ci = clopper_pearson_ci(n_orr, n_total)

        n_dcr = n_cr + n_pr + n_sd
        dcr_rate = n_dcr / n_total if n_total > 0 else 0
        dcr_ci = clopper_pearson_ci(n_dcr, n_total)

        results[str(arm)] = {
            "arm": arm,
            "n_total": n_total,
            "n_evaluable": n_eval,
            "bor_counts": {
                "CR": n_cr, "PR": n_pr, "SD": n_sd, "PD": n_pd, "NE": n_ne
            },
            "orr_n": n_orr,
            "orr_rate": round(orr_rate, 4),
            "orr_ci_lower": round(orr_ci[0], 4),
            "orr_ci_upper": round(orr_ci[1], 4),
            "dcr_n": n_dcr,
            "dcr_rate": round(dcr_rate, 4),
            "dcr_ci_lower": round(dcr_ci[0], 4),
            "dcr_ci_upper": round(dcr_ci[1], 4),
        }

    # Difference in ORR
    orr_exp = results["1"]["orr_rate"]
    orr_ctrl = results["0"]["orr_rate"]
    orr_diff = orr_exp - orr_ctrl

    # Fisher exact test
    fisher_table = [
        [results["1"]["orr_n"], results["1"]["n_total"] - results["1"]["orr_n"]],
        [results["0"]["orr_n"], results["0"]["n_total"] - results["0"]["orr_n"]]
    ]
    _, fisher_p = stats.fisher_exact(fisher_table)

    # Chi-square test
    chi2, chi_p, _, _ = stats.chi2_contingency(fisher_table, correction=False)

    # Wald CI for difference
    n1 = results["1"]["n_total"]
    n0 = results["0"]["n_total"]
    se_diff = np.sqrt(orr_exp * (1 - orr_exp) / n1 + orr_ctrl * (1 - orr_ctrl) / n0) if n1 > 0 and n0 > 0 else 0
    diff_ci_lower = round(orr_diff - 1.96 * se_diff, 4)
    diff_ci_upper = round(orr_diff + 1.96 * se_diff, 4)

    # BOR distribution
    bor_dist = {}
    for bor_val in ["CR", "PR", "SD", "PD", "NE"]:
        n_ctrl = int(((data_itt["TRT01PN"] == 0) & (data_itt["BOR"] == bor_val)).sum())
        n_exp = int(((data_itt["TRT01PN"] == 1) & (data_itt["BOR"] == bor_val)).sum())
        bor_dist[bor_val] = {"BOR": bor_val, "n_control": n_ctrl, "n_experimental": n_exp}

    return {
        "by_arm": results,
        "orr_difference": round(orr_diff, 4),
        "orr_diff_ci_lower": diff_ci_lower,
        "orr_diff_ci_upper": diff_ci_upper,
        "fisher_exact_p": round(fisher_p, 6),
        "chi_square_p": round(chi_p, 6),
        "bor_distribution": bor_dist,
    }


# ─────────────────────────────────────────────────────
# ARS Output Envelope
# ─────────────────────────────────────────────────────

def write_ars_output(results, filepath):
    ars = {
        "reportingEvent": {
            "id": "TC-025-BOR",
            "name": "Best Overall Response Summary",
            "version": "1.0"
        },
        "analysisResults": [
            {
                "id": "TC-025-BOR-001",
                "analysisId": "BOR-SUMMARY",
                "method": "ClopperPearson",
                "purpose": "Summarize best overall response per RECIST 1.1",
                "results": results
            }
        ],
        "referencingMetadata": {
            "dataset": "ADRS",
            "paramcd": "BOR",
            "population": "ITT"
        }
    }
    with open(filepath, "w") as f:
        json.dump(ars, f, indent=2)
    print(f"Wrote ARS output to: {filepath}")


# ─────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────

def main():
    args = parse_args()

    if args.data:
        data = pd.read_csv(args.data)
    else:
        data = generate_bor_data(seed=args.seed, n_subjects=args.n)

    result = {
        "test_case_id": "TC-025",
        "endpoint": "Best Overall Response",
        "population": "ITT",
        "summary": compute_bor_summary(data),
        "language": "Python",
        "version": "1.0"
    }

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Wrote output to: {args.output}")
    else:
        print("\n=== BENCHMARK OUTPUT ===")
        print(json.dumps(result, indent=2))
        print("=== END OUTPUT ===")

    if args.ars_output:
        write_ars_output(result, args.ars_output)


if __name__ == "__main__":
    main()
