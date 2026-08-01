#!/usr/bin/env python3
"""tc_010_csr_statistical.py — TC-010 Python Ground Truth
Level 3: CSR Statistical Sections (ICH E3)

Computes all statistics that populate CSR Sections 9 and 11 for a completed
Phase III oncology trial, mirroring the R ground truth (tc-010-csr-statistical.R)
so that R and Python produce IDENTICAL results on the SAME shared data
(cross-language score = 1.0000).

REGULATORY NOTE (ITT-only):
    Phase III oncology superiority trial. ITT is the SOLE primary analysis
    population. No per-protocol analysis is performed, per FDA/EMA standards.

Usage:
    python3 tc_010_csr_statistical.py --data-adsl <adsl.csv> --data-adtte <adtte.csv> \
        --data-adrs <adrs.csv> --data-adae <adae.csv> --data-adlb <adlb.csv> \
        --output <TC-010.json>
"""

import argparse
import json
import math
import sys
from collections import Counter, OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd
from lifelines import CoxPHFitter
from lifelines.statistics import logrank_test
from scipy import stats

Z975 = 1.959963984540054  # z_{0.975}


def round4(x):
    if x is None:
        return None
    if isinstance(x, float) and math.isnan(x):
        return None
    return round(float(x), 4)


def pct(num, den):
    if den == 0:
        return None
    return round4(100 * num / den)


def _km_median_ci(times, events):
    """KM median + 95% CI (log transform), replicating R survival::survfit
    (conf.type='log', Brookmeyer-Crowley step-function inversion).

    - median: first event time where S(t) <= 0.5
    - LCL: smallest t where S_lower(t) <= 0.5
    - UCL: smallest t where S_upper(t) <  0.5 (None if never)

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
        se_log = math.sqrt(cum) if cum > 0 else 0.0
        Slo = S * math.exp(-Z975 * se_log) if S > 0 else 0.0
        Shi = S * math.exp(+Z975 * se_log) if S > 0 else 0.0
        rows.append((float(ti), S, Slo, Shi))
    df = pd.DataFrame(rows, columns=["t", "S", "Slo", "Shi"])
    med_idx = df.index[df["S"] <= 0.5]
    if len(med_idx) == 0:
        return {"median": None, "ci_lower": None, "ci_upper": None}
    med = round4(df["t"].iloc[med_idx].min())
    lcl_idx = df.index[df["Slo"] <= 0.5]
    ci_lower = round4(df["t"].iloc[lcl_idx].min()) if len(lcl_idx) else None
    ucl_idx = df.index[df["Shi"] < 0.5]
    ci_upper = round4(df["t"].iloc[ucl_idx].min()) if len(ucl_idx) else None
    return {"median": med, "ci_lower": ci_lower, "ci_upper": ci_upper}


def cox_result(time, event, trt):
    """Cox PH HR + 95% CI + p (Efron ties — lifelines default, matching R coxph ties='efron')."""
    df = pd.DataFrame({"time": time, "event": event, "trt": trt})
    df = df[df["time"] > 0].copy()
    cph = CoxPHFitter()
    cph.fit(df, duration_col="time", event_col="event", formula="trt")
    hr = round4(cph.summary.loc["trt", "exp(coef)"])
    ci_lower = round4(cph.summary.loc["trt", "exp(coef) lower 95%"])
    ci_upper = round4(cph.summary.loc["trt", "exp(coef) upper 95%"])
    p = round4(cph.summary.loc["trt", "p"])
    return {"hr": hr, "ci_lower": ci_lower, "ci_upper": ci_upper, "p": p}


def logrank_p(time, event, trt):
    """Log-rank (Mantel-Cox) p-value, 2-sided."""
    a_mask = np.array(trt) == "Active"
    p_mask = np.array(trt) == "Placebo"
    lr = logrank_test(time[a_mask], time[p_mask], event_observed_A=event[a_mask],
                      event_observed_B=event[p_mask])
    return round4(float(lr.p_value))


def cat_test(a_events, a_n, b_events, b_n):
    """Fisher exact p + risk difference + Wald CI."""
    table = [[a_events, a_n - a_events], [b_events, b_n - b_events]]
    _, ft_p = stats.fisher_exact(table, alternative="two-sided")
    rd = round4(a_events / a_n - b_events / b_n)
    se = math.sqrt((a_events / a_n * (1 - a_events / a_n) / a_n) +
                   (b_events / b_n * (1 - b_events / b_n) / b_n))
    return {
        "rd": rd,
        "ci_lower": round4(rd - 1.96 * se),
        "ci_upper": round4(rd + 1.96 * se),
        "fisher_p": round4(ft_p),
    }


# ─── ARS v1.0 envelope builder ───
def build_ars(result):
    """Build a CDISC ARS v1.0 envelope from the TC-010 result dict.

    Mirrors the build_tc010() function from scripts/ars-extend-level3.py.
    Phase III oncology superiority trial — ITT is the sole primary analysis
    population; no per-protocol analysis per FDA/EMA standards.
    """
    sd = result.get("study_design", {})
    disp = result.get("section_11_1_disposition", {})
    demo = result.get("section_11_2_demographics", {})
    eff = result.get("section_11_4_efficacy", {})
    pfs = eff.get("primary_pfs", {})
    osr = eff.get("secondary_os", {})
    orr = eff.get("secondary_orr_dcr", {})
    safety = result.get("section_11_5_safety", {})
    sby = safety.get("by_arm", {})

    return {
        "ars_version": "1.0",
        "analysisResult": {
            "id": "TC-010",
            "version": "1.0",
            "analysisReason": "ICH E3 CSR statistical sections — disposition, "
                              "demographics, primary/secondary efficacy, subgroup "
                              "forest, sensitivity, safety",
            "analysisMethod": {
                "name": "KM + Cox PH (Efron) + log-rank + RECIST 1.1 + descriptive stats",
                "codeTemplate": "survfit(Surv(AVAL, 1-CNSR) ~ TRT01A); coxph(...); "
                                "prop.test(x, n); t.test(AGE ~ TRT01A)",
                "parameters": {
                    "csr_standard": "ICH E3",
                    "primary_endpoint": sd.get("primary_endpoint"),
                    "secondary_endpoints": sd.get("secondary_endpoints"),
                    "km_ci_method": "Brookmeyer-Crowley (log-log transform)",
                    "cox_ties": "Efron",
                    "response_criteria": "RECIST 1.1",
                    "itt_primary": True,
                    "pp_analysis": "not performed (FDA/EMA oncology standard)",
                },
            },
            "analysisVariables": [
                {"name": "AVAL", "dataset": "ADTTE", "role": "analysis time (PFS/OS)"},
                {"name": "CNSR", "dataset": "ADTTE", "role": "censoring (0=event)"},
                {"name": "BOR", "dataset": "ADRS", "role": "best overall response"},
                {"name": "AESOC", "dataset": "ADAE", "role": "System Organ Class"},
                {"name": "AEDECOD", "dataset": "ADAE", "role": "Preferred Term"},
                {"name": "TRT01A", "dataset": "ADSL", "role": "treatment"},
                {"name": "ITTFL", "dataset": "ADSL", "role": "ITT flag"},
                {"name": "SAFFL", "dataset": "ADSL", "role": "safety flag"},
                {"name": "AGE", "dataset": "ADSL", "role": "age (baseline balance)"},
                {"name": "SEX", "dataset": "ADSL", "role": "sex (baseline balance)"},
            ],
            "analysisPopulation": {
                "name": "ITT (primary) + Safety (secondary)",
                "filter": "ITTFL = 'Y' (primary efficacy); SAFFL = 'Y' (safety)",
            },
            "analysisDataset": "ADTTE/ADRS/ADAE",
            "resultGroups": [
                {"id": "Active", "n": sd.get("n_subjects", 400) // 2 if sd.get("n_subjects") else None},
                {"id": "Placebo", "n": sd.get("n_subjects", 400) // 2 if sd.get("n_subjects") else None},
            ],
            "documentation": "Level 3 ICH E3 CSR statistical sections. Phase III "
                              "oncology superiority trial — ITT is the sole primary "
                              "analysis population; no per-protocol analysis performed "
                              "per FDA/EMA standards. Covers Section 9 (methods) and "
                              "Section 11 (disposition, demographics, primary PFS, "
                              "secondary OS/ORR/DCR, subgroup forest, sensitivity, safety).",
            "analysisResultsData": {
                "statistics": [
                    {"name": "n_randomized", "value": disp.get("n_randomized")},
                    {"name": "n_treated", "value": disp.get("n_treated")},
                    {"name": "n_completed", "value": disp.get("n_completed_total")},
                    {"name": "n_discontinued", "value": disp.get("n_discontinued_total")},
                    {"name": "n_major_deviations", "value": disp.get("n_major_deviations_total")},
                    {"name": "age_balance_p", "value": demo.get("age_balance_test", {}).get("p")},
                    {"name": "sex_balance_p", "value": demo.get("sex_balance_test", {}).get("p")},
                    {"name": "pfs_median_active", "value": pfs.get("by_arm", {}).get("Active", {}).get("median"), "unit": "days"},
                    {"name": "pfs_median_placebo", "value": pfs.get("by_arm", {}).get("Placebo", {}).get("median"), "unit": "days"},
                    {"name": "pfs_cox_hr", "value": pfs.get("cox", {}).get("hr")},
                    {"name": "pfs_cox_ci_lower", "value": pfs.get("cox", {}).get("ci_lower")},
                    {"name": "pfs_cox_ci_upper", "value": pfs.get("cox", {}).get("ci_upper")},
                    {"name": "pfs_cox_p", "value": pfs.get("cox", {}).get("p")},
                    {"name": "pfs_logrank_p", "value": pfs.get("logrank_p")},
                    {"name": "pfs_events_active", "value": pfs.get("by_arm", {}).get("Active", {}).get("n_events")},
                    {"name": "pfs_events_placebo", "value": pfs.get("by_arm", {}).get("Placebo", {}).get("n_events")},
                    {"name": "os_cox_hr", "value": osr.get("cox", {}).get("hr")},
                    {"name": "os_cox_ci_lower", "value": osr.get("cox", {}).get("ci_lower")},
                    {"name": "os_cox_ci_upper", "value": osr.get("cox", {}).get("ci_upper")},
                    {"name": "os_cox_p", "value": osr.get("cox", {}).get("p")},
                    {"name": "os_logrank_p", "value": osr.get("logrank_p")},
                    {"name": "orr_active_pct", "value": orr.get("by_arm", {}).get("Active", {}).get("orr_pct"), "unit": "%"},
                    {"name": "orr_placebo_pct", "value": orr.get("by_arm", {}).get("Placebo", {}).get("orr_pct"), "unit": "%"},
                    {"name": "orr_risk_difference", "value": orr.get("risk_difference", {}).get("rd")},
                    {"name": "orr_fisher_p", "value": orr.get("risk_difference", {}).get("fisher_p")},
                    {"name": "dcr_active_pct", "value": orr.get("by_arm", {}).get("Active", {}).get("dcr_pct"), "unit": "%"},
                    {"name": "dcr_placebo_pct", "value": orr.get("by_arm", {}).get("Placebo", {}).get("dcr_pct"), "unit": "%"},
                    {"name": "sensitivity_pfs_hr", "value": eff.get("sensitivity_pfs", {}).get("cox", {}).get("hr")},
                    {"name": "sensitivity_pfs_p", "value": eff.get("sensitivity_pfs", {}).get("cox", {}).get("p")},
                    {"name": "any_ae_active", "value": sby.get("Active", {}).get("n_any_ae")},
                    {"name": "any_ae_placebo", "value": sby.get("Placebo", {}).get("n_any_ae")},
                    {"name": "sae_active", "value": sby.get("Active", {}).get("n_sae")},
                    {"name": "sae_placebo", "value": sby.get("Placebo", {}).get("n_sae")},
                    {"name": "g3_active", "value": sby.get("Active", {}).get("n_grade3_plus")},
                    {"name": "g3_placebo", "value": sby.get("Placebo", {}).get("n_grade3_plus")},
                    {"name": "n_deaths_total", "value": safety.get("death_summary", {}).get("n_deaths_total")},
                ],
            },
        },
    }


def main():
    parser = argparse.ArgumentParser(description="TC-010 Python Ground Truth")
    parser.add_argument("--data-adsl", default="cross-lang-results/shared/adsl_tc010.csv")
    parser.add_argument("--data-adtte", default="cross-lang-results/shared/adtte_tc010.csv")
    parser.add_argument("--data-adrs", default="cross-lang-results/shared/adrs_tc010.csv")
    parser.add_argument("--data-adae", default="cross-lang-results/shared/adae_tc010.csv")
    parser.add_argument("--data-adlb", default="cross-lang-results/shared/adlb_tc010.csv")
    parser.add_argument("--output", default="cross-lang-results/python-output/TC-010.json")
    parser.add_argument("--ars-output", default=None,
                        help="Write CDISC ARS v1.0 envelope to this path")
    args = parser.parse_args()

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    print(f"[TC-010 Py] Reading shared data...", file=sys.stderr)
    adsl = pd.read_csv(args.data_adsl)
    adtte = pd.read_csv(args.data_adtte)
    adrs = pd.read_csv(args.data_adrs)
    adae = pd.read_csv(args.data_adae)
    adlb = pd.read_csv(args.data_adlb)
    print(f"[TC-010 Py] ADSL={len(adsl)} ADTTE={len(adtte)} ADRS={len(adrs)} "
          f"ADAE={len(adae)} ADLB={len(adlb)}", file=sys.stderr)

    arms = ["Active", "Placebo"]

    def _table_to_dict(s):
        """Convert a pandas Series (value counts) to an OrderedDict of {str: int}."""
        return OrderedDict((str(k), int(v)) for k, v in s.items())

    result = OrderedDict([
        ("tc_id", "TC-010"),
        ("tc_title", "CSR Statistical Sections (ICH E3)"),
        ("level", 3),
        ("study_design", OrderedDict([
            ("study_id", "BENCHMARK-010"),
            ("phase", "Phase III"),
            ("indication", "Advanced solid tumors"),
            ("arms", arms),
            ("n_subjects", int(len(adsl))),
            ("primary_endpoint", "PFS per RECIST 1.1"),
            ("secondary_endpoints", ["ORR", "DCR", "OS"]),
            ("population", "ITT (all randomized subjects)"),
            ("regulatory_note",
             "ITT is the sole primary analysis population. No per-protocol analysis performed per FDA/EMA standards for Phase III oncology."),
        ])),
    ])

    # ── Section 9: Statistical Methods ──
    import platform
    result["section_9_methods"] = OrderedDict([
        ("analysis_populations", OrderedDict([
            ("ITT", "All randomized subjects (ITTFL = Y)"),
            ("safety", "All subjects who received any study treatment (SAFFL = Y)"),
        ])),
        ("primary_analysis", "ITT population"),
        ("primary_endpoint_method",
         "Kaplan-Meier estimation; Cox proportional hazards for HR; log-rank test (2-sided, alpha=0.05)"),
        ("software", OrderedDict([
            ("python", platform.python_version()),
            ("lifelines", __import__("lifelines").__version__),
        ])),
        ("data_cutoff", "Database lock after last patient last visit"),
        ("missing_data_handling",
         "Subjects with missing PFS event date censored at last known tumor assessment date"),
        ("multiplicity",
         "No multiplicity adjustment for primary endpoint (single primary); secondary endpoints reported descriptively"),
    ])

    # ── Section 11.1: Patient Disposition ──
    dispo = OrderedDict()
    dispo["n_randomized"] = int(len(adsl))
    dispo["n_treated"] = int(len(adsl))
    dispo["by_arm"] = OrderedDict()
    for arm in arms:
        sub = adsl[adsl["TRT01P"] == arm]
        disc = sub[sub["DISCONTINUED"] == 1]
        disc_reasons = _table_to_dict(disc["DISC_REASON"].value_counts())
        dispo["by_arm"][arm] = OrderedDict([
            ("n_randomized", int(len(sub))),
            ("n_completed", int((sub["DISCONTINUED"] == 0).sum())),
            ("pct_completed", pct(int((sub["DISCONTINUED"] == 0).sum()), len(sub))),
            ("n_discontinued", int(len(disc))),
            ("pct_discontinued", pct(int(len(disc)), len(sub))),
            ("n_died", int((sub["DIED"] == 1).sum())),
            ("pct_died", pct(int((sub["DIED"] == 1).sum()), len(sub))),
            ("discontinuation_reasons", disc_reasons),
            ("n_major_deviations", int((sub["MAJOR_DEVIATION"] == 1).sum())),
            ("pct_major_deviations", pct(int((sub["MAJOR_DEVIATION"] == 1).sum()), len(sub))),
            ("total_deviations", int(sub["N_DEVIATIONS"].sum())),
        ])
    dispo["n_completed_total"] = int((adsl["DISCONTINUED"] == 0).sum())
    dispo["n_discontinued_total"] = int((adsl["DISCONTINUED"] == 1).sum())
    dispo["n_major_deviations_total"] = int((adsl["MAJOR_DEVIATION"] == 1).sum())
    dispo["total_deviations_all"] = int(adsl["N_DEVIATIONS"].sum())
    result["section_11_1_disposition"] = dispo

    # ── Section 11.2: Demographics ──
    demo = OrderedDict([("by_arm", OrderedDict()), ("overall", OrderedDict())])
    demo_vars = ["AGE", "ECOG", "TRT_DURATION_MO"]
    for arm in arms:
        sub = adsl[adsl["TRT01P"] == arm]
        arm_demo = OrderedDict([("n", int(len(sub)))])
        for dv in demo_vars:
            vals = sub[dv]
            arm_demo[dv] = OrderedDict([
                ("mean", round4(vals.mean())), ("sd", round4(vals.std(ddof=1))),
                ("median", round4(vals.median())), ("min", round4(vals.min())),
                ("max", round4(vals.max())),
            ])
        arm_demo["sex"] = _table_to_dict(sub["SEX"].value_counts())
        arm_demo["agegr1"] = _table_to_dict(sub["AGEGR1"].value_counts())
        arm_demo["race"] = _table_to_dict(sub["RACE"].value_counts())
        arm_demo["ecog_dist"] = _table_to_dict(sub["ECOG"].value_counts())
        arm_demo["disease_stage"] = _table_to_dict(sub["DISEASE_STAGE"].value_counts())
        demo["by_arm"][arm] = arm_demo
    demo["overall"] = OrderedDict([
        ("n", int(len(adsl))),
        ("AGE", OrderedDict([
            ("mean", round4(adsl["AGE"].mean())), ("sd", round4(adsl["AGE"].std(ddof=1))),
            ("median", round4(adsl["AGE"].median())), ("min", round4(adsl["AGE"].min())),
            ("max", round4(adsl["AGE"].max())),
        ])),
        ("sex", _table_to_dict(adsl["SEX"].value_counts())),
        ("agegr1", _table_to_dict(adsl["AGEGR1"].value_counts())),
        ("race", _table_to_dict(adsl["RACE"].value_counts())),
        ("ecog_dist", _table_to_dict(adsl["ECOG"].value_counts())),
        ("disease_stage", _table_to_dict(adsl["DISEASE_STAGE"].value_counts())),
    ])
    # Balance tests (diff = Placebo - Active, matching R's diff(estimate) convention)
    age_g = {"Active": adsl[adsl["TRT01P"] == "Active"]["AGE"].values,
             "Placebo": adsl[adsl["TRT01P"] == "Placebo"]["AGE"].values}
    age_tt = stats.ttest_ind(age_g["Active"], age_g["Placebo"], equal_var=False)
    demo["age_balance_test"] = OrderedDict([
        ("method", "t-test"), ("p", round4(age_tt.pvalue)),
        ("mean_diff", round4(age_g["Placebo"].mean() - age_g["Active"].mean())),
    ])
    sex_tab = pd.crosstab(adsl["SEX"], adsl["TRT01P"])
    chi2, sex_p, _, _ = stats.chi2_contingency(sex_tab.values)
    demo["sex_balance_test"] = OrderedDict([("method", "chi-square"), ("p", round4(sex_p))])
    result["section_11_2_demographics"] = demo

    # ── Section 11.4: Efficacy ──
    eff = OrderedDict()

    # Primary: PFS
    pfs = adtte[adtte["PARAM"] == "PFS"].copy()
    pfs_result = OrderedDict([("endpoint", "PFS"), ("method", "Kaplan-Meier + Cox PH + log-rank")])
    pfs_result["by_arm"] = OrderedDict()
    for arm in arms:
        sub = pfs[pfs["TRT01P"] == arm]
        mc = _km_median_ci(sub["AVAL"].values, (1 - sub["CNSR"]).values)
        ev = int((sub["CNSR"] == 0).sum())
        pfs_result["by_arm"][arm] = OrderedDict([
            ("n", int(len(sub))), ("n_events", ev), ("n_censored", int((sub["CNSR"] == 1).sum())),
            ("median", mc["median"]), ("ci_lower", mc["ci_lower"]), ("ci_upper", mc["ci_upper"]),
        ])
    pfs_result["cox"] = cox_result(pfs["AVAL"].values, (1 - pfs["CNSR"]).values, pfs["TRT01PN"].values)
    pfs_result["logrank_p"] = logrank_p(pfs["AVAL"].values, (1 - pfs["CNSR"]).values, pfs["TRT01P"].values)
    pfs_result["interpretation"] = ("Significant PFS benefit for Active vs Placebo"
                                     if pfs_result["cox"]["p"] < 0.05
                                     else "No significant PFS difference")
    eff["primary_pfs"] = pfs_result

    # Secondary: OS
    os_d = adtte[adtte["PARAM"] == "OS"].copy()
    os_result = OrderedDict([("endpoint", "OS"), ("method", "Kaplan-Meier + Cox PH + log-rank")])
    os_result["by_arm"] = OrderedDict()
    for arm in arms:
        sub = os_d[os_d["TRT01P"] == arm]
        mc = _km_median_ci(sub["AVAL"].values, (1 - sub["CNSR"]).values)
        os_result["by_arm"][arm] = OrderedDict([
            ("n", int(len(sub))), ("n_events", int((sub["CNSR"] == 0).sum())),
            ("n_censored", int((sub["CNSR"] == 1).sum())),
            ("median", mc["median"]), ("ci_lower", mc["ci_lower"]), ("ci_upper", mc["ci_upper"]),
        ])
    os_result["cox"] = cox_result(os_d["AVAL"].values, (1 - os_d["CNSR"]).values, os_d["TRT01PN"].values)
    os_result["logrank_p"] = logrank_p(os_d["AVAL"].values, (1 - os_d["CNSR"]).values, os_d["TRT01P"].values)
    eff["secondary_os"] = os_result

    # Secondary: ORR + DCR
    orr_result = OrderedDict([("endpoint", "ORR (CR+PR)"), ("method", "RECIST 1.1")])
    orr_result["by_arm"] = OrderedDict()
    for arm in arms:
        sub = adrs[adrs["TRT01P"] == arm]
        n = len(sub)
        n_resp = int(sub["AVALC"].isin(["CR", "PR"]).sum())
        n_dcr = int(sub["AVALC"].isin(["CR", "PR", "SD"]).sum())
        orr_result["by_arm"][arm] = OrderedDict([
            ("n", n), ("n_responders", n_resp), ("orr_pct", pct(n_resp, n)),
            ("n_dcr", n_dcr), ("dcr_pct", pct(n_dcr, n)),
            ("bor_dist", _table_to_dict(sub["AVALC"].value_counts())),
        ])
    a_sub = adrs[adrs["TRT01P"] == "Active"]
    p_sub = adrs[adrs["TRT01P"] == "Placebo"]
    a_resp = int(a_sub["AVALC"].isin(["CR", "PR"]).sum())
    p_resp = int(p_sub["AVALC"].isin(["CR", "PR"]).sum())
    orr_result["risk_difference"] = cat_test(a_resp, len(a_sub), p_resp, len(p_sub))
    a_dcr = int(a_sub["AVALC"].isin(["CR", "PR", "SD"]).sum())
    p_dcr = int(p_sub["AVALC"].isin(["CR", "PR", "SD"]).sum())
    orr_result["dcr_risk_difference"] = cat_test(a_dcr, len(a_sub), p_dcr, len(p_sub))
    eff["secondary_orr_dcr"] = orr_result

    # Subgroup forest plot
    pfs_adsl = pfs.merge(adsl[["USUBJID", "SEX", "AGEGR1", "ECOG", "DISEASE_STAGE"]],
                         on="USUBJID", how="left")
    subgroups = [
        ("SEX", "Sex (M vs F)"),
        ("AGEGR1", "Age group (<65 vs >=65)"),
        ("ECOG", "ECOG (0 vs 1)"),
        ("DISEASE_STAGE", "Disease stage (IIIB vs IV)"),
    ]
    subgroup_results = OrderedDict()
    for sg_var, sg_label in subgroups:
        sg_res = OrderedDict()
        levels = sorted(pfs_adsl[sg_var].dropna().unique())
        for lv in levels:
            sub = pfs_adsl[pfs_adsl[sg_var] == lv]
            if len(sub) > 5 and sub["TRT01PN"].nunique() == 2 and int((sub["CNSR"] == 0).sum()) > 2:
                try:
                    cox = cox_result(sub["AVAL"].values, (1 - sub["CNSR"]).values, sub["TRT01PN"].values)
                except Exception:
                    cox = {"hr": None, "ci_lower": None, "ci_upper": None, "p": None}
                sg_res[str(lv)] = OrderedDict([
                    ("n", int(len(sub))), ("n_events", int((sub["CNSR"] == 0).sum())),
                    ("hr", cox["hr"]), ("ci_lower", cox["ci_lower"]),
                    ("ci_upper", cox["ci_upper"]), ("p", cox["p"]),
                ])
            else:
                sg_res[str(lv)] = OrderedDict([
                    ("n", int(len(sub))), ("n_events", int((sub["CNSR"] == 0).sum())), ("hr", None),
                ])
        subgroup_results[sg_var] = sg_res
    eff["subgroup_forest"] = subgroup_results

    # Sensitivity: PFS censoring at non-progression discontinuation
    pfs_sens = pfs.merge(adsl[["USUBJID", "DISC_REASON", "FOLLOWUP_DAYS"]], on="USUBJID", how="left")
    pfs_sens["CNSR_sens"] = pfs_sens["CNSR"].copy()
    pfs_sens["AVAL_sens"] = pfs_sens["AVAL"].copy()
    mask = (pfs_sens["DISC_REASON"].isin(["Withdrawal by subject", "Physician decision"]) &
            (pfs_sens["CNSR"] == 0))
    pfs_sens.loc[mask, "CNSR_sens"] = 1
    pfs_sens.loc[mask, "AVAL_sens"] = pfs_sens.loc[mask, ["AVAL_sens", "FOLLOWUP_DAYS"]].min(axis=1)
    sens_result = OrderedDict([
        ("method", "Censor at last follow-up if discontinued for non-progression reasons"),
        ("cox", cox_result(pfs_sens["AVAL_sens"].values, (1 - pfs_sens["CNSR_sens"]).values,
                           pfs_sens["TRT01PN"].values)),
        ("logrank_p", logrank_p(pfs_sens["AVAL_sens"].values, (1 - pfs_sens["CNSR_sens"]).values,
                                pfs_sens["TRT01P"].values)),
    ])
    eff["sensitivity_pfs"] = sens_result
    result["section_11_4_efficacy"] = eff

    # ── Section 11.5: Safety ──
    safety = OrderedDict([("by_arm", OrderedDict())])
    for arm in arms:
        sub_adsl = adsl[adsl["TRT01P"] == arm]
        sub_ae = adae[adae["TRT01P"] == arm]
        n = len(sub_adsl)
        subj_ae = sub_ae["USUBJID"].nunique()
        subj_sae = sub_ae[sub_ae["AESER"] == "Y"]["USUBJID"].nunique()
        subj_g3 = sub_ae[sub_ae["AETOXGR"] >= 3]["USUBJID"].nunique()
        subj_disc = sub_ae[sub_ae["AEACN"] == "Drug withdrawn"]["USUBJID"].nunique()
        subj_died = int((sub_adsl["DIED"] == 1).sum())
        safety["by_arm"][arm] = OrderedDict([
            ("n", n),
            ("n_any_ae", int(subj_ae)), ("pct_any_ae", pct(subj_ae, n)),
            ("n_sae", int(subj_sae)), ("pct_sae", pct(subj_sae, n)),
            ("n_grade3_plus", int(subj_g3)), ("pct_grade3_plus", pct(subj_g3, n)),
            ("n_disc_due_ae", int(subj_disc)), ("pct_disc_due_ae", pct(subj_disc, n)),
            ("n_deaths", subj_died), ("pct_deaths", pct(subj_died, n)),
            ("total_ae_reports", int(len(sub_ae))),
            ("n_ae_by_grade", _table_to_dict(sub_ae["AETOXGR"].value_counts().sort_index())),
        ])
    # Top SOCs (Active)
    active_ae = adae[adae["TRT01P"] == "Active"]
    soc_counts = active_ae.groupby("AESOC")["USUBJID"].nunique().sort_values(ascending=False)
    n_active = len(adsl[adsl["TRT01P"] == "Active"])
    top_socs = OrderedDict()
    for soc_name in list(soc_counts.index)[:5]:
        sub = active_ae[active_ae["AESOC"] == soc_name]
        n_subj = sub["USUBJID"].nunique()
        pt_counts = _table_to_dict(sub["AEDECOD"].value_counts())
        top_pts = OrderedDict(list(pt_counts.items())[:3])
        top_socs[soc_name] = OrderedDict([
            ("n_subjects", int(n_subj)), ("pct", pct(n_subj, n_active)),
            ("n_reports", int(len(sub))), ("top_pts", top_pts),
        ])
    safety["top_socs_active"] = top_socs
    # Death summary
    safety["death_summary"] = OrderedDict([
        ("n_deaths_total", int(adsl["DIED"].sum())),
        ("n_deaths_active", int(adsl[adsl["TRT01P"] == "Active"]["DIED"].sum())),
        ("n_deaths_placebo", int(adsl[adsl["TRT01P"] == "Placebo"]["DIED"].sum())),
        ("n_grade5_ae_reports", int((adae["AETOXGR"] == 5).sum())),
    ])
    # Lab abnormalities
    lab = OrderedDict()
    for arm in arms:
        sub = adlb[adlb["TRT01P"] == arm]
        lab[arm] = OrderedDict([
            ("n_alt_3xuln", int((sub["ALT_3XULN"] == 1).sum())),
            ("pct_alt_3xuln", pct(int((sub["ALT_3XULN"] == 1).sum()), len(sub))),
            ("n_ast_3xuln", int((sub["AST_3XULN"] == 1).sum())),
            ("pct_ast_3xuln", pct(int((sub["AST_3XULN"] == 1).sum()), len(sub))),
            ("n_bili_2xuln", int((sub["BILI_2XULN"] == 1).sum())),
            ("pct_bili_2xuln", pct(int((sub["BILI_2XULN"] == 1).sum()), len(sub))),
            ("alt_mean", round4(sub["ALT_MAX"].mean())),
            ("ast_mean", round4(sub["AST_MAX"].mean())),
            ("bili_mean", round4(sub["BILI_MAX"].mean())),
        ])
    safety["lab_abnormalities"] = lab
    result["section_11_5_safety"] = safety

    # ── Write output ──
    json_str = json.dumps(result, indent=2, default=str)
    Path(args.output).write_text(json_str)
    print(f"[TC-010 Py] Wrote {args.output} ({len(json_str)} bytes)", file=sys.stderr)

    # Summary
    print("[TC-010 Py] Summary:", file=sys.stderr)
    print(f"  PFS: Active median={pfs_result['by_arm']['Active']['median']}, "
          f"Placebo median={pfs_result['by_arm']['Placebo']['median']}, "
          f"HR={pfs_result['cox']['hr']}, p={pfs_result['cox']['p']}", file=sys.stderr)
    print(f"  OS:  Active median={os_result['by_arm']['Active']['median']}, "
          f"Placebo median={os_result['by_arm']['Placebo']['median']}, "
          f"HR={os_result['cox']['hr']}, p={os_result['cox']['p']}", file=sys.stderr)
    print(f"  ORR: Active={orr_result['by_arm']['Active']['orr_pct']}%, "
          f"Placebo={orr_result['by_arm']['Placebo']['orr_pct']}%", file=sys.stderr)
    print("[TC-010 Py] Done.", file=sys.stderr)

    # ── ARS envelope output ──
    if args.ars_output:
        ars_envelope = build_ars(result)
        ars_path = Path(args.ars_output)
        ars_path.parent.mkdir(parents=True, exist_ok=True)
        with open(ars_path, "w") as f:
            json.dump(ars_envelope, f, indent=2, default=str)
        print(f"[TC-010 Py] Wrote ARS envelope to: {ars_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
