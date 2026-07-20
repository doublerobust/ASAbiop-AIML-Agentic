#!/usr/bin/env python3
"""tc_007_regulatory_response.py — TC-007 Ground Truth Analysis (Python)

Level 3: Regulatory Response to ITT vs. PP Discrepancy

Mirrors the R implementation: ITT/PP Cox analysis, exclusion pattern,
tipping point, sensitivity analyses.

Usage:
    python tc_007_regulatory_response.py --data-adtte <path> --data-adsl <path> [--out <path>]
    python tc_007_regulatory_response.py  # generates data internally

Dependencies: pandas, numpy, lifelines, scipy
"""

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from lifelines import CoxPHFitter, KaplanMeierFitter
    from lifelines.statistics import logrank_test
    from scipy.stats import fisher_exact
except ImportError:
    print("Install lifelines and scipy: pip install lifelines scipy", file=sys.stderr)
    sys.exit(1)


# ─── Data generation (fallback when no shared CSV) ───
def generate_tc007_data(seed=42, n_subjects=500):
    rng = np.random.default_rng(seed)
    base_rate = math.log(2) / 6.0
    hr_itt = 0.72

    trt = np.repeat([0, 1], n_subjects // 2)
    rng.shuffle(trt)
    trt_label = np.where(trt == 0, "Placebo", "Active")

    hazard = np.where(trt == 0, base_rate, base_rate * hr_itt)
    aval = rng.exponential(1.0 / hazard)
    cens_rate = base_rate * 0.30 / 0.70
    cens_time = rng.exponential(1.0 / cens_rate)
    observed = np.minimum(aval, cens_time)
    cnsr = np.where(aval <= cens_time, 0, 1)

    # PP exclusions — prefer censored in Active, events in Placebo
    n_excl = round(n_subjects * 0.174)
    active_idx = np.where(trt == 1)[0]
    placebo_idx = np.where(trt == 0)[0]

    excl_active_target = round(n_excl * 0.51)
    # Active: 70% censored, 30% events
    active_events = active_idx[cnsr[active_idx] == 0]
    active_cens = active_idx[cnsr[active_idx] == 1]
    n_act_cens = min(round(excl_active_target * 0.70), len(active_cens))
    n_act_evt = min(excl_active_target - n_act_cens, len(active_events))
    excl_active = np.concatenate([
        rng.choice(active_cens, n_act_cens, replace=False),
        rng.choice(active_events, n_act_evt, replace=False),
    ])

    excl_placebo_target = n_excl - len(excl_active)
    # Placebo: 70% events, 30% censored
    placebo_events = placebo_idx[cnsr[placebo_idx] == 0]
    placebo_cens = placebo_idx[cnsr[placebo_idx] == 1]
    n_pla_evt = min(round(excl_placebo_target * 0.70), len(placebo_events))
    n_pla_cens = min(excl_placebo_target - n_pla_evt, len(placebo_cens))
    excl_placebo = np.concatenate([
        rng.choice(placebo_events, n_pla_evt, replace=False),
        rng.choice(placebo_cens, n_pla_cens, replace=False),
    ])

    excl_indices = np.concatenate([excl_active, excl_placebo])

    ppfl = np.array(["Y"] * n_subjects, dtype=object)
    ppfl[excl_indices] = "N"

    # Exclusion reasons
    reasons_pool = (
        ["Major protocol violation"] * round(n_excl * 0.32)
        + ["Early discontinuation before first post-baseline assessment"] * round(n_excl * 0.40)
        + ["Prohibited medication use"] * (n_excl - round(n_excl * 0.32) - round(n_excl * 0.40))
    )
    rng.shuffle(reasons_pool)
    ppdecod = np.array([None] * n_subjects, dtype=object)
    for j, idx in enumerate(excl_indices):
        if j < len(reasons_pool):
            ppdecod[idx] = reasons_pool[j]

    # ADSL
    age = rng.normal(58, 12).round().astype(int)
    sex = rng.choice(["M", "F"], n_subjects, p=[0.55, 0.45])
    race = rng.choice(["White", "Black", "Asian", "Other"], n_subjects, p=[0.60, 0.15, 0.20, 0.05])
    ecog = rng.choice([0, 1], n_subjects, p=[0.6, 0.4])

    adsl = pd.DataFrame({
        "USUBJID": [f"SUBJ-{i+1:04d}" for i in range(n_subjects)],
        "STUDYID": "BENCHMARK-001",
        "TRT01PN": trt,
        "TRT01P": trt_label,
        "AGE": age,
        "AGEGR1": np.where(age < 65, "<65", ">=65"),
        "SEX": sex,
        "RACE": race,
        "ECOG": ecog,
        "ITTFL": "Y",
        "SAFFL": "Y",
        "PPFL": ppfl,
        "PPDECOD": ppdecod,
    })

    adtte = pd.DataFrame({
        "USUBJID": adsl["USUBJID"],
        "STUDYID": "BENCHMARK-001",
        "TRT01PN": trt,
        "TRT01P": trt_label,
        "AVAL": np.round(observed, 2),
        "CNSR": cnsr,
        "PARAMCD": "PFS",
        "PARAM": "Progression-Free Survival",
        "ITTFL": "Y",
        "PPFL": ppfl,
    })

    return adsl, adtte


# ─── Cox PH helper ───
def fit_cox(data):
    df = data.copy()
    df["event"] = 1 - df["CNSR"]
    df["trt_num"] = (df["TRT01P"] == "Active").astype(int)
    cph = CoxPHFitter()
    cph.fit(df[["AVAL", "event", "trt_num"]], duration_col="AVAL", event_col="event")
    hr = round(math.exp(cph.params_["trt_num"]), 4)
    ci = cph.confidence_intervals_.loc["trt_num"]
    ci_lo = round(math.exp(ci.iloc[0]), 4)
    ci_hi = round(math.exp(ci.iloc[1]), 4)
    p = round(cph.summary.loc["trt_num", "p"], 6)
    return hr, ci_lo, ci_hi, p


def km_median(data, trt_label):
    df = data[data["TRT01P"] == trt_label].copy()
    df["event"] = 1 - df["CNSR"]
    kmf = KaplanMeierFitter()
    kmf.fit(df["AVAL"], event_observed=df["event"])
    return round(kmf.median_survival_time_, 4)


def logrank_p(data):
    g0 = data[data["TRT01P"] == "Placebo"]
    g1 = data[data["TRT01P"] == "Active"]
    result = logrank_test(
        g0["AVAL"], g1["AVAL"],
        event_observed_A=1 - g0["CNSR"], event_observed_B=1 - g1["CNSR"]
    )
    return round(result.p_value, 6)


# ─── Tipping point ───
def tipping_point(adtte, max_shift=50):
    """Reclassify censored excluded Active subjects as events until ITT p >= 0.05."""
    results = []
    for n_shift in range(max_shift + 1):
        modified = adtte.copy()
        excl_active_censored = modified.index[
            (modified["PPFL"] == "N") &
            (modified["TRT01P"] == "Active") &
            (modified["CNSR"] == 1)
        ]
        if n_shift > 0 and n_shift <= len(excl_active_censored):
            modified.loc[excl_active_censored[:n_shift], "CNSR"] = 0
        hr, ci_lo, ci_hi, p = fit_cox(modified)
        results.append({"n_shifted": n_shift, "hr": hr, "p_value": p})
        if p >= 0.05:
            print(f"Tipping point reached at n_shift = {n_shift} (HR = {hr}, p = {p})")
            return {"tipping_n": n_shift, "tipping_hr": hr, "tipping_p": p, "curve": results}
    print("Tipping point not reached within max_shift")
    return {"tipping_n": None, "tipping_hr": None, "tipping_p": None, "curve": results}


# ─── Main ───
def main():
    parser = argparse.ArgumentParser(description="TC-007 Regulatory Response Analysis")
    parser.add_argument("--data-adtte", type=str, default=None)
    parser.add_argument("--data-adsl", type=str, default=None)
    parser.add_argument("--out", type=str, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n", type=int, default=500)
    args = parser.parse_args()

    if args.data_adtte and args.data_adsl:
        adtte = pd.read_csv(args.data_adtte)
        adsl = pd.read_csv(args.data_adsl)
    else:
        adsl, adtte = generate_tc007_data(seed=args.seed, n_subjects=args.n)

    # ITT
    itt_data = adtte[adtte["ITTFL"] == "Y"]
    itt_hr, itt_ci_lo, itt_ci_hi, itt_p = fit_cox(itt_data)
    itt_lr_p = logrank_p(itt_data)
    itt_med_active = km_median(itt_data, "Active")
    itt_med_placebo = km_median(itt_data, "Placebo")

    # PP
    pp_data = adtte[adtte["PPFL"] == "Y"]
    pp_hr, pp_ci_lo, pp_ci_hi, pp_p = fit_cox(pp_data)
    pp_lr_p = logrank_p(pp_data)
    pp_med_active = km_median(pp_data, "Active")
    pp_med_placebo = km_median(pp_data, "Placebo")

    # Exclusion pattern
    n_total = len(adsl)
    n_pp = int((adsl["PPFL"] == "Y").sum())
    n_excl = n_total - n_pp
    excl_active = int(((adsl["PPFL"] == "N") & (adsl["TRT01P"] == "Active")).sum())
    excl_placebo = int(((adsl["PPFL"] == "N") & (adsl["TRT01P"] == "Placebo")).sum())

    excl_event_rate = round(float(adtte[adtte["PPFL"] == "N"]["CNSR"].apply(lambda x: x == 0).mean()), 4)
    incl_event_rate = round(float(adtte[adtte["PPFL"] == "Y"]["CNSR"].apply(lambda x: x == 0).mean()), 4)

    # Fisher's exact test for arm imbalance
    incl_active = int(((adsl["PPFL"] == "Y") & (adsl["TRT01P"] == "Active")).sum())
    incl_placebo = int(((adsl["PPFL"] == "Y") & (adsl["TRT01P"] == "Placebo")).sum())
    fisher_mat = [[excl_active, incl_active], [excl_placebo, incl_placebo]]
    _, fisher_p = fisher_exact(fisher_mat)
    fisher_p = round(float(fisher_p), 6)

    # Event imbalance among excluded
    excl_events_active = int(((adtte["PPFL"] == "N") & (adtte["TRT01P"] == "Active") & (adtte["CNSR"] == 0)).sum())
    excl_events_placebo = int(((adtte["PPFL"] == "N") & (adtte["TRT01P"] == "Placebo") & (adtte["CNSR"] == 0)).sum())
    excl_cens_active = excl_active - excl_events_active
    excl_cens_placebo = excl_placebo - excl_events_placebo
    _, event_imb_p = fisher_exact([[excl_events_active, excl_cens_active],
                                    [excl_events_placebo, excl_cens_placebo]])
    event_imb_p = round(float(event_imb_p), 6)

    # Exclusion reasons
    excl_df = adsl[adsl["PPFL"] == "N"]
    reasons = excl_df["PPDECOD"].value_counts().to_dict()

    # Tipping point
    tipping = tipping_point(adtte, max_shift=50)

    # Sensitivity: worst-case
    wc_data = adtte.copy()
    wc_mask = (wc_data["PPFL"] == "N") & (wc_data["TRT01P"] == "Active")
    wc_data.loc[wc_mask, "CNSR"] = 1
    wc_data.loc[wc_mask, "AVAL"] = 0.01
    wc_hr, _, _, wc_p = fit_cox(wc_data)

    # Sensitivity: best-case
    bc_data = adtte.copy()
    bc_data.loc[bc_data["PPFL"] == "N", "CNSR"] = 0
    bc_hr, _, _, bc_p = fit_cox(bc_data)

    result = {
        "tc_id": "TC-007",
        "tc_title": "Regulatory Response to ITT vs. PP Discrepancy",
        "level": 3,
        "analysis": {
            "itt": {
                "n": int((adtte["ITTFL"] == "Y").sum()),
                "hr": itt_hr,
                "hr_ci_lower": itt_ci_lo,
                "hr_ci_upper": itt_ci_hi,
                "logrank_p": itt_lr_p,
                "wald_p": itt_p,
                "median_pfs_active": itt_med_active,
                "median_pfs_placebo": itt_med_placebo,
            },
            "pp": {
                "n": n_pp,
                "hr": pp_hr,
                "hr_ci_lower": pp_ci_lo,
                "hr_ci_upper": pp_ci_hi,
                "logrank_p": pp_lr_p,
                "wald_p": pp_p,
                "median_pfs_active": pp_med_active,
                "median_pfs_placebo": pp_med_placebo,
            },
            "discrepancy": {
                "itt_hr": itt_hr,
                "pp_hr": pp_hr,
                "hr_difference": round(itt_hr - pp_hr, 4),
                "itt_significant": bool(itt_p < 0.05),
                "pp_significant": bool(pp_p < 0.05),
            },
            "exclusion_pattern": {
                "n_total": n_total,
                "n_itt": int((adsl["ITTFL"] == "Y").sum()),
                "n_pp": n_pp,
                "n_excluded": n_excl,
                "excluded_active": excl_active,
                "excluded_placebo": excl_placebo,
                "exclusion_rate_active": round(excl_active / max(1, int((adsl["TRT01P"] == "Active").sum())), 4),
                "exclusion_rate_placebo": round(excl_placebo / max(1, int((adsl["TRT01P"] == "Placebo").sum())), 4),
                "event_rate_excluded": excl_event_rate,
                "event_rate_included": incl_event_rate,
                "fisher_arm_imbalance_p": fisher_p,
                "excl_events_active": excl_events_active,
                "excl_events_placebo": excl_events_placebo,
                "event_imbalance_fisher_p": event_imb_p,
                "reasons": reasons,
            },
            "tipping_point": {
                "n_shifted": tipping["tipping_n"],
                "hr_at_tipping": tipping["tipping_hr"],
                "p_at_tipping": tipping["tipping_p"],
                "interpretation": (
                    f"Reclassifying {tipping['tipping_n']} event(s) among excluded Active "
                    f"subjects to censored would make the ITT result non-significant (p >= 0.05)."
                ),
            },
            "sensitivity_analyses": {
                "worst_case": {
                    "description": "All excluded Active subjects censored at time ~0",
                    "hr": wc_hr,
                    "p_value": wc_p,
                },
                "best_case": {
                    "description": "All excluded subjects have events",
                    "hr": bc_hr,
                    "p_value": bc_p,
                },
                "per_protocol": {
                    "description": "PP analysis (excludes protocol deviations)",
                    "hr": pp_hr,
                    "p_value": pp_p,
                },
            },
        },
    }

    if args.out:
        from pathlib import Path
        Path(args.out).write_text(json.dumps(result, indent=2, default=str))
        print(f"Wrote output to: {args.out}")
    else:
        print("\n=== BENCHMARK OUTPUT ===")
        print(json.dumps(result, indent=2, default=str))
        print("=== END OUTPUT ===")


if __name__ == "__main__":
    main()
