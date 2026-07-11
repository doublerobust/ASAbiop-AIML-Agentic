#!/usr/bin/env python3
"""TC-033: Dose Intensity Summary (Relative Dose Intensity) — Python

Computes Relative Dose Intensity (RDI) per subject and summarizes by arm:
  RDI = (actual cumulative dose / planned cumulative dose) × 100

Output: Per-subject RDI, arm-level summary (N, mean, SD, median, range),
        % subjects with RDI >= 80%, % with dose reduction, % with dose interruption

Dependencies: numpy, pandas
Usage: python tc_033_dose_intensity.py --seed 42 --n 200 --output results.json
"""

import argparse
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd


def generate_exposure_data(n: int, seed: int) -> pd.DataFrame:
    """Generate ADEX-style exposure dataset with planned vs actual dose."""
    rng = np.random.default_rng(seed)
    n_exp = n // 2
    n_ctl = n - n_exp
    trt = np.array([1] * n_exp + [0] * n_ctl)
    rng.shuffle(trt)

    # Treatment duration (weeks)
    dur = np.where(
        trt == 1,
        rng.normal(48, 10, size=n),
        rng.normal(27, 7, size=n),
    ).round().astype(int)
    dur = np.maximum(dur, 2)

    # Planned daily dose (mg): Exp=12, Ctl=6
    planned_daily = np.where(trt == 1, 12, 6)
    planned_cum = planned_daily * dur * 7

    # Adherence
    adherence = np.where(
        trt == 1,
        rng.uniform(0.70, 1.0, size=n),
        rng.uniform(0.80, 1.0, size=n),
    )
    actual_cum = planned_cum * adherence

    # Dose reduction
    dose_reduced = rng.binomial(1, np.where(trt == 1, 0.15, 0.08))
    # Dose interruption
    dose_interrupt = rng.binomial(1, np.where(trt == 1, 0.10, 0.05))

    # RDI
    rdi = (actual_cum / planned_cum) * 100

    return pd.DataFrame({
        "USUBJID": [f"SUB{i:04d}" for i in range(1, n + 1)],
        "TRT01PN": trt.astype(int),
        "TRT01A": np.where(trt == 1, "Experimental", "Control"),
        "TREATDUR": dur,
        "PLANDOSE": planned_cum.astype(float),
        "ACTUALDOSE": np.round(actual_cum, 2),
        "RDI": np.round(rdi, 2),
        "DOSERED": dose_reduced,
        "DOSEINT": dose_interrupt,
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


def main():
    parser = argparse.ArgumentParser(description="TC-033: Dose Intensity Summary")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--output", type=str, default="")
    parser.add_argument("--data", type=str, default="")
    parser.add_argument("--data-csv", type=str, default="", dest="data_csv")
    parser.add_argument("--ars-output", type=str, default="")
    args = parser.parse_args()

    data_path = args.data or args.data_csv

    print(f"[{pd.Timestamp.now()}] TC-033 Dose Intensity Summary | seed={args.seed} n={args.n}")

    if data_path and Path(data_path).exists():
        df = pd.read_csv(data_path)
        print(f"Loaded data: {data_path} ({len(df)} rows)")
    else:
        df = generate_exposure_data(args.n, args.seed)
        print(f"Generated data: {len(df)} subjects")

    exp_df = df[df["TRT01PN"] == 1]
    ctl_df = df[df["TRT01PN"] == 0]

    # RDI >= 80%
    rdi_ge80_exp = int((exp_df["RDI"] >= 80).sum())
    rdi_ge80_ctl = int((ctl_df["RDI"] >= 80).sum())

    # Dose reduction
    dose_red_exp = int(exp_df["DOSERED"].sum())
    dose_red_ctl = int(ctl_df["DOSERED"].sum())

    # Dose interruption
    dose_int_exp = int(exp_df["DOSEINT"].sum())
    dose_int_ctl = int(ctl_df["DOSEINT"].sum())

    result = {
        "tc_id": "TC-033",
        "tc_name": "Dose Intensity Summary",
        "metadata": {
            "n_total": int(len(df)),
            "n_experimental": int(len(exp_df)),
            "n_control": int(len(ctl_df)),
            "population": "SAFETY",
            "rdi_threshold": 80,
            "duration_unit": "weeks",
            "dose_unit": "mg",
            "python_version": sys.version,
        },
        "rdi_summary": {
            "experimental": summarize_cont(exp_df["RDI"]),
            "control": summarize_cont(ctl_df["RDI"]),
        },
        "rdi_ge80": {
            "experimental": {
                "n": rdi_ge80_exp,
                "pct": round(rdi_ge80_exp / len(exp_df) * 100, 2),
            },
            "control": {
                "n": rdi_ge80_ctl,
                "pct": round(rdi_ge80_ctl / len(ctl_df) * 100, 2),
            },
        },
        "dose_reduction": {
            "experimental": {
                "n": dose_red_exp,
                "pct": round(dose_red_exp / len(exp_df) * 100, 2),
            },
            "control": {
                "n": dose_red_ctl,
                "pct": round(dose_red_ctl / len(ctl_df) * 100, 2),
            },
        },
        "dose_interruption": {
            "experimental": {
                "n": dose_int_exp,
                "pct": round(dose_int_exp / len(exp_df) * 100, 2),
            },
            "control": {
                "n": dose_int_ctl,
                "pct": round(dose_int_ctl / len(ctl_df) * 100, 2),
            },
        },
        "treatment_duration": {
            "experimental": summarize_cont(exp_df["TREATDUR"]),
            "control": summarize_cont(ctl_df["TREATDUR"]),
        },
        "per_subject": [
            {
                "USUBJID": row["USUBJID"],
                "TRT01A": row["TRT01A"],
                "TREATDUR": int(row["TREATDUR"]),
                "PLANDOSE": float(row["PLANDOSE"]),
                "ACTUALDOSE": float(row["ACTUALDOSE"]),
                "RDI": float(row["RDI"]),
                "DOSERED": int(row["DOSERED"]),
                "DOSEINT": int(row["DOSEINT"]),
            }
            for _, row in df.iterrows()
        ],
    }

    json_out = json.dumps(result, indent=2)

    if args.output:
        Path(args.output).write_text(json_out)
        print(f"Written: {args.output}")
    else:
        print(json_out)

    # ARS output
    if args.ars_output:
        ars = {
            "analysisResult": {
                "id": "TC-033",
                "version": "1.0",
                "analysisReason": "Summary of relative dose intensity by treatment arm",
                "analysisMethod": {
                    "name": "Dose Intensity Summary",
                    "codeTemplate": "RDI = (ACTUALDOSE / PLANDOSE) * 100",
                    "parameters": [
                        {"name": "actual_dose", "role": "input", "source": "ADEX.ACTUALDOSE"},
                        {"name": "planned_dose", "role": "input", "source": "ADEX.PLANDOSE"},
                        {"name": "rdi_threshold", "role": "parameter", "value": 80},
                    ],
                },
                "analysisVariables": [
                    {"name": "TRT01A", "role": "treatment", "dataset": "ADSL"},
                    {"name": "RDI", "role": "result", "dataset": "derived"},
                    {"name": "DOSERED", "role": "flag", "dataset": "ADEX"},
                    {"name": "DOSEINT", "role": "flag", "dataset": "ADEX"},
                ],
                "analysisPopulation": {
                    "id": "SAFETY",
                    "filter": "SAFFL == 'Y'",
                    "n": int(len(df)),
                },
                "resultGroups": [
                    {"id": "EXP", "label": "Experimental", "n": int(len(exp_df))},
                    {"id": "CTL", "label": "Control", "n": int(len(ctl_df))},
                ],
                "analysisResultsData": [
                    {"groupId": "EXP", "metric": "mean_RDI", "value": round(float(exp_df["RDI"].mean()), 4)},
                    {"groupId": "CTL", "metric": "mean_RDI", "value": round(float(ctl_df["RDI"].mean()), 4)},
                    {"groupId": "EXP", "metric": "pct_RDI_ge80", "value": round(rdi_ge80_exp / len(exp_df) * 100, 2)},
                    {"groupId": "CTL", "metric": "pct_RDI_ge80", "value": round(rdi_ge80_ctl / len(ctl_df) * 100, 2)},
                ],
            }
        }
        Path(args.ars_output).write_text(json.dumps(ars, indent=2))
        print(f"ARS written: {args.ars_output}")


if __name__ == "__main__":
    main()
