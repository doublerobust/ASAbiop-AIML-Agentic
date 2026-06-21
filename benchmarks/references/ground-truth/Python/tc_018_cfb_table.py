#!/usr/bin/env python3
"""TC-018: Change from Baseline Table
Longitudinal efficacy: baseline, change from baseline at each visit, CIs, p-values.
Output: JSON with visit-wise summary stats and treatment comparisons.

Dependencies: numpy, pandas, scipy
"""

import argparse
import json
import sys
import numpy as np
import pandas as pd
from scipy import stats


def generate_cfb(n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n_exp = n // 2
    n_ctl = n - n_exp
    trt = np.array([1] * n_exp + [0] * n_ctl)
    rng.shuffle(trt)

    visits = ["BASELINE", "WEEK_6", "WEEK_12", "WEEK_18", "WEEK_24"]
    baseline = rng.normal(50, 15, size=n)

    all_rows = []
    for idx, vn in enumerate(visits):
        if vn == "BASELINE":
            vals = baseline.copy()
            chg = np.zeros(n)
        else:
            weeks = int(vn.split("_")[1])
            change = np.where(
                trt == 1,
                -0.8 * weeks + rng.normal(0, 8, size=n),
                -0.1 * weeks + rng.normal(0, 8, size=n),
            )
            vals = baseline + change
            chg = change

        for i in range(n):
            all_rows.append({
                "USUBJID": f"SUB{i:04d}",
                "TRT01PN": int(trt[i]),
                "TRT01A": "Experimental" if trt[i] == 1 else "Control",
                "AVISIT": vn,
                "AVISITN": idx,
                "AVAL": round(float(vals[i]), 2),
                "CHG": round(float(chg[i]), 2),
                "BASE": round(float(baseline[i]), 2),
            })

    return pd.DataFrame(all_rows)


def summarize_chg(d: pd.DataFrame) -> dict:
    n = len(d)
    if n == 0:
        return {"n": 0, "mean_chg": 0, "sd_chg": 0, "median_chg": 0,
                "se_chg": 0, "ci_lower": 0, "ci_upper": 0,
                "mean_aval": 0, "sd_aval": 0}
    chg = d["CHG"].values
    aval = d["AVAL"].values
    sd_chg = float(np.std(chg, ddof=1)) if n > 1 else 0.0
    se_chg = sd_chg / np.sqrt(n) if n > 0 else 0.0
    return {
        "n": int(n),
        "mean_chg": round(float(np.mean(chg)), 4),
        "sd_chg": round(sd_chg, 4),
        "median_chg": round(float(np.median(chg)), 4),
        "se_chg": round(se_chg, 4),
        "ci_lower": round(float(np.mean(chg) - 1.96 * se_chg), 4),
        "ci_upper": round(float(np.mean(chg) + 1.96 * se_chg), 4),
        "mean_aval": round(float(np.mean(aval)), 4),
        "sd_aval": round(float(np.std(aval, ddof=1)), 4) if n > 1 else 0.0,
    }


def main():
    parser = argparse.ArgumentParser(description="TC-018: Change from Baseline Table")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--output", type=str, default="")
    parser.add_argument("--data", type=str, default="")
    args = parser.parse_args()

    print(f"[{pd.Timestamp.now()}] TC-018 CFB Table | seed={args.seed} n={args.n}")

    if args.data:
        df = pd.read_csv(args.data)
    else:
        df = generate_cfb(args.n, args.seed)

    visits_sorted = df.sort_values("AVISITN")["AVISIT"].unique()

    visit_results = {}
    for vn in visits_sorted:
        vd = df[df["AVISIT"] == vn]
        exp_d = vd[vd["TRT01PN"] == 1]
        ctl_d = vd[vd["TRT01PN"] == 0]

        p_val = None
        if vn != "BASELINE" and len(exp_d) > 1 and len(ctl_d) > 1:
            tt = stats.ttest_ind(exp_d["CHG"].values, ctl_d["CHG"].values)
            p_val = round(float(tt.pvalue), 6)
        elif vn == "BASELINE" and len(exp_d) > 1 and len(ctl_d) > 1:
            tt = stats.ttest_ind(exp_d["AVAL"].values, ctl_d["AVAL"].values)
            p_val = round(float(tt.pvalue), 6)

        visit_results[vn] = {
            "visit": vn,
            "experimental": summarize_chg(exp_d),
            "control": summarize_chg(ctl_d),
            "p_value": p_val,
        }

    n_subj = df["USUBJID"].nunique()
    result = {
        "tc_id": "TC-018",
        "tc_name": "Change from Baseline Table",
        "metadata": {
            "n_total": int(n_subj),
            "n_experimental": int(df[df["TRT01PN"] == 1]["USUBJID"].nunique()),
            "n_control": int(df[df["TRT01PN"] == 0]["USUBJID"].nunique()),
            "population": "ITT",
            "visits": list(visits_sorted),
            "endpoint": "Tumor Size",
            "endpoint_unit": "mm",
            "python_version": sys.version.split()[0],
        },
        "visits": visit_results,
    }

    js = json.dumps(result, indent=2)
    if args.output:
        with open(args.output, "w") as f:
            f.write(js)
        print(f"Written: {args.output}")
    else:
        print(js)


if __name__ == "__main__":
    main()
