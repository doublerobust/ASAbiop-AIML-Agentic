#!/usr/bin/env python3
"""TC-016: Exposure Summary Table
Treatment exposure: duration, cumulative dose, dose intensity, relative dose intensity.
Output: JSON with summary stats per treatment arm.

Dependencies: numpy, pandas
"""

import argparse
import json
import sys
import numpy as np
import pandas as pd


def generate_exposure(n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n_exp = n // 2
    n_ctl = n - n_exp
    trt = np.array([1] * n_exp + [0] * n_ctl)
    rng.shuffle(trt)

    # Treatment duration (weeks)
    dur = np.where(
        trt == 1,
        rng.normal(48, 12, size=n),
        rng.normal(28, 8, size=n),
    ).round().astype(int)
    dur = np.maximum(dur, 2)

    planned_daily = np.where(trt == 1, 10, 5)
    adherence = rng.uniform(0.75, 1.0, size=n)
    cum_dose = planned_daily * dur * 7 * adherence
    dose_intensity = (cum_dose / (planned_daily * dur * 7)) * 100
    dose_reduced = rng.binomial(1, np.where(trt == 1, 0.15, 0.08))

    return pd.DataFrame({
        "USUBJID": [f"SUB{i:04d}" for i in range(1, n + 1)],
        "TRT01PN": trt.astype(int),
        "TRT01A": np.where(trt == 1, "Experimental", "Control"),
        "TREATDUR": dur,
        "CUMDOSE": np.round(cum_dose, 2),
        "PLANDOSE": (planned_daily * dur * 7).astype(float),
        "DOSEINT": np.round(dose_intensity, 2),
        "DOSERED": dose_reduced,
    })


def summarize_cont(x):
    arr = np.asarray(x, dtype=float)
    return {
        "n": int(len(arr)),
        "mean": round(float(np.mean(arr)), 4),
        "sd": round(float(np.std(arr, ddof=1)), 4),
        "median": round(float(np.median(arr)), 4),
        "min": round(float(np.min(arr)), 4),
        "max": round(float(np.max(arr)), 4),
        "q1": round(float(np.percentile(arr, 25)), 4),
        "q3": round(float(np.percentile(arr, 75)), 4),
    }


def summarize_categorical(x):
    arr = np.asarray(x)
    return {
        "n": int(len(arr)),
        "n_yes": int(np.sum(arr == 1)),
        "n_no": int(np.sum(arr == 0)),
        "pct_yes": round(float(np.mean(arr == 1) * 100), 2),
    }


def main():
    parser = argparse.ArgumentParser(description="TC-016: Exposure Summary Table")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--output", type=str, default="")
    parser.add_argument("--data", type=str, default="")
    args = parser.parse_args()

    print(f"[{pd.Timestamp.now()}] TC-016 Exposure Summary | seed={args.seed} n={args.n}")

    if args.data:
        df = pd.read_csv(args.data)
    else:
        df = generate_exposure(args.n, args.seed)

    exp_df = df[df["TRT01PN"] == 1]
    ctl_df = df[df["TRT01PN"] == 0]

    result = {
        "tc_id": "TC-016",
        "tc_name": "Exposure Summary Table",
        "metadata": {
            "n_total": int(len(df)),
            "n_experimental": int(len(exp_df)),
            "n_control": int(len(ctl_df)),
            "population": "SAFETY",
            "duration_unit": "weeks",
            "dose_unit": "mg",
            "python_version": sys.version.split()[0],
        },
        "treatment_duration": {
            "experimental": summarize_cont(exp_df["TREATDUR"]),
            "control": summarize_cont(ctl_df["TREATDUR"]),
        },
        "cumulative_dose": {
            "experimental": summarize_cont(exp_df["CUMDOSE"]),
            "control": summarize_cont(ctl_df["CUMDOSE"]),
        },
        "dose_intensity": {
            "experimental": summarize_cont(exp_df["DOSEINT"]),
            "control": summarize_cont(ctl_df["DOSEINT"]),
        },
        "dose_reduction": {
            "experimental": summarize_categorical(exp_df["DOSERED"]),
            "control": summarize_categorical(ctl_df["DOSERED"]),
        },
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
