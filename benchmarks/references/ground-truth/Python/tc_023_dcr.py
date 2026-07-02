#!/usr/bin/env python3
"""TC-023 Ground Truth: Disease Control Rate (DCR) (Python)

Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark.

DCR is defined as the proportion of subjects with disease control,
where disease control = CR + PR + SD (best overall response).

Key difference from TC-020 (ORR):
  ORR (TC-020): CR + PR rate
  DCR (TC-023): CR + PR + SD rate (broader benefit measure)

This tests:
  1. Correct response categorization (CR/PR/SD = disease control)
  2. Binomial proportion CI (Wilson score interval)
  3. Risk difference with CI between arms
  4. Cross-TFL consistency: DCR >= ORR (every responder also has disease control)

Dependencies: pandas, numpy, scipy
Usage: python tc_023_dcr.py --seed 42 --n 200 --output results.json
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


def generate_tumor_response(seed=42, n_subjects=200):
    """Generate synthetic tumor response dataset (same structure as TC-020).

    Ensures cross-TFL consistency between ORR and DCR.
    """
    rng = np.random.default_rng(seed)

    trt = rng.choice([0, 1], size=n_subjects)
    sex = rng.choice(["Male", "Female"], size=n_subjects, p=[0.55, 0.45])
    age = np.round(rng.normal(58, 12, n_subjects)).astype(int)
    agegr1 = np.where(age < 65, "<65", ">=65")
    ecog = rng.choice([0, 1], size=n_subjects, p=[0.6, 0.4])

    # Response probability — same as TC-020 for cross-TFL consistency
    orr_prob = np.where(trt == 1,
                        np.where(ecog == 0, 0.45, 0.30),
                        np.where(ecog == 0, 0.25, 0.15))

    is_responder = rng.binomial(1, orr_prob)
    is_cr = np.where(is_responder == 1, rng.binomial(1, 0.3, n_subjects), 0)

    bor = np.where(is_cr == 1, "CR",
                   np.where(is_responder == 1, "PR",
                            rng.choice(["SD", "PD"], size=n_subjects, p=[0.4, 0.6])))

    aval_orr = np.where(np.isin(bor, ["CR", "PR"]), 1, 0)
    aval_dcr = np.where(np.isin(bor, ["CR", "PR", "SD"]), 1, 0)

    ittfl = np.where(rng.random(n_subjects) < 0.95, "Y", "N")

    return pd.DataFrame({
        "USUBJID": [f"SUBJ-{i+1:04d}" for i in range(n_subjects)],
        "STUDYID": "BENCHMARK-001",
        "TRT01PN": trt,
        "TRT01A": np.where(trt == 0, "Control", "Experimental"),
        "SEX": sex,
        "AGEGR1": agegr1,
        "ECOG": ecog,
        "BOR": bor,
        "AVAL_ORR": aval_orr,
        "AVAL_DCR": aval_dcr,
        "ITTFL": ittfl,
    })


def wilson_ci(x, n, conf=0.95):
    """Wilson score confidence interval for a proportion."""
    z = stats.norm.ppf(1 - (1 - conf) / 2)
    p = x / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    margin = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return center - margin, center + margin


def compute_dcr(data):
    """Compute Disease Control Rate by subgroup with Wilson CI."""
    # Filter to ITT population
    data = data[data["ITTFL"] == "Y"].copy()

    subgroups = ["SEX", "AGEGR1", "ECOG"]
    subgroup_levels = {
        "SEX": ["Male", "Female"],
        "AGEGR1": ["<65", ">=65"],
        "ECOG": [0, 1],
    }

    overall_exp = data[data["TRT01PN"] == 1]
    overall_ctrl = data[data["TRT01PN"] == 0]

    # Overall DCR
    dcr_exp = overall_exp["AVAL_DCR"].sum() / len(overall_exp) * 100
    dcr_ctrl = overall_ctrl["AVAL_DCR"].sum() / len(overall_ctrl) * 100

    ci_exp = wilson_ci(overall_exp["AVAL_DCR"].sum(), len(overall_exp))
    ci_ctrl = wilson_ci(overall_ctrl["AVAL_DCR"].sum(), len(overall_ctrl))

    # Risk difference with normal approximation CI
    diff = dcr_exp - dcr_ctrl
    se_diff = np.sqrt(
        (dcr_exp / 100 * (1 - dcr_exp / 100)) / len(overall_exp) +
        (dcr_ctrl / 100 * (1 - dcr_ctrl / 100)) / len(overall_ctrl)
    ) * 100
    z = stats.norm.ppf(0.975)
    diff_ci_lower = round(diff - z * se_diff, 1)
    diff_ci_upper = round(diff + z * se_diff, 1)

    overall = {
        "dcr_experimental": round(dcr_exp, 1),
        "dcr_control": round(dcr_ctrl, 1),
        "n_experimental": len(overall_exp),
        "n_control": len(overall_ctrl),
        "disease_controlled_exp": int(overall_exp["AVAL_DCR"].sum()),
        "disease_controlled_ctrl": int(overall_ctrl["AVAL_DCR"].sum()),
        "ci_lower_experimental": round(ci_exp[0] * 100, 1),
        "ci_upper_experimental": round(ci_exp[1] * 100, 1),
        "ci_lower_control": round(ci_ctrl[0] * 100, 1),
        "ci_upper_control": round(ci_ctrl[1] * 100, 1),
        "dcr_difference": round(diff, 1),
        "diff_ci_lower": diff_ci_lower,
        "diff_ci_upper": diff_ci_upper,
    }

    # Subgroup-level DCR
    subgroup_results = []
    for sg in subgroups:
        for lvl in subgroup_levels[sg]:
            sg_exp = data[(data["TRT01PN"] == 1) & (data[sg] == lvl)]
            sg_ctrl = data[(data["TRT01PN"] == 0) & (data[sg] == lvl)]

            if len(sg_exp) == 0 or len(sg_ctrl) == 0:
                continue

            dcr_e = sg_exp["AVAL_DCR"].sum() / len(sg_exp) * 100
            dcr_c = sg_ctrl["AVAL_DCR"].sum() / len(sg_ctrl) * 100
            ci_e = wilson_ci(sg_exp["AVAL_DCR"].sum(), len(sg_exp))
            ci_c = wilson_ci(sg_ctrl["AVAL_DCR"].sum(), len(sg_ctrl))

            sg_diff = dcr_e - dcr_c
            sg_se = np.sqrt(
                (dcr_e / 100 * (1 - dcr_e / 100)) / len(sg_exp) +
                (dcr_c / 100 * (1 - dcr_c / 100)) / len(sg_ctrl)
            ) * 100

            subgroup_results.append({
                "subgroup": sg,
                "level": lvl,
                "dcr_experimental": round(dcr_e, 1),
                "dcr_control": round(dcr_c, 1),
                "n_experimental": len(sg_exp),
                "n_control": len(sg_ctrl),
                "disease_controlled_exp": int(sg_exp["AVAL_DCR"].sum()),
                "disease_controlled_ctrl": int(sg_ctrl["AVAL_DCR"].sum()),
                "ci_lower_experimental": round(ci_e[0] * 100, 1),
                "ci_upper_experimental": round(ci_e[1] * 100, 1),
                "ci_lower_control": round(ci_c[0] * 100, 1),
                "ci_upper_control": round(ci_c[1] * 100, 1),
                "dcr_difference": round(sg_diff, 1),
                "diff_ci_lower": round(sg_diff - z * sg_se, 1),
                "diff_ci_upper": round(sg_diff + z * sg_se, 1),
            })

    # BOR distribution by arm
    bor_distribution = []
    for arm_val in [1, 0]:
        arm_label = "Experimental" if arm_val == 1 else "Control"
        arm_data = data[data["TRT01PN"] == arm_val]
        for bor_cat in ["CR", "PR", "SD", "PD"]:
            n_cat = int((arm_data["BOR"] == bor_cat).sum())
            bor_distribution.append({
                "arm": arm_label,
                "bor": bor_cat,
                "n": n_cat,
                "pct": round(n_cat / len(arm_data) * 100, 1),
            })

    return {
        "test_case_id": "TC-023",
        "variant_id": None,
        "language": "Python",
        "package": "scipy",
        "package_version": stats.__version__ if hasattr(stats, "__version__") else "unknown",
        "overall": overall,
        "subgroups": subgroup_results,
        "bor_distribution": bor_distribution,
        "endpoint": "DCR",
        "population": "ITT",
        "dcr_definition": "CR + PR + SD",
        "seed": None,
    }


def main():
    parser = argparse.ArgumentParser(
        description="TC-023: Disease Control Rate (DCR) (Python)"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--n", type=int, default=200, help="Number of subjects")
    parser.add_argument("--data", type=str, default=None,
                        help="Shared tumor response CSV")
    parser.add_argument("--output", type=str, default=None, help="Output JSON path")
    parser.add_argument("--ars-output", type=str, default=None,
                        help="ARS-compatible output JSON path")
    args = parser.parse_args()

    print(f"TC-023: Disease Control Rate (Python) — seed={args.seed}, n={args.n}")

    if args.data:
        data = pd.read_csv(args.data)
        print(f"Loaded shared data with {len(data)} subjects")
    else:
        data = generate_tumor_response(seed=args.seed, n_subjects=args.n)
        print(f"Generated tumor response data with {len(data)} subjects")

    result = compute_dcr(data)
    result["seed"] = args.seed
    result["variant_id"] = f"v{args.seed}"

    print("\n" + "─" * 50)
    print(f"DCR Definition: {result['dcr_definition']}")
    o = result["overall"]
    print(f"Overall DCR:   Exp={o['dcr_experimental']}%, "
          f"Ctrl={o['dcr_control']}%, Diff={o['dcr_difference']}%")
    print(f"95% CI (Exp):   ({o['ci_lower_experimental']}, {o['ci_upper_experimental']})")
    print(f"95% CI (Ctrl):  ({o['ci_lower_control']}, {o['ci_upper_control']})")
    print(f"Subgroups analyzed: {len(result['subgroups'])}")
    print("─" * 50)

    print("\n=== BENCHMARK OUTPUT ===")
    print(json.dumps(result, indent=2, default=str))
    print("=== END OUTPUT ===")

    if args.output:
        outpath = Path(args.output)
        outpath.parent.mkdir(parents=True, exist_ok=True)
        with open(outpath, "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"Wrote output to: {outpath}")

    if args.ars_output:
        o = result["overall"]
        ars_envelope = {
            "ars_version": "1.0",
            "analysisResult": {
                "id": "TC-023",
                "version": "1.0",
                "analysisReason": "Secondary efficacy endpoint: disease control rate",
                "analysisMethod": {
                    "name": "Binomial proportion with Wilson CI",
                    "codeTemplate": "sum(BOR in ['CR','PR','SD']) / n * 100",
                    "parameters": {
                        "ci_method": "Wilson score",
                        "alpha": 0.05,
                        "dcr_definition": "CR + PR + SD",
                        "risk_difference_ci": "normal approximation",
                    },
                },
                "analysisVariables": [
                    {"name": "BOR", "dataset": "ADRS", "role": "best overall response"},
                    {"name": "TRT01A", "dataset": "ADSL", "role": "treatment"},
                    {"name": "ITTFL", "dataset": "ADSL", "role": "population flag"},
                ],
                "analysisPopulation": {"name": "ITT", "filter": "ITTFL = 'Y'"},
                "analysisDataset": "ADRS",
                "resultGroups": [
                    {"id": "Experimental",
                     "n": o["n_experimental"],
                     "events": o["disease_controlled_exp"]},
                    {"id": "Control",
                     "n": o["n_control"],
                     "events": o["disease_controlled_ctrl"]},
                ],
                "documentation": "DCR = CR+PR+SD rate with Wilson CI; risk difference with normal approximation CI",
                "analysisResultsData": {
                    "statistics": [
                        {"name": "dcr_experimental", "value": o["dcr_experimental"], "unit": "percent"},
                        {"name": "dcr_control", "value": o["dcr_control"], "unit": "percent"},
                        {"name": "dcr_difference", "value": o["dcr_difference"], "unit": "percent"},
                        {"name": "ci_lower_experimental", "value": o["ci_lower_experimental"]},
                        {"name": "ci_upper_experimental", "value": o["ci_upper_experimental"]},
                        {"name": "ci_lower_control", "value": o["ci_lower_control"]},
                        {"name": "ci_upper_control", "value": o["ci_upper_control"]},
                        {"name": "diff_ci_lower", "value": o["diff_ci_lower"]},
                        {"name": "diff_ci_upper", "value": o["diff_ci_upper"]},
                        {"name": "n_experimental", "value": o["n_experimental"]},
                        {"name": "n_control", "value": o["n_control"]},
                    ]
                },
            },
        }
        ars_path = Path(args.ars_output)
        ars_path.parent.mkdir(parents=True, exist_ok=True)
        with open(ars_path, "w") as f:
            json.dump(ars_envelope, f, indent=2, default=str)
        print(f"Wrote ARS-compatible output to: {ars_path}")


if __name__ == "__main__":
    main()
