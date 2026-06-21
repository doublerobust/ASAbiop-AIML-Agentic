#!/usr/bin/env python3
"""TC-017: Laboratory Shift Table
Baseline vs worst post-baseline lab category shifts (LOW/NORMAL/HIGH).
Output: JSON with shift counts per cell, overall percentages.

Dependencies: numpy, pandas
"""

import argparse
import json
import sys
import numpy as np
import pandas as pd


def generate_labs(n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n_exp = n // 2
    n_ctl = n - n_exp
    trt = np.array([1] * n_exp + [0] * n_ctl)
    rng.shuffle(trt)

    # Baseline hemoglobin (g/L)
    baseline_hgb = rng.normal(140, 18, size=n)

    # 3 post-baseline visits; worst = min for hemoglobin
    post_hgb = np.empty(n)
    for i in range(n):
        effect = -5 if trt[i] == 1 else 0
        vals = rng.normal(baseline_hgb[i] + effect, 10, size=3)
        post_hgb[i] = vals.min()

    # Categorize
    def categorize(x_arr):
        cats = np.empty(len(x_arr), dtype=object)
        cats[x_arr < 120] = "LOW"
        cats[(x_arr >= 120) & (x_arr <= 160)] = "NORMAL"
        cats[x_arr > 160] = "HIGH"
        return cats

    bl_cat = categorize(baseline_hgb)
    post_cat = categorize(post_hgb)

    return pd.DataFrame({
        "USUBJID": [f"SUB{i:04d}" for i in range(1, n + 1)],
        "TRT01PN": trt.astype(int),
        "TRT01A": np.where(trt == 1, "Experimental", "Control"),
        "LBTEST": "Hemoglobin",
        "BL_VAL": np.round(baseline_hgb, 2),
        "BL_CAT": bl_cat,
        "POST_VAL": np.round(post_hgb, 2),
        "POST_CAT": post_cat,
    })


def categorize_val(x):
    if x < 120:
        return "LOW"
    elif x > 160:
        return "HIGH"
    return "NORMAL"


def build_shift(d: pd.DataFrame) -> dict:
    cats = ["LOW", "NORMAL", "HIGH"]
    counts = {bl: {post: 0 for post in cats} for bl in cats}

    for _, row in d.iterrows():
        bl = row["BL_CAT"]
        post = row["POST_CAT"]
        if bl in cats and post in cats:
            counts[bl][post] += 1

    n_total = sum(counts[bl][post] for bl in cats for post in cats)
    percentages = {}
    for bl in cats:
        percentages[bl] = {}
        for post in cats:
            percentages[bl][post] = round(counts[bl][post] / n_total * 100, 2) if n_total > 0 else 0.0

    return {
        "counts": counts,
        "percentages": percentages,
        "n_total": int(n_total),
        "n_stable_normal": int(counts["NORMAL"]["NORMAL"]),
        "n_low_to_normal": int(counts["LOW"]["NORMAL"]),
        "n_normal_to_low": int(counts["NORMAL"]["LOW"]),
        "n_normal_to_high": int(counts["NORMAL"]["HIGH"]),
        "n_high_to_normal": int(counts["HIGH"]["NORMAL"]),
    }


def main():
    parser = argparse.ArgumentParser(description="TC-017: Lab Shift Table")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--output", type=str, default="")
    parser.add_argument("--data", type=str, default="")
    args = parser.parse_args()

    print(f"[{pd.Timestamp.now()}] TC-017 Lab Shift Table | seed={args.seed} n={args.n}")

    if args.data:
        df = pd.read_csv(args.data)
    else:
        df = generate_labs(args.n, args.seed)

    exp_df = df[df["TRT01PN"] == 1]
    ctl_df = df[df["TRT01PN"] == 0]

    result = {
        "tc_id": "TC-017",
        "tc_name": "Laboratory Shift Table",
        "metadata": {
            "n_total": int(len(df)),
            "n_experimental": int(len(exp_df)),
            "n_control": int(len(ctl_df)),
            "population": "SAFETY",
            "lab_test": "Hemoglobin",
            "lab_unit": "g/L",
            "categories": ["LOW", "NORMAL", "HIGH"],
            "thresholds": {"low": 120, "high": 160},
            "n_post_baseline_visits": 3,
            "python_version": sys.version.split()[0],
        },
        "shift_overall": build_shift(df),
        "shift_experimental": build_shift(exp_df),
        "shift_control": build_shift(ctl_df),
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
