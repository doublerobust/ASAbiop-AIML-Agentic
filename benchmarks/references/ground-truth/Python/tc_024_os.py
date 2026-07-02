#!/usr/bin/env python3
"""TC-024 Ground Truth: Overall Survival (OS) — KM Median

Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark.

OS is defined as the time from randomization to death from any cause.
Unlike PFS (TC-001), the event is death only (not progression).

This tests:
  1. Correct identification of OS endpoint (death event, not progression)
  2. KM median estimation with death-only event
  3. Log-rank test for treatment comparison
  4. Hazard ratio from Cox PH model

Dependencies: lifelines, numpy, pandas, scipy, pyyaml
Usage: python tc_024_os.py --seed 42 --n 200 --output results.json
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from lifelines import KaplanMeierFitter, CoxPHFitter
from lifelines.statistics import logrank_test

# ─────────────────────────────────────────────────────
# Argument parsing
# ─────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="TC-024 Overall Survival KM Median")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--arm", type=int, default=1)
    parser.add_argument("--data", type=str, default=None)
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--ars-output", type=str, default=None)
    return parser.parse_args()


# ─────────────────────────────────────────────────────
# Generate OS-specific ADTTE data
# ─────────────────────────────────────────────────────

def generate_os_adtte(seed=42, n_subjects=200, hr=0.75):
    """Generate synthetic ADTTE data for OS endpoint."""
    rng = np.random.default_rng(seed)
    base_rate = np.log(2) / 14.0  # median OS control = 14 months

    trt = rng.integers(0, 2, size=n_subjects)
    hazard_mult = np.where(trt == 0, 1.0, hr)

    # Time to death
    death_time = rng.exponential(1.0 / (base_rate * hazard_mult))

    # Censoring
    cens_time = rng.exponential(1.0 / (base_rate * 0.2))

    observed_time = np.minimum(death_time, cens_time)
    cnsr = np.where(death_time <= cens_time, 0, 1)  # 0 = event, 1 = censored

    # Strata
    sex = rng.choice(["M", "F"], size=n_subjects, p=[0.55, 0.45])
    ecog = rng.choice([0, 1], size=n_subjects, p=[0.6, 0.4])
    age = np.round(rng.normal(58, 12, size=n_subjects)).astype(int)
    agegr1 = np.where(age < 65, "<65", ">=65")

    df = pd.DataFrame({
        "USUBJID": [f"SUBJ-{i+1:04d}" for i in range(n_subjects)],
        "STUDYID": "BENCHMARK-001",
        "TRT01PN": trt,
        "TRT01P": np.where(trt == 0, "Placebo", "Active"),
        "AVAL": np.round(observed_time, 2),
        "CNSR": cnsr,
        "PARAMCD": "OS",
        "PARAM": "Overall Survival",
        "ITTFL": np.where(rng.random(n_subjects) < 0.95, "Y", "N"),
        "SAFFL": np.where(rng.random(n_subjects) < 0.98, "Y", "N"),
        "SEX": sex,
        "ECOG": ecog,
        "AGEGR1": agegr1,
    })
    return df


# ─────────────────────────────────────────────────────
# TC-024 Core Computation
# ─────────────────────────────────────────────────────

def compute_os_median(adtte, arm=1, population="ITT"):
    """Compute OS KM median, log-rank test, and Cox PH HR."""
    if population == "ITT":
        data = adtte[(adtte["ITTFL"] == "Y") & (adtte["TRT01PN"] == arm)].copy()
    else:
        data = adtte[adtte["TRT01PN"] == arm].copy()

    if len(data) == 0:
        raise ValueError(f"No subjects in arm {arm} for population {population}")

    kmf = KaplanMeierFitter()
    kmf.fit(durations=data["AVAL"], event_observed=(1 - data["CNSR"]))

    median_os = round(kmf.median_survival_time_, 2)

    # CI for median — use the survival function at the median time
    sf = kmf.survival_function_
    ci_lower = kmf.confidence_interval_survival_function_
    # Find the CI at median time
    median_idx = (sf.index <= median_os).sum() - 1
    if median_idx >= 0 and median_idx < len(ci_lower):
        # Use the Brookmeyer-Crowley style CI from the survival function
        ci_lo = round(float(ci_lower.iloc[median_idx, 0]), 2) if not np.isnan(ci_lower.iloc[median_idx, 0]) else None
        ci_hi = round(float(ci_lower.iloc[median_idx, 1]), 2) if not np.isnan(ci_lower.iloc[median_idx, 1]) else None
    else:
        ci_lo = None
        ci_hi = None

    n_events = int(data["CNSR"].eq(0).sum())
    n_total = int(len(data))
    event_rate = round(n_events / n_total, 4)

    # Log-rank test (treatment comparison on full ITT)
    data_itt = adtte[adtte["ITTFL"] == "Y"].copy()
    arm0 = data_itt[data_itt["TRT01PN"] == 0]
    arm1 = data_itt[data_itt["TRT01PN"] == 1]

    lr = logrank_test(
        arm0["AVAL"], arm1["AVAL"],
        event_observed_A=(1 - arm0["CNSR"]),
        event_observed_B=(1 - arm1["CNSR"])
    )
    lr_chisq = round(float(lr.test_statistic), 4)
    lr_p = round(float(lr.p_value), 6)

    # Cox PH model
    cox_data = data_itt[["AVAL", "CNSR", "TRT01PN"]].copy()
    cox_data["event"] = 1 - cox_data["CNSR"]
    cph = CoxPHFitter()
    cph.fit(cox_data[["AVAL", "event", "TRT01PN"]], duration_col="AVAL", event_col="event")
    hr = round(float(np.exp(cph.params_["TRT01PN"])), 4)
    hr_ci = cph.confidence_intervals_
    hr_ci_lower = round(float(np.exp(hr_ci.loc["TRT01PN", "95% lower-bound"])), 4)
    hr_ci_upper = round(float(np.exp(hr_ci.loc["TRT01PN", "95% upper-bound"])), 4)

    return {
        "median_os": median_os,
        "median_ci_lower": ci_lo,
        "median_ci_upper": ci_hi,
        "n_events": n_events,
        "n_total": n_total,
        "event_rate": event_rate,
        "logrank_chisq": lr_chisq,
        "logrank_p": lr_p,
        "hazard_ratio": hr,
        "hr_ci_lower": hr_ci_lower,
        "hr_ci_upper": hr_ci_upper,
        "arm": arm,
        "population": population,
    }


# ─────────────────────────────────────────────────────
# ARS Output Envelope (ARS v1.0 compatible)
# ─────────────────────────────────────────────────────

def write_ars_output(results, filepath):
    ars = {
        "reportingEvent": {
            "id": "TC-024-OS",
            "name": "Overall Survival KM Median",
            "version": "1.0"
        },
        "analysisResults": [
            {
                "id": "TC-024-OS-001",
                "analysisId": "OS-KM-MEDIAN",
                "method": "KaplanMeier",
                "purpose": "Estimate median overall survival",
                "results": results
            }
        ],
        "referencingMetadata": {
            "dataset": "ADTTE",
            "paramcd": "OS",
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
        adtte = pd.read_csv(args.data)
    else:
        adtte = generate_os_adtte(seed=args.seed, n_subjects=args.n)

    # Compute for both arms
    results_arm0 = compute_os_median(adtte, arm=0, population="ITT")
    results_arm1 = compute_os_median(adtte, arm=1, population="ITT")

    # Subgroup analysis
    subgroups = []
    data_itt = adtte[adtte["ITTFL"] == "Y"].copy()
    for var in ["SEX", "AGEGR1", "ECOG"]:
        levels = sorted(data_itt[var].unique())
        for lvl in levels:
            data_sub = data_itt[data_itt[var] == lvl]
            if len(data_sub) == 0:
                continue
            arm0_sub = data_sub[data_sub["TRT01PN"] == 0]
            arm1_sub = data_sub[data_sub["TRT01PN"] == 1]
            if len(arm0_sub) == 0 or len(arm1_sub) == 0:
                continue

            kmf0 = KaplanMeierFitter()
            kmf0.fit(arm0_sub["AVAL"], event_observed=(1 - arm0_sub["CNSR"]))
            kmf1 = KaplanMeierFitter()
            kmf1.fit(arm1_sub["AVAL"], event_observed=(1 - arm1_sub["CNSR"]))

            try:
                cox_sub = CoxPHFitter()
                cox_sub_data = data_sub[["AVAL", "CNSR", "TRT01PN"]].copy()
                cox_sub_data["event"] = 1 - cox_sub_data["CNSR"]
                cox_sub.fit(cox_sub_data[["AVAL", "event", "TRT01PN"]],
                           duration_col="AVAL", event_col="event")
                hr_sub = round(float(np.exp(cox_sub.params_["TRT01PN"])), 4)
            except Exception:
                hr_sub = None

            subgroups.append({
                "variable": var,
                "level": str(lvl),
                "median_exp": round(float(kmf1.median_survival_time_), 2) if not np.isnan(kmf1.median_survival_time_) else None,
                "median_ctrl": round(float(kmf0.median_survival_time_), 2) if not np.isnan(kmf0.median_survival_time_) else None,
                "n_exp": int(len(arm1_sub)),
                "n_ctrl": int(len(arm0_sub)),
                "hr": hr_sub
            })

    result = {
        "test_case_id": "TC-024",
        "endpoint": "Overall Survival",
        "population": "ITT",
        "arm_control": results_arm0,
        "arm_experimental": results_arm1,
        "subgroups": subgroups,
        "censoring_summary": {
            "n_censored": int(data_itt["CNSR"].sum()),
            "n_events": int((1 - data_itt["CNSR"]).sum()),
            "censoring_rate": round(float(data_itt["CNSR"].sum() / len(data_itt)), 4)
        },
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
