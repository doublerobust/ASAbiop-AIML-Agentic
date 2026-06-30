#!/usr/bin/env python3
"""TC-021 Ground Truth: Time-to-Progression (TTP) — KM Median (Python)

Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark.

Key difference from TC-001 (PFS):
  PFS: event = disease progression OR death (whichever comes first)
  TTP: event = disease progression only; death is censored

This tests whether the agent correctly handles censoring rules —
a common source of programming errors in oncology trials.

Dependencies: pandas, numpy, lifelines (>= 0.29.0)
Usage: python tc_021_ttp.py --seed 42 --n 200 --output results.json
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from lifelines import KaplanMeierFitter
from lifelines.utils import median_survival_times
import lifelines


def generate_ttp_adtte(seed=42, n_subjects=200, hr=0.75):
    """Generate TTP-specific ADTTE dataset.

    Stores both TTP (death censored) and PFS (death as event) for cross-TFL validation.
    """
    rng = np.random.default_rng(seed)
    base_rate = np.log(2) / 6.0  # median PFS control = 6 months
    trt = rng.choice([0, 1], size=n_subjects)
    hazard_mult = np.where(trt == 0, 1.0, hr)

    prog_time = rng.exponential(1.0 / (base_rate * hazard_mult))
    death_time = rng.exponential(1.0 / (base_rate * 0.3 * hazard_mult))
    cens_time = rng.exponential(1.0 / (base_rate * 0.3 / 0.7))

    # TTP: event = progression only; death censored
    ttp_time = np.minimum(prog_time, cens_time)
    ttp_cnsr = np.where(prog_time <= cens_time, 0, 1)

    # If death occurs before progression and before censoring → censored at death
    death_before_prog = (death_time < prog_time) & (death_time < cens_time)
    ttp_time = np.where(death_before_prog, death_time, ttp_time)
    ttp_cnsr = np.where(death_before_prog, 1, ttp_cnsr)

    # PFS: event = progression OR death
    pfs_time = np.minimum(np.minimum(prog_time, death_time), cens_time)
    pfs_event = (prog_time <= cens_time) | (death_time <= cens_time)
    pfs_cnsr = np.where(pfs_event, 0, 1)

    sex = rng.choice(["Male", "Female"], size=n_subjects, p=[0.5, 0.5])
    ecog = rng.choice([0, 1], size=n_subjects, p=[0.6, 0.4])
    ittfl = np.where(rng.random(n_subjects) < 0.95, "Y", "N")

    df = pd.DataFrame({
        "USUBJID": [f"SUBJ-{i+1:04d}" for i in range(n_subjects)],
        "STUDYID": "BENCHMARK-001",
        "TRT01PN": trt,
        "TRT01P": np.where(trt == 0, "Placebo", "Active"),
        "AVAL": np.round(ttp_time, 2),
        "CNSR": ttp_cnsr.astype(int),
        "PARAMCD": "TTP",
        "PARAM": "Time to Progression",
        "ITTFL": ittfl,
        "SAFFL": np.where(rng.random(n_subjects) < 0.98, "Y", "N"),
        "SEX": sex,
        "ECOG": ecog,
        "PFS_AVAL": np.round(pfs_time, 2),
        "PFS_CNSR": pfs_cnsr.astype(int),
    })
    return df


def compute_ttp_median(adtte, arm=1, population="ITT", conf_type="log-log", seed=42):
    """Compute KM median TTP for specified arm."""
    if population == "ITT":
        data = adtte[(adtte["ITTFL"] == "Y") & (adtte["TRT01PN"] == arm)].copy()
    else:
        data = adtte[adtte["TRT01PN"] == arm].copy()

    if len(data) == 0:
        raise ValueError(f"No subjects in arm {arm} for population {population}")

    durations = data["AVAL"].values
    event_observed = (1 - data["CNSR"]).values

    kmf = KaplanMeierFitter()
    kmf.fit(durations, event_observed, label='TTP')

    median_ttp = kmf.median_survival_time_
    ci = kmf.confidence_interval_

    n_total = len(data)
    n_events = int(event_observed.sum())

    if np.isnan(median_ttp) or median_ttp == np.inf:
        return {
            "test_case_id": "TC-021",
            "variant_id": f"v{seed}",
            "language": "Python",
            "package": "lifelines",
            "package_version": lifelines.__version__,
            "median_ttp": None,
            "ci_lower": None,
            "ci_upper": None,
            "n_events": n_events,
            "n_total": n_total,
            "ci_method": conf_type,
            "endpoint": "TTP",
            "censoring_rule": "death censored (progression only)",
            "estimable": False,
            "seed": seed,
        }

    # Extract CI of the median (Brookmeyer-Crowley interval)
    try:
        ci_median = median_survival_times(kmf.confidence_interval_)
        lo = float(ci_median.iloc[0, 0])
        hi = float(ci_median.iloc[0, 1])
        ci_lower = None if np.isinf(lo) or pd.isna(lo) else round(lo, 4)
        ci_upper = None if np.isinf(hi) or pd.isna(hi) else round(hi, 4)
    except (KeyError, IndexError, ValueError, StopIteration):
        ci_lower = None
        ci_upper = None

    return {
        "test_case_id": "TC-021",
        "variant_id": f"v{seed}",
        "language": "Python",
        "package": "lifelines",
        "package_version": lifelines.__version__,
        "median_ttp": float(round(median_ttp, 4)),
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "n_events": n_events,
        "n_total": n_total,
        "ci_method": conf_type,
        "endpoint": "TTP",
        "censoring_rule": "death censored (progression only)",
        "estimable": True,
        "seed": seed,
    }


def main():
    parser = argparse.ArgumentParser(description="TC-021: Time-to-Progression KM Median (Python)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--arm", type=int, default=1, help="Treatment arm (0=Control, 1=Experimental)")
    parser.add_argument("--conf-type", type=str, default="log-log")
    parser.add_argument("--data", type=str, default=None, help="Shared ADTTE CSV")
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--ars-output", type=str, default=None)
    args = parser.parse_args()

    seed = args.seed
    print(f"TC-021: Time-to-Progression KM Median (Python) — seed={seed}, n={args.n}, arm={args.arm}")

    if args.data:
        adtte = pd.read_csv(args.data)
        print(f"Loaded shared ADTTE with {len(adtte)} subjects")
    else:
        adtte = generate_ttp_adtte(seed=seed, n_subjects=args.n)
        print(f"Generated TTP ADTTE with {len(adtte)} subjects")

    result = compute_ttp_median(adtte, arm=args.arm, conf_type=args.conf_type, seed=seed)

    print("\n" + "─" * 50)
    print(f"Endpoint:       {result['endpoint']}")
    print(f"Censoring rule: {result['censoring_rule']}")
    if result["estimable"]:
        print(f"Median TTP:     {result['median_ttp']:.1f} months")
        print(f"95% CI:         ({result['ci_lower']}, {result['ci_upper']})")
    else:
        print("Median TTP:     Not estimable")
    print(f"N events:      {result['n_events']} / {result['n_total']}")
    print(f"Python lifelines v{result['package_version']}")
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
        ars_envelope = {
            "ars_version": "1.0",
            "analysisResult": {
                "id": "TC-021",
                "version": "1.0",
                "analysisReason": "Secondary efficacy endpoint: time to disease progression",
                "analysisMethod": {
                    "name": "Kaplan-Meier",
                    "codeTemplate": "lifelines.KaplanMeierFitter().fit(AVAL, 1-CNSR)",
                    "parameters": {
                        "conf_type": result["ci_method"],
                        "alpha": 0.05,
                        "censoring_rule": "death censored"
                    }
                },
                "analysisVariables": [
                    {"name": "AVAL", "dataset": "ADTTE", "role": "analysis time"},
                    {"name": "CNSR", "dataset": "ADTTE", "role": "censoring (death = censored)"},
                    {"name": "TRT01A", "dataset": "ADSL", "role": "treatment"}
                ],
                "analysisPopulation": {"name": "ITT", "filter": "ITTFL = 'Y'"},
                "analysisDataset": "ADTTE",
                "resultGroups": [
                    {"id": "Experimental" if args.arm == 1 else "Control",
                     "n": result["n_total"], "events": result["n_events"]}
                ],
                "documentation": "KM median TTP estimation; death treated as censoring (progression-only events)",
                "analysisResultsData": {
                    "statistics": [
                        {"name": "median_ttp", "value": result["median_ttp"], "unit": "months"},
                        {"name": "ci_lower", "value": result["ci_lower"]},
                        {"name": "ci_upper", "value": result["ci_upper"]},
                        {"name": "n_events", "value": result["n_events"]},
                        {"name": "n_total", "value": result["n_total"]},
                        {"name": "estimable", "value": result["estimable"]}
                    ]
                }
            }
        }
        ars_path = Path(args.ars_output)
        ars_path.parent.mkdir(parents=True, exist_ok=True)
        with open(ars_path, "w") as f:
            json.dump(ars_envelope, f, indent=2, default=str)
        print(f"Wrote ARS-compatible output to: {ars_path}")


if __name__ == "__main__":
    main()
