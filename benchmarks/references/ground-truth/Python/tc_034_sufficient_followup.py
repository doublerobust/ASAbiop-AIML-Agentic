#!/usr/bin/env python3
"""TC-034: Sufficient Follow-up Assessment — Python

Assesses whether subjects have sufficient safety follow-up per protocol
(e.g., 90 days post-last-dose). Also computes median follow-up duration
using the reverse Kaplan-Meier method.

Output:
  - N (%) with adequate follow-up by arm (>= threshold days post-last-dose)
  - Median follow-up duration (reverse KM) by arm with CI
  - N still ongoing, N discontinued, N died
  - Per-subject follow-up details

Dependencies: numpy, pandas, lifelines
Usage: python tc_034_sufficient_followup.py --seed 42 --n 200 --output results.json
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import date, timedelta

import numpy as np
import pandas as pd


def generate_followup_data(n: int, seed: int, threshold: int = 90) -> pd.DataFrame:
    """Generate ADSL-style follow-up dataset."""
    rng = np.random.default_rng(seed)
    n_exp = n // 2
    n_ctl = n - n_exp
    trt = np.array([1] * n_exp + [0] * n_ctl)
    rng.shuffle(trt)

    # Randomization date (study start: 2023-01-01 + random offset)
    rand_offset = rng.integers(0, 366, size=n)
    rand_date = np.array([date(2023, 1, 1) + timedelta(days=int(d)) for d in rand_offset])

    # Treatment duration (weeks)
    treat_dur_weeks = np.where(
        trt == 1,
        rng.normal(42, 10, size=n),
        rng.normal(24, 7, size=n),
    ).round().astype(int)
    treat_dur_weeks = np.maximum(treat_dur_weeks, 2)

    # Last dose date
    last_dose_date = np.array(
        [rand_date[i] + timedelta(weeks=int(treat_dur_weeks[i])) for i in range(n)]
    )

    # Follow-up post-last-dose (days)
    fu_post_dose = np.where(
        trt == 1,
        rng.normal(120, 40, size=n),
        rng.normal(100, 35, size=n),
    ).round().astype(int)
    fu_post_dose = np.maximum(fu_post_dose, 0)

    # Last follow-up date
    last_fu_date = np.array(
        [last_dose_date[i] + timedelta(days=int(fu_post_dose[i])) for i in range(n)]
    )

    # Subject status: 1=Ongoing, 2=Completed, 3=Discontinued, 4=Died
    status_prob = np.where(
        trt == 1,
        [0.20, 0.55, 0.15, 0.10],
        [0.15, 0.65, 0.12, 0.08],
    )
    status = np.array([
        rng.choice(4, p=status_prob[trt[i]]) + 1 for i in range(n)
    ])

    # For died subjects, cap follow-up
    died_mask = status == 4
    if died_mask.any():
        fu_post_dose[died_mask] = np.maximum(
            rng.normal(45, 20, size=died_mask.sum()).round().astype(int),
            0,
        )
        last_fu_date = np.array(
            [last_dose_date[i] + timedelta(days=int(fu_post_dose[i])) for i in range(n)]
        )

    # Follow-up from randomization (total days)
    fu_from_rand = np.array(
        [(last_fu_date[i] - rand_date[i]).days for i in range(n)]
    )

    # Adequate follow-up: >= threshold days post-last-dose AND not died
    adequate = ((fu_post_dose >= threshold) & (status != 4)).astype(int)

    status_labels = np.where(status == 1, "ONGOING",
                     np.where(status == 2, "COMPLETED",
                     np.where(status == 3, "DISCONTINUED", "DIED")))

    return pd.DataFrame({
        "USUBJID": [f"SUB{i:04d}" for i in range(1, n + 1)],
        "TRT01PN": trt.astype(int),
        "TRT01A": np.where(trt == 1, "Experimental", "Control"),
        "RANDDT": rand_date,
        "LASTDOSEDT": last_dose_date,
        "LASTFUDT": last_fu_date,
        "TREATDUR_W": treat_dur_weeks,
        "FU_POST_DOSE": fu_post_dose,
        "FU_FROM_RAND": fu_from_rand,
        "ADEQUATE_FU": adequate,
        "STATUS": status,
        "STATUS_LABEL": status_labels,
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


def reverse_km_median(time, status_label):
    """Reverse KM: event = alive (not DIED), censored = died.

    Returns median survival time and CI (Brookmeyer-Crowley method):
    - Lower CI: first time where upper CI of S(t) drops below 0.5
    - Upper CI: last time where lower CI of S(t) stays above 0.5
    """
    from lifelines import KaplanMeierFitter

    event = (status_label != "DIED").astype(int)
    if event.sum() == 0:
        return {"median": None, "ci_lower": None, "ci_upper": None}

    kmf = KaplanMeierFitter()
    kmf.fit(time, event_observed=event)

    med = kmf.median_survival_time_
    if np.isinf(med) or np.isnan(med):
        return {"median": None, "ci_lower": None, "ci_upper": None}

    med = float(med)

    # Brookmeyer-Crowley CI for median:
    # Find times where the CI bands of S(t) cross 0.5
    ci_df = kmf.confidence_interval_survival_function_
    # lifelines gives: index = timeline, columns = lower/upper bounds of S(t)
    # Column names: like 'KM_lower_0.95' and 'KM_upper_0.95'
    col_lower = ci_df.columns[0]  # lower CI of S(t)
    col_upper = ci_df.columns[1]  # upper CI of S(t)

    # Brookmeyer-Crowley CI for median:
    # Lower CI of median: last time where lower CI of S(t) >= 0.5
    # (the latest time where the lower bound still hasn't crossed 0.5)
    lower_cross = ci_df.index[ci_df[col_lower] >= 0.5]
    ci_lower = float(lower_cross[-1]) if len(lower_cross) > 0 else None

    # Upper CI of median: first time where upper CI of S(t) <= 0.5
    # (the earliest time where even the upper bound has crossed 0.5)
    upper_cross = ci_df.index[ci_df[col_upper] <= 0.5]
    ci_upper = float(upper_cross[0]) if len(upper_cross) > 0 else None

    return {
        "median": round(med, 4),
        "ci_lower": round(ci_lower, 4) if ci_lower is not None else None,
        "ci_upper": round(ci_upper, 4) if ci_upper is not None else None,
    }


def main():
    parser = argparse.ArgumentParser(description="TC-034: Sufficient Follow-up Assessment")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--output", type=str, default="")
    parser.add_argument("--data", type=str, default="")
    parser.add_argument("--data-csv", type=str, default="", dest="data_csv")
    parser.add_argument("--ars-output", type=str, default="")
    parser.add_argument("--threshold", type=int, default=90)
    args = parser.parse_args()

    data_path = args.data or args.data_csv
    threshold = args.threshold

    print(f"[{pd.Timestamp.now()}] TC-034 Sufficient Follow-up Assessment | seed={args.seed} n={args.n} threshold={threshold}d")

    if data_path and Path(data_path).exists():
        df = pd.read_csv(data_path)
        df["RANDDT"] = pd.to_datetime(df["RANDDT"]).dt.date
        df["LASTDOSEDT"] = pd.to_datetime(df["LASTDOSEDT"]).dt.date
        df["LASTFUDT"] = pd.to_datetime(df["LASTFUDT"]).dt.date
        print(f"Loaded data: {data_path} ({len(df)} rows)")
    else:
        df = generate_followup_data(args.n, args.seed, threshold)
        print(f"Generated data: {len(df)} subjects")

    exp_df = df[df["TRT01PN"] == 1]
    ctl_df = df[df["TRT01PN"] == 0]

    # Adequate follow-up counts
    adeq_exp = int(exp_df["ADEQUATE_FU"].sum())
    adeq_ctl = int(ctl_df["ADEQUATE_FU"].sum())

    # Status distribution
    def status_counts(sub_df):
        return {
            "ongoing": int((sub_df["STATUS_LABEL"] == "ONGOING").sum()),
            "completed": int((sub_df["STATUS_LABEL"] == "COMPLETED").sum()),
            "discontinued": int((sub_df["STATUS_LABEL"] == "DISCONTINUED").sum()),
            "died": int((sub_df["STATUS_LABEL"] == "DIED").sum()),
        }

    status_exp = status_counts(exp_df)
    status_ctl = status_counts(ctl_df)

    # Reverse KM median follow-up
    revkm_exp = reverse_km_median(exp_df["FU_FROM_RAND"].values, exp_df["STATUS_LABEL"].values)
    revkm_ctl = reverse_km_median(ctl_df["FU_FROM_RAND"].values, ctl_df["STATUS_LABEL"].values)

    # Follow-up post-dose summary
    fu_post_exp = summarize_cont(exp_df["FU_POST_DOSE"])
    fu_post_ctl = summarize_cont(ctl_df["FU_POST_DOSE"])

    # Follow-up from randomization summary
    fu_rand_exp = summarize_cont(exp_df["FU_FROM_RAND"])
    fu_rand_ctl = summarize_cont(ctl_df["FU_FROM_RAND"])

    result = {
        "tc_id": "TC-034",
        "tc_name": "Sufficient Follow-up Assessment",
        "metadata": {
            "n_total": int(len(df)),
            "n_experimental": int(len(exp_df)),
            "n_control": int(len(ctl_df)),
            "population": "SAFETY",
            "followup_threshold_days": int(threshold),
            "date_unit": "days",
            "python_version": sys.version,
        },
        "adequate_followup": {
            "experimental": {
                "n": adeq_exp,
                "pct": round(adeq_exp / len(exp_df) * 100, 2),
            },
            "control": {
                "n": adeq_ctl,
                "pct": round(adeq_ctl / len(ctl_df) * 100, 2),
            },
        },
        "status_distribution": {
            "experimental": status_exp,
            "control": status_ctl,
        },
        "reverse_km_followup": {
            "experimental": revkm_exp,
            "control": revkm_ctl,
        },
        "fu_post_dose": {
            "experimental": fu_post_exp,
            "control": fu_post_ctl,
        },
        "fu_from_randomization": {
            "experimental": fu_rand_exp,
            "control": fu_rand_ctl,
        },
        "per_subject": [
            {
                "USUBJID": row["USUBJID"],
                "TRT01A": row["TRT01A"],
                "RANDDT": str(row["RANDDT"]),
                "LASTDOSEDT": str(row["LASTDOSEDT"]),
                "LASTFUDT": str(row["LASTFUDT"]),
                "TREATDUR_W": int(row["TREATDUR_W"]),
                "FU_POST_DOSE": int(row["FU_POST_DOSE"]),
                "FU_FROM_RAND": int(row["FU_FROM_RAND"]),
                "ADEQUATE_FU": int(row["ADEQUATE_FU"]),
                "STATUS": int(row["STATUS"]),
                "STATUS_LABEL": row["STATUS_LABEL"],
            }
            for _, row in df.iterrows()
        ],
    }

    json_out = json.dumps(result, indent=2, default=str)

    if args.output:
        Path(args.output).write_text(json_out)
        print(f"Written: {args.output}")
    else:
        print(json_out)

    # ARS output
    if args.ars_output:
        ars = {
            "analysisResult": {
                "id": "TC-034",
                "version": "1.0",
                "analysisReason": "Assess sufficiency of safety follow-up per protocol requirements",
                "analysisMethod": {
                    "name": "Sufficient Follow-up Assessment",
                    "codeTemplate": "adequate = (fu_post_dose >= threshold) & (status != DIED)",
                    "parameters": [
                        {"name": "followup_threshold", "role": "parameter", "value": threshold},
                        {"name": "fu_post_dose", "role": "input", "source": "ADSL.LASTFUDT - ADSL.LASTDOSEDT"},
                        {"name": "status", "role": "input", "source": "ADSL.EOSSTT"},
                    ],
                },
                "analysisVariables": [
                    {"name": "TRT01A", "role": "treatment", "dataset": "ADSL"},
                    {"name": "FU_POST_DOSE", "role": "result", "dataset": "derived"},
                    {"name": "ADEQUATE_FU", "role": "flag", "dataset": "derived"},
                    {"name": "STATUS_LABEL", "role": "status", "dataset": "ADSL"},
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
                    {"groupId": "EXP", "metric": "pct_adequate_fu", "value": round(adeq_exp / len(exp_df) * 100, 2)},
                    {"groupId": "CTL", "metric": "pct_adequate_fu", "value": round(adeq_ctl / len(ctl_df) * 100, 2)},
                    {"groupId": "EXP", "metric": "median_followup", "value": revkm_exp["median"]},
                    {"groupId": "CTL", "metric": "median_followup", "value": revkm_ctl["median"]},
                ],
            }
        }
        Path(args.ars_output).write_text(json.dumps(ars, indent=2, default=str))
        print(f"ARS written: {args.ars_output}")


if __name__ == "__main__":
    main()
