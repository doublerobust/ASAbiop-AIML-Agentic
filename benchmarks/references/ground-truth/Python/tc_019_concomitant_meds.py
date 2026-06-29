#!/usr/bin/env python3
"""TC-019 Ground Truth: Concomitant Medications Summary Table (Python)

Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark.

Summarizes concomitant medications by ATC class and preferred name:
  - Number of subjects taking each medication (n, %)
  - Sorted by ATC class, then descending frequency
  - Summary rows: Any CM, subjects with >=1 CM

Dependencies: pandas, numpy
Usage: python tc_019_concomitant_meds.py --seed 42 --n 200 --output results.json
"""

import argparse
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd


def generate_adcm(seed=42, n_subjects=200):
    """Generate synthetic ADCM (concomitant medications) dataset."""
    rng = np.random.default_rng(seed)

    atc_classes = {
        "J01": {"name": "Antibacterials for systemic use",
                "meds": ["Amoxicillin", "Ciprofloxacin", "Azithromycin"]},
        "N02": {"name": "Analgesics",
                "meds": ["Paracetamol", "Ibuprofen", "Tramadol"]},
        "C03": {"name": "Diuretics",
                "meds": ["Furosemide", "Hydrochlorothiazide"]},
        "A02": {"name": "Drugs for acid related disorders",
                "meds": ["Omeprazole", "Pantoprazole", "Ranitidine"]},
        "N05": {"name": "Psycholeptics",
                "meds": ["Diazepam", "Lorazepam", "Zolpidem"]},
        "C07": {"name": "Beta blocking agents",
                "meds": ["Metoprolol", "Atenolol", "Bisoprolol"]},
        "B01": {"name": "Antithrombotic agents",
                "meds": ["Warfarin", "Heparin", "Apixaban"]},
        "M01": {"name": "Antiinflammatory/antirheumatic products",
                "meds": ["Naproxen", "Celecoxib", "Diclofenac"]},
    }

    indications = ["Pain", "Infection", "Hypertension", "Anxiety",
                   "GERD", "Thrombosis", "Inflammation", "Edema"]

    records = []
    trt = rng.choice([0, 1], size=n_subjects)

    for i in range(n_subjects):
        n_meds = rng.choice(6, p=[0.05, 0.15, 0.25, 0.25, 0.20, 0.10])
        if n_meds == 0:
            continue

        class_indices = rng.choice(len(atc_classes),
                                   size=min(n_meds, len(atc_classes)),
                                   replace=False)
        for cls_idx in class_indices:
            cls_code = list(atc_classes.keys())[cls_idx]
            cls = atc_classes[cls_code]
            med = rng.choice(cls["meds"])
            records.append({
                "USUBJID": f"SUBJ-{i+1:04d}",
                "STUDYID": "BENCHMARK-001",
                "ATCCLAS": cls_code,
                "ATCCLAS1": cls["name"],
                "CMDECOD": med,
                "CMINDC": rng.choice(indications),
                "TRT01PN": int(trt[i]),
            })

    return pd.DataFrame(records)


def compute_cm_summary(adcm, n_subjects_per_arm):
    """Compute concomitant medications summary table."""
    n_exp, n_ctrl = n_subjects_per_arm

    # Any CM
    exp_subjects = adcm[adcm["TRT01PN"] == 1]["USUBJID"].nunique()
    ctrl_subjects = adcm[adcm["TRT01PN"] == 0]["USUBJID"].nunique()

    summary_rows = [{
        "category": "Any concomitant medication",
        "n_experimental": int(exp_subjects),
        "pct_experimental": round(100 * exp_subjects / n_exp, 1) if n_exp > 0 else 0,
        "n_control": int(ctrl_subjects),
        "pct_control": round(100 * ctrl_subjects / n_ctrl, 1) if n_ctrl > 0 else 0,
    }]

    detailed_rows = []
    atc_classes_sorted = sorted(adcm["ATCCLAS"].unique())

    for cls in atc_classes_sorted:
        cls_data = adcm[adcm["ATCCLAS"] == cls]
        cls_name = cls_data["ATCCLAS1"].iloc[0]

        for arm, label, denom in [(1, "exp", n_exp), (0, "ctrl", n_ctrl)]:
            arm_data = cls_data[cls_data["TRT01PN"] == arm]
            n_subj = arm_data["USUBJID"].nunique()
            pct = round(100 * n_subj / denom, 1) if denom > 0 else 0
            if label == "exp":
                exp_n, exp_pct = int(n_subj), pct
            else:
                ctrl_n, ctrl_pct = int(n_subj), pct

        detailed_rows.append({
            "atc_class": cls,
            "atc_class_name": cls_name,
            "n_experimental": exp_n,
            "pct_experimental": exp_pct,
            "n_control": ctrl_n,
            "pct_control": ctrl_pct,
        })

        # By medication within class
        meds_sorted = sorted(cls_data["CMDECOD"].unique())
        for med in meds_sorted:
            med_data = cls_data[cls_data["CMDECOD"] == med]
            for arm, label, denom in [(1, "exp", n_exp), (0, "ctrl", n_ctrl)]:
                arm_data = med_data[med_data["TRT01PN"] == arm]
                n_subj = arm_data["USUBJID"].nunique()
                pct = round(100 * n_subj / denom, 1) if denom > 0 else 0
                if label == "exp":
                    med_exp_n, med_exp_pct = int(n_subj), pct
                else:
                    med_ctrl_n, med_ctrl_pct = int(n_subj), pct

            detailed_rows.append({
                "atc_class": cls,
                "atc_class_name": cls_name,
                "medication": med,
                "n_experimental": med_exp_n,
                "pct_experimental": med_exp_pct,
                "n_control": med_ctrl_n,
                "pct_control": med_ctrl_pct,
            })

    return {
        "test_case_id": "TC-019",
        "variant_id": None,
        "language": "Python",
        "package": "pandas",
        "package_version": pd.__version__,
        "summary_rows": summary_rows,
        "detailed_rows": detailed_rows,
        "n_experimental": n_exp,
        "n_control": n_ctrl,
        "seed": None,
    }


def main():
    parser = argparse.ArgumentParser(
        description="TC-019: Concomitant Medications Summary (Python)"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--n", type=int, default=200, help="Number of subjects")
    parser.add_argument("--data", type=str, default=None,
                        help="Shared ADCM CSV (for cross-language verification)")
    parser.add_argument("--output", type=str, default=None, help="Output JSON path")
    args = parser.parse_args()

    print(f"TC-019: Concomitant Medications Summary (Python) — seed={args.seed}, n={args.n}")

    if args.data:
        adcm = pd.read_csv(args.data)
        print(f"Loaded shared ADCM with {len(adcm)} records")
    else:
        adcm = generate_adcm(seed=args.seed, n_subjects=args.n)
        print(f"Generated ADCM with {len(adcm)} records across "
              f"{adcm['USUBJID'].nunique()} subjects")

    # Determine subjects per arm
    if args.data:
        # Derive from unique subjects in the data
        unique_subjects = adcm.drop_duplicates(subset='USUBJID')
        n_exp = int((unique_subjects['TRT01PN'] == 1).sum())
        n_ctrl = int((unique_subjects['TRT01PN'] == 0).sum())
    else:
        rng = np.random.default_rng(args.seed)
        trt = rng.choice([0, 1], size=args.n)
        n_exp = int((trt == 1).sum())
        n_ctrl = int((trt == 0).sum())

    result = compute_cm_summary(adcm, (n_exp, n_ctrl))
    result["seed"] = args.seed
    result["variant_id"] = f"v{args.seed}"

    print("\n" + "─" * 50)
    s = result["summary_rows"][0]
    print(f"Any CM:  Exp={s['n_experimental']} ({s['pct_experimental']}%), "
          f"Ctrl={s['n_control']} ({s['pct_control']}%)")
    print(f"ATC classes: {adcm['ATCCLAS'].nunique()}")
    print(f"Medications: {adcm['CMDECOD'].nunique()}")
    print("─" * 50)

    print("\n=== BENCHMARK OUTPUT ===")
    print(json.dumps(result, indent=2))
    print("=== END OUTPUT ===")

    if args.output:
        outpath = Path(args.output)
        outpath.parent.mkdir(parents=True, exist_ok=True)
        with open(outpath, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Wrote output to: {outpath}")


if __name__ == "__main__":
    main()
