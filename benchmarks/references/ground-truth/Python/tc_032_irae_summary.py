#!/usr/bin/env python3
"""TC-032: Immune-Related Adverse Event (irAE) Summary.

Generates an I-O specific safety summary table with:
- Rows: irAE categories (Endocrine, Dermatologic, Hepatic, GI, Pulmonary, Other)
  → Preferred Term (PT) → Severity Grade (CTCAE v5.0)
- Columns: Treatment arms (Experimental vs Control)
- Cells: n (%) for each irAE term by severity
- Overall irAE summary: Any irAE, Grade 3+, irAE leading to discontinuation
- Median time-to-onset by category

Usage:
    python tc_032_irae_summary.py --seed 42 --n 200 --output tc-032-output.json
    python tc_032_irae_summary.py --data-csv adae.csv --output tc-032-output.json
    python tc_032_irae_summary.py --ars-output tc-032-ars.json
"""

import argparse
import json
import random
from collections import defaultdict

# --- Argument parsing ---
parser = argparse.ArgumentParser(description="TC-032 irAE Summary")
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--n", type=int, default=200)
parser.add_argument("--output", type=str, default="tc-032-output.json")
parser.add_argument("--data-csv", type=str, default=None,
                    help="Load shared ADAE dataset from CSV instead of generating")
parser.add_argument("--ars-output", type=str, default=None,
                    help="Output ARS v1.0-compatible JSON envelope to this file")
args = parser.parse_args()

random.seed(args.seed)
n_subjects = args.n
n_arm = n_subjects // 2

# --- Immune-related AE categories (pre-specified per I-O literature) ---
IRAE_CATEGORIES = {
    "Endocrine disorders": {
        "soc_list": ["Endocrine disorders"],
        "pts": [
            "Hypothyroidism", "Hyperthyroidism", "Thyroiditis",
            "Adrenal insufficiency", "Hypophysitis", "Type 1 diabetes mellitus",
            "Autoimmune diabetes"
        ]
    },
    "Dermatologic disorders": {
        "soc_list": ["Skin and subcutaneous tissue disorders"],
        "pts": [
            "Rash maculo-papular", "Vitiligo", "Pruritus",
            "Alopecia", "Psoriasis", "Dermatitis bullous",
            "Erythema multiforme"
        ]
    },
    "Hepatic disorders": {
        "soc_list": ["Hepatobiliary disorders"],
        "pts": [
            "Hepatitis", "Autoimmune hepatitis", "Hepatotoxicity",
            "Blood bilirubin increased", "Liver function test abnormal"
        ]
    },
    "Gastrointestinal disorders": {
        "soc_list": ["Gastrointestinal disorders"],
        "pts": [
            "Colitis", "Diarrhoea", "Enterocolitis",
            "Gastritis", "Pancreatitis"
        ]
    },
    "Pulmonary disorders": {
        "soc_list": ["Respiratory, thoracic and mediastinal disorders"],
        "pts": [
            "Pneumonitis", "Interstitial lung disease", "Pleural effusion",
            "Cough", "Dyspnoea"
        ]
    },
    "Other immune-related": {
        "soc_list": ["Musculoskeletal and connective tissue disorders",
                     "Renal and urinary disorders",
                     "Blood and lymphatic system disorders",
                     "Nervous system disorders"],
        "pts": [
            "Arthritis", "Myositis", "Nephritis",
            "Autoimmune nephritis", "Anaemia", "Neutropenia",
            "Guillain-Barre syndrome", "Myasthenia gravis",
            "Encephalitis", "Meningitis aseptic"
        ]
    }
}

# CTCAE v5.0 severity grades
SEVERITY_GRADES = [1, 2, 3, 4, 5]
# irAEs tend to be more evenly distributed than general AEs
IRAE_SEVERITY_WEIGHTS = [0.35, 0.30, 0.20, 0.10, 0.05]

# Subject IDs
subjid_exp = [f"SUBJ-{i:04d}" for i in range(1, n_arm + 1)]
subjid_ctl = [f"SUBJ-{i:04d}" for i in range(n_arm + 1, n_subjects + 1)]


def generate_irae_records(subjids, arm, seed_offset):
    """Generate ADAE records for immune-related AEs."""
    rng = random.Random(args.seed + seed_offset)
    records = []

    # I-O agents (e.g. checkpoint inhibitors) have higher irAE rates
    rate_mult = 1.5 if arm == "Experimental" else 0.6

    for category, cat_info in IRAE_CATEGORIES.items():
        for pt in cat_info["pts"]:
            base_rate = rng.uniform(0.01, 0.15)
            adj_rate = min(base_rate * rate_mult, 0.90)
            n_events = sum(1 for _ in subjids if rng.random() < adj_rate)

            if n_events > 0:
                affected = rng.sample(subjids, min(n_events, len(subjids)))
                for s in affected:
                    severity = rng.choices(SEVERITY_GRADES, weights=IRAE_SEVERITY_WEIGHTS)[0]

                    # irAEs: higher severity → more likely to lead to treatment modification
                    if severity >= 3:
                        aeacn = rng.choices(
                            ["DOSE NOT CHANGED", "DOSE REDUCED", "DRUG WITHDRAWN",
                             "DRUG INTERRUPTED", "CORTICOSTEROID THERAPY"],
                            weights=[0.20, 0.15, 0.20, 0.25, 0.20]
                        )[0]
                    else:
                        aeacn = rng.choices(
                            ["DOSE NOT CHANGED", "DOSE REDUCED", "DRUG WITHDRAWN",
                             "DRUG INTERRUPTED", "CORTICOSTEROID THERAPY"],
                            weights=[0.55, 0.10, 0.05, 0.10, 0.20]
                        )[0]

                    # Time to onset (days from randomization): typically 1-6 months for irAEs
                    ttonset = rng.randint(14, 180)

                    records.append({
                        "USUBJID": s,
                        "AEBODSYS": cat_info["soc_list"][0],  # primary SOC
                        "AEDECOD": pt,
                        "AESEV": str(severity),
                        "AESER": "Y" if severity >= 4 else rng.choices(["Y", "N"], weights=[0.08, 0.92])[0],
                        "AEACN": aeacn,
                        "AEFLAG": "IMMUNE",
                        "TRT01A": arm,
                        "ASTDT": ttonset,  # days from randomization
                    })
    return records


if args.data_csv:
    import csv
    adae = []
    with open(args.data_csv, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            adae.append(row)
    n_arm = len(set(r["USUBJID"] for r in adae if r["TRT01A"] == "Experimental"))
    n_arm_ctl = len(set(r["USUBJID"] for r in adae if r["TRT01A"] == "Control"))
    n_subjects = n_arm + n_arm_ctl
else:
    adae_exp = generate_irae_records(subjid_exp, "Experimental", 1100)
    adae_ctl = generate_irae_records(subjid_ctl, "Control", 1200)
    adae = adae_exp + adae_ctl

# Filter to immune-related AEs only
irae_records = [r for r in adae if r.get("AEFLAG") == "IMMUNE"]

# --- Classify irAEs by category ---
def classify_irae(pt):
    """Classify a PT into irAE category."""
    for category, cat_info in IRAE_CATEGORIES.items():
        if pt in cat_info["pts"]:
            return category
    return "Other immune-related"


# --- Compute irAE summary ---
def unique_subjects(records, filter_fn=None):
    if filter_fn:
        return len(set(r["USUBJID"] for r in records if filter_fn(r)))
    return len(set(r["USUBJID"] for r in records))


# Overall irAE summary
any_irae_exp = unique_subjects(irae_records, lambda r: r["TRT01A"] == "Experimental")
any_irae_ctl = unique_subjects(irae_records, lambda r: r["TRT01A"] == "Control")
g3plus_exp = unique_subjects(irae_records, lambda r: r["TRT01A"] == "Experimental" and int(r["AESEV"]) >= 3)
g3plus_ctl = unique_subjects(irae_records, lambda r: r["TRT01A"] == "Control" and int(r["AESEV"]) >= 3)
disc_exp = unique_subjects(irae_records, lambda r: r["TRT01A"] == "Experimental" and r["AEACN"] == "DRUG WITHDRAWN")
disc_ctl = unique_subjects(irae_records, lambda r: r["TRT01A"] == "Control" and r["AEACN"] == "DRUG WITHDRAWN")
steroid_exp = unique_subjects(irae_records, lambda r: r["TRT01A"] == "Experimental" and "CORTICOSTEROID" in r["AEACN"])
steroid_ctl = unique_subjects(irae_records, lambda r: r["TRT01A"] == "Control" and "CORTICOSTEROID" in r["AEACN"])

n_exp = n_arm
n_ctl = n_subjects - n_arm

summary_rows = [
    {
        "category": "Any immune-related AE",
        "n_experimental": any_irae_exp,
        "pct_experimental": round(100 * any_irae_exp / n_exp, 1) if n_exp > 0 else 0.0,
        "n_control": any_irae_ctl,
        "pct_control": round(100 * any_irae_ctl / n_ctl, 1) if n_ctl > 0 else 0.0,
    },
    {
        "category": "Grade ≥3 immune-related AE",
        "n_experimental": g3plus_exp,
        "pct_experimental": round(100 * g3plus_exp / n_exp, 1) if n_exp > 0 else 0.0,
        "n_control": g3plus_ctl,
        "pct_control": round(100 * g3plus_ctl / n_ctl, 1) if n_ctl > 0 else 0.0,
    },
    {
        "category": "irAE leading to discontinuation",
        "n_experimental": disc_exp,
        "pct_experimental": round(100 * disc_exp / n_exp, 1) if n_exp > 0 else 0.0,
        "n_control": disc_ctl,
        "pct_control": round(100 * disc_ctl / n_ctl, 1) if n_ctl > 0 else 0.0,
    },
    {
        "category": "irAE requiring corticosteroids",
        "n_experimental": steroid_exp,
        "pct_experimental": round(100 * steroid_exp / n_exp, 1) if n_exp > 0 else 0.0,
        "n_control": steroid_ctl,
        "pct_control": round(100 * steroid_ctl / n_ctl, 1) if n_ctl > 0 else 0.0,
    },
]

# --- Severity summary by grade ---
severity_summary = []
for grade in SEVERITY_GRADES:
    exp_n = unique_subjects(irae_records, lambda r, g=grade: r["AESEV"] == str(g) and r["TRT01A"] == "Experimental")
    ctl_n = unique_subjects(irae_records, lambda r, g=grade: r["AESEV"] == str(g) and r["TRT01A"] == "Control")
    severity_summary.append({
        "grade": grade,
        "n_experimental": exp_n,
        "pct_experimental": round(100 * exp_n / n_exp, 1) if n_exp > 0 else 0.0,
        "n_control": ctl_n,
        "pct_control": round(100 * ctl_n / n_ctl, 1) if n_ctl > 0 else 0.0,
    })

# --- By category → PT → Severity ---
cat_counts = defaultdict(lambda: {"Experimental": defaultdict(set), "Control": defaultdict(set)})
pt_counts = defaultdict(lambda: {"Experimental": defaultdict(set), "Control": defaultdict(set)})

for r in irae_records:
    cat = classify_irae(r["AEDECOD"])
    pt = r["AEDECOD"]
    arm = r["TRT01A"]
    grade = r["AESEV"]
    cat_counts[cat][arm][grade].add(r["USUBJID"])
    pt_counts[(cat, pt)][arm][grade].add(r["USUBJID"])

# Build irae_table
irae_table = []
category_order = list(IRAE_CATEGORIES.keys())

for cat in category_order:
    cat_exp = len(set().union(*cat_counts[cat]["Experimental"].values())) if cat_counts[cat]["Experimental"] else 0
    cat_ctl = len(set().union(*cat_counts[cat]["Control"].values())) if cat_counts[cat]["Control"] else 0

    irae_table.append({
        "category": "category",
        "irae_category": cat,
        "pt": None,
        "severity": None,
        "n_experimental": cat_exp,
        "pct_experimental": round(100 * cat_exp / n_exp, 1) if n_exp > 0 else 0.0,
        "n_control": cat_ctl,
        "pct_control": round(100 * cat_ctl / n_ctl, 1) if n_ctl > 0 else 0.0,
    })

    # Category by severity
    for grade in SEVERITY_GRADES:
        exp_n = len(cat_counts[cat]["Experimental"].get(str(grade), set()))
        ctl_n = len(cat_counts[cat]["Control"].get(str(grade), set()))
        irae_table.append({
            "category": "category_severity",
            "irae_category": cat,
            "pt": None,
            "severity": grade,
            "n_experimental": exp_n,
            "pct_experimental": round(100 * exp_n / n_exp, 1) if n_exp > 0 else 0.0,
            "n_control": ctl_n,
            "pct_control": round(100 * ctl_n / n_ctl, 1) if n_ctl > 0 else 0.0,
        })

    # PTs within category, sorted by descending max frequency
    pts_in_cat = [(k, v) for k, v in pt_counts.items() if k[0] == cat]
    pts_in_cat.sort(key=lambda x: max(
        len(set().union(*x[1]["Experimental"].values())) if x[1]["Experimental"] else 0,
        len(set().union(*x[1]["Control"].values())) if x[1]["Control"] else 0
    ), reverse=True)

    for (c, pt), counts in pts_in_cat:
        pt_exp = len(set().union(*counts["Experimental"].values())) if counts["Experimental"] else 0
        pt_ctl = len(set().union(*counts["Control"].values())) if counts["Control"] else 0
        irae_table.append({
            "category": "pt",
            "irae_category": cat,
            "pt": pt,
            "severity": None,
            "n_experimental": pt_exp,
            "pct_experimental": round(100 * pt_exp / n_exp, 1) if n_exp > 0 else 0.0,
            "n_control": pt_ctl,
            "pct_control": round(100 * pt_ctl / n_ctl, 1) if n_ctl > 0 else 0.0,
        })

        # PT by severity
        for grade in SEVERITY_GRADES:
            exp_n = len(counts["Experimental"].get(str(grade), set()))
            ctl_n = len(counts["Control"].get(str(grade), set()))
            irae_table.append({
                "category": "pt_severity",
                "irae_category": cat,
                "pt": pt,
                "severity": grade,
                "n_experimental": exp_n,
                "pct_experimental": round(100 * exp_n / n_exp, 1) if n_exp > 0 else 0.0,
                "n_control": ctl_n,
                "pct_control": round(100 * ctl_n / n_ctl, 1) if n_ctl > 0 else 0.0,
            })

# --- Median time-to-onset by category ---
onset_by_cat = defaultdict(lambda: {"Experimental": [], "Control": []})
for r in irae_records:
    cat = classify_irae(r["AEDECOD"])
    onset_by_cat[cat][r["TRT01A"]].append(int(r["ASTDT"]))

onset_summary = []
for cat in category_order:
    exp_onsets = sorted(onset_by_cat[cat]["Experimental"])
    ctl_onsets = sorted(onset_by_cat[cat]["Control"])

    def median_val(lst):
        if not lst:
            return None
        n = len(lst)
        if n % 2 == 1:
            return lst[n // 2]
        else:
            return round((lst[n // 2 - 1] + lst[n // 2]) / 2, 1)

    onset_summary.append({
        "irae_category": cat,
        "median_onset_experimental": median_val(exp_onsets),
        "median_onset_control": median_val(ctl_onsets),
        "n_experimental": len(exp_onsets),
        "n_control": len(ctl_onsets),
    })

output = {
    "test_case_id": "TC-032",
    "title": "Immune-Related Adverse Event Summary",
    "parameters": {"seed": args.seed, "n_subjects": n_subjects},
    "population": {
        "description": "Safety population (SAFFL = 'Y')",
        "n_experimental": n_exp,
        "n_control": n_ctl,
    },
    "severity_grades": SEVERITY_GRADES,
    "severity_summary": severity_summary,
    "summary": summary_rows,
    "irae_table": irae_table,
    "onset_summary": onset_summary,
    "metadata": {
        "language": "Python",
        "packages": ["json", "random", "collections"],
    },
}

with open(args.output, "w") as f:
    json.dump(output, f, indent=2)

print(f"TC-032 output written to {args.output}")
print(f"  Subjects: {n_subjects} (Exp={n_exp}, Ctrl={n_ctl})")
print(f"  irAE records: {len(irae_records)}")
print(f"  Categories: {len(category_order)}")
print(f"  Any irAE: Exp={any_irae_exp} ({round(100*any_irae_exp/n_exp,1)}%), Ctrl={any_irae_ctl} ({round(100*any_irae_ctl/n_ctl,1)}%)")
print(f"  Grade ≥3: Exp={g3plus_exp}, Ctrl={g3plus_ctl}")

# --- ARS output (optional) ---
if args.ars_output:
    ars_envelope = {
        "analysisResult": {
            "id": "TC-032",
            "version": "1.0",
            "analysisReason": "Safety: immune-related AE summary by category and severity",
            "analysisMethod": {
                "name": "irAE summary by category and severity",
                "codeTemplate": "tc_032_irae_summary.py",
                "parameters": {
                    "severity_grades": SEVERITY_GRADES,
                    "irae_categories": list(IRAE_CATEGORIES.keys()),
                    "population": "SAFETY",
                    "irae_filter": "AEFLAG = 'IMMUNE'",
                },
            },
            "analysisVariables": [
                {"name": "AEDECOD", "dataset": "ADAE", "role": "category"},
                {"name": "AESEV", "dataset": "ADAE", "role": "severity"},
                {"name": "AEFLAG", "dataset": "ADAE", "role": "immune_flag"},
                {"name": "TRT01A", "dataset": "ADSL", "role": "treatment"},
                {"name": "ASTDT", "dataset": "ADAE", "role": "onset_date"},
            ],
            "analysisPopulation": {
                "id": "SAFETY",
                "filter": "SAFFL = 'Y' AND AEFLAG = 'IMMUNE'",
                "n": n_subjects,
            },
            "resultGroups": [
                {"id": "Experimental", "n": n_exp},
                {"id": "Control", "n": n_ctl},
            ],
            "analysisResultsData": {
                "statistics": [
                    {"name": f"grade_{g}_n_experimental", "value": s["n_experimental"]}
                    for g, s in zip(SEVERITY_GRADES, severity_summary)
                ] + [
                    {"name": f"grade_{g}_n_control", "value": s["n_control"]}
                    for g, s in zip(SEVERITY_GRADES, severity_summary)
                ] + [
                    {"name": "any_irae_n_experimental", "value": any_irae_exp},
                    {"name": "any_irae_n_control", "value": any_irae_ctl},
                    {"name": "g3plus_n_experimental", "value": g3plus_exp},
                    {"name": "g3plus_n_control", "value": g3plus_ctl},
                ],
                "timeToOnset": [
                    {
                        "category": o["irae_category"],
                        "median_experimental": o["median_onset_experimental"],
                        "median_control": o["median_onset_control"],
                    }
                    for o in onset_summary
                ],
            },
        },
    }
    with open(args.ars_output, "w") as f:
        json.dump(ars_envelope, f, indent=2)
    print(f"ARS envelope written to {args.ars_output}")
