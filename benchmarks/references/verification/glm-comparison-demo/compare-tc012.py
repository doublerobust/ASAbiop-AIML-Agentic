#!/usr/bin/env python3
"""Compare R and Python TC-012 output on identical data.

Usage:
    # Step 1: Generate common data + R analysis
    Rscript compare-tc012.R

    # Step 2: Run Python analysis on same data
    python3 compare-tc012.py

    # Step 3: Check agreement
    python3 check-comparison.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from lifelines import CoxPHFitter

HERE = Path(__file__).parent
DATA_CSV = HERE / "tc012-common-data.csv"
PY_OUT = HERE / "tc012-py-output.json"

if not DATA_CSV.exists():
    print("ERROR: Common data file not found.")
    print("Run 'Rscript compare-tc012.R' first to generate the common dataset.")
    sys.exit(1)

# Load the same data R used
all_df = pd.read_csv(str(DATA_CSV))
all_df["TRTN"] = (all_df["TRT01A"] == "Experimental").astype(int)
all_df["EVENT"] = (all_df["CNSR"] == 0).astype(int)


def estimate_hr(df, subgroup_var=None, subgroup_val=None):
    if subgroup_var and subgroup_val:
        subset = df[df[subgroup_var] == subgroup_val]
    else:
        subset = df

    n_exp = int((subset["TRTN"] == 1).sum())
    n_ctl = int((subset["TRTN"] == 0).sum())
    events_exp = int(subset.loc[subset["TRTN"] == 1, "EVENT"].sum())
    events_ctl = int(subset.loc[subset["TRTN"] == 0, "EVENT"].sum())

    if events_exp == 0 or events_ctl == 0 or len(subset) < 10:
        return None

    try:
        cph = CoxPHFitter()
        cph.fit(subset[["AVAL", "EVENT", "TRTN"]], duration_col="AVAL",
                event_col="EVENT", formula="TRTN")
        hr = float(np.exp(cph.params_["TRTN"]))
        ci = cph.confidence_intervals_.loc["TRTN"]
        ci_lower = float(np.exp(ci.iloc[0]))
        ci_upper = float(np.exp(ci.iloc[1]))
    except Exception:
        return None

    return {
        "hr": round(hr, 3),
        "ci_lower": round(ci_lower, 3),
        "ci_upper": round(ci_upper, 3),
        "n_experimental": n_exp,
        "n_control": n_ctl,
        "events_experimental": events_exp,
        "events_control": events_ctl,
    }


overall = estimate_hr(all_df)

subgroups = [
    ("AGEGR1", "<65", "Age <65"),
    ("AGEGR1", ">=65", "Age >=65"),
    ("SEX", "Male", "Male"),
    ("SEX", "Female", "Female"),
    ("ECOGGR1", "0", "ECOG PS 0"),
    ("ECOGGR1", "1+", "ECOG PS 1+"),
    ("REGION", "North America", "North America"),
    ("REGION", "Europe", "Europe"),
    ("REGION", "Asia", "Asia"),
    ("PRIORTRT", "Yes", "Prior therapy: Yes"),
    ("PRIORTRT", "No", "Prior therapy: No"),
]

subgroup_results = []
for var, val, label in subgroups:
    result = estimate_hr(all_df, var, val)
    if result:
        subgroup_results.append({
            "subgroup": label,
            "variable": var,
            "value": val,
            **result,
        })


def interaction_pvalue(df, var):
    sub = df[["AVAL", "EVENT", "TRTN", var]].copy()
    levels = sorted(sub[var].unique())
    if len(levels) < 2:
        return None
    dummies = pd.get_dummies(sub[var], prefix=var, drop_first=True).astype(float)
    design = pd.concat([sub[["AVAL", "EVENT", "TRTN"]], dummies], axis=1)
    inter_cols = []
    for c in dummies.columns:
        ic = f"TRTN_x_{c}"
        design[ic] = design["TRTN"] * design[c]
        inter_cols.append(ic)
    try:
        cph = CoxPHFitter()
        cph.fit(design, duration_col="AVAL", event_col="EVENT")
        pvals = [float(cph.summary.loc[ic, "p"]) for ic in inter_cols
                 if ic in cph.summary.index]
        if not pvals:
            return None
        return round(min(pvals), 4)
    except Exception:
        return None


interaction_pvals = {}
for var in ["AGEGR1", "SEX", "ECOGGR1", "REGION", "PRIORTRT"]:
    p = interaction_pvalue(all_df, var)
    if p is not None:
        interaction_pvals[var] = p

py_out = {
    "test_case_id": "TC-012",
    "language": "Python (lifelines CoxPHFitter)",
    "overall": overall,
    "subgroups": subgroup_results,
    "interaction_pvalues": interaction_pvals,
}

with open(str(PY_OUT), "w") as f:
    json.dump(py_out, f, indent=2)
print(f"Python output written to: {PY_OUT}")
