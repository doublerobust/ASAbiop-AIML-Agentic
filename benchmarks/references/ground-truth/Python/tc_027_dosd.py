#!/usr/bin/env python3
"""TC-027 Ground Truth: Duration of Stable Disease (DOSD) — KM Median (Python)

Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark.

DOSD is defined as the time from first documentation of Stable Disease (SD)
to disease progression or death, among subjects whose Best Overall Response
is SD. This is a subset analysis on a non-trivial population (typically
30-45% of ITT).

Key distinctions from other time-to-event TCs:
  DOR (TC-022): Responders only (CR+PR), time from response to PD/death
  DOSD (TC-027): SD subjects only, time from SD documentation to PD/death
                 DOSD subjects and DOR subjects are disjoint (SD vs CR+PR)

This tests:
  1. Correct subset identification (BOR = SD only, not CR/PR/PD/NE)
  2. Time-to-event analysis on a non-trivial subset
  3. KM estimation with small-to-moderate sample sizes
  4. Cross-TFL consistency: DOSD N = SD count from TC-025 BOR Summary

Dependencies: lifelines, numpy, scipy, json, argparse
Usage: python tc_027_dosd.py --seed 42 --n 200 --output results.json
"""

import json
import argparse
import sys
import math
from pathlib import Path

import numpy as np
import pandas as pd
from lifelines import KaplanMeierFitter, CoxPHFitter
from lifelines.statistics import logrank_test
from lifelines.utils import median_survival_times
import lifelines


# ─────────────────────────────────────────────────────
# Data Generation
# ─────────────────────────────────────────────────────

def generate_dosd_adtte(seed=42, n_subjects=200, hr=0.80):
    """Generate DOSD-specific ADTTE dataset.

    Among subjects with BOR=SD, computes time from first SD documentation
    to disease progression or death.

    BOR distribution consistent with TC-025 (BOR Summary):
      Control: CR 2%, PR 18%, SD 45%, PD 30%, NE 5%
      Active:  CR 8%, PR 35%, SD 35%, PD 15%, NE 7%
    """
    rng = np.random.default_rng(seed)
    base_rate = math.log(2) / 4.5  # median DOSD control = 4.5 months

    trt = rng.choice([0, 1], size=n_subjects)
    hazard_mult = np.where(trt == 0, 1.0, hr)

    # BOR distribution consistent with TC-025
    bor = np.empty(n_subjects, dtype=object)
    for i in range(n_subjects):
        if trt[i] == 0:
            bor[i] = rng.choice(["CR", "PR", "SD", "PD", "NE"], p=[0.02, 0.18, 0.45, 0.30, 0.05])
        else:
            bor[i] = rng.choice(["CR", "PR", "SD", "PD", "NE"], p=[0.08, 0.35, 0.35, 0.15, 0.07])

    is_sd = (bor == "SD")

    # Time to SD documentation (from randomization): ~1-3 months
    time_to_sd = np.where(is_sd, rng.exponential(1.0 / (1.0 / 1.5), size=n_subjects), np.nan)

    # Time from SD documentation to progression or death
    prog_time = rng.exponential(1.0 / (base_rate * hazard_mult))
    death_time = rng.exponential(1.0 / (base_rate * 0.3 * hazard_mult))
    cens_time = rng.exponential(1.0 / (base_rate * 0.3 / 0.7))

    event_from_sd = np.minimum(prog_time, death_time)

    observed_dosd = np.full(n_subjects, np.nan)
    dosd_cnsr = np.full(n_subjects, np.nan)

    for i in range(n_subjects):
        if not is_sd[i]:
            continue

        event_time_abs = time_to_sd[i] + event_from_sd[i]

        if cens_time[i] < event_time_abs and cens_time[i] > time_to_sd[i]:
            # Censored after SD documentation but before event
            observed_dosd[i] = cens_time[i] - time_to_sd[i]
            dosd_cnsr[i] = 1
        elif cens_time[i] <= time_to_sd[i]:
            # Censored before SD documentation
            observed_dosd[i] = max(cens_time[i] - time_to_sd[i], 0.01)
            dosd_cnsr[i] = 1
        else:
            # Event observed
            observed_dosd[i] = event_from_sd[i]
            dosd_cnsr[i] = 0

    # Stratification factors
    sex = rng.choice(["M", "F"], size=n_subjects, p=[0.55, 0.45])
    ecog = rng.choice([0, 1], size=n_subjects, p=[0.6, 0.4])
    age = np.round(rng.normal(58, 12, n_subjects)).astype(int)
    agegr1 = np.where(age < 65, "<65", ">=65")

    ittfl = np.where(rng.random(n_subjects) < 0.95, "Y", "N")
    saffl = np.where(rng.random(n_subjects) < 0.98, "Y", "N")

    df = pd.DataFrame({
        "USUBJID": [f"SUBJ-{i+1:04d}" for i in range(n_subjects)],
        "STUDYID": "BENCHMARK-001",
        "TRT01PN": trt,
        "TRT01P": np.where(trt == 0, "Placebo", "Active"),
        "AVAL": np.round(observed_dosd, 2),
        "CNSR": dosd_cnsr,
        "PARAMCD": "DOSD",
        "PARAM": "Duration of Stable Disease",
        "ITTFL": ittfl,
        "SAFFL": saffl,
        "SEX": sex,
        "ECOG": ecog,
        "AGEGR1": agegr1,
        "BOR": bor,
        "IS_SD": is_sd.astype(int),
        "TIME_TO_SD": np.round(time_to_sd, 2),
    })
    return df


def read_shared_data(path):
    """Read shared CSV data."""
    df = pd.read_csv(path)
    return df


# ─────────────────────────────────────────────────────
# Core Computation
# ─────────────────────────────────────────────────────

def compute_dosd_median(adtte, arm=1, population="ITT", conf_type="log-log"):
    """Compute KM median DOSD for a given arm among BOR=SD subjects."""
    if population == "ITT":
        data = adtte[(adtte["ITTFL"] == "Y") & (adtte["TRT01PN"] == arm)].copy()
    else:
        data = adtte[adtte["TRT01PN"] == arm].copy()

    n_total_in_arm = len(data)

    # Filter to SD subjects only
    data = data[(data["IS_SD"] == 1) & data["AVAL"].notna() & (data["AVAL"] > 0)].copy()

    if len(data) == 0:
        return {
            "median_dosd": None,
            "median_ci_lower": None,
            "median_ci_upper": None,
            "n_sd": 0,
            "n_events": 0,
            "n_total": n_total_in_arm,
            "event_rate": None,
            "hazard_ratio": None,
            "hr_ci_lower": None,
            "hr_ci_upper": None,
            "logrank_chisq": None,
            "logrank_p": None,
            "ci_method": conf_type,
            "arm": arm,
            "population": "ITT with BOR=SD",
            "estimable": False,
        }

    durations = data["AVAL"].values
    event_observed = (1 - data["CNSR"]).values.astype(int)

    kmf = KaplanMeierFitter()
    kmf.fit(durations, event_observed, label='DOSD')

    median_dosd = kmf.median_survival_time_
    n_sd = len(data)
    n_events = int(event_observed.sum())
    n_total = len(data)
    event_rate = round(n_events / n_total, 4)

    if np.isnan(median_dosd) or median_dosd == np.inf:
        median_dosd_val = None
        ci_lower = None
        ci_upper = None
    else:
        median_dosd_val = round(float(median_dosd), 2)

        # CI via Brookmeyer-Crowley (log-log transformation)
        try:
            ci_median = median_survival_times(kmf.confidence_interval_)
            lo = float(ci_median.iloc[0, 0])
            hi = float(ci_median.iloc[0, 1])
            ci_lower = None if (np.isinf(lo) or pd.isna(lo)) else round(lo, 2)
            ci_upper = None if (np.isinf(hi) or pd.isna(hi)) else round(hi, 2)
        except (KeyError, IndexError, ValueError, StopIteration):
            ci_lower = None
            ci_upper = None

    # Log-rank test and Cox PH among SD subjects
    data_lr = adtte[(adtte["ITTFL"] == "Y") & (adtte["IS_SD"] == 1) &
                    adtte["AVAL"].notna() & (adtte["AVAL"] > 0)].copy()

    lr_p = None
    lr_chisq = None
    hr = None
    hr_ci_lower = None
    hr_ci_upper = None

    if len(data_lr) > 0 and data_lr["TRT01PN"].nunique() > 1:
        arm0 = data_lr[data_lr["TRT01PN"] == 0]
        arm1 = data_lr[data_lr["TRT01PN"] == 1]

        if len(arm0) > 0 and len(arm1) > 0:
            t0 = arm0["AVAL"].values
            e0 = (1 - arm0["CNSR"]).values
            t1 = arm1["AVAL"].values
            e1 = (1 - arm1["CNSR"]).values

            try:
                lr_result = logrank_test(t0, t1, e0, e1)
                lr_chisq = round(float(lr_result.test_statistic), 4)
                lr_p = round(float(lr_result.p_value), 6)
            except Exception:
                pass

            try:
                cox_df = data_lr[["AVAL", "CNSR", "TRT01PN"]].copy()
                cox_df["CNSR"] = 1 - cox_df["CNSR"]  # event column
                cph = CoxPHFitter()
                cph.fit(cox_df, duration_col="AVAL", event_col="CNSR", formula="TRT01PN")
                hr = round(float(np.exp(cph.params_["TRT01PN"])), 4)
                hr_ci = cph.confidence_intervals_
                hr_ci_lower = round(float(np.exp(hr_ci.loc["TRT01PN", "95% lower-bound"])), 4)
                hr_ci_upper = round(float(np.exp(hr_ci.loc["TRT01PN", "95% upper-bound"])), 4)
            except Exception:
                pass

    estimable = median_dosd_val is not None

    return {
        "median_dosd": median_dosd_val,
        "median_ci_lower": ci_lower,
        "median_ci_upper": ci_upper,
        "n_sd": n_sd,
        "n_events": n_events,
        "n_total": n_total,
        "event_rate": event_rate,
        "hazard_ratio": hr,
        "hr_ci_lower": hr_ci_lower,
        "hr_ci_upper": hr_ci_upper,
        "logrank_chisq": lr_chisq,
        "logrank_p": lr_p,
        "ci_method": conf_type,
        "arm": arm,
        "population": "ITT with BOR=SD",
        "estimable": estimable,
    }


def write_ars_output(results, filepath):
    """Write ARS v1.0-compatible JSON envelope."""
    ars = {
        "reportingEvent": {
            "id": "TC-027-DOSD",
            "name": "DOSD KM Median",
            "version": "1.0",
        },
        "analysisResults": [
            {
                "id": "TC-027-DOSD-001",
                "analysisId": "DOSD-KM-MEDIAN",
                "method": "KaplanMeier",
                "purpose": "Estimate median duration of stable disease among BOR=SD subjects",
                "results": results,
            }
        ],
        "referencingMetadata": {
            "dataset": "ADTTE",
            "paramcd": "DOSD",
            "population": "ITT with BOR=SD",
        },
    }
    with open(filepath, "w") as f:
        json.dump(ars, f, indent=2)
    print(f"Wrote ARS output to: {filepath}")


def main():
    parser = argparse.ArgumentParser(description="TC-027: Duration of Stable Disease KM Median (Python)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--arm", type=int, default=1)
    parser.add_argument("--conf-type", type=str, default="log-log")
    parser.add_argument("--data", type=str, default=None, help="Shared ADTTE CSV")
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--ars-output", type=str, default=None)
    args = parser.parse_args()

    seed = args.seed
    print(f"TC-027: Duration of Stable Disease KM Median (Python) — seed={seed}, n={args.n}")

    if args.data:
        adtte = read_shared_data(args.data)
        print(f"Loaded shared ADTTE with {len(adtte)} subjects")
    else:
        adtte = generate_dosd_adtte(seed=seed, n_subjects=args.n)
        print(f"Generated DOSD ADTTE with {len(adtte)} subjects")

    results_arm0 = compute_dosd_median(adtte, arm=0, population="ITT", conf_type=args.conf_type)
    results_arm1 = compute_dosd_median(adtte, arm=1, population="ITT", conf_type=args.conf_type)

    # Subgroup analysis (among SD subjects)
    subgroups = []
    data_sd = adtte[(adtte["ITTFL"] == "Y") & (adtte["IS_SD"] == 1) &
                    adtte["AVAL"].notna() & (adtte["AVAL"] > 0)].copy()

    for var in ["SEX", "AGEGR1", "ECOG"]:
        levels = sorted(data_sd[var].unique())
        for lvl in levels:
            data_sub = data_sd[data_sd[var] == lvl]
            if len(data_sub) < 5:
                continue

            arm0_sub = data_sub[data_sub["TRT01PN"] == 0]
            arm1_sub = data_sub[data_sub["TRT01PN"] == 1]

            if len(arm0_sub) == 0 or len(arm1_sub) == 0:
                continue

            med_exp = None
            med_ctrl = None

            try:
                kmf1 = KaplanMeierFitter().fit(arm1_sub["AVAL"].values,
                                                (1 - arm1_sub["CNSR"]).values.astype(int))
                m1 = kmf1.median_survival_time_
                if not np.isnan(m1):
                    med_exp = round(float(m1), 2)
            except Exception:
                pass

            try:
                kmf0 = KaplanMeierFitter().fit(arm0_sub["AVAL"].values,
                                                (1 - arm0_sub["CNSR"]).values.astype(int))
                m0 = kmf0.median_survival_time_
                if not np.isnan(m0):
                    med_ctrl = round(float(m0), 2)
            except Exception:
                pass

            # Cox PH for subgroup HR
            hr_sub = None
            try:
                cox_df = data_sub[["AVAL", "CNSR", "TRT01PN"]].copy()
                cox_df["CNSR"] = 1 - cox_df["CNSR"]
                cph = CoxPHFitter().fit(cox_df, duration_col="AVAL", event_col="CNSR", formula="TRT01PN")
                hr_sub = round(float(np.exp(cph.params_["TRT01PN"])), 4)
            except Exception:
                pass

            subgroups.append({
                "variable": var,
                "level": str(lvl),
                "median_exp": med_exp,
                "median_ctrl": med_ctrl,
                "n_exp": len(arm1_sub),
                "n_ctrl": len(arm0_sub),
                "hr": hr_sub,
            })

    # Censoring summary
    n_censored = int(data_sd["CNSR"].sum())
    n_events_sd = int((1 - data_sd["CNSR"]).sum())
    n_sd_total = len(data_sd)

    result = {
        "test_case_id": "TC-027",
        "endpoint": "Duration of Stable Disease",
        "population": "ITT with BOR=SD",
        "arm_control": results_arm0,
        "arm_experimental": results_arm1,
        "subgroups": subgroups,
        "censoring_summary": {
            "n_censored": n_censored,
            "n_events": n_events_sd,
            "censoring_rate": round(n_censored / n_sd_total, 4) if n_sd_total > 0 else None,
        },
        "language": "Python",
        "version": "1.0",
    }

    print("\n" + "─" * 50)
    print(f"Endpoint:       {result['endpoint']}")
    print(f"Population:     {result['population']}")
    if results_arm1["estimable"]:
        print(f"Median DOSD (exp):  {results_arm1['median_dosd']:.1f} months")
        print(f"Median DOSD (ctrl): {results_arm0['median_dosd']:.1f} months")
    else:
        print("Median DOSD:     Not estimable")
    print(f"N SD subjects: {n_sd_total} (ctrl: {results_arm0['n_sd']}, exp: {results_arm1['n_sd']})")
    print(f"N events:       {n_events_sd}")
    print(f"Python lifelines v{lifelines.__version__}")
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
        write_ars_output(result, args.ars_output)


if __name__ == "__main__":
    main()
