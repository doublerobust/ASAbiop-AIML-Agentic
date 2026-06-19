#!/usr/bin/env python3
"""TC-013: Waterfall Plot Data — Best % Change in Tumor Size.

Computes best percentage change from baseline in tumor size (sum of
longest diameters) for each subject, categorized as:
- Complete Response (CR): -100%
- Partial Response (PR): >= -30% decrease
- Progressive Disease (PD): >= +20% increase
- Stable Disease (SD): neither PR nor PD

Per RECIST 1.1 criteria.

Usage:
    python tc_013_waterfall.py --seed 42 --n 150 --output tc-013-output.json
"""

import argparse
import json
import random
from statistics import median as _median

# --- Argument parsing ---
parser = argparse.ArgumentParser(description="TC-013 Waterfall Plot Data")
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--n", type=int, default=150)
parser.add_argument("--output", type=str, default="tc-013-output.json")
args = parser.parse_args()

random.seed(args.seed)
n_subjects = args.n


# --- Data generation ---
def generate_tumor_response(n, seed_offset):
    """Generate best % change in tumor size with realistic distribution."""
    random.seed(args.seed + seed_offset)
    records = []

    for i in range(n):
        subj = f"SUBJ-{i+1:04d}"
        arm = "Experimental" if i < n // 2 else "Control"

        # Treatment effect: experimental arm has more responders
        if arm == "Experimental":
            # Distribution: ~15% CR, ~35% PR, ~30% SD, ~20% PD
            category = random.choices(
                ["CR", "PR", "SD", "PD"],
                weights=[0.15, 0.35, 0.30, 0.20]
            )[0]
        else:
            # Control: ~5% CR, ~20% PR, ~35% SD, ~40% PD
            category = random.choices(
                ["CR", "PR", "SD", "PD"],
                weights=[0.05, 0.20, 0.35, 0.40]
            )[0]

        # Generate % change within category bounds
        if category == "CR":
            pct_change = -100.0
        elif category == "PR":
            pct_change = random.uniform(-99.0, -30.0)
        elif category == "SD":
            pct_change = random.uniform(-29.9, 19.9)
        else:  # PD
            pct_change = random.uniform(20.0, 200.0)

        # Baseline tumor size (mm)
        baseline_sld = random.uniform(15, 100)

        records.append({
            "USUBJID": subj,
            "TRT01A": arm,
            "BASELINE": round(baseline_sld, 1),
            "BESTPCHG": round(pct_change, 1),
            "BOR": category,
        })

    return records


subjects = generate_tumor_response(n_subjects, 100)

# Sort by best % change (ascending for waterfall)
subjects.sort(key=lambda x: x["BESTPCHG"])

# --- Summary statistics ---
def compute_summary(data, arm=None):
    if arm:
        subset = [r for r in data if r["TRT01A"] == arm]
    else:
        subset = data

    n = len(subset)
    n_cr = sum(1 for r in subset if r["BOR"] == "CR")
    n_pr = sum(1 for r in subset if r["BOR"] == "PR")
    n_sd = sum(1 for r in subset if r["BOR"] == "SD")
    n_pd = sum(1 for r in subset if r["BOR"] == "PD")
    orr = round(100 * (n_cr + n_pr) / n, 1) if n > 0 else 0
    dcr = round(100 * (n_cr + n_pr + n_sd) / n, 1) if n > 0 else 0

    changes = [r["BESTPCHG"] for r in subset]
    # BUGFIX: sorted(changes)[len(changes)//2] is NOT the median for even-length
    # lists (it takes the upper-middle element, never averaging the two middle
    # values). Use a correct median so this ground truth is actually correct.
    median_change = round(_median(changes), 1) if changes else None
    mean_change = round(sum(changes) / len(changes), 1) if changes else None

    return {
        "n": n,
        "n_cr": n_cr,
        "n_pr": n_pr,
        "n_sd": n_sd,
        "n_pd": n_pd,
        "orr_pct": orr,
        "dcr_pct": dcr,
        "median_best_pct_change": median_change,
        "mean_best_pct_change": mean_change,
    }


summary_exp = compute_summary(subjects, "Experimental")
summary_ctl = compute_summary(subjects, "Control")
summary_all = compute_summary(subjects)

# --- Output ---
output = {
    "test_case_id": "TC-013",
    "title": "Waterfall Plot — Best Percentage Change in Tumor Size",
    "parameters": {"seed": args.seed, "n_subjects": n_subjects},
    "response_criteria": "RECIST 1.1",
    "thresholds": {
        "CR": -100.0,
        "PR": -30.0,
        "PD": 20.0,
    },
    "summary": {
        "all": summary_all,
        "experimental": summary_exp,
        "control": summary_ctl,
    },
    "subjects": subjects,
    "metadata": {
        "language": "Python",
        "sorting": "ascending by BESTPCHG",
        "packages": ["json", "random", "statistics"],
    },
}

with open(args.output, "w") as f:
    json.dump(output, f, indent=2)

print(f"TC-013 output written to: {args.output}")
