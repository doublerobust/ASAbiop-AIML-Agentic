#!/usr/bin/env python3
"""TC-011: Adverse Event Summary Table by SOC and Preferred Term.

Generates a safety summary table with:
- Rows: System Organ Class (SOC) → Preferred Term (PT) hierarchy
- Columns: Treatment arms (Experimental vs Control)
- Cells: n (%) for each AE term, sorted by descending frequency
- Overall AEs, Serious AEs, and AEs leading to discontinuation

Usage:
    python tc_011_ae_summary.py --seed 42 --n 200 --output tc-011-output.json
"""

import argparse
import json
import random
from collections import defaultdict
from datetime import datetime

# --- Argument parsing ---
parser = argparse.ArgumentParser(description="TC-011 AE Summary Table")
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--n", type=int, default=200)
parser.add_argument("--output", type=str, default="tc-011-output.json")
args = parser.parse_args()

random.seed(args.seed)
n_subjects = args.n
n_arm = n_subjects // 2

# --- Data generation ---
# Define SOC/PT hierarchy with realistic frequencies
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

# Subject IDs
subjid_exp = [f"SUBJ-{i:04d}" for i in range(1, n_arm + 1)]
subjid_ctl = [f"SUBJ-{i:04d}" for i in range(n_arm + 1, n_subjects + 1)]

# Generate AE records
def generate_aes(subjids, arm, seed_offset):
    random.seed(args.seed + seed_offset)
    records = []
    rate_mult = 1.3 if arm == "Experimental" else 1.0

    for soc, pts in AE_CATALOG.items():
        for pt in pts:
            base_rate = random.uniform(0.02, 0.25)
            adj_rate = min(base_rate * rate_mult, 0.95)
            n_events = sum(1 for _ in subjids if random.random() < adj_rate)
            if n_events > 0:
                affected = random.sample(subjids, min(n_events, len(subjids)))
                for s in affected:
                    aeser = random.choices(["Y", "N"], weights=[0.1, 0.9])[0]
                    aeacn = random.choices(
                        ["DOSE NOT CHANGED", "DOSE REDUCED", "DRUG WITHDRAWN"],
                        weights=[0.7, 0.2, 0.1]
                    )[0]
                    records.append({
                        "USUBJID": s,
                        "AEBODSYS": soc,
                        "AEDECOD": pt,
                        "AESER": aeser,
                        "AEACN": aeacn,
                        "TRT01A": arm,
                    })
    return records


adae_exp = generate_aes(subjid_exp, "Experimental", 100)
adae_ctl = generate_aes(subjid_ctl, "Control", 200)
adae = adae_exp + adae_ctl

# --- Compute AE summary ---
def unique_subjects(records, filter_fn=None):
    if filter_fn:
        return len(set(r["USUBJID"] for r in records if filter_fn(r)))
    return len(set(r["USUBJID"] for r in records))


any_exp = unique_subjects(adae, lambda r: r["TRT01A"] == "Experimental")
any_ctl = unique_subjects(adae, lambda r: r["TRT01A"] == "Control")
ser_exp = unique_subjects(adae, lambda r: r["AESER"] == "Y" and r["TRT01A"] == "Experimental")
ser_ctl = unique_subjects(adae, lambda r: r["AESER"] == "Y" and r["TRT01A"] == "Control")
disc_exp = unique_subjects(adae, lambda r: r["AEACN"] == "DRUG WITHDRAWN" and r["TRT01A"] == "Experimental")
disc_ctl = unique_subjects(adae, lambda r: r["AEACN"] == "DRUG WITHDRAWN" and r["TRT01A"] == "Control")


def fmt_n_pct(n, total):
    pct = round(100 * n / total, 1) if total > 0 else 0.0
    return {"n": n, "pct": pct}


# By SOC and PT
pt_counts = defaultdict(lambda: {"Experimental": set(), "Control": set()})
soc_counts = defaultdict(lambda: {"Experimental": set(), "Control": set()})

for r in adae:
    key = (r["AEBODSYS"], r["AEDECOD"])
    pt_counts[key][r["TRT01A"]].add(r["USUBJID"])
    soc_counts[r["AEBODSYS"]][r["TRT01A"]].add(r["USUBJID"])

# Build output
ae_table = []

# Summary rows
for label, exp_n, ctl_n in [
    ("Any adverse event", any_exp, any_ctl),
    ("Serious adverse events", ser_exp, ser_ctl),
    ("Adverse events leading to discontinuation", disc_exp, disc_ctl),
]:
    ae_table.append({
        "category": "summary",
        "soc": label,
        "pt": None,
        "n_experimental": exp_n,
        "pct_experimental": round(100 * exp_n / n_arm, 1),
        "n_control": ctl_n,
        "pct_control": round(100 * ctl_n / n_arm, 1),
    })

# SOC/PT detail rows
for soc in AE_CATALOG:
    soc_exp = len(soc_counts[soc]["Experimental"])
    soc_ctl = len(soc_counts[soc]["Control"])
    ae_table.append({
        "category": "soc",
        "soc": soc,
        "pt": None,
        "n_experimental": soc_exp,
        "pct_experimental": round(100 * soc_exp / n_arm, 1),
        "n_control": soc_ctl,
        "pct_control": round(100 * soc_ctl / n_arm, 1),
    })

    # PTs within SOC, sorted by descending max frequency
    pts_in_soc = [(k, v) for k, v in pt_counts.items() if k[0] == soc]
    pts_in_soc.sort(key=lambda x: max(len(x[1]["Experimental"]), len(x[1]["Control"])), reverse=True)

    for (s, pt), counts in pts_in_soc:
        pt_exp = len(counts["Experimental"])
        pt_ctl = len(counts["Control"])
        ae_table.append({
            "category": "pt",
            "soc": soc,
            "pt": pt,
            "n_experimental": pt_exp,
            "pct_experimental": round(100 * pt_exp / n_arm, 1),
            "n_control": pt_ctl,
            "pct_control": round(100 * pt_ctl / n_arm, 1),
        })

output = {
    "test_case_id": "TC-011",
    "title": "Adverse Event Summary Table by SOC and PT",
    "parameters": {"seed": args.seed, "n_subjects": n_subjects},
    "population": {
        "description": "Safety population (SAFFL = 'Y')",
        "n_experimental": n_arm,
        "n_control": n_arm,
    },
    "summary": ae_table[:3],
    "ae_table": ae_table,
    "metadata": {
        "language": "Python",
        "packages": ["json", "random", "collections"],
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    },
}

with open(args.output, "w") as f:
    json.dump(output, f, indent=2)

print(f"TC-011 output written to: {args.output}")
