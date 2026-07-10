#!/usr/bin/env python3
"""TC-029: Adverse Event Summary Table by Severity.

Generates a safety summary table with:
- Rows: System Organ Class (SOC) → Preferred Term (PT) → Severity Grade
- Columns: Treatment arms (Experimental vs Control)
- Cells: n (%) for each AE term by severity, sorted by descending frequency
- Overall AEs by severity (Grade 1-5, CTCAE v5.0)
- Any AE, Serious AEs, and AEs leading to discontinuation by severity

Usage:
    python tc_029_ae_severity.py --seed 42 --n 200 --output tc-029-output.json
"""

import argparse
import json
import random
from collections import defaultdict

# --- Argument parsing ---
parser = argparse.ArgumentParser(description="TC-029 AE Summary by Severity")
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--n", type=int, default=200)
parser.add_argument("--output", type=str, default="tc-029-output.json")
parser.add_argument("--data-csv", type=str, default=None,
                    help="Load shared ADAE dataset from CSV instead of generating")
parser.add_argument("--ars-output", type=str, default=None,
                    help="Output ARS v1.0-compatible JSON envelope to this file")
args = parser.parse_args()

random.seed(args.seed)
n_subjects = args.n
n_arm = n_subjects // 2

# --- Data generation ---
AE_CATALOG = {
    "Gastrointestinal disorders": [
        "Nausea", "Diarrhoea", "Vomiting", "Abdominal pain", "Constipation"
    ],
    "General disorders and administration site conditions": [
        "Fatigue", "Pyrexia", "Oedema peripheral", "Asthenia"
    ],
    "Nervous system disorders": [
        "Headache", "Dizziness", "Neuropathy peripheral", "Dysgeusia"
    ],
    "Skin and subcutaneous tissue disorders": [
        "Rash", "Pruritus", "Alopecia", "Dry skin"
    ],
    "Investigations": [
        "ALT increased", "AST increased", "Blood creatinine increased", "Weight decreased"
    ],
    "Respiratory, thoracic and mediastinal disorders": [
        "Cough", "Dyspnoea", "Epistaxis"
    ],
    "Musculoskeletal and connective tissue disorders": [
        "Arthralgia", "Myalgia", "Back pain"
    ],
    "Infections and infestations": [
        "Upper respiratory tract infection", "Urinary tract infection", "Nasopharyngitis"
    ],
}

# CTCAE v5.0 severity grades: 1=Mild, 2=Moderate, 3=Severe, 4=Life-threatening, 5=Death
SEVERITY_GRADES = [1, 2, 3, 4, 5]
# Probability weights for severity grades (most AEs are grade 1-2)
SEVERITY_WEIGHTS = [0.50, 0.30, 0.15, 0.04, 0.01]

# Subject IDs
subjid_exp = [f"SUBJ-{i:04d}" for i in range(1, n_arm + 1)]
subjid_ctl = [f"SUBJ-{i:04d}" for i in range(n_arm + 1, n_subjects + 1)]


def generate_aes(subjids, arm, seed_offset):
    """Generate ADAE records with severity grades."""
    rng = random.Random(args.seed + seed_offset)
    records = []
    rate_mult = 1.3 if arm == "Experimental" else 1.0

    for soc, pts in AE_CATALOG.items():
        for pt in pts:
            base_rate = rng.uniform(0.02, 0.25)
            adj_rate = min(base_rate * rate_mult, 0.95)
            n_events = sum(1 for _ in subjids if rng.random() < adj_rate)
            if n_events > 0:
                affected = rng.sample(subjids, min(n_events, len(subjids)))
                for s in affected:
                    severity = rng.choices(SEVERITY_GRADES, weights=SEVERITY_WEIGHTS)[0]
                    aeser = "Y" if severity >= 4 else rng.choices(["Y", "N"], weights=[0.05, 0.95])[0]
                    aeacn = rng.choices(
                        ["DOSE NOT CHANGED", "DOSE REDUCED", "DRUG WITHDRAWN"],
                        weights=[0.7, 0.2, 0.1]
                    )[0]
                    # Higher severity → more likely dose reduced/withdrawn
                    if severity >= 3:
                        aeacn = rng.choices(
                            ["DOSE NOT CHANGED", "DOSE REDUCED", "DRUG WITHDRAWN"],
                            weights=[0.4, 0.35, 0.25]
                        )[0]
                    records.append({
                        "USUBJID": s,
                        "AEBODSYS": soc,
                        "AEDECOD": pt,
                        "AESEV": str(severity),
                        "AESER": aeser,
                        "AEACN": aeacn,
                        "TRT01A": arm,
                    })
    return records


if args.data_csv:
    import csv
    adae = []
    with open(args.data_csv, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            adae.append(row)
    # Derive n_exp/n_ctrl from data
    n_arm = len(set(r["USUBJID"] for r in adae if r["TRT01A"] == "Experimental"))
    n_arm_ctl = len(set(r["USUBJID"] for r in adae if r["TRT01A"] == "Control"))
    n_subjects = n_arm + n_arm_ctl
else:
    adae_exp = generate_aes(subjid_exp, "Experimental", 100)
    adae_ctl = generate_aes(subjid_ctl, "Control", 200)
    adae = adae_exp + adae_ctl


# --- Compute AE summary by severity ---
def unique_subjects(records, filter_fn=None):
    if filter_fn:
        return len(set(r["USUBJID"] for r in records if filter_fn(r)))
    return len(set(r["USUBJID"] for r in records))


# Summary by severity grade
severity_summary = []
for grade in SEVERITY_GRADES:
    exp_n = unique_subjects(adae, lambda r: r["AESEV"] == str(grade) and r["TRT01A"] == "Experimental")
    ctl_n = unique_subjects(adae, lambda r: r["AESEV"] == str(grade) and r["TRT01A"] == "Control")
    severity_summary.append({
        "grade": grade,
        "n_experimental": exp_n,
        "pct_experimental": round(100 * exp_n / n_arm, 1) if n_arm > 0 else 0.0,
        "n_control": ctl_n,
        "pct_control": round(100 * ctl_n / (n_subjects - n_arm), 1) if (n_subjects - n_arm) > 0 else 0.0,
    })

# Overall summary rows
any_exp = unique_subjects(adae, lambda r: r["TRT01A"] == "Experimental")
any_ctl = unique_subjects(adae, lambda r: r["TRT01A"] == "Control")
ser_exp = unique_subjects(adae, lambda r: r["AESER"] == "Y" and r["TRT01A"] == "Experimental")
ser_ctl = unique_subjects(adae, lambda r: r["AESER"] == "Y" and r["TRT01A"] == "Control")
disc_exp = unique_subjects(adae, lambda r: r["AEACN"] == "DRUG WITHDRAWN" and r["TRT01A"] == "Experimental")
disc_ctl = unique_subjects(adae, lambda r: r["AEACN"] == "DRUG WITHDRAWN" and r["TRT01A"] == "Control")

summary_rows = [
    {
        "category": "Any adverse event",
        "n_experimental": any_exp,
        "pct_experimental": round(100 * any_exp / n_arm, 1) if n_arm > 0 else 0.0,
        "n_control": any_ctl,
        "pct_control": round(100 * any_ctl / (n_subjects - n_arm), 1) if (n_subjects - n_arm) > 0 else 0.0,
    },
    {
        "category": "Serious adverse events",
        "n_experimental": ser_exp,
        "pct_experimental": round(100 * ser_exp / n_arm, 1) if n_arm > 0 else 0.0,
        "n_control": ser_ctl,
        "pct_control": round(100 * ser_ctl / (n_subjects - n_arm), 1) if (n_subjects - n_arm) > 0 else 0.0,
    },
    {
        "category": "AEs leading to discontinuation",
        "n_experimental": disc_exp,
        "pct_experimental": round(100 * disc_exp / n_arm, 1) if n_arm > 0 else 0.0,
        "n_control": disc_ctl,
        "pct_control": round(100 * disc_ctl / (n_subjects - n_arm), 1) if (n_subjects - n_arm) > 0 else 0.0,
    },
]

# By SOC → PT → Severity
pt_counts = defaultdict(lambda: {"Experimental": defaultdict(set), "Control": defaultdict(set)})
soc_counts = defaultdict(lambda: {"Experimental": defaultdict(set), "Control": defaultdict(set)})

for r in adae:
    grade = r["AESEV"]
    soc = r["AEBODSYS"]
    pt = r["AEDECOD"]
    arm = r["TRT01A"]
    pt_counts[(soc, pt)][arm][grade].add(r["USUBJID"])
    soc_counts[soc][arm][grade].add(r["USUBJID"])

# Build ae_table (SOC → PT → severity)
ae_table = []

for soc in AE_CATALOG:
    # SOC-level severity breakdown
    soc_row = {
        "category": "soc",
        "soc": soc,
        "pt": None,
        "severity": None,
        "n_experimental": len(set().union(*soc_counts[soc]["Experimental"].values())) if soc_counts[soc]["Experimental"] else 0,
        "n_control": len(set().union(*soc_counts[soc]["Control"].values())) if soc_counts[soc]["Control"] else 0,
    }
    soc_row["pct_experimental"] = round(100 * soc_row["n_experimental"] / n_arm, 1) if n_arm > 0 else 0.0
    soc_row["pct_control"] = round(100 * soc_row["n_control"] / (n_subjects - n_arm), 1) if (n_subjects - n_arm) > 0 else 0.0
    ae_table.append(soc_row)

    # SOC-level by severity
    for grade in SEVERITY_GRADES:
        exp_n = len(soc_counts[soc]["Experimental"].get(str(grade), set()))
        ctl_n = len(soc_counts[soc]["Control"].get(str(grade), set()))
        ae_table.append({
            "category": "soc_severity",
            "soc": soc,
            "pt": None,
            "severity": grade,
            "n_experimental": exp_n,
            "pct_experimental": round(100 * exp_n / n_arm, 1) if n_arm > 0 else 0.0,
            "n_control": ctl_n,
            "pct_control": round(100 * ctl_n / (n_subjects - n_arm), 1) if (n_subjects - n_arm) > 0 else 0.0,
        })

    # PTs within SOC, sorted by descending max frequency
    pts_in_soc = [(k, v) for k, v in pt_counts.items() if k[0] == soc]
    pts_in_soc.sort(key=lambda x: max(
        len(set().union(*x[1]["Experimental"].values())) if x[1]["Experimental"] else 0,
        len(set().union(*x[1]["Control"].values())) if x[1]["Control"] else 0
    ), reverse=True)

    for (s, pt), counts in pts_in_soc:
        pt_exp = len(set().union(*counts["Experimental"].values())) if counts["Experimental"] else 0
        pt_ctl = len(set().union(*counts["Control"].values())) if counts["Control"] else 0
        ae_table.append({
            "category": "pt",
            "soc": soc,
            "pt": pt,
            "severity": None,
            "n_experimental": pt_exp,
            "pct_experimental": round(100 * pt_exp / n_arm, 1) if n_arm > 0 else 0.0,
            "n_control": pt_ctl,
            "pct_control": round(100 * pt_ctl / (n_subjects - n_arm), 1) if (n_subjects - n_arm) > 0 else 0.0,
        })

        # PT by severity
        for grade in SEVERITY_GRADES:
            exp_n = len(counts["Experimental"].get(str(grade), set()))
            ctl_n = len(counts["Control"].get(str(grade), set()))
            ae_table.append({
                "category": "pt_severity",
                "soc": soc,
                "pt": pt,
                "severity": grade,
                "n_experimental": exp_n,
                "pct_experimental": round(100 * exp_n / n_arm, 1) if n_arm > 0 else 0.0,
                "n_control": ctl_n,
                "pct_control": round(100 * ctl_n / (n_subjects - n_arm), 1) if (n_subjects - n_arm) > 0 else 0.0,
            })

output = {
    "test_case_id": "TC-029",
    "title": "Adverse Event Summary Table by SOC, PT, and Severity",
    "parameters": {"seed": args.seed, "n_subjects": n_subjects},
    "population": {
        "description": "Safety population (SAFFL = 'Y')",
        "n_experimental": n_arm,
        "n_control": n_subjects - n_arm,
    },
    "severity_grades": SEVERITY_GRADES,
    "severity_summary": severity_summary,
    "summary": summary_rows,
    "ae_table": ae_table,
    "metadata": {
        "language": "Python",
        "packages": ["json", "random", "collections"],
    },
}

with open(args.output, "w") as f:
    json.dump(output, f, indent=2)

print(f"TC-029 output written to {args.output}")
print(f"  Subjects: {n_subjects} (Exp={n_arm}, Ctrl={n_subjects - n_arm})")
print(f"  AE records: {len(adae)}")
print(f"  Severity summary: {[(g, s['n_experimental'], s['n_control']) for g, s in zip(SEVERITY_GRADES, severity_summary)]}")

# --- ARS output (optional) ---
if args.ars_output:
    ars_envelope = {
        "analysisResult": {
            "id": "TC-029",
            "version": "1.0",
            "analysisReason": "Safety: AE summary by SOC, PT, and CTCAE severity grade",
            "analysisMethod": {
                "name": "AE summary by severity",
                "codeTemplate": "tc_029_ae_severity.py",
                "parameters": {
                    "severity_grades": SEVERITY_GRADES,
                    "population": "SAFETY",
                },
            },
            "analysisVariables": [
                {"name": "AEBODSYS", "dataset": "ADAE", "role": "category"},
                {"name": "AEDECOD", "dataset": "ADAE", "role": "category"},
                {"name": "AESEV", "dataset": "ADAE", "role": "severity"},
                {"name": "TRT01A", "dataset": "ADSL", "role": "treatment"},
            ],
            "analysisPopulation": {
                "id": "SAFETY",
                "filter": "SAFFL = 'Y'",
                "n": n_subjects,
            },
            "resultGroups": [
                {"id": "Experimental", "n": n_arm},
                {"id": "Control", "n": n_subjects - n_arm},
            ],
            "analysisResultsData": {
                "statistics": [
                    {"name": f"grade_{g}_n_experimental", "value": s["n_experimental"]}
                    for g, s in zip(SEVERITY_GRADES, severity_summary)
                ] + [
                    {"name": f"grade_{g}_n_control", "value": s["n_control"]}
                    for g, s in zip(SEVERITY_GRADES, severity_summary)
                ],
            },
        },
    }
    with open(args.ars_output, "w") as f:
        json.dump(ars_envelope, f, indent=2)
    print(f"ARS envelope written to {args.ars_output}")
