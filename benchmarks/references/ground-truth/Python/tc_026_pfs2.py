#!/usr/bin/env python3
"""TC-026 Ground Truth: Time to Second Progression (PFS2) — KM Median

Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark.

PFS2 is defined as the time from randomization to the second disease
progression or death, whichever comes first. Unlike PFS (TC-001) which
captures time to first progression/death, PFS2 captures the total
duration of disease control including post-progression benefit.

Dependencies: lifelines, numpy, scipy, json, argparse
Usage: python tc_026_pfs2.py --seed 42 --n 200 --output results.json
"""

import json
import argparse
import sys
import math
import numpy as np
from lifelines import KaplanMeierFitter, CoxPHFitter
from lifelines.statistics import logrank_test, multivariate_logrank_test
from scipy import stats

# ─────────────────────────────────────────────────────
# Data Generation
# ─────────────────────────────────────────────────────

def generate_pfs2_adtte(seed=42, n_subjects=200, hr=0.65):
    """Generate PFS2 ADTTE data.

    PFS2 time >= PFS time for all subjects (by construction).
    Subjects without first progression are censored.
    """
    rng = np.random.default_rng(seed)
    base_rate = math.log(2) / 9.0  # median PFS2 control = 9 months

    trt = rng.binomial(1, 0.5, n_subjects)
    hazard_mult = np.where(trt == 0, 1.0, hr)

    # Time to first progression
    prog1_time = rng.exponential(1.0 / (base_rate * 1.5 * hazard_mult), n_subjects)

    # Gap between first and second progression
    prog2_gap = rng.exponential(1.0 / (base_rate * 0.8 * hazard_mult), n_subjects)

    # Time to death
    death_time = rng.exponential(1.0 / (base_rate * 0.4 * hazard_mult), n_subjects)

    # Censoring (lost to follow-up)
    cens_time = rng.exponential(1.0 / (base_rate * 0.15), n_subjects)

    # Absolute time of second progression
    prog2_time = prog1_time + prog2_gap

    observed_time = np.zeros(n_subjects)
    cnsr = np.zeros(n_subjects, dtype=int)

    for i in range(n_subjects):
        if prog1_time[i] > cens_time[i]:
            # No first progression observed
            observed_time[i] = cens_time[i]
            cnsr[i] = 1
        else:
            # First progression observed; check second progression vs death vs censoring
            t2 = min(prog2_time[i], death_time[i])
            if t2 <= cens_time[i]:
                observed_time[i] = t2
                cnsr[i] = 0
            else:
                observed_time[i] = cens_time[i]
                cnsr[i] = 1

    # Stratification factors
    sex = rng.choice(["M", "F"], n_subjects, p=[0.55, 0.45])
    ecog = rng.binomial(1, 0.4, n_subjects)
    age = np.round(rng.normal(58, 12, n_subjects)).astype(int)
    agegr1 = np.where(age < 65, "<65", ">=65")

    # ITT/SAFETY flags
    ittfl = np.where(rng.uniform(size=n_subjects) < 0.95, "Y", "N")
    saffl = np.where(rng.uniform(size=n_subjects) < 0.98, "Y", "N")

    records = []
    for i in range(n_subjects):
        records.append({
            "USUBJID": f"SUBJ-{i+1:04d}",
            "STUDYID": "BENCHMARK-001",
            "TRT01PN": int(trt[i]),
            "TRT01P": "Active" if trt[i] == 1 else "Placebo",
            "AVAL": round(float(observed_time[i]), 2),
            "CNSR": int(cnsr[i]),
            "PARAMCD": "PFS2",
            "PARAM": "Progression-Free Survival 2",
            "ITTFL": ittfl[i],
            "SAFFL": saffl[i],
            "SEX": sex[i],
            "ECOG": int(ecog[i]),
            "AGEGR1": agegr1[i],
        })
    return records


def read_shared_data(path):
    """Read shared CSV data."""
    import csv
    records = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["TRT01PN"] = int(row["TRT01PN"])
            row["AVAL"] = float(row["AVAL"])
            row["CNSR"] = int(row["CNSR"])
            row["ECOG"] = int(row["ECOG"]) if "ECOG" in row else 0
            records.append(row)
    return records


# ─────────────────────────────────────────────────────
# Core Computation
# ─────────────────────────────────────────────────────

def compute_pfs2_median(adtte, arm=1, population="ITT"):
    """Compute PFS2 KM median for a given arm."""
    if population == "ITT":
        data = [r for r in adtte if r["ITTFL"] == "Y" and r["TRT01PN"] == arm]
    else:
        data = [r for r in adtte if r["TRT01PN"] == arm]

    if not data:
        raise ValueError(f"No subjects in arm {arm} for population {population}")

    times = np.array([r["AVAL"] for r in data])
    events = np.array([1 - r["CNSR"] for r in data])

    kmf = KaplanMeierFitter()
    kmf.fit(times, event_observed=events)

    median_pfs2 = kmf.median_survival_time_
    if np.isnan(median_pfs2):
        median_pfs2 = None
    else:
        median_pfs2 = round(float(median_pfs2), 2)

    # CI via Brookmeyer-Crowley (log-log transformation)
    # Use lifelines confidence interval
    ci_df = kmf.confidence_interval_
    ci_lower = round(float(ci_df.iloc[-1, 0]), 2) if not ci_df.empty else None
    ci_upper = round(float(ci_df.iloc[-1, 1]), 2) if not ci_df.empty else None

    n_events = int(events.sum())
    n_total = len(data)
    event_rate = round(n_events / n_total, 4)

    # Log-rank test
    data_lr = [r for r in adtte if r["ITTFL"] == "Y"]
    arm0 = [r for r in data_lr if r["TRT01PN"] == 0]
    arm1 = [r for r in data_lr if r["TRT01PN"] == 1]

    t0 = np.array([r["AVAL"] for r in arm0])
    e0 = np.array([1 - r["CNSR"] for r in arm0])
    t1 = np.array([r["AVAL"] for r in arm1])
    e1 = np.array([1 - r["CNSR"] for r in arm1])

    lr_result = logrank_test(t0, t1, e0, e1)
    lr_chisq = round(float(lr_result.test_statistic), 4)
    lr_p = round(float(lr_result.p_value), 6)

    # Cox PH for HR
    cox_data = []
    for r in data_lr:
        cox_data.append({"AVAL": r["AVAL"], "CNSR": 1 - r["CNSR"], "TRT01PN": r["TRT01PN"]})
    import pandas as pd
    cox_df = pd.DataFrame(cox_data)
    cph = CoxPHFitter()
    cph.fit(cox_df, duration_col="AVAL", event_col="CNSR", formula="TRT01PN")

    hr = round(float(np.exp(cph.params_["TRT01PN"])), 4)
    hr_ci = cph.confidence_intervals_
    hr_ci_lower = round(float(np.exp(hr_ci.loc["TRT01PN", "95% lower-bound"])), 4)
    hr_ci_upper = round(float(np.exp(hr_ci.loc["TRT01PN", "95% upper-bound"])), 4)

    return {
        "median_pfs2": median_pfs2,
        "median_ci_lower": ci_lower,
        "median_ci_upper": ci_upper,
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


def write_ars_output(results, filepath):
    """Write ARS v1.0-compatible JSON envelope."""
    ars = {
        "reportingEvent": {
            "id": "TC-026-PFS2",
            "name": "PFS2 KM Median",
            "version": "1.0",
        },
        "analysisResults": [
            {
                "id": "TC-026-PFS2-001",
                "analysisId": "PFS2-KM-MEDIAN",
                "method": "KaplanMeier",
                "purpose": "Estimate median progression-free survival 2",
                "results": results,
            }
        ],
        "referencingMetadata": {
            "dataset": "ADTTE",
            "paramcd": "PFS2",
            "population": "ITT",
        },
    }
    with open(filepath, "w") as f:
        json.dump(ars, f, indent=2)
    print(f"Wrote ARS output to: {filepath}")


def main():
    parser = argparse.ArgumentParser(description="TC-026: PFS2 KM Median")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--arm", type=int, default=1)
    parser.add_argument("--data", type=str, default=None)
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--ars-output", type=str, default=None)
    args = parser.parse_args()

    if args.data:
        adtte = read_shared_data(args.data)
    else:
        adtte = generate_pfs2_adtte(seed=args.seed, n_subjects=args.n)

    results_arm0 = compute_pfs2_median(adtte, arm=0, population="ITT")
    results_arm1 = compute_pfs2_median(adtte, arm=1, population="ITT")

    # Subgroup analysis
    subgroups = []
    data_itt = [r for r in adtte if r["ITTFL"] == "Y"]
    for var in ["SEX", "AGEGR1", "ECOG"]:
        levels = sorted(set(r[var] for r in data_itt))
        for lvl in levels:
            data_sub = [r for r in data_itt if str(r[var]) == str(lvl)]
            if not data_sub:
                continue

            arm0_sub = [r for r in data_sub if r["TRT01PN"] == 0]
            arm1_sub = [r for r in data_sub if r["TRT01PN"] == 1]

            if not arm0_sub or not arm1_sub:
                continue

            t0 = np.array([r["AVAL"] for r in arm0_sub])
            e0 = np.array([1 - r["CNSR"] for r in arm0_sub])
            t1 = np.array([r["AVAL"] for r in arm1_sub])
            e1 = np.array([1 - r["CNSR"] for r in arm1_sub])

            kmf0 = KaplanMeierFitter().fit(t0, e0)
            kmf1 = KaplanMeierFitter().fit(t1, e1)

            med_exp = kmf1.median_survival_time_
            med_ctrl = kmf0.median_survival_time_

            # Cox PH for subgroup HR
            try:
                cox_data = [{"AVAL": r["AVAL"], "CNSR": 1 - r["CNSR"], "TRT01PN": r["TRT01PN"]} for r in data_sub]
                import pandas as pd
                cox_df = pd.DataFrame(cox_data)
                cph = CoxPHFitter().fit(cox_df, duration_col="AVAL", event_col="CNSR", formula="TRT01PN")
                hr = round(float(np.exp(cph.params_["TRT01PN"])), 4)
            except Exception:
                hr = None

            subgroups.append({
                "variable": var,
                "level": str(lvl),
                "median_exp": round(float(med_exp), 2) if not np.isnan(med_exp) else None,
                "median_ctrl": round(float(med_ctrl), 2) if not np.isnan(med_ctrl) else None,
                "n_exp": len(arm1_sub),
                "n_ctrl": len(arm0_sub),
                "hr": hr,
            })

    n_censored = sum(r["CNSR"] for r in data_itt)
    n_events = sum(1 - r["CNSR"] for r in data_itt)

    result = {
        "test_case_id": "TC-026",
        "endpoint": "Progression-Free Survival 2",
        "population": "ITT",
        "arm_control": results_arm0,
        "arm_experimental": results_arm1,
        "subgroups": subgroups,
        "censoring_summary": {
            "n_censored": int(n_censored),
            "n_events": int(n_events),
            "censoring_rate": round(n_censored / len(data_itt), 4),
        },
        "language": "Python",
        "version": "1.0",
    }

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Wrote output to: {args.output}")
    else:
        print(json.dumps(result, indent=2))

    if args.ars_output:
        write_ars_output(result, args.ars_output)


if __name__ == "__main__":
    main()
