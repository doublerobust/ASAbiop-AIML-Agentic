#!/usr/bin/env python3
"""TC-031: Time-to-First-Treatment — Python

Time from randomization to first dose of study treatment.
Subjects who never receive treatment are censored at their follow-up time.

Output:
  - KM median time-to-first-treatment by arm with CI
  - Log-rank p-value (treatment arm comparison)
  - Cox HR for treatment arm
  - N received treatment, N censored by arm
  - TTT summary statistics by arm (mean, median, range)
  - Per-subject TTT details

Dependencies: numpy, pandas, lifelines
Usage: python tc_031_time_to_first_treatment.py --seed 42 --n 200 --output results.json
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import date, timedelta

import numpy as np
import pandas as pd
from lifelines import KaplanMeierFitter
from lifelines.utils import median_survival_times
from lifelines.statistics import logrank_test
from lifelines import CoxPHFitter


def generate_ttt_data(n: int, seed: int) -> pd.DataFrame:
    """Generate ADSL-style time-to-first-treatment dataset."""
    rng = np.random.default_rng(seed)
    n_exp = n // 2
    n_ctl = n - n_exp
    trt = np.array([1] * n_exp + [0] * n_ctl)
    rng.shuffle(trt)

    # Randomization date
    rand_offset = rng.integers(0, 366, size=n)
    rand_date = np.array([date(2023, 1, 1) + timedelta(days=int(d)) for d in rand_offset])

    # Time-to-first-treatment (days)
    ttt_days = np.where(
        trt == 1,
        rng.normal(3, 2, size=n),
        rng.normal(5, 3, size=n),
    ).round().astype(int)
    ttt_days = np.maximum(ttt_days, 0)

    # Some subjects never receive treatment (~5%)
    n_never = max(1, round(n * 0.05))
    never_tx_idx = rng.choice(n, size=n_never, replace=False)
    ttt_days[never_tx_idx] = -1  # sentinel for NA

    # First dose date
    first_dose_date = np.array([
        rand_date[i] + timedelta(days=int(ttt_days[i])) if ttt_days[i] >= 0 else None
        for i in range(n)
    ])

    # Received treatment flag
    received_tx = (ttt_days >= 0).astype(int)

    # Censoring: 1 = censored (never treated), 0 = event (received treatment)
    cnsr_ttt = (ttt_days < 0).astype(int)

    # For censored subjects, set TTT to follow-up time
    fu_days_censored = rng.normal(180, 60, size=n_never).round().astype(int)
    fu_days_censored = np.maximum(fu_days_censored, 30)
    ttt_days[never_tx_idx] = fu_days_censored

    # TTT in months
    ttt_months = np.round(ttt_days / 30.4375, 4)

    # Stratification factors
    sex = rng.choice(["M", "F"], size=n)
    agegr1 = rng.choice(["<65", ">=65"], size=n)
    ecog = rng.choice([0, 1], size=n)
    ittfl = np.where(rng.random(n) < 0.95, "Y", "N")
    saffl = np.where(rng.random(n) < 0.98, "Y", "N")

    return pd.DataFrame({
        "USUBJID": [f"SUB{i:04d}" for i in range(1, n + 1)],
        "TRT01PN": trt.astype(int),
        "TRT01A": np.where(trt == 1, "Experimental", "Control"),
        "RANDDT": rand_date,
        "FIRSTDOSEDT": first_dose_date,
        "TTT_DAYS": ttt_days.astype(int),
        "TTT_MONTHS": ttt_months,
        "RECEIVED_TX": received_tx,
        "CNSR_TTT": cnsr_ttt,
        "ITTFL": ittfl,
        "SAFFL": saffl,
        "SEX": sex,
        "AGEGR1": agegr1,
        "ECOG": ecog,
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


def km_median_ttt(sub_df, conf_type="log-log"):
    """Compute KM median time-to-first-treatment for a single arm."""
    time = sub_df["TTT_DAYS"].values.astype(float)
    event = (1 - sub_df["CNSR_TTT"]).values.astype(int)  # 1 = received treatment
    n_total = len(time)
    n_events = int(event.sum())

    if n_events == 0:
        return {
            "median": None, "ci_lower": None, "ci_upper": None,
            "n_events": 0, "n_total": n_total, "estimable": False,
        }

    kmf = KaplanMeierFitter()
    kmf.fit(time, event_observed=event, alpha=0.05)

    med = kmf.median_survival_time_
    estimable = not (med is None or np.isinf(med) or np.isnan(med))

    if not estimable:
        return {
            "median": None, "ci_lower": None, "ci_upper": None,
            "n_events": n_events, "n_total": n_total, "estimable": False,
        }

    med = float(med)

    # Brookmeyer-Crowley CI for median using lifelines utility
    # (same approach as TC-001)
    ci_median = median_survival_times(kmf.confidence_interval_)
    lo = float(ci_median.iloc[0, 0])
    hi = float(ci_median.iloc[0, 1])
    ci_lower = None if np.isinf(lo) or np.isnan(lo) else lo
    ci_upper = None if np.isinf(hi) or np.isnan(hi) else hi

    return {
        "median": round(med, 4),
        "ci_lower": round(float(ci_lower), 4) if ci_lower is not None else None,
        "ci_upper": round(float(ci_upper), 4) if ci_upper is not None else None,
        "n_events": n_events,
        "n_total": n_total,
        "estimable": True,
    }


def main():
    parser = argparse.ArgumentParser(description="TC-031: Time-to-First-Treatment")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--output", type=str, default="")
    parser.add_argument("--data", type=str, default="")
    parser.add_argument("--data-csv", type=str, default="", dest="data_csv")
    parser.add_argument("--ars-output", type=str, default="")
    args = parser.parse_args()

    data_path = args.data or args.data_csv

    print(f"[{pd.Timestamp.now()}] TC-031 Time-to-First-Treatment | seed={args.seed} n={args.n}")

    if data_path and Path(data_path).exists():
        df = pd.read_csv(data_path)
        df["RANDDT"] = pd.to_datetime(df["RANDDT"]).dt.date
        print(f"Loaded data: {data_path} ({len(df)} rows)")
    else:
        df = generate_ttt_data(args.n, args.seed)
        print(f"Generated data: {len(df)} subjects")

    # ITT population filter
    df_itt = df[df["ITTFL"] == "Y"].copy()

    exp_df = df_itt[df_itt["TRT01PN"] == 1]
    ctl_df = df_itt[df_itt["TRT01PN"] == 0]

    # KM median TTT per arm
    km_exp = km_median_ttt(exp_df)
    km_ctl = km_median_ttt(ctl_df)

    # Log-rank test
    try:
        lr = logrank_test(
            exp_df["TTT_DAYS"].values, ctl_df["TTT_DAYS"].values,
            event_observed_A=(1 - exp_df["CNSR_TTT"]).values,
            event_observed_B=(1 - ctl_df["CNSR_TTT"]).values,
        )
        logrank_result = {
            "chisq": round(float(lr.test_statistic), 4),
            "df": 1,
            "p_value": round(float(lr.p_value), 4),
        }
    except Exception:
        logrank_result = {"chisq": None, "df": None, "p_value": None}

    # Cox PH HR
    try:
        cox_df = df_itt[["TTT_DAYS", "CNSR_TTT", "TRT01PN"]].copy()
        cox_df["event"] = 1 - cox_df["CNSR_TTT"]
        cph = CoxPHFitter()
        cph.fit(cox_df[["TTT_DAYS", "event", "TRT01PN"]], "TTT_DAYS", "event")
        # hazard_ratios_ already returns exp(coef), do NOT re-exponentiate
        hr = float(cph.hazard_ratios_["TRT01PN"])
        ci = cph.confidence_intervals_.loc["TRT01PN"]
        cox_result = {
            "hr": round(hr, 4),
            "hr_lower": round(float(np.exp(ci.iloc[0])), 4),
            "hr_upper": round(float(np.exp(ci.iloc[1])), 4),
            "p_value": round(float(cph.summary.loc["TRT01PN", "p"]), 4),
            "n": int(cph._n_examples),
        }
    except Exception:
        cox_result = {"hr": None, "hr_lower": None, "hr_upper": None, "p_value": None, "n": None}

    # TTT summary
    ttt_summary_exp = summarize_cont(exp_df["TTT_DAYS"])
    ttt_summary_ctl = summarize_cont(ctl_df["TTT_DAYS"])

    # Received treatment counts
    received_exp = int(exp_df["RECEIVED_TX"].sum())
    received_ctl = int(ctl_df["RECEIVED_TX"].sum())
    censored_exp = int(exp_df["CNSR_TTT"].sum())
    censored_ctl = int(ctl_df["CNSR_TTT"].sum())

    result = {
        "tc_id": "TC-031",
        "tc_name": "Time-to-First-Treatment",
        "metadata": {
            "n_total": int(len(df_itt)),
            "n_experimental": int(len(exp_df)),
            "n_control": int(len(ctl_df)),
            "population": "ITT",
            "time_unit": "days",
            "censoring_rule": "subjects who never receive treatment are censored at follow-up time",
            "python_version": sys.version,
        },
        "km_median_ttt": {
            "experimental": km_exp,
            "control": km_ctl,
        },
        "logrank_test": logrank_result,
        "cox_hr": cox_result,
        "ttt_summary": {
            "experimental": ttt_summary_exp,
            "control": ttt_summary_ctl,
        },
        "received_treatment": {
            "experimental": {
                "n_received": received_exp,
                "n_censored": censored_exp,
                "pct_received": round(received_exp / len(exp_df) * 100, 2),
            },
            "control": {
                "n_received": received_ctl,
                "n_censored": censored_ctl,
                "pct_received": round(received_ctl / len(ctl_df) * 100, 2),
            },
        },
        "per_subject": [
            {
                "USUBJID": row["USUBJID"],
                "TRT01A": row["TRT01A"],
                "RANDDT": str(row["RANDDT"]),
                "FIRSTDOSEDT": str(row["FIRSTDOSEDT"]) if pd.notna(row["FIRSTDOSEDT"]) else None,
                "TTT_DAYS": int(row["TTT_DAYS"]),
                "TTT_MONTHS": float(row["TTT_MONTHS"]),
                "RECEIVED_TX": int(row["RECEIVED_TX"]),
                "CNSR_TTT": int(row["CNSR_TTT"]),
            }
            for _, row in df_itt.iterrows()
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
                "id": "TC-031",
                "version": "1.0",
                "analysisReason": "Assess time from randomization to first dose of study treatment",
                "analysisMethod": {
                    "name": "Kaplan-Meier Time-to-First-Treatment",
                    "codeTemplate": "lifelines.KaplanMeierFitter().fit(TTT_DAYS, 1-CNSR_TTT)",
                    "parameters": [
                        {"name": "conf_type", "role": "parameter", "value": "log-log"},
                        {"name": "alpha", "role": "parameter", "value": 0.05},
                        {"name": "censoring_rule", "role": "parameter", "value": "never treated = censored at follow-up"},
                    ],
                },
                "analysisVariables": [
                    {"name": "TTT_DAYS", "role": "analysis time", "dataset": "ADSL"},
                    {"name": "CNSR_TTT", "role": "censoring", "dataset": "ADSL"},
                    {"name": "RECEIVED_TX", "role": "event flag", "dataset": "ADSL"},
                    {"name": "TRT01A", "role": "treatment", "dataset": "ADSL"},
                ],
                "analysisPopulation": {
                    "id": "ITT",
                    "filter": "ITTFL = 'Y'",
                    "n": int(len(df_itt)),
                },
                "resultGroups": [
                    {"id": "EXP", "label": "Experimental", "n": int(len(exp_df))},
                    {"id": "CTL", "label": "Control", "n": int(len(ctl_df))},
                ],
                "analysisResultsData": [
                    {"groupId": "EXP", "metric": "median_ttt_days", "value": km_exp["median"]},
                    {"groupId": "CTL", "metric": "median_ttt_days", "value": km_ctl["median"]},
                    {"groupId": "EXP", "metric": "n_received", "value": received_exp},
                    {"groupId": "CTL", "metric": "n_received", "value": received_ctl},
                    {"groupId": "ALL", "metric": "logrank_p", "value": logrank_result["p_value"]},
                    {"groupId": "ALL", "metric": "cox_hr", "value": cox_result["hr"]},
                ],
            }
        }
        Path(args.ars_output).write_text(json.dumps(ars, indent=2, default=str))
        print(f"ARS written: {args.ars_output}")


if __name__ == "__main__":
    main()
