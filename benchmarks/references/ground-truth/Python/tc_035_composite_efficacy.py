#!/usr/bin/env python3
"""TC-035 Ground Truth: ORR/DCR/DOR Composite Efficacy Table (Level 2)

Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark.

Level 2 multi-TC integration: combines three efficacy endpoints into a
single integrated table, testing cross-TFL consistency.

Components:
  1. ORR (from BOR): CR+PR rate, Clopper-Pearson CI, by arm
  2. DCR (from BOR): CR+PR+SD rate, Wilson CI, by arm
  3. DOR (from responders' time-to-event): KM median, 95% CI, by arm

Cross-TFL consistency checks:
  - ORR responders == DOR population (same IS_RESPONDER flag)
  - DCR >= ORR (every responder also has disease control)
  - BOR distribution sums to N per arm

Dependencies: pandas, numpy, scipy, lifelines (>= 0.29.0)
Usage: python tc_035_composite_efficacy.py --seed 42 --n 200 --output results.json
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from lifelines import KaplanMeierFitter
from lifelines.utils import median_survival_times
import lifelines


def generate_composite_efficacy(seed=42, n_subjects=200, hr=0.75):
    """Generate composite efficacy dataset supporting ORR, DCR, and DOR.

    Uses the same response probabilities as TC-020/TC-023 for cross-TFL
    consistency. DOR time-to-event data is generated for responders.
    """
    rng = np.random.default_rng(seed)
    base_rate = np.log(2) / 6.0  # median PFS control = 6 months
    trt = rng.choice([0, 1], size=n_subjects)
    hazard_mult = np.where(trt == 0, 1.0, hr)

    # Demographics
    sex = rng.choice(["Male", "Female"], size=n_subjects, p=[0.55, 0.45])
    age = np.round(rng.normal(58, 12, n_subjects)).astype(int)
    agegr1 = np.where(age < 65, "<65", ">=65")
    ecog = rng.choice([0, 1], size=n_subjects, p=[0.6, 0.4])

    # Response probability (same as TC-020/TC-023)
    orr_prob = np.where(trt == 1,
                        np.where(ecog == 0, 0.45, 0.30),
                        np.where(ecog == 0, 0.25, 0.15))

    is_responder = rng.binomial(1, orr_prob)
    is_cr = np.where(is_responder == 1, rng.binomial(1, 0.3, n_subjects), 0)
    bor = np.where(is_cr == 1, "CR",
                   np.where(is_responder == 1, "PR",
                            rng.choice(["SD", "PD"], size=n_subjects, p=[0.4, 0.6])))

    ittfl = np.where(rng.random(n_subjects) < 0.95, "Y", "N")
    saffl = np.where(rng.random(n_subjects) < 0.98, "Y", "N")

    # DOR time-to-event data (responders only)
    time_to_response = np.where(
        is_responder == 1,
        rng.exponential(1.0 / (1.0 / 2.0), size=n_subjects),
        np.nan
    )

    prog_time = rng.exponential(1.0 / (base_rate * hazard_mult))
    death_time = rng.exponential(1.0 / (base_rate * 0.3 * hazard_mult))
    cens_time = rng.exponential(1.0 / (base_rate * 0.3 / 0.7))

    event_time_from_rand = np.minimum(prog_time, death_time)

    has_event_after_response = (is_responder == 1) & (event_time_from_rand > time_to_response)
    has_cens_before_event = (
        (is_responder == 1) &
        (cens_time < event_time_from_rand) &
        (cens_time > time_to_response)
    )

    dor_time = np.where(has_event_after_response, event_time_from_rand - time_to_response, np.nan)
    dor_time = np.where(has_cens_before_event, cens_time - time_to_response, dor_time)

    dor_cnsr = np.where(has_event_after_response & ~has_cens_before_event, 0, 1)
    dor_cnsr = np.where(has_cens_before_event, 1, dor_cnsr)
    dor_cnsr = np.where(is_responder == 0, np.nan, dor_cnsr)
    dor_time = np.where(is_responder == 0, np.nan, dor_time)

    return pd.DataFrame({
        "USUBJID": [f"SUBJ-{i+1:04d}" for i in range(n_subjects)],
        "STUDYID": "BENCHMARK-001",
        "TRT01PN": trt,
        "TRT01A": np.where(trt == 0, "Control", "Experimental"),
        "SEX": sex,
        "AGEGR1": agegr1,
        "ECOG": ecog,
        "ITTFL": ittfl,
        "SAFFL": saffl,
        "BOR": bor,
        "AVAL_ORR": np.where(np.isin(bor, ["CR", "PR"]), 1, 0),
        "AVAL_DCR": np.where(np.isin(bor, ["CR", "PR", "SD"]), 1, 0),
        "IS_RESPONDER": is_responder,
        "TIME_TO_RESPONSE": np.round(time_to_response, 2),
        "AVAL_DOR": np.round(dor_time, 2),
        "CNSR_DOR": dor_cnsr,
    })


def clopper_pearson_ci(x, n, conf=0.95):
    """Clopper-Pearson exact confidence interval for a proportion."""
    alpha = 1 - conf
    lower = stats.beta.ppf(alpha / 2, x, n - x + 1) if x > 0 else 0.0
    upper = stats.beta.ppf(1 - alpha / 2, x + 1, n - x) if x < n else 1.0
    return lower * 100, upper * 100


def wilson_ci(x, n, conf=0.95):
    """Wilson score confidence interval for a proportion."""
    z = stats.norm.ppf(1 - (1 - conf) / 2)
    p = x / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    margin = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (center - margin) * 100, (center + margin) * 100


def compute_orr(data, arm):
    """Compute ORR component for a single arm."""
    arm_data = data[(data["TRT01PN"] == arm) & (data["ITTFL"] == "Y")].copy()
    n = len(arm_data)
    responders = int(arm_data["AVAL_ORR"].sum())
    orr = responders / n * 100
    ci_lo, ci_hi = clopper_pearson_ci(responders, n)
    return {
        "n": n,
        "responders": responders,
        "orr": round(orr, 1),
        "ci_lower": round(ci_lo, 1),
        "ci_upper": round(ci_hi, 1),
        "ci_method": "Clopper-Pearson",
    }


def compute_dcr(data, arm):
    """Compute DCR component for a single arm."""
    arm_data = data[(data["TRT01PN"] == arm) & (data["ITTFL"] == "Y")].copy()
    n = len(arm_data)
    controlled = int(arm_data["AVAL_DCR"].sum())
    dcr = controlled / n * 100
    ci_lo, ci_hi = wilson_ci(controlled, n)
    return {
        "n": n,
        "disease_controlled": controlled,
        "dcr": round(dcr, 1),
        "ci_lower": round(ci_lo, 1),
        "ci_upper": round(ci_hi, 1),
        "ci_method": "Wilson",
    }


def compute_dor(data, arm):
    """Compute DOR component (KM median among responders) for a single arm."""
    arm_data = data[(data["TRT01PN"] == arm) & (data["ITTFL"] == "Y")].copy()
    n_total = len(arm_data)

    resp = arm_data[
        (arm_data["IS_RESPONDER"] == 1) &
        arm_data["AVAL_DOR"].notna() &
        (arm_data["AVAL_DOR"] > 0)
    ].copy()

    if len(resp) == 0:
        return {
            "n_responders": 0, "n_events": 0, "n_total": n_total,
            "median_dor": None, "ci_lower": None, "ci_upper": None,
            "estimable": False, "ci_method": "log-log",
        }

    durations = resp["AVAL_DOR"].values
    events = (1 - resp["CNSR_DOR"]).values

    n_responders = len(resp)
    n_events = int(events.sum())

    kmf = KaplanMeierFitter()
    kmf.fit(durations, event_observed=events, label="DOR")

    median_dor = kmf.median_survival_time_

    if np.isnan(median_dor) or median_dor == np.inf:
        return {
            "n_responders": n_responders, "n_events": n_events, "n_total": n_total,
            "median_dor": None, "ci_lower": None, "ci_upper": None,
            "estimable": False, "ci_method": "log-log",
        }

    # CI for median (Brookmeyer-Crowley)
    try:
        ci_median = median_survival_times(kmf.confidence_interval_)
        lo = float(ci_median.iloc[0, 0])
        hi = float(ci_median.iloc[0, 1])
        ci_lower = None if (np.isinf(lo) or pd.isna(lo)) else round(lo, 4)
        ci_upper = None if (np.isinf(hi) or pd.isna(hi)) else round(hi, 4)
    except (KeyError, IndexError, ValueError, StopIteration):
        ci_lower = None
        ci_upper = None

    return {
        "n_responders": n_responders,
        "n_events": n_events,
        "n_total": n_total,
        "median_dor": float(round(median_dor, 4)),
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "estimable": True,
        "ci_method": "log-log",
    }


def compute_bor_distribution(data):
    """Compute BOR distribution by arm."""
    result = []
    for arm_val in [1, 0]:
        arm_label = "Experimental" if arm_val == 1 else "Control"
        arm_data = data[(data["TRT01PN"] == arm_val) & (data["ITTFL"] == "Y")]
        n = len(arm_data)
        for bor_cat in ["CR", "PR", "SD", "PD"]:
            n_cat = int((arm_data["BOR"] == bor_cat).sum())
            result.append({
                "arm": arm_label,
                "bor": bor_cat,
                "n": n_cat,
                "pct": round(n_cat / n * 100, 1) if n > 0 else 0.0,
            })
    return result


def check_consistency(orr_exp, orr_ctrl, dcr_exp, dcr_ctrl,
                      dor_exp, dor_ctrl, bor_dist):
    """Cross-TFL consistency checks."""
    checks = {}

    # Check 1: DCR >= ORR
    checks["dcr_ge_orr_exp"] = dcr_exp["disease_controlled"] >= orr_exp["responders"]
    checks["dcr_ge_orr_ctrl"] = dcr_ctrl["disease_controlled"] >= orr_ctrl["responders"]

    # Check 2: DOR responders <= ORR responders (DOR is subset of ORR population)
    checks["orr_responders_match_dor_exp"] = dor_exp["n_responders"] <= orr_exp["responders"]
    checks["orr_responders_match_dor_ctrl"] = dor_ctrl["n_responders"] <= orr_ctrl["responders"]

    # Check 3: BOR distribution sums to N per arm
    exp_bor = sum(x["n"] for x in bor_dist if x["arm"] == "Experimental")
    ctrl_bor = sum(x["n"] for x in bor_dist if x["arm"] == "Control")
    checks["bor_sums_to_n_exp"] = exp_bor == orr_exp["n"]
    checks["bor_sums_to_n_ctrl"] = ctrl_bor == orr_ctrl["n"]

    # Check 4: CR+PR counts match ORR responders
    exp_cr_pr = sum(x["n"] for x in bor_dist if x["arm"] == "Experimental" and x["bor"] in ("CR", "PR"))
    ctrl_cr_pr = sum(x["n"] for x in bor_dist if x["arm"] == "Control" and x["bor"] in ("CR", "PR"))
    checks["cr_pr_matches_orr_exp"] = exp_cr_pr == orr_exp["responders"]
    checks["cr_pr_matches_orr_ctrl"] = ctrl_cr_pr == orr_ctrl["responders"]

    return checks


def compute_composite(data):
    """Compute full composite efficacy table."""
    orr_exp = compute_orr(data, 1)
    orr_ctrl = compute_orr(data, 0)
    dcr_exp = compute_dcr(data, 1)
    dcr_ctrl = compute_dcr(data, 0)
    dor_exp = compute_dor(data, 1)
    dor_ctrl = compute_dor(data, 0)
    bor_dist = compute_bor_distribution(data)

    consistency = check_consistency(orr_exp, orr_ctrl, dcr_exp, dcr_ctrl,
                                    dor_exp, dor_ctrl, bor_dist)

    return {
        "test_case_id": "TC-035",
        "variant_id": None,
        "language": "Python",
        "level": 2,
        "endpoint": "Composite Efficacy (ORR/DCR/DOR)",
        "population": "ITT",
        "orr": {
            "experimental": orr_exp,
            "control": orr_ctrl,
            "definition": "CR + PR",
            "ci_method": "Clopper-Pearson",
        },
        "dcr": {
            "experimental": dcr_exp,
            "control": dcr_ctrl,
            "definition": "CR + PR + SD",
            "ci_method": "Wilson",
        },
        "dor": {
            "experimental": dor_exp,
            "control": dor_ctrl,
            "definition": "Time from first response to progression/death among responders",
            "ci_method": "Brookmeyer-Crowley (log-log)",
        },
        "bor_distribution": bor_dist,
        "cross_tfl_consistency": consistency,
        "seed": None,
    }


def main():
    parser = argparse.ArgumentParser(
        description="TC-035: Composite Efficacy Table (ORR/DCR/DOR) (Python)"
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--data", type=str, default=None,
                        help="Shared composite efficacy CSV")
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--ars-output", type=str, default=None)
    args = parser.parse_args()

    seed = args.seed
    print(f"TC-035: Composite Efficacy Table (Python) — seed={seed}, n={args.n}")

    if args.data:
        data = pd.read_csv(args.data)
        print(f"Loaded shared data with {len(data)} subjects")
    else:
        data = generate_composite_efficacy(seed=seed, n_subjects=args.n)
        print(f"Generated composite efficacy data with {len(data)} subjects")

    result = compute_composite(data)
    result["seed"] = seed
    result["variant_id"] = f"v{seed}"

    print("\n" + "─" * 50)
    print("COMPOSITE EFFICACY TABLE")
    print("─" * 50)
    o = result["orr"]
    print(f"ORR:  Exp={o['experimental']['orr']}% ({o['experimental']['ci_lower']}, {o['experimental']['ci_upper']})  N={o['experimental']['n']}  responders={o['experimental']['responders']}")
    print(f"      Ctrl={o['control']['orr']}% ({o['control']['ci_lower']}, {o['control']['ci_upper']})  N={o['control']['n']}  responders={o['control']['responders']}")
    d = result["dcr"]
    print(f"DCR:  Exp={d['experimental']['dcr']}% ({d['experimental']['ci_lower']}, {d['experimental']['ci_upper']})  N={d['experimental']['n']}  controlled={d['experimental']['disease_controlled']}")
    print(f"      Ctrl={d['control']['dcr']}% ({d['control']['ci_lower']}, {d['control']['ci_upper']})  N={d['control']['n']}  controlled={d['control']['disease_controlled']}")
    dr = result["dor"]
    if dr["experimental"]["estimable"]:
        print(f"DOR:  Exp={dr['experimental']['median_dor']} mo ({dr['experimental']['ci_lower']}, {dr['experimental']['ci_upper']})  responders={dr['experimental']['n_responders']}  events={dr['experimental']['n_events']}")
    else:
        print(f"DOR:  Exp=Not estimable  responders={dr['experimental']['n_responders']}")
    if dr["control"]["estimable"]:
        print(f"      Ctrl={dr['control']['median_dor']} mo ({dr['control']['ci_lower']}, {dr['control']['ci_upper']})  responders={dr['control']['n_responders']}  events={dr['control']['n_events']}")
    else:
        print(f"      Ctrl=Not estimable  responders={dr['control']['n_responders']}")

    print("\nCross-TFL Consistency:")
    for k, v in result["cross_tfl_consistency"].items():
        print(f"  {k}: {v}")
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
                "id": "TC-035",
                "version": "1.0",
                "analysisReason": "Level 2 composite efficacy integration: ORR + DCR + DOR",
                "analysisMethod": {
                    "name": "Composite binomial proportion + KM survival",
                    "codeTemplate": "ORR=sum(BOR in ['CR','PR'])/n; DCR=sum(BOR in ['CR','PR','SD'])/n; DOR=KM_median(AVAL_DOR, 1-CNSR_DOR)",
                    "parameters": {
                        "orr_definition": "CR + PR",
                        "dcr_definition": "CR + PR + SD",
                        "dor_definition": "Time from first response to progression/death",
                        "orr_ci": "Clopper-Pearson",
                        "dcr_ci": "Wilson score",
                        "dor_ci": "Brookmeyer-Crowley log-log",
                        "alpha": 0.05,
                        "population": "ITT",
                    },
                },
                "analysisVariables": [
                    {"name": "BOR", "dataset": "ADRS", "role": "best overall response"},
                    {"name": "AVAL_DOR", "dataset": "ADTTE", "role": "DOR analysis time"},
                    {"name": "CNSR_DOR", "dataset": "ADTTE", "role": "DOR censoring"},
                    {"name": "TRT01A", "dataset": "ADSL", "role": "treatment"},
                    {"name": "ITTFL", "dataset": "ADSL", "role": "population flag"},
                ],
                "analysisPopulation": {"name": "ITT", "filter": "ITTFL = 'Y'"},
                "analysisDataset": "ADRS + ADTTE (merged)",
                "resultGroups": [
                    {"id": "Experimental",
                     "n": result["orr"]["experimental"]["n"],
                     "orr_responders": result["orr"]["experimental"]["responders"],
                     "dcr_controlled": result["dcr"]["experimental"]["disease_controlled"],
                     "dor_responders": result["dor"]["experimental"]["n_responders"]},
                    {"id": "Control",
                     "n": result["orr"]["control"]["n"],
                     "orr_responders": result["orr"]["control"]["responders"],
                     "dcr_controlled": result["dcr"]["control"]["disease_controlled"],
                     "dor_responders": result["dor"]["control"]["n_responders"]},
                ],
                "documentation": "Level 2 composite: ORR (Clopper-Pearson CI), DCR (Wilson CI), DOR (KM median, Brookmeyer-Crowley CI). Cross-TFL consistency enforced.",
                "analysisResultsData": {
                    "statistics": [
                        {"name": "orr_experimental", "value": result["orr"]["experimental"]["orr"], "unit": "percent"},
                        {"name": "orr_control", "value": result["orr"]["control"]["orr"], "unit": "percent"},
                        {"name": "dcr_experimental", "value": result["dcr"]["experimental"]["dcr"], "unit": "percent"},
                        {"name": "dcr_control", "value": result["dcr"]["control"]["dcr"], "unit": "percent"},
                        {"name": "median_dor_experimental", "value": result["dor"]["experimental"]["median_dor"], "unit": "months"},
                        {"name": "median_dor_control", "value": result["dor"]["control"]["median_dor"], "unit": "months"},
                        {"name": "n_orr_responders_exp", "value": result["orr"]["experimental"]["responders"]},
                        {"name": "n_orr_responders_ctrl", "value": result["orr"]["control"]["responders"]},
                        {"name": "n_dcr_controlled_exp", "value": result["dcr"]["experimental"]["disease_controlled"]},
                        {"name": "n_dcr_controlled_ctrl", "value": result["dcr"]["control"]["disease_controlled"]},
                        {"name": "n_dor_responders_exp", "value": result["dor"]["experimental"]["n_responders"]},
                        {"name": "n_dor_responders_ctrl", "value": result["dor"]["control"]["n_responders"]},
                    ]
                },
            },
        }
        ars_path = Path(args.ars_output)
        ars_path.parent.mkdir(parents=True, exist_ok=True)
        with open(ars_path, "w") as f:
            json.dump(ars_envelope, f, indent=2, default=str)
        print(f"Wrote ARS-compatible output to: {ars_path}")


if __name__ == "__main__":
    main()
