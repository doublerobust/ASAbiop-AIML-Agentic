#!/usr/bin/env python3
"""TC-014: Listing of Key Protocol Deviations.

Generates a listing of protocol deviations with:
- Subject ID, arm, deviation category, description, date, severity
- Categories: eligibility, consent, visit window, prohibited medication,
  dose modification, endpoint deviation
- Sorted by subject ID

Usage:
    python tc_014_pd_listing.py --seed 42 --n 200 --output tc-014-output.json
"""

import argparse
import json
import random
from datetime import datetime, timedelta

# --- Argument parsing ---
parser = argparse.ArgumentParser(description="TC-014 Protocol Deviation Listing")
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--n", type=int, default=200)
parser.add_argument("--output", type=str, default="tc-014-output.json")
args = parser.parse_args()

random.seed(args.seed)
n_subjects = args.n
n_arm = n_subjects // 2


# --- Protocol deviation catalog ---
PD_CATALOG = {
    "Eligibility": [
        ("ELIG-01", "Inclusion criterion not met: baseline lab value outside range"),
        ("ELIG-02", "Exclusion criterion violated: prior therapy within washout period"),
        ("ELIG-03", "Informed consent obtained after first dose"),
    ],
    "Visit Window": [
        ("VISIT-01", "Visit conducted outside protocol-specified window (+7 days)"),
        ("VISIT-02", "Missing required assessment at scheduled visit"),
        ("VISIT-03", "Visit conducted >14 days outside window"),
    ],
    "Prohibited Medication": [
        ("PROHIB-01", "Concomitant medication prohibited per protocol"),
        ("PROHIB-02", "Prior medication washout period not completed"),
    ],
    "Dose Modification": [
        ("DOSE-01", "Dose modification not per protocol algorithm"),
        ("DOSE-02", "Treatment delay >7 days without protocol authorization"),
        ("DOSE-03", "Dose administered outside ±10% of protocol-specified dose"),
    ],
    "Consent": [
        ("CONSENT-01", "Informed consent form version not current"),
        ("CONSENT-02", "Consent re-consent not obtained after protocol amendment"),
    ],
    "Endpoint Deviation": [
        ("ENDPT-01", "Primary endpoint assessment not performed per schedule"),
        ("ENDPT-02", "Imaging assessment not reviewed by independent radiologist"),
    ],
}


# --- Data generation ---
def generate_protocol_deviations(subjids, arm, seed_offset):
    """Generate protocol deviations for a subset of subjects."""
    random.seed(args.seed + seed_offset)
    records = []
    study_start = datetime(2025, 1, 15)

    # ~30% of subjects have at least one PD
    pd_subjects = random.sample(subjids, k=int(len(subjids) * 0.30))

    for subj in pd_subjects:
        # Each PD subject has 1-3 deviations
        n_pds = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]
        categories = random.sample(list(PD_CATALOG.keys()), k=min(n_pds, len(PD_CATALOG)))

        for cat in categories:
            code, desc = random.choice(PD_CATALOG[cat])
            # Random study day (1-365)
            study_day = random.randint(1, 365)
            pd_date = study_start + timedelta(days=study_day)

            severity = random.choices(
                ["Major", "Minor", "Critical"],
                weights=[0.5, 0.35, 0.15]
            )[0]

            records.append({
                "USUBJID": subj,
                "TRT01A": arm,
                "PD_CAT": cat,
                "PD_CODE": code,
                "PDDESC": desc,
                "PDDY": study_day,
                "PDDTC": pd_date.strftime("%Y-%m-%d"),
                "SEVERITY": severity,
            })

    return records


subjid_exp = [f"SUBJ-{i:04d}" for i in range(1, n_arm + 1)]
subjid_ctl = [f"SUBJ-{i:04d}" for i in range(n_arm + 1, n_subjects + 1)]

pds_exp = generate_protocol_deviations(subjid_exp, "Experimental", 100)
pds_ctl = generate_protocol_deviations(subjid_ctl, "Control", 200)
all_pds = pds_exp + pds_ctl

# Sort by subject ID
all_pds.sort(key=lambda x: (x["TRT01A"], x["USUBJID"], x["PDDY"]))

# --- Summary statistics ---
def compute_pd_summary(data, arm=None):
    if arm:
        subset = [r for r in data if r["TRT01A"] == arm]
    else:
        subset = data

    n_subjects_with_pd = len(set(r["USUBJID"] for r in subset))
    n_total_pds = len(subset)

    by_category = {}
    for cat in PD_CATALOG:
        cat_records = [r for r in subset if r["PD_CAT"] == cat]
        by_category[cat] = {
            "n_subjects": len(set(r["USUBJID"] for r in cat_records)),
            "n_deviations": len(cat_records),
        }

    by_severity = {}
    for sev in ["Critical", "Major", "Minor"]:
        by_severity[sev] = sum(1 for r in subset if r["SEVERITY"] == sev)

    return {
        "n_subjects_with_pd": n_subjects_with_pd,
        "n_total_deviations": n_total_pds,
        "by_category": by_category,
        "by_severity": by_severity,
    }


summary_all = compute_pd_summary(all_pds)
summary_exp = compute_pd_summary(all_pds, "Experimental")
summary_ctl = compute_pd_summary(all_pds, "Control")

# --- Output ---
output = {
    "test_case_id": "TC-014",
    "title": "Listing of Key Protocol Deviations",
    "parameters": {"seed": args.seed, "n_subjects": n_subjects},
    "population": {
        "description": "All randomized subjects",
        "n_experimental": n_arm,
        "n_control": n_arm,
    },
    "summary": {
        "all": summary_all,
        "experimental": summary_exp,
        "control": summary_ctl,
    },
    "listing": all_pds,
    "metadata": {
        "language": "Python",
        "sorting": "TRT01A, USUBJID, PDDY",
        "packages": ["json", "random", "datetime"],
    },
}

with open(args.output, "w") as f:
    json.dump(output, f, indent=2)

print(f"TC-014 output written to: {args.output}")
