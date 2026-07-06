#!/usr/bin/env python3
"""TC-028: Change in Tumor Size by Cycle (Longitudinal).

Computes percentage change from baseline in tumor size (sum of longest
diameters, SLD) at each treatment cycle (C2D1, C3D1, C4D1, C5D1, C6D1)
for each subject. Produces:
- Per-subject longitudinal trajectory
- Visit-wise summary statistics (mean, median, n, SE) by arm
- Overall summary (best response, worst response, time to best response)

This tests the agent's ability to:
1. Compute longitudinal % change from baseline across multiple visits
2. Handle missing visits (not all subjects have all assessments)
3. Summarize by visit and arm with descriptive statistics
4. Identify best/worst response timing

Usage:
    python tc_028_tumor_size_by_cycle.py --seed 42 --n 150 --output tc-028-output.json
"""

import argparse
import json
import math
import random
from statistics import mean, median

parser = argparse.ArgumentParser(description="TC-028: Change in Tumor Size by Cycle")
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--n", type=int, default=150)
parser.add_argument("--output", type=str, default="tc-028-output.json")
parser.add_argument("--data-csv", type=str, default=None,
                    help="Load shared longitudinal tumor data from CSV")
parser.add_argument("--ars-output", type=str, default=None,
                    help="Emit CDISC ARS v1.0 envelope to this file")
args = parser.parse_args()

random.seed(args.seed)
n_subjects = args.n

# Treatment cycles for assessment
CYCLES = ["C1D1", "C2D1", "C3D1", "C4D1", "C5D1", "C6D1"]
BASELINE_CYCLE = "C1D1"


def generate_longitudinal_tumor(n, seed_offset):
    """Generate longitudinal tumor size data with realistic trajectories.

    Each subject has a baseline (C1D1) and subsequent assessments at
    each cycle. Not all subjects have all assessments (dropout, PD, etc.).

    Trajectory model:
    - Experimental: initial shrinkage then possible regrowth
    - Control: slower shrinkage, earlier regrowth
    """
    random.seed(args.seed + seed_offset)
    records = []

    for i in range(n):
        subj = f"SUBJ-{i+1:04d}"
        arm = "Experimental" if i < n // 2 else "Control"
        baseline_sld = round(random.uniform(20, 120), 1)  # mm

        # Treatment effect parameters
        if arm == "Experimental":
            initial_response = random.gauss(-25, 15)  # % change per cycle
            regrowth_rate = random.gauss(5, 3)  # % per cycle after nadir
            nadir_cycle = random.choice([1, 2, 2, 3, 3, 4])
        else:
            initial_response = random.gauss(-8, 12)
            regrowth_rate = random.gauss(8, 4)
            nadir_cycle = random.choice([1, 1, 2, 2, 3])

        # Probability of missing a visit (increases over time)
        base_dropout = 0.05

        visits = []
        current_pct = 0.0  # Baseline is 0% change

        for cycle_idx, cycle in enumerate(CYCLES):
            if cycle == BASELINE_CYCLE:
                visits.append({
                    "cycle": cycle,
                    "cycle_num": 0,
                    "sld": baseline_sld,
                    "pct_change": 0.0,
                    "available": True,
                })
                continue

            # Dropout probability increases with each cycle
            dropout_prob = base_dropout * (cycle_idx)
            if random.random() < dropout_prob:
                # Subject dropped out — no further assessments
                break

            # Compute SLD trajectory
            cycle_num = cycle_idx  # 1, 2, 3, 4, 5
            if cycle_num <= nadir_cycle:
                # Responding phase
                pct = initial_response * cycle_num
            else:
                # Post-nadir regrowth
                nadir_pct = initial_response * nadir_cycle
                cycles_since_nadir = cycle_num - nadir_cycle
                pct = nadir_pct + regrowth_rate * cycles_since_nadir

            # Add noise
            pct += random.gauss(0, 3)

            sld = baseline_sld * (1 + pct / 100)
            sld = max(sld, 0)  # Can't be negative

            visits.append({
                "cycle": cycle,
                "cycle_num": cycle_num,
                "sld": round(sld, 1),
                "pct_change": round(pct, 1),
                "available": True,
            })

        records.append({
            "USUBJID": subj,
            "TRT01A": arm,
            "TRT01PN": 1 if arm == "Experimental" else 0,
            "BASELINE_SLD": baseline_sld,
            "N_VISITS": len(visits),
            "VISITS": visits,
        })

    return records


def compute_visit_summary(subjects, cycle, arm=None):
    """Compute summary statistics for a specific cycle."""
    if arm:
        subset = [s for s in subjects if s["TRT01A"] == arm]
    else:
        subset = subjects

    pct_changes = []
    slds = []
    n_with_visit = 0

    for subj in subset:
        for v in subj["VISITS"]:
            if v["cycle"] == cycle and v.get("available", True):
                pct_changes.append(v["pct_change"])
                slds.append(v["sld"])
                n_with_visit += 1
                break  # One per subject

    n_total = len(subset)
    n_missing = n_total - n_with_visit

    if pct_changes:
        return {
            "cycle": cycle,
            "arm": arm or "All",
            "n_total": n_total,
            "n_assessed": n_with_visit,
            "n_missing": n_missing,
            "mean_pct_change": round(mean(pct_changes), 2),
            "median_pct_change": round(median(pct_changes), 2),
            "se_pct_change": round(
                (sum((x - mean(pct_changes)) ** 2 for x in pct_changes) /
                 max(len(pct_changes) - 1, 1)) ** 0.5 / max(len(pct_changes), 1) ** 0.5,
                3
            ),
            "mean_sld": round(mean(slds), 2),
            "median_sld": round(median(slds), 2),
            "min_pct_change": round(min(pct_changes), 1),
            "max_pct_change": round(max(pct_changes), 1),
        }
    else:
        return {
            "cycle": cycle,
            "arm": arm or "All",
            "n_total": n_total,
            "n_assessed": 0,
            "n_missing": n_total,
            "mean_pct_change": None,
            "median_pct_change": None,
            "se_pct_change": None,
            "mean_sld": None,
            "median_sld": None,
            "min_pct_change": None,
            "max_pct_change": None,
        }


def compute_subject_summary(subjects):
    """Compute per-subject best/worst response and timing."""
    summaries = []
    for subj in subjects:
        pct_values = [v["pct_change"] for v in subj["VISITS"]
                      if v["cycle"] != BASELINE_CYCLE and v.get("available", True)]
        if not pct_values:
            summaries.append({
                "USUBJID": subj["USUBJID"],
                "TRT01A": subj["TRT01A"],
                "best_pct_change": None,
                "worst_pct_change": None,
                "time_to_best": None,
                "n_assessments": 0,
            })
            continue

        best_idx = min(range(len(pct_values)), key=lambda i: pct_values[i])
        worst_idx = max(range(len(pct_values)), key=lambda i: pct_values[i])

        visits_nonbaseline = [v for v in subj["VISITS"]
                              if v["cycle"] != BASELINE_CYCLE and v.get("available", True)]

        summaries.append({
            "USUBJID": subj["USUBJID"],
            "TRT01A": subj["TRT01A"],
            "best_pct_change": round(pct_values[best_idx], 1),
            "worst_pct_change": round(pct_values[worst_idx], 1),
            "time_to_best_cycle": visits_nonbaseline[best_idx]["cycle"],
            "time_to_worst_cycle": visits_nonbaseline[worst_idx]["cycle"],
            "n_assessments": len(pct_values),
        })
    return summaries


# --- Main ---
if args.data_csv:
    import csv
    subjects = []
    with open(args.data_csv, newline="") as f:
        reader = csv.DictReader(f)
        current_subj = None
        for row in reader:
            if row.get("USUBJID") != current_subj:
                if current_subj is not None:
                    subjects.append(records)
                current_subj = row["USUBJID"]
                records = {
                    "USUBJID": row["USUBJID"],
                    "TRT01A": row["TRT01A"],
                    "TRT01PN": int(row["TRT01PN"]),
                    "BASELINE_SLD": float(row["BASELINE_SLD"]),
                    "VISITS": [],
                }
            records["VISITS"].append({
                "cycle": row["CYCLE"],
                "cycle_num": int(row["CYCLE_NUM"]),
                "sld": float(row["SLD"]),
                "pct_change": float(row["PCT_CHANGE"]),
                "available": True,
            })
        if current_subj is not None:
            subjects.append(records)
else:
    subjects = generate_longitudinal_tumor(n_subjects, 200)

# Compute visit-wise summaries
visit_summaries = {}
for cycle in CYCLES:
    visit_summaries[cycle] = {
        "all": compute_visit_summary(subjects, cycle),
        "experimental": compute_visit_summary(subjects, cycle, "Experimental"),
        "control": compute_visit_summary(subjects, cycle, "Control"),
    }

# Compute per-subject summaries
subject_summaries = compute_subject_summary(subjects)

# Compute arm-level overall summaries
def arm_overall_summary(subjects, arm):
    subset = [s for s in subject_summaries if s["TRT01A"] == arm]
    best_values = [s["best_pct_change"] for s in subset if s["best_pct_change"] is not None]
    worst_values = [s["worst_pct_change"] for s in subset if s["worst_pct_change"] is not None]
    return {
        "arm": arm,
        "n_subjects": len(subset),
        "mean_best_pct_change": round(mean(best_values), 2) if best_values else None,
        "median_best_pct_change": round(median(best_values), 2) if best_values else None,
        "mean_worst_pct_change": round(mean(worst_values), 2) if worst_values else None,
        "median_worst_pct_change": round(median(worst_values), 2) if worst_values else None,
        "mean_n_assessments": round(mean([s["n_assessments"] for s in subset]), 1),
    }

overall_summary = {
    "experimental": arm_overall_summary(subjects, "Experimental"),
    "control": arm_overall_summary(subjects, "Control"),
}

output = {
    "test_case_id": "TC-028",
    "title": "Change in Tumor Size by Cycle (Longitudinal)",
    "parameters": {"seed": args.seed, "n_subjects": n_subjects},
    "cycles": CYCLES,
    "baseline_cycle": BASELINE_CYCLE,
    "visit_summaries": visit_summaries,
    "overall_summary": overall_summary,
    "subject_summaries": subject_summaries,
    "n_subjects": len(subjects),
    "metadata": {
        "language": "Python",
        "packages": ["json", "random", "statistics"],
    },
}

with open(args.output, "w") as f:
    json.dump(output, f, indent=2)

print(f"TC-028 output written to: {args.output}")

# --- ARS Output (optional) ---
if args.ars_output:
    ars_envelope = {
        "analysisResult": {
            "id": "TC-028",
            "version": "1.0",
            "analysisReason": "Longitudinal tumor size change assessment per RECIST 1.1",
        },
        "analysisMethod": {
            "name": "Descriptive statistics of percentage change from baseline in tumor size by cycle",
            "codeTemplate": "mean/median/min/max of pct_change by cycle and arm",
            "parameters": {
                "cycles": CYCLES,
                "baseline_cycle": BASELINE_CYCLE,
            },
        },
        "analysisVariables": [
            {"name": "SLD", "dataset": "ADTR", "role": "analysis"},
            {"name": "PCT_CHANGE", "dataset": "ADTR", "role": "derived"},
            {"name": "TRT01A", "dataset": "ADSL", "role": "grouping"},
            {"name": "AVISIT", "dataset": "ADTR", "role": "timing"},
        ],
        "analysisPopulation": {
            "name": "ITT",
            "filter": "ITTFL='Y'",
        },
        "resultGroups": [
            {"name": "Experimental", "n": sum(1 for s in subjects if s["TRT01A"] == "Experimental")},
            {"name": "Control", "n": sum(1 for s in subjects if s["TRT01A"] == "Control")},
        ],
        "analysisResultsData": {
            "statistics": [
                {"name": f"mean_pct_change_{cyc}_experimental",
                 "value": visit_summaries[cyc]["experimental"]["mean_pct_change"]}
                for cyc in CYCLES
            ] + [
                {"name": f"mean_pct_change_{cyc}_control",
                 "value": visit_summaries[cyc]["control"]["mean_pct_change"]}
                for cyc in CYCLES
            ]
        },
    }
    with open(args.ars_output, "w") as f:
        json.dump(ars_envelope, f, indent=2)
    print(f"TC-028 ARS envelope written to: {args.ars_output}")
