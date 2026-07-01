#!/usr/bin/env python3
"""TC-022 Ground Truth: Duration of Response (DOR) — KM Median (Python)

Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark.

DOR is defined as the time from first documented response (CR or PR)
to disease progression or death, among subjects who achieved a response.

Key differences from TC-001 (PFS) and TC-021 (TTP):
  PFS (TC-001): All subjects, event = progression OR death
  TTP (TC-021): All subjects, event = progression only (death censored)
  DOR (TC-022): Responders only, event = progression OR death

This tests:
  1. Correct subsetting to responder population (CR + PR)
  2. KM estimation on a selected subset (not full ITT)
  3. Handling of left truncation (response occurs after randomization)

Dependencies: pandas, numpy, lifelines (>= 0.29.0)
Usage: python tc_022_dor.py --seed 42 --n 200 --output results.json
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from lifelines import KaplanMeierFitter
from lifelines.utils import median_survival_times
import lifelines


def generate_dor_adtte(seed=42, n_subjects=200, hr=0.75):
    """Generate DOR-specific ADTTE dataset.

    Among responders (CR/PR), computes time from first response to
    progression or death. Includes TIME_TO_RESPONSE for left truncation.
    """
    rng = np.random.default_rng(seed)
    base_rate = np.log(2) / 6.0  # median PFS control = 6 months
    trt = rng.choice([0, 1], size=n_subjects)
    hazard_mult = np.where(trt == 0, 1.0, hr)

    # Response probability depends on treatment
    orr_prob = np.where(trt == 1, 0.40, 0.20)
    is_responder = rng.binomial(1, orr_prob)

    # Time to response (among responders): exponential with mean ~2 months
    time_to_response = np.where(
        is_responder == 1,
        rng.exponential(1.0 / (1.0 / 2.0), size=n_subjects),
        np.nan
    )

    # Time to progression or death (from randomization)
    prog_time = rng.exponential(1.0 / (base_rate * hazard_mult))
    death_time = rng.exponential(1.0 / (base_rate * 0.3 * hazard_mult))
    cens_time = rng.exponential(1.0 / (base_rate * 0.3 / 0.7))

    # Event time from randomization
    event_time_from_rand = np.minimum(prog_time, death_time)

    # For responders: DOR = time from response to event or censoring
    has_event_after_response = (is_responder == 1) & (event_time_from_rand > time_to_response)
    has_cens_before_event = (
        (is_responder == 1) &
        (cens_time < event_time_from_rand) &
        (cens_time > time_to_response)
    )

    # DOR time
    dor_time = np.where(
        has_event_after_response,
        event_time_from_rand - time_to_response,
        np.nan
    )
    dor_time = np.where(
        has_cens_before_event,
        cens_time - time_to_response,
        dor_time
    )

    # Censoring indicator: 0 = event, 1 = censored
    dor_cnsr = np.where(has_event_after_response & ~has_cens_before_event, 0, 1)
    dor_cnsr = np.where(has_cens_before_event, 1, dor_cnsr)
    dor_cnsr = np.where(is_responder == 0, np.nan, dor_cnsr)
    dor_time = np.where(is_responder == 0, np.nan, dor_time)

    # Response type: ~30% CR, ~70% PR among responders
    is_cr = np.where(is_responder == 1, rng.binomial(1, 0.3, size=n_subjects), 0)
    bor = np.where(is_cr == 1, "CR",
                   np.where(is_responder == 1, "PR",
                            rng.choice(["SD", "PD"], size=n_subjects, p=[0.4, 0.6])))

    sex = rng.choice(["Male", "Female"], size=n_subjects, p=[0.5, 0.5])
    ecog = rng.choice([0, 1], size=n_subjects, p=[0.6, 0.4])
    ittfl = np.where(rng.random(n_subjects) < 0.95, "Y", "N")

    df = pd.DataFrame({
        "USUBJID": [f"SUBJ-{i+1:04d}" for i in range(n_subjects)],
        "STUDYID": "BENCHMARK-001",
        "TRT01PN": trt,
        "TRT01P": np.where(trt == 0, "Placebo", "Active"),
        "AVAL": np.round(dor_time, 2),
        "CNSR": dor_cnsr,
        "PARAMCD": "DOR",
        "PARAM": "Duration of Response",
        "ITTFL": ittfl,
        "SAFFL": np.where(rng.random(n_subjects) < 0.98, "Y", "N"),
        "SEX": sex,
        "ECOG": ecog,
        "BOR": bor,
        "IS_RESPONDER": is_responder,
        "TIME_TO_RESPONSE": np.round(time_to_response, 2),
    })
    return df


def compute_dor_median(adtte, arm=1, population="ITT", conf_type="log-log", seed=42):
    """Compute KM median DOR for specified arm among responders."""
    if population == "ITT":
        data = adtte[(adtte["ITTFL"] == "Y") & (adtte["TRT01PN"] == arm)].copy()
    else:
        data = adtte[adtte["TRT01PN"] == arm].copy()

    n_total_in_arm = len(data)

    # Filter to responders only
    data = data[(data["IS_RESPONDER"] == 1) & data["AVAL"].notna() & (data["AVAL"] > 0)].copy()

    if len(data) == 0:
        return {
            "test_case_id": "TC-022",
            "variant_id": f"v{seed}",
            "language": "Python",
            "package": "lifelines",
            "package_version": lifelines.__version__,
            "median_dor": None,
            "ci_lower": None,
            "ci_upper": None,
            "n_responders": 0,
            "n_events": 0,
            "n_total": n_total_in_arm,
            "ci_method": conf_type,
            "endpoint": "DOR",
            "population": "responders (CR+PR)",
            "censoring_rule": "event = progression or death",
            "estimable": False,
            "seed": seed,
        }

    durations = data["AVAL"].values
    event_observed = (1 - data["CNSR"]).values

    kmf = KaplanMeierFitter()
    kmf.fit(durations, event_observed, label='DOR')

    median_dor = kmf.median_survival_time_
    n_responders = len(data)
    n_events = int(event_observed.sum())

    if np.isnan(median_dor) or median_dor == np.inf:
        return {
            "test_case_id": "TC-022",
            "variant_id": f"v{seed}",
            "language": "Python",
            "package": "lifelines",
            "package_version": lifelines.__version__,
            "median_dor": None,
            "ci_lower": None,
            "ci_upper": None,
            "n_responders": n_responders,
            "n_events": n_events,
            "n_total": n_total_in_arm,
            "ci_method": conf_type,
            "endpoint": "DOR",
            "population": "responders (CR+PR)",
            "censoring_rule": "event = progression or death",
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
        "test_case_id": "TC-022",
        "variant_id": f"v{seed}",
        "language": "Python",
        "package": "lifelines",
        "package_version": lifelines.__version__,
        "median_dor": float(round(median_dor, 4)),
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "n_responders": n_responders,
        "n_events": n_events,
        "n_total": n_total_in_arm,
        "ci_method": conf_type,
        "endpoint": "DOR",
        "population": "responders (CR+PR)",
        "censoring_rule": "event = progression or death",
        "estimable": True,
        "seed": seed,
    }


def main():
    parser = argparse.ArgumentParser(description="TC-022: Duration of Response KM Median (Python)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--arm", type=int, default=1, help="Treatment arm (0=Control, 1=Experimental)")
    parser.add_argument("--conf-type", type=str, default="log-log")
    parser.add_argument("--data", type=str, default=None, help="Shared ADTTE CSV")
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--ars-output", type=str, default=None)
    args = parser.parse_args()

    seed = args.seed
    print(f"TC-022: Duration of Response KM Median (Python) — seed={seed}, n={args.n}, arm={args.arm}")

    if args.data:
        adtte = pd.read_csv(args.data)
        print(f"Loaded shared ADTTE with {len(adtte)} subjects")
    else:
        adtte = generate_dor_adtte(seed=seed, n_subjects=args.n)
        print(f"Generated DOR ADTTE with {len(adtte)} subjects")

    result = compute_dor_median(adtte, arm=args.arm, conf_type=args.conf_type, seed=seed)

    print("\n" + "─" * 50)
    print(f"Endpoint:       {result['endpoint']}")
    print(f"Population:     {result['population']}")
    print(f"Censoring rule: {result['censoring_rule']}")
    if result["estimable"]:
        print(f"Median DOR:     {result['median_dor']:.1f} months")
        print(f"95% CI:         ({result['ci_lower']}, {result['ci_upper']})")
    else:
        print("Median DOR:     Not estimable")
    print(f"N responders:  {result['n_responders']} / {result['n_total']}")
    print(f"N events:      {result['n_events']}")
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
                "id": "TC-022",
                "version": "1.0",
                "analysisReason": "Secondary efficacy endpoint: duration of response among responders",
                "analysisMethod": {
                    "name": "Kaplan-Meier",
                    "codeTemplate": "lifelines.KaplanMeierFitter().fit(AVAL, 1-CNSR)",
                    "parameters": {
                        "conf_type": result["ci_method"],
                        "alpha": 0.05,
                        "population": "responders (CR+PR)",
                        "event_definition": "progression or death"
                    }
                },
                "analysisVariables": [
                    {"name": "AVAL", "dataset": "ADTTE", "role": "analysis time (from response)"},
                    {"name": "CNSR", "dataset": "ADTTE", "role": "censoring"},
                    {"name": "BOR", "dataset": "ADRS", "role": "best overall response"},
                    {"name": "TRT01A", "dataset": "ADSL", "role": "treatment"}
                ],
                "analysisPopulation": {"name": "Responders", "filter": "IS_RESPONDER = 1 AND ITTFL = 'Y'"},
                "analysisDataset": "ADTTE",
                "resultGroups": [
                    {"id": "Experimental" if args.arm == 1 else "Control",
                     "n": result["n_responders"], "events": result["n_events"]}
                ],
                "documentation": "KM median DOR estimation among responders (CR+PR); event = progression or death",
                "analysisResultsData": {
                    "statistics": [
                        {"name": "median_dor", "value": result["median_dor"], "unit": "months"},
                        {"name": "ci_lower", "value": result["ci_lower"]},
                        {"name": "ci_upper", "value": result["ci_upper"]},
                        {"name": "n_responders", "value": result["n_responders"]},
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
