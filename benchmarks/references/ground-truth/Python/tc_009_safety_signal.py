#!/usr/bin/env python3
"""tc_009_safety_signal.py — TC-009 Ground Truth Analysis (Python)

Level 3: Safety Signal Evaluation and DMC Report

Performs a comprehensive safety signal evaluation for a Phase 3 oncology
trial DMC review, covering all 8 areas specified in the TC-009 design:
  1. AE Overview — overall/SAE/discontinuation/death rates by arm
  2. Exposure-Adjusted AE Rates — per 100 patient-years
  3. Grade 3+ Events — with risk difference and 95% CI
  4. Laboratory Abnormalities — Hy's Law (hepatotoxicity), QTc prolongation
  5. Time-to-First Grade 3+ AE — KM median, log-rank, Cox PH
  6. AE of Special Interest — irAEs with onset timing
  7. Statistical Signal Detection — Empirical Bayes (MGPS), risk difference
  8. Safety Recommendation — Continue / Modify / Pause based on totality

Mirrors the R implementation (tc-009-safety-signal.R) exactly. For TRUE
cross-language verification, R and Python read the SAME shared CSV datasets
(adsl_tc009.csv, adae_tc009.csv, adlb_tc009.csv) so that all counts and
statistics are computed on identical inputs.

Usage:
    python tc_009_safety_signal.py \\
        --data-adsl <path> --data-adae <path> --data-adlb <path> [--out <path>]
    python tc_009_safety_signal.py   # generates data internally (smoke test only)

Dependencies: pandas, numpy, scipy, lifelines
"""

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import norm
from lifelines import CoxPHFitter
from lifelines.statistics import logrank_test


# ─── Helpers (mirror R helpers exactly) ───
Z975 = float(norm.ppf(0.975))


def risk_diff_ci(n_active, n_total_active, n_placebo, n_total_placebo):
    """Risk difference (Active - Placebo) with 95% normal-approximation CI.

    Mirrors R risk_diff_ci(): rounds rd/ci to 4 dp, pct to 2 dp.
    """
    p_a = n_active / n_total_active
    p_p = n_placebo / n_total_placebo
    rd = p_a - p_p
    se = math.sqrt(p_a * (1 - p_a) / n_total_active + p_p * (1 - p_p) / n_total_placebo)
    ci_lower = rd - Z975 * se
    ci_upper = rd + Z975 * se
    return {
        "rd": round(rd, 4),
        "ci_lower": round(ci_lower, 4),
        "ci_upper": round(ci_upper, 4),
        "pct_active": round(p_a * 100, 2),
        "pct_placebo": round(p_p * 100, 2),
    }


def fisher_p(a, b, c, d):
    """Two-sided Fisher exact p-value, rounded to 6 dp. Mirrors R fisher_p()."""
    table = [[a, b], [c, d]]
    _, p = stats.fisher_exact(table, alternative="two-sided")
    return round(float(p), 6)


def _int(x):
    """Coerce to int (pandas may return numpy int64); None stays None."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    return int(x)


def _float_round(x, n):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    return round(float(x), n)


# ─── Data generation (smoke-test fallback only; not used for cross-lang) ───
def generate_data(seed=42, n_per_arm=200):
    """Minimal standalone generator for smoke testing.

    NOTE: This does NOT reproduce the R RNG. For true cross-language
    verification, pass --data-adsl/--data-adae/--data-adlb to read the shared
    CSVs written by generate_tc009_safety_signal.R.
    """
    rng = np.random.default_rng(seed)
    n_total = n_per_arm * 2
    trt = np.array(["Placebo"] * n_per_arm + ["Active"] * n_per_arm)
    trt01pn = (trt == "Active").astype(int)
    usubjid = np.array([f"SUBJ-{i:04d}" for i in range(1, n_total + 1)])

    followup = np.clip(rng.normal(425, 90, n_total), 180, 730).round()
    discontinued = rng.binomial(1, np.where(trt == "Active", 0.18, 0.12))
    followup = np.where(discontinued == 1, np.clip(rng.uniform(60, 300, n_total), 60, 300).round(), followup)
    exposure_py = np.round(followup / 365.25, 4)
    died = rng.binom(1, np.where(trt == "Active", 0.06, 0.09))
    sex = rng.choice(["Male", "Female"], n_total, p=[0.55, 0.45])
    age = np.clip(rng.normal(62, 10, n_total), 35, 85).round()
    agegr1 = np.where(age < 65, "<65", ">=65")

    adsl = pd.DataFrame({
        "USUBJID": usubjid, "STUDYID": "BENCHMARK-009", "TRT01P": trt,
        "TRT01PN": trt01pn, "SAFFL": "Y", "ITTFL": "Y", "SEX": sex, "AGE": age,
        "AGEGR1": agegr1, "FOLLOWUP_DAYS": followup, "EXPOSURE_PY": exposure_py,
        "DISCONTINUED": discontinued, "DIED": died,
    })

    # Minimal ADLB + ADAE so the script runs end-to-end (counts won't match R).
    adlb = adsl[["USUBJID", "TRT01P", "TRT01PN"]].copy()
    adlb["HYS_LAW"] = "N"
    adlb["ALT_3XULN"] = "N"
    adlb["AST_3XULN"] = "N"
    adlb["BILI_2XULN"] = "N"
    adlb["QTC_PROLONGED"] = "N"
    adae = pd.DataFrame(columns=["USUBJID", "TRT01P", "TRT01PN", "AESOC",
                                 "AEDECOD", "AESEV", "AESER", "AEACN",
                                 "AEOSI", "AESTDY"])
    return adsl, adae, adlb


# ─── Core analysis ───
def analyze(adsl, adae, adlb):
    # Ensure expected dtypes
    adae = adae.copy()
    adae["AESEV"] = pd.to_numeric(adae["AESEV"], errors="coerce").fillna(0).astype(int)

    n_active = int((adsl["TRT01P"] == "Active").sum())
    n_placebo = int((adsl["TRT01P"] == "Placebo").sum())
    n_total = n_active + n_placebo
    py_active = round(float(adsl.loc[adsl["TRT01P"] == "Active", "EXPOSURE_PY"].sum()), 4)
    py_placebo = round(float(adsl.loc[adsl["TRT01P"] == "Placebo", "EXPOSURE_PY"].sum()), 4)

    # ─── 1. AE Overview (subject-level, de-duplicated) ───
    def _agg_subj(g):
        return pd.Series({
            "any_ae": bool((g["AESEV"] >= 1).any()),
            "any_sae": bool((g["AESER"] == "Y").any()),
            "any_disc": bool(g["AEACN"].isin(["DRUG_WITHDRAWN"]).any()),
            "any_died": bool((g["AEDECOD"] == "Death").any() or (g["AESEV"] == 5).any()),
        })

    if len(adae) > 0:
        ae_subj = (adae.groupby(["USUBJID", "TRT01P"]).apply(_agg_subj, include_groups=False)
                   .reset_index())
    else:
        ae_subj = pd.DataFrame(columns=["USUBJID", "TRT01P", "any_ae", "any_sae", "any_disc", "any_died"])

    overview = adsl[["USUBJID", "TRT01P"]].merge(
        ae_subj[["USUBJID", "TRT01P", "any_ae", "any_sae", "any_disc", "any_died"]],
        on=["USUBJID", "TRT01P"], how="left")
    for c in ["any_ae", "any_sae", "any_disc", "any_died"]:
        overview[c] = overview[c].fillna(False).astype(bool)

    act = overview["TRT01P"] == "Active"
    plb = overview["TRT01P"] == "Placebo"

    n_any_ae_a = int((overview["any_ae"] & act).sum())
    n_any_ae_p = int((overview["any_ae"] & plb).sum())
    n_sae_a = int((overview["any_sae"] & act).sum())
    n_sae_p = int((overview["any_sae"] & plb).sum())
    n_disc_a = int((overview["any_disc"] & act).sum())
    n_disc_p = int((overview["any_disc"] & plb).sum())
    n_died_a = int((overview["any_died"] & act).sum())
    n_died_p = int((overview["any_died"] & plb).sum())

    rd_any = risk_diff_ci(n_any_ae_a, n_active, n_any_ae_p, n_placebo)
    rd_sae = risk_diff_ci(n_sae_a, n_active, n_sae_p, n_placebo)
    rd_disc = risk_diff_ci(n_disc_a, n_active, n_disc_p, n_placebo)
    rd_died = risk_diff_ci(n_died_a, n_active, n_died_p, n_placebo)

    ae_records_active = int((adae["TRT01P"] == "Active").sum()) if len(adae) else 0
    ae_records_placebo = int((adae["TRT01P"] == "Placebo").sum()) if len(adae) else 0

    ae_overview = {
        "by_arm": {
            "Active": {"n": n_active, "n_any_ae": n_any_ae_a, "pct_any_ae": rd_any["pct_active"],
                       "n_sae": n_sae_a, "pct_sae": rd_sae["pct_active"],
                       "n_disc": n_disc_a, "pct_disc": rd_disc["pct_active"],
                       "n_died": n_died_a, "pct_died": rd_died["pct_active"],
                       "total_ae_reports": ae_records_active},
            "Placebo": {"n": n_placebo, "n_any_ae": n_any_ae_p, "pct_any_ae": rd_any["pct_placebo"],
                        "n_sae": n_sae_p, "pct_sae": rd_sae["pct_placebo"],
                        "n_disc": n_disc_p, "pct_disc": rd_disc["pct_placebo"],
                        "n_died": n_died_p, "pct_died": rd_died["pct_placebo"],
                        "total_ae_reports": ae_records_placebo},
        },
        "risk_difference": {
            "any_ae": {"rd": rd_any["rd"], "ci_lower": rd_any["ci_lower"], "ci_upper": rd_any["ci_upper"],
                       "fisher_p": fisher_p(n_any_ae_a, n_active - n_any_ae_a, n_any_ae_p, n_placebo - n_any_ae_p)},
            "sae": {"rd": rd_sae["rd"], "ci_lower": rd_sae["ci_lower"], "ci_upper": rd_sae["ci_upper"],
                    "fisher_p": fisher_p(n_sae_a, n_active - n_sae_a, n_sae_p, n_placebo - n_sae_p)},
            "discontinuation": {"rd": rd_disc["rd"], "ci_lower": rd_disc["ci_lower"], "ci_upper": rd_disc["ci_upper"],
                                "fisher_p": fisher_p(n_disc_a, n_active - n_disc_a, n_disc_p, n_placebo - n_disc_p)},
            "death": {"rd": rd_died["rd"], "ci_lower": rd_died["ci_lower"], "ci_upper": rd_died["ci_upper"],
                      "fisher_p": fisher_p(n_died_a, n_active - n_died_a, n_died_p, n_placebo - n_died_p)},
        },
    }

    # ─── 2. Exposure-Adjusted AE Rates ───
    if len(adae) > 0:
        pt_freq = (adae.groupby(["TRT01P", "AEDECOD"])["USUBJID"]
                   .nunique().reset_index(name="n_subjects"))
        pt_freq["pct"] = pt_freq.apply(
            lambda r: round(r["n_subjects"] / (n_active if r["TRT01P"] == "Active" else n_placebo) * 100, 2),
            axis=1)
    else:
        pt_freq = pd.DataFrame(columns=["TRT01P", "AEDECOD", "n_subjects", "pct"])

    common_pts = sorted(pt_freq.loc[pt_freq["pct"] >= 5.0, "AEDECOD"].unique().tolist())

    ea_rows = {}
    for pt in common_pts:
        sub = pt_freq[pt_freq["AEDECOD"] == pt]
        n_a = int(sub.loc[sub["TRT01P"] == "Active", "n_subjects"].sum() if (sub["TRT01P"] == "Active").any() else 0)
        n_p = int(sub.loc[sub["TRT01P"] == "Placebo", "n_subjects"].sum() if (sub["TRT01P"] == "Placebo").any() else 0)
        if n_a == 0 and n_p == 0:
            continue
        rate_a = round(n_a / py_active * 100, 2) if py_active else 0.0
        rate_p = round(n_p / py_placebo * 100, 2) if py_placebo else 0.0
        rd = risk_diff_ci(n_a, n_active, n_p, n_placebo)
        ea_rows[pt] = {"pt": pt, "n_active": n_a, "n_placebo": n_p,
                       "rate_per_100py_active": rate_a, "rate_per_100py_placebo": rate_p,
                       "rd_per_100py": round(rate_a - rate_p, 2),
                       "rd_pct_ci_lower": rd["ci_lower"], "rd_pct_ci_upper": rd["ci_upper"]}

    sae_recs_active = int(((adae["TRT01P"] == "Active") & (adae["AESER"] == "Y")).sum()) if len(adae) else 0
    sae_recs_placebo = int(((adae["TRT01P"] == "Placebo") & (adae["AESER"] == "Y")).sum()) if len(adae) else 0

    exposure_adjusted = {
        "total_patient_years": {"Active": py_active, "Placebo": py_placebo},
        "ae_per_100py": {"Active": round(ae_records_active / py_active * 100, 2) if py_active else 0.0,
                         "Placebo": round(ae_records_placebo / py_placebo * 100, 2) if py_placebo else 0.0},
        "sae_per_100py": {"Active": round(sae_recs_active / py_active * 100, 2) if py_active else 0.0,
                          "Placebo": round(sae_recs_placebo / py_placebo * 100, 2) if py_placebo else 0.0},
        "common_pts": ea_rows,
    }

    # ─── 3. Grade 3+ Events ───
    if len(adae) > 0:
        g3 = adae[adae["AESEV"] >= 3].groupby("TRT01P")["USUBJID"].nunique()
    else:
        g3 = pd.Series(dtype=int)
    n_g3_a = int(g3.get("Active", 0))
    n_g3_p = int(g3.get("Placebo", 0))
    rd_g3 = risk_diff_ci(n_g3_a, n_active, n_g3_p, n_placebo)

    if len(adae) > 0:
        g3_pt = (adae[adae["AESEV"] >= 3].groupby(["TRT01P", "AEDECOD"])["USUBJID"].nunique()
                 .reset_index(name="n"))
    else:
        g3_pt = pd.DataFrame(columns=["TRT01P", "AEDECOD", "n"])

    g3_top = {}
    for pt in g3_pt["AEDECOD"].unique():
        sub = g3_pt[g3_pt["AEDECOD"] == pt]
        n_a = int(sub.loc[sub["TRT01P"] == "Active", "n"].sum() if (sub["TRT01P"] == "Active").any() else 0)
        n_p = int(sub.loc[sub["TRT01P"] == "Placebo", "n"].sum() if (sub["TRT01P"] == "Placebo").any() else 0)
        rd = risk_diff_ci(n_a, n_active, n_p, n_placebo)
        g3_top[pt] = {"pt": pt, "n_active": n_a, "n_placebo": n_p,
                      "rd": rd["rd"], "ci_lower": rd["ci_lower"], "ci_upper": rd["ci_upper"]}

    grade3_plus = {
        "by_arm": {"Active": {"n": n_g3_a, "pct": rd_g3["pct_active"]},
                   "Placebo": {"n": n_g3_p, "pct": rd_g3["pct_placebo"]}},
        "risk_difference": rd_g3["rd"],
        "rd_ci": {"lower": rd_g3["ci_lower"], "upper": rd_g3["ci_upper"]},
        "fisher_p": fisher_p(n_g3_a, n_active - n_g3_a, n_g3_p, n_placebo - n_g3_p),
        "top_pts": g3_top,
    }

    # ─── 4. Laboratory Abnormalities (Hy's Law & QTc) ───
    # per-subject adlb (1 row/subject): flag counts by arm
    hys_a = int(((adlb["HYS_LAW"] == "Y") & (adlb["TRT01P"] == "Active")).sum())
    hys_p = int(((adlb["HYS_LAW"] == "Y") & (adlb["TRT01P"] == "Placebo")).sum())
    rd_hys = risk_diff_ci(hys_a, n_active, hys_p, n_placebo)

    alt3_a = int(((adlb["ALT_3XULN"] == "Y") & (adlb["TRT01P"] == "Active")).sum())
    alt3_p = int(((adlb["ALT_3XULN"] == "Y") & (adlb["TRT01P"] == "Placebo")).sum())
    ast3_a = int(((adlb["AST_3XULN"] == "Y") & (adlb["TRT01P"] == "Active")).sum())
    ast3_p = int(((adlb["AST_3XULN"] == "Y") & (adlb["TRT01P"] == "Placebo")).sum())
    bili2_a = int(((adlb["BILI_2XULN"] == "Y") & (adlb["TRT01P"] == "Active")).sum())
    bili2_p = int(((adlb["BILI_2XULN"] == "Y") & (adlb["TRT01P"] == "Placebo")).sum())

    qtc_a = int(((adlb["QTC_PROLONGED"] == "Y") & (adlb["TRT01P"] == "Active")).sum())
    qtc_p = int(((adlb["QTC_PROLONGED"] == "Y") & (adlb["TRT01P"] == "Placebo")).sum())
    rd_qtc = risk_diff_ci(qtc_a, n_active, qtc_p, n_placebo)

    lab_abnormalities = {
        "hys_law": {
            "n_active": hys_a, "n_placebo": hys_p,
            "pct_active": rd_hys["pct_active"], "pct_placebo": rd_hys["pct_placebo"],
            "risk_difference": rd_hys["rd"], "rd_ci": {"lower": rd_hys["ci_lower"], "upper": rd_hys["ci_upper"]},
            "fisher_p": fisher_p(hys_a, n_active - hys_a, hys_p, n_placebo - hys_p),
            "interpretation": "Hy's Law: ALT or AST >3xULN AND bilirubin >2xULN. Indicates high risk of severe drug-induced liver injury (DILI).",
        },
        "qtc_prolongation": {
            "n_active": qtc_a, "n_placebo": qtc_p,
            "pct_active": rd_qtc["pct_active"], "pct_placebo": rd_qtc["pct_placebo"],
            "risk_difference": rd_qtc["rd"], "rd_ci": {"lower": rd_qtc["ci_lower"], "upper": rd_qtc["ci_upper"]},
            "fisher_p": fisher_p(qtc_a, n_active - qtc_a, qtc_p, n_placebo - qtc_p),
            "definition": "QTc > 480ms or increase > 60ms from baseline",
        },
        "alt_elevation_3xuln": {"n_active": alt3_a, "n_placebo": alt3_p},
        "ast_elevation_3xuln": {"n_active": ast3_a, "n_placebo": ast3_p},
        "bili_elevation_2xuln": {"n_active": bili2_a, "n_placebo": bili2_p},
    }

    # ─── 5. Time-to-First Grade 3+ AE (KM, log-rank, Cox) ───
    if len(adae) > 0:
        g3_first = (adae[adae["AESEV"] >= 3].groupby("USUBJID")["AESTDY"].min()
                    .reset_index().rename(columns={"AESTDY": "first_g3_day"}))
    else:
        g3_first = pd.DataFrame(columns=["USUBJID", "first_g3_day"])

    tte = adsl[["USUBJID", "TRT01P", "FOLLOWUP_DAYS"]].merge(g3_first, on="USUBJID", how="left")
    tte["time"] = np.where(tte["first_g3_day"].isna(), tte["FOLLOWUP_DAYS"], tte["first_g3_day"])
    tte["event"] = np.where(tte["first_g3_day"].isna(), 0, 1)
    tte = tte[tte["time"].notna() & (tte["time"] > 0)].copy()
    tte["time"] = tte["time"].astype(float)

    def _km_median_ci(times, events):
        """KM median + 95% CI, replicating R survival::survfit (conf.type="log",
        Brookmeyer-Crowley step-function inversion) exactly.

        - median: first event time where S(t) <= 0.5
        - LCL: smallest t where S_lower(t) <= 0.5
        - UCL: smallest t where S_upper(t) <  0.5 (NA if upper CI never drops below 0.5)

        S_lower/upper use the log transform: S*exp(∓z*se_log) with
        se_log = sqrt(Greenwood cumulative variance of log S) = sqrt(Σ d/(n(n-d))).
        """
        times = np.asarray(times, dtype=float)
        events = np.asarray(events, dtype=int)
        order = np.argsort(times)
        t = times[order]
        e = events[order]
        ut = np.unique(t)
        S = 1.0
        cum = 0.0
        rows = []
        for ti in ut:
            nr = int(np.sum(t >= ti))
            d = int(np.sum((t == ti) & (e == 1)))
            if nr > 0:
                S *= (1 - d / nr)
                if nr - d > 0:
                    cum += d / (nr * (nr - d))
            se_log = math.sqrt(cum)
            Slo = S * math.exp(-Z975 * se_log) if S > 0 else 0.0
            Shi = S * math.exp(+Z975 * se_log) if S > 0 else 0.0
            rows.append((float(ti), S, Slo, Shi))
        df = pd.DataFrame(rows, columns=["t", "S", "Slo", "Shi"])
        # median: first time S<=0.5
        med_idx = df.index[df["S"] <= 0.5]
        if len(med_idx) == 0:
            return {"median": None, "ci_lower": None, "ci_upper": None}
        med = round(float(df["t"].iloc[med_idx].min()), 4)
        # LCL: smallest t where Slo<=0.5
        lcl_idx = df.index[df["Slo"] <= 0.5]
        ci_lower = round(float(df["t"].iloc[lcl_idx].min()), 4) if len(lcl_idx) else None
        # UCL: smallest t where Shi<0.5; NA if never
        ucl_idx = df.index[df["Shi"] < 0.5]
        ci_upper = round(float(df["t"].iloc[ucl_idx].min()), 4) if len(ucl_idx) else None
        return {"median": med, "ci_lower": ci_lower, "ci_upper": ci_upper}

    t_act = tte[tte["TRT01P"] == "Active"]
    t_plb = tte[tte["TRT01P"] == "Placebo"]
    med_active = _km_median_ci(t_act["time"].values, t_act["event"].values)
    med_placebo = _km_median_ci(t_plb["time"].values, t_plb["event"].values)

    # Log-rank (Mantel-Cox), two-sided
    lr = logrank_test(t_act["time"], t_plb["time"], t_act["event"], t_plb["event"])
    lr_p = round(float(lr.p_value), 6)

    # Cox PH (Efron ties), Active vs Placebo (Placebo reference)
    cox_df = tte[["time", "event", "TRT01P"]].copy()
    cox_df["TRT01P_f"] = (cox_df["TRT01P"] == "Active").astype(int)  # 1=Active, 0=Placebo
    cox_hr = cox_ci_lo = cox_ci_hi = cox_p = None
    if cox_df["TRT01P_f"].nunique() > 1:
        cph = CoxPHFitter()
        try:
            cph.fit(cox_df[["time", "event", "TRT01P_f"]], duration_col="time", event_col="event")
            s = cph.summary.loc["TRT01P_f"]
            cox_hr = round(float(s["exp(coef)"]), 4)
            cox_ci_lo = round(float(s["exp(coef) lower 95%"]), 4)
            cox_ci_hi = round(float(s["exp(coef) upper 95%"]), 4)
            cox_p = round(float(s["p"]), 6)
        except Exception as e:
            sys.stderr.write(f"[warn] Cox fit failed: {e}\n")

    time_to_grade3 = {
        "n_with_g3": int(tte["event"].sum()),
        "median_active": med_active,
        "median_placebo": med_placebo,
        "logrank_p": lr_p,
        "cox_hr": cox_hr,
        "cox_ci": {"lower": cox_ci_lo, "upper": cox_ci_hi},
        "cox_p": cox_p,
        "n_active_events": int(tte.loc[tte["TRT01P"] == "Active", "event"].sum()),
        "n_placebo_events": int(tte.loc[tte["TRT01P"] == "Placebo", "event"].sum()),
    }

    # ─── 6. AE of Special Interest (irAE) ───
    if len(adae) > 0:
        irae = adae[adae["AEOSI"] == "Y"].copy()
    else:
        irae = pd.DataFrame(columns=adae.columns)
    if len(irae) > 0:
        onset = (irae.groupby(["TRT01P", "USUBJID"])["AESTDY"].min()
                 .reset_index().rename(columns={"AESTDY": "onset_day"}))
        agg = onset.groupby("TRT01P").agg(n_subjects=("USUBJID", "nunique"),
                                          median_onset=("onset_day", "median")).reset_index()
    else:
        agg = pd.DataFrame(columns=["TRT01P", "n_subjects", "median_onset"])

    n_irae_a = int(agg.loc[agg["TRT01P"] == "Active", "n_subjects"].sum() if (agg["TRT01P"] == "Active").any() else 0)
    n_irae_p = int(agg.loc[agg["TRT01P"] == "Placebo", "n_subjects"].sum() if (agg["TRT01P"] == "Placebo").any() else 0)
    med_onset_a = _float_round(float(agg.loc[agg["TRT01P"] == "Active", "median_onset"].iloc[0]), 2) if (agg["TRT01P"] == "Active").any() else None
    med_onset_p = _float_round(float(agg.loc[agg["TRT01P"] == "Placebo", "median_onset"].iloc[0]), 2) if (agg["TRT01P"] == "Placebo").any() else None
    rd_irae = risk_diff_ci(n_irae_a, n_active, n_irae_p, n_placebo)

    ae_special_interest = {
        "irae": {
            "n_active": n_irae_a, "n_placebo": n_irae_p,
            "pct_active": rd_irae["pct_active"], "pct_placebo": rd_irae["pct_placebo"],
            "risk_difference": rd_irae["rd"], "rd_ci": {"lower": rd_irae["ci_lower"], "upper": rd_irae["ci_upper"]},
            "fisher_p": fisher_p(n_irae_a, n_active - n_irae_a, n_irae_p, n_placebo - n_irae_p),
            "median_onset_active": med_onset_a, "median_onset_placebo": med_onset_p,
        }
    }

    # ─── 7. Statistical Signal Detection ───
    # 7a. MGPS (Empirical Bayes, add-one-half shrinkage)
    if len(adae) > 0:
        o_active = adae[adae["TRT01P"] == "Active"].groupby("AEDECOD")["USUBJID"].nunique()
        o_placebo = adae[adae["TRT01P"] == "Placebo"].groupby("AEDECOD")["USUBJID"].nunique()
    else:
        o_active = pd.Series(dtype=int); o_placebo = pd.Series(dtype=int)
    all_pts_idx = sorted(set(o_active.index) | set(o_placebo.index))

    mgps_rows = {}
    for pt in all_pts_idx:
        o_a = int(o_active.get(pt, 0))
        o_p = int(o_placebo.get(pt, 0))
        n_pt = o_a + o_p
        e_a = (n_active * n_pt) / n_total
        e_p = (n_placebo * n_pt) / n_total
        ebgm_a = round((o_a + 0.5) / (e_a + 0.5), 4) if e_a > 0 else 0
        ebgm_p = round((o_p + 0.5) / (e_p + 0.5), 4) if e_p > 0 else 0
        signal_a = (ebgm_a >= 2.0 and o_a >= 3 and e_a > 0)
        signal_p = (ebgm_p >= 2.0 and o_p >= 3 and e_p > 0)
        mgps_rows[pt] = {"pt": pt, "o_active": o_a, "o_placebo": o_p,
                         "e_active": round(e_a, 4), "e_placebo": round(e_p, 4),
                         "ebgm_active": ebgm_a, "ebgm_placebo": ebgm_p,
                         "signal_active": bool(signal_a), "signal_placebo": bool(signal_p)}

    # 7b. Risk-difference signals (for common_pts)
    rd_signal_rows = {}
    for pt in common_pts:
        sub = pt_freq[pt_freq["AEDECOD"] == pt]
        n_a = int(sub.loc[sub["TRT01P"] == "Active", "n_subjects"].sum() if (sub["TRT01P"] == "Active").any() else 0)
        n_p = int(sub.loc[sub["TRT01P"] == "Placebo", "n_subjects"].sum() if (sub["TRT01P"] == "Placebo").any() else 0)
        rd = risk_diff_ci(n_a, n_active, n_p, n_placebo)
        rd_signal_rows[pt] = {"pt": pt, "n_active": n_a, "n_placebo": n_p,
                              "rd": rd["rd"], "ci_lower": rd["ci_lower"], "ci_upper": rd["ci_upper"],
                              "fisher_p": fisher_p(n_a, n_active - n_a, n_p, n_placebo - n_p),
                              "signal_active_higher": bool(rd["ci_lower"] > 0)}

    signal_detection = {
        "mgps": {"method": "Empirical Bayes (MGPS-style, add-one-half shrinkage)",
                 "threshold": "EBGM >= 2.0 AND observed >= 3",
                 "results": mgps_rows},
        "risk_difference_signals": rd_signal_rows,
    }

    # ─── 8. Safety Recommendation ───
    hys_signal = (hys_a >= 5) and (rd_hys["ci_lower"] > 0)
    qtc_signal = (qtc_a >= 5) and (rd_qtc["ci_lower"] > 0)
    irae_signal = (n_irae_a >= 10) and (rd_irae["ci_lower"] > 0)
    g3_signal = (rd_g3["ci_lower"] > 0)
    disc_signal = (rd_disc["ci_lower"] > 0)
    died_signal = (rd_died["ci_lower"] > 0)
    n_signals = sum([hys_signal, qtc_signal, irae_signal, g3_signal, disc_signal])

    key_findings = []
    if hys_signal:
        key_findings.append(f"Hy's Law cases significantly higher in Active arm ({hys_a} vs {hys_p}, Fisher p={lab_abnormalities['hys_law']['fisher_p']:.4f}) — high DILI risk")
    if qtc_signal:
        key_findings.append(f"QTc prolongation signal in Active arm ({qtc_a} vs {qtc_p}, Fisher p={lab_abnormalities['qtc_prolongation']['fisher_p']:.4f})")
    if irae_signal:
        key_findings.append(f"Immune-related AEs significantly higher in Active arm ({n_irae_a} vs {n_irae_p}, Fisher p={ae_special_interest['irae']['fisher_p']:.4f})")
    if g3_signal:
        key_findings.append(f"Grade 3+ AE rate higher in Active (RD={rd_g3['rd']*100:.2f}%, 95% CI [{rd_g3['ci_lower']*100:.2f}, {rd_g3['ci_upper']*100:.2f}])")
    if disc_signal:
        key_findings.append(f"Treatment discontinuation due to AEs higher in Active (RD={rd_disc['rd']*100:.2f}%)")

    if hys_signal and n_signals >= 4:
        recommendation = "Pause"
        rationale = ("Multiple significant safety signals including Hy's Law hepatotoxicity with heavy overall signal burden. "
                     "Recommend pausing enrollment pending protocol amendment and DMC charter review.")
    elif hys_signal or (qtc_signal and irae_signal):
        recommendation = "Modify"
        rationale = ("Significant safety signal(s) detected (Hy's Law hepatotoxicity and/or combined QTc+irAE signals). "
                     "Recommend continuing with enhanced monitoring, protocol amendment for hepatotoxicity/cardiac monitoring, and tighter stopping rules.")
    elif n_signals >= 2:
        recommendation = "Modify"
        rationale = "Multiple safety signals detected. Recommend enhanced monitoring and protocol amendment."
    else:
        recommendation = "Continue with enhanced monitoring"
        rationale = "No critical safety signals requiring modification. Recommend continuing with routine DMC monitoring schedule."

    conditions = []
    if hys_signal:
        conditions += ["Implement enhanced hepatotoxicity monitoring (weekly LFTs for first 8 weeks)",
                       "Protocol amendment for Hy's Law case management algorithm",
                       "Consider independent hepatic safety review board"]
    if qtc_signal:
        conditions += ["Implement serial ECG monitoring (baseline, C1D1, C2D1, then monthly)",
                       "Exclude subjects with baseline QTc > 470ms",
                       "Protocol amendment for QTc prolongation management"]
    if irae_signal:
        conditions += ["Implement irAE management guidelines per ASCO/NCCN",
                       "Mandatory corticosteroid availability for Grade 2+ irAE management"]
    conditions += ["Continue routine DMC safety reviews at planned intervals"]

    recommendation_out = {
        "overall": recommendation,
        "rationale": rationale,
        "key_findings": key_findings,
        "conditions": conditions,
        "signals_summary": {"hys_law": bool(hys_signal), "qtc": bool(qtc_signal), "irae": bool(irae_signal),
                            "grade3_plus": bool(g3_signal), "discontinuation": bool(disc_signal),
                            "death": bool(died_signal), "n_signals": int(n_signals)},
    }

    result = {
        "tc_id": "TC-009",
        "tc_title": "Safety Signal Evaluation and DMC Report",
        "level": 3,
        "study_design": {
            "n_subjects": n_total,
            "n_per_arm": {"Active": n_active, "Placebo": n_placebo},
            "total_patient_years": {"Active": py_active, "Placebo": py_placebo},
            "arms": ["Active", "Placebo"],
        },
        "ae_overview": ae_overview,
        "exposure_adjusted": exposure_adjusted,
        "grade3_plus": grade3_plus,
        "lab_abnormalities": lab_abnormalities,
        "time_to_grade3": time_to_grade3,
        "ae_special_interest": ae_special_interest,
        "signal_detection": signal_detection,
        "recommendation": recommendation_out,
    }
    return result


def main():
    ap = argparse.ArgumentParser(description="TC-009 Safety Signal Evaluation (Python ground truth)")
    ap.add_argument("--data-adsl", default=None)
    ap.add_argument("--data-adae", default=None)
    ap.add_argument("--data-adlb", default=None)
    ap.add_argument("--out", "--output", dest="out", default=None)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--n", type=int, default=200)
    args = ap.parse_args()

    if args.data_adsl and args.data_adae and args.data_adlb:
        adsl = pd.read_csv(args.data_adsl)
        adae = pd.read_csv(args.data_adae)
        adlb = pd.read_csv(args.data_adlb)
    else:
        sys.stderr.write("[info] No shared data provided; generating standalone smoke-test data (will NOT match R).\n")
        adsl, adae, adlb = generate_data(seed=args.seed, n_per_arm=args.n)

    result = analyze(adsl, adae, adlb)

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w") as f:
            json.dump(result, f, indent=2, allow_nan=False)
        print(f"Wrote output to: {args.out}")
    else:
        print("\n=== BENCHMARK OUTPUT ===")
        print(json.dumps(result, indent=2, allow_nan=False))
        print("=== END OUTPUT ===")


if __name__ == "__main__":
    main()
