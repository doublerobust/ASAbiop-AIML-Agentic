#!/usr/bin/env python3
"""TC-020 Ground Truth: ORR (Objective Response Rate) by Subgroup (Python)

Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark.

Computes ORR (CR+PR rate) by pre-specified subgroups with:
  - Subgroup-level ORR (n/N, %) for each arm
  - Cochran-Mantel-Haenszel chi-square test for treatment-by-subgroup interaction
  - Forest-plot-ready output: ORR difference (Exp - Ctrl) with 95% CI per subgroup

Dependencies: pandas, numpy, scipy
Usage: python tc_020_orr_by_subgroup.py --seed 42 --n 200 --output results.json
"""

import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats


def generate_tumor_response(seed=42, n_subjects=200):
    """Generate synthetic tumor response dataset."""
    rng = np.random.default_rng(seed)

    trt = rng.choice([0, 1], size=n_subjects)
    sex = rng.choice(["Male", "Female"], size=n_subjects, p=[0.55, 0.45])
    age = np.round(rng.normal(58, 12, n_subjects)).astype(int)
    agegr1 = np.where(age < 65, "<65", ">=65")
    ecog = rng.choice([0, 1], size=n_subjects, p=[0.6, 0.4])

    # Response probability
    orr_prob = np.where(trt == 1,
                        np.where(ecog == 0, 0.45, 0.30),
                        np.where(ecog == 0, 0.25, 0.15))

    is_responder = rng.binomial(1, orr_prob)
    is_cr = np.where(is_responder == 1, rng.binomial(1, 0.3, n_subjects), 0)

    bor = np.where(is_cr == 1, "CR",
                   np.where(is_responder == 1, "PR",
                            rng.choice(["SD", "PD"], size=n_subjects, p=[0.4, 0.6])))

    aval = np.where(np.isin(bor, ["CR", "PR"]), 1, 0)

    return pd.DataFrame({
        "USUBJID": [f"SUBJ-{i+1:04d}" for i in range(n_subjects)],
        "STUDYID": "BENCHMARK-001",
        "TRT01PN": trt,
        "TRT01A": np.where(trt == 0, "Control", "Experimental"),
        "SEX": sex,
        "AGEGR1": agegr1,
        "ECOG": ecog,
        "BOR": bor,
        "AVAL": aval,
    })


def wilson_ci(x, n, conf=0.95):
    """Wilson score confidence interval for a proportion."""
    z = stats.norm.ppf(1 - (1 - conf) / 2)
    p = x / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    margin = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return center - margin, center + margin


def compute_orr_by_subgroup(data):
    """Compute ORR by subgroup with interaction tests."""
    subgroups = ["SEX", "AGEGR1", "ECOG"]
    subgroup_levels = {
        "SEX": ["Male", "Female"],
        "AGEGR1": ["<65", ">=65"],
        "ECOG": ["0", "1"],
    }

    overall_exp = data[data["TRT01PN"] == 1]
    overall_ctrl = data[data["TRT01PN"] == 0]

    orr_exp = overall_exp["AVAL"].sum() / len(overall_exp) * 100
    orr_ctrl = overall_ctrl["AVAL"].sum() / len(overall_ctrl) * 100

    ci_exp = wilson_ci(overall_exp["AVAL"].sum(), len(overall_exp))
    ci_ctrl = wilson_ci(overall_ctrl["AVAL"].sum(), len(overall_ctrl))

    overall = {
        "orr_experimental": round(orr_exp, 1),
        "orr_control": round(orr_ctrl, 1),
        "n_experimental": len(overall_exp),
        "n_control": len(overall_ctrl),
        "responders_experimental": int(overall_exp["AVAL"].sum()),
        "responders_control": int(overall_ctrl["AVAL"].sum()),
        "ci_lower_experimental": round(ci_exp[0] * 100, 1),
        "ci_upper_experimental": round(ci_exp[1] * 100, 1),
        "ci_lower_control": round(ci_ctrl[0] * 100, 1),
        "ci_upper_control": round(ci_ctrl[1] * 100, 1),
        "orr_difference": round(orr_exp - orr_ctrl, 1),
    }

    subgroup_results = []
    for sg in subgroups:
        for lvl in subgroup_levels[sg]:
            sg_exp = data[(data["TRT01PN"] == 1) & (data[sg] == lvl)]
            sg_ctrl = data[(data["TRT01PN"] == 0) & (data[sg] == lvl)]

            if len(sg_exp) == 0 or len(sg_ctrl) == 0:
                continue

            orr_e = sg_exp["AVAL"].sum() / len(sg_exp) * 100
            orr_c = sg_ctrl["AVAL"].sum() / len(sg_ctrl) * 100
            ci_e = wilson_ci(sg_exp["AVAL"].sum(), len(sg_exp))
            ci_c = wilson_ci(sg_ctrl["AVAL"].sum(), len(sg_ctrl))

            diff = orr_e - orr_c
            se_diff = np.sqrt(
                (orr_e / 100 * (1 - orr_e / 100)) / len(sg_exp) +
                (orr_c / 100 * (1 - orr_c / 100)) / len(sg_ctrl)
            ) * 100
            z = stats.norm.ppf(0.975)

            subgroup_results.append({
                "subgroup": sg,
                "level": lvl,
                "orr_experimental": round(orr_e, 1),
                "orr_control": round(orr_c, 1),
                "n_experimental": len(sg_exp),
                "n_control": len(sg_ctrl),
                "responders_experimental": int(sg_exp["AVAL"].sum()),
                "responders_control": int(sg_ctrl["AVAL"].sum()),
                "ci_lower_experimental": round(ci_e[0] * 100, 1),
                "ci_upper_experimental": round(ci_e[1] * 100, 1),
                "ci_lower_control": round(ci_c[0] * 100, 1),
                "ci_upper_control": round(ci_c[1] * 100, 1),
                "orr_difference": round(diff, 1),
                "diff_ci_lower": round(diff - z * se_diff, 1),
                "diff_ci_upper": round(diff + z * se_diff, 1),
            })

    # CMH interaction tests
    interaction_pvalues = []
    for sg in subgroups:
        # Build 2x2xK contingency table
        levels = subgroup_levels[sg]
        # Use scipy.stats.chi2_contingency on the 2x2 table pooled
        # For CMH, use stratified analysis
        try:
            from statsmodels.stats.contingency_tables import StratifiedTable
            strata = []
            for lvl in levels:
                d = data[data[sg] == lvl]
                if len(d) == 0:
                    continue
                tbl = pd.crosstab(d["TRT01PN"], d["AVAL"])
                if tbl.shape == (2, 2):
                    strata.append(tbl.values)

            if len(strata) >= 2:
                st = StratifiedTable(strata)
                cmh_p = st.test_null_odds().pvalue
                common_or = st.oddsratio_pooled
                interaction_pvalues.append({
                    "subgroup": sg,
                    "cmh_p_value": round(float(cmh_p), 4),
                    "cmh_common_or": round(float(common_or), 4),
                })
        except ImportError:
            # statsmodels not available; use scipy CMH approximation
            # Fall back to simple chi-square on treatment x response
            # stratified by subgroup
            for lvl in levels:
                d = data[data[sg] == lvl]
                if len(d) == 0:
                    continue
                tbl = pd.crosstab(d["TRT01PN"], d["AVAL"])
                if tbl.shape == (2, 2):
                    chi2, p, _, _ = stats.chi2_contingency(tbl.values)
                    interaction_pvalues.append({
                        "subgroup": f"{sg}_{lvl}",
                        "cmh_p_value": round(float(p), 4),
                        "cmh_common_or": None,
                    })

    return {
        "test_case_id": "TC-020",
        "variant_id": None,
        "language": "Python",
        "package": "scipy",
        "package_version": stats.__version__ if hasattr(stats, "__version__") else "unknown",
        "overall": overall,
        "subgroups": subgroup_results,
        "interaction_pvalues": interaction_pvalues,
        "seed": None,
    }


def main():
    parser = argparse.ArgumentParser(
        description="TC-020: ORR by Subgroup (Python)"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--n", type=int, default=200, help="Number of subjects")
    parser.add_argument("--data", type=str, default=None,
                        help="Shared tumor response CSV")
    parser.add_argument("--output", type=str, default=None, help="Output JSON path")
    args = parser.parse_args()

    print(f"TC-020: ORR by Subgroup (Python) — seed={args.seed}, n={args.n}")

    if args.data:
        data = pd.read_csv(args.data)
        print(f"Loaded shared data with {len(data)} subjects")
    else:
        data = generate_tumor_response(seed=args.seed, n_subjects=args.n)
        print(f"Generated tumor response data with {len(data)} subjects")

    result = compute_orr_by_subgroup(data)
    result["seed"] = args.seed
    result["variant_id"] = f"v{args.seed}"

    print("\n" + "─" * 50)
    o = result["overall"]
    print(f"Overall ORR:  Exp={o['orr_experimental']}%, "
          f"Ctrl={o['orr_control']}%, Diff={o['orr_difference']}%")
    print(f"Subgroups analyzed: {len(result['subgroups'])}")
    print(f"Interaction tests: {len(result['interaction_pvalues'])}")
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


if __name__ == "__main__":
    main()
