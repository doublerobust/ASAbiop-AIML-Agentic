#!/usr/bin/env python3
"""
ARS Envelope Generator for Remaining Level 1 Test Cases

Covers 13 TCs that have cross-language-verified JSON outputs but do not yet
have ARS envelopes generated:
  TC-001 (KM Median PFS), TC-002 (Demographics), TC-019 (Concomitant Meds),
  TC-023 (DCR), TC-024 (OS), TC-025 (BOR Summary), TC-026 (PFS2),
  TC-027 (DOSD), TC-029 (AE Severity), TC-030 (ORR Interaction),
  TC-032 (irAE Summary), TC-033 (Dose Intensity), TC-034 (Sufficient Follow-up)

Reads existing benchmark JSON outputs from cross-lang-results/{r,python}-output/,
wraps them in CDISC ARS v1.0 envelopes, and writes to cross-lang-results/ars-output/.

This extends ARS coverage from 17 TCs to 30 TCs (all with verified output).

Regulatory note: For Phase III oncology superiority trials, ITT is the sole
primary analysis population per FDA/EMA standards. No per-protocol analysis is
performed. TCs involving safety endpoints use the safety analysis set
(SAFFL = 'Y'). TC-027 (DOSD) is a subset of ITT subjects with BOR=SD, still
within the ITT framework.
"""

import json
from pathlib import Path
from typing import Any

BENCH_DIR = Path(__file__).parent.parent
R_DIR = BENCH_DIR / "cross-lang-results" / "r-output"
PY_DIR = BENCH_DIR / "cross-lang-results" / "python-output"
ARS_DIR = BENCH_DIR / "cross-lang-results" / "ars-output"

# Shared regulatory documentation for Phase III oncology ITT-only TCs
_ITT_DOC = (
    "Phase III oncology superiority trial. ITT is the sole primary analysis "
    "population per FDA/EMA standards; no per-protocol analysis is performed."
)


def make_ars(
    tc_id: str,
    reason: str,
    method_name: str,
    code_template: str,
    parameters: dict,
    variables: list,
    population: dict,
    dataset: str,
    result_groups: list,
    documentation: str,
    statistics: list,
) -> dict:
    """Build an ARS v1.0 envelope."""
    return {
        "ars_version": "1.0",
        "analysisResult": {
            "id": tc_id,
            "version": "1.0",
            "analysisReason": reason,
            "analysisMethod": {
                "name": method_name,
                "codeTemplate": code_template,
                "parameters": parameters,
            },
            "analysisVariables": variables,
            "analysisPopulation": population,
            "analysisDataset": dataset,
            "resultGroups": result_groups,
            "documentation": documentation,
            "analysisResultsData": {
                "statistics": statistics,
            },
        },
    }


# ─────────────────────────────────────────────────────
# Per-TC ARS builders
# ─────────────────────────────────────────────────────

def build_tc001(data: dict) -> dict:
    """TC-001: KM Median PFS estimation."""
    return make_ars(
        tc_id="TC-001",
        reason="Primary efficacy: Kaplan-Meier median PFS estimation with 95% CI",
        method_name="Kaplan-Meier survival estimation",
        code_template="survfit(Surv(AVAL, 1-CNSR) ~ 1)",
        parameters={
            "ci_method": data.get("ci_method", "log-log"),
            "estimable": data.get("estimable", True),
        },
        variables=[
            {"name": "AVAL", "dataset": "ADTTE", "role": "analysis time"},
            {"name": "CNSR", "dataset": "ADTTE", "role": "censoring"},
            {"name": "TRT01A", "dataset": "ADSL", "role": "treatment"},
            {"name": "ITTFL", "dataset": "ADSL", "role": "ITT flag"},
        ],
        population={"name": "ITT", "filter": "ITTFL = 'Y'"},
        dataset="ADTTE",
        result_groups=[{"id": "Overall", "n": data.get("n_total", 0)}],
        documentation=f"KM median PFS estimation. {_ITT_DOC}",
        statistics=[
            {"name": "median_pfs", "value": data.get("median_pfs"), "unit": "months"},
            {"name": "ci_lower", "value": data.get("ci_lower"), "unit": "months"},
            {"name": "ci_upper", "value": data.get("ci_upper"), "unit": "months"},
            {"name": "n_events", "value": data.get("n_events")},
            {"name": "n_total", "value": data.get("n_total")},
            {"name": "estimable", "value": data.get("estimable")},
        ],
    )


def build_tc002(data: dict) -> dict:
    """TC-002: Baseline demographics table."""
    age_by_arm = data.get("age_by_arm", [])
    exp_age = next((a for a in age_by_arm if a.get("TRT01PN") == 1), {})
    ctl_age = next((a for a in age_by_arm if a.get("TRT01PN") == 0), {})
    n_total = data.get("n_total", 0)
    n_exp = exp_age.get("count", 0)
    n_ctl = ctl_age.get("count", 0)

    # Categorical counts: extract sex M/F per arm
    cats = data.get("categorical_by_arm", [])
    sex_m_exp = next((c.get("n", 0) for c in cats if c.get("variable") == "Sex" and c.get("level") == "M" and c.get("TRT01PN") == 1), 0)
    sex_f_exp = next((c.get("n", 0) for c in cats if c.get("variable") == "Sex" and c.get("level") == "F" and c.get("TRT01PN") == 1), 0)
    sex_m_ctl = next((c.get("n", 0) for c in cats if c.get("variable") == "Sex" and c.get("level") == "M" and c.get("TRT01PN") == 0), 0)
    sex_f_ctl = next((c.get("n", 0) for c in cats if c.get("variable") == "Sex" and c.get("level") == "F" and c.get("TRT01PN") == 0), 0)

    return make_ars(
        tc_id="TC-002",
        reason="Baseline characteristics: demographics summary table by treatment arm",
        method_name="Descriptive statistics + frequency tabulation",
        code_template="summary(AGE ~ TRT01P); table(SEX, TRT01P)",
        parameters={
            "continuous_vars": ["AGE"],
            "categorical_vars": ["SEX", "RACE", "ECOG"],
            "stats": ["n", "mean", "SD", "median", "min", "max"],
        },
        variables=[
            {"name": "AGE", "dataset": "ADSL", "role": "continuous: age"},
            {"name": "SEX", "dataset": "ADSL", "role": "categorical: sex"},
            {"name": "RACE", "dataset": "ADSL", "role": "categorical: race"},
            {"name": "ECOG", "dataset": "ADSL", "role": "categorical: ECOG"},
            {"name": "TRT01P", "dataset": "ADSL", "role": "treatment"},
            {"name": "SAFFL", "dataset": "ADSL", "role": "safety flag"},
        ],
        population={"name": "Safety", "filter": "SAFFL = 'Y'"},
        dataset="ADSL",
        result_groups=[
            {"id": "Active", "n": n_exp},
            {"id": "Placebo", "n": n_ctl},
        ],
        documentation=f"Baseline demographics: age (continuous) and sex/race/ECOG (categorical) by treatment arm. {_ITT_DOC}",
        statistics=[
            {"name": "n_total", "value": n_total},
            {"name": "n_active", "value": n_exp},
            {"name": "n_placebo", "value": n_ctl},
            {"name": "mean_age_active", "value": exp_age.get("mean"), "unit": "years"},
            {"name": "mean_age_placebo", "value": ctl_age.get("mean"), "unit": "years"},
            {"name": "median_age_active", "value": exp_age.get("median"), "unit": "years"},
            {"name": "median_age_placebo", "value": ctl_age.get("median"), "unit": "years"},
            {"name": "sd_age_active", "value": exp_age.get("std"), "unit": "years"},
            {"name": "sd_age_placebo", "value": ctl_age.get("std"), "unit": "years"},
            {"name": "min_age_active", "value": exp_age.get("min"), "unit": "years"},
            {"name": "max_age_active", "value": exp_age.get("max"), "unit": "years"},
            {"name": "min_age_placebo", "value": ctl_age.get("min"), "unit": "years"},
            {"name": "max_age_placebo", "value": ctl_age.get("max"), "unit": "years"},
            {"name": "n_sex_male_active", "value": sex_m_exp},
            {"name": "n_sex_female_active", "value": sex_f_exp},
            {"name": "n_sex_male_placebo", "value": sex_m_ctl},
            {"name": "n_sex_female_placebo", "value": sex_f_ctl},
        ],
    )


def build_tc019(data: dict) -> dict:
    """TC-019: Concomitant medications summary table."""
    n_exp = data.get("n_experimental", 0)
    n_ctl = data.get("n_control", 0)
    summary = data.get("summary_rows", [])
    any_cm = summary[0] if summary else {}
    detailed = data.get("detailed_rows", [])
    atc_classes = set()
    for row in detailed:
        atc_classes.add(row.get("atc_class", ""))
    n_atc = len(atc_classes)

    return make_ars(
        tc_id="TC-019",
        reason="Safety: concomitant medications summary by ATC class and medication",
        method_name="Frequency tabulation by ATC hierarchy",
        code_template="aggregate(CMDECOD ~ TRT01A + ATC_CLASS, data=ADCM)",
        parameters={
            "hierarchy": "ATC class → medication",
            "sort": "alphabetical by ATC class",
        },
        variables=[
            {"name": "CMDECOD", "dataset": "ADCM", "role": "medication name"},
            {"name": "ATC_CLASS", "dataset": "ADCM", "role": "ATC class"},
            {"name": "TRT01A", "dataset": "ADSL", "role": "treatment"},
            {"name": "SAFFL", "dataset": "ADSL", "role": "safety flag"},
        ],
        population={"name": "Safety", "filter": "SAFFL = 'Y'"},
        dataset="ADCM",
        result_groups=[
            {"id": "Experimental", "n": n_exp},
            {"id": "Control", "n": n_ctl},
        ],
        documentation=f"Concomitant medications summary: {n_atc} ATC classes, {len(detailed)} detailed rows (class + medication). {_ITT_DOC}",
        statistics=[
            {"name": "n_experimental", "value": n_exp},
            {"name": "n_control", "value": n_ctl},
            {"name": "n_atc_classes", "value": n_atc},
            {"name": "n_detailed_rows", "value": len(detailed)},
            {"name": "n_any_conmed_experimental", "value": any_cm.get("n_experimental", 0)},
            {"name": "n_any_conmed_control", "value": any_cm.get("n_control", 0)},
            {"name": "pct_any_conmed_experimental", "value": any_cm.get("pct_experimental", 0), "unit": "%"},
            {"name": "pct_any_conmed_control", "value": any_cm.get("pct_control", 0), "unit": "%"},
        ],
    )


def build_tc023(data: dict) -> dict:
    """TC-023: Disease Control Rate (DCR) by subgroup."""
    o = data.get("overall", {})
    n_exp = o.get("n_experimental", 0)
    n_ctl = o.get("n_control", 0)
    bor = data.get("bor_distribution", [])

    return make_ars(
        tc_id="TC-023",
        reason="Efficacy: Disease Control Rate (DCR = CR + PR + SD) by subgroup with CI",
        method_name="Binomial proportion + Wald CI",
        code_template="prop.test(x=disease_controlled, n=n_total)",
        parameters={
            "dcr_definition": data.get("dcr_definition", "CR + PR + SD"),
            "ci_method": "wald",
            "subgroups": ["SEX", "AGEGR1", "ECOG"],
        },
        variables=[
            {"name": "BOR", "dataset": "ADRS", "role": "best overall response"},
            {"name": "TRT01A", "dataset": "ADSL", "role": "treatment"},
            {"name": "ITTFL", "dataset": "ADSL", "role": "ITT flag"},
            {"name": "SEX", "dataset": "ADSL", "role": "subgroup: sex"},
            {"name": "AGEGR1", "dataset": "ADSL", "role": "subgroup: age group"},
            {"name": "ECOG", "dataset": "ADSL", "role": "subgroup: ECOG"},
        ],
        population={"name": "ITT", "filter": "ITTFL = 'Y'"},
        dataset="ADRS",
        result_groups=[
            {"id": "Experimental", "n": n_exp},
            {"id": "Control", "n": n_ctl},
        ],
        documentation=f"DCR (CR+PR+SD) overall and by subgroup (SEX, AGEGR1, ECOG) with 95% CI. {_ITT_DOC}",
        statistics=[
            {"name": "dcr_experimental", "value": o.get("dcr_experimental"), "unit": "%"},
            {"name": "dcr_control", "value": o.get("dcr_control"), "unit": "%"},
            {"name": "dcr_difference", "value": o.get("dcr_difference"), "unit": "%"},
            {"name": "diff_ci_lower", "value": o.get("diff_ci_lower"), "unit": "%"},
            {"name": "diff_ci_upper", "value": o.get("diff_ci_upper"), "unit": "%"},
            {"name": "n_experimental", "value": n_exp},
            {"name": "n_control", "value": n_ctl},
            {"name": "disease_controlled_exp", "value": o.get("disease_controlled_exp")},
            {"name": "disease_controlled_ctrl", "value": o.get("disease_controlled_ctrl")},
            {"name": "ci_lower_experimental", "value": o.get("ci_lower_experimental"), "unit": "%"},
            {"name": "ci_upper_experimental", "value": o.get("ci_upper_experimental"), "unit": "%"},
            {"name": "ci_lower_control", "value": o.get("ci_lower_control"), "unit": "%"},
            {"name": "ci_upper_control", "value": o.get("ci_upper_control"), "unit": "%"},
        ] + [
            {"name": f"n_cr_{'exp' if r.get('arm') == 'Experimental' else 'ctrl'}", "value": r.get("n")}
            for r in bor if r.get("bor") == "CR"
        ],
    )


def _build_survival_tc(tc_id, reason, endpoint_name, data, median_key, dataset="ADTTE"):
    """Shared builder for survival-analysis TCs (TC-024, TC-026, TC-027)."""
    arm_exp = data.get("arm_experimental", {})
    arm_ctl = data.get("arm_control", {})
    censoring = data.get("censoring_summary", {})
    subgroups = data.get("subgroups", [])

    pop_name = data.get("population", "ITT")
    pop_filter = "ITTFL = 'Y'" if "ITT" in pop_name else "SAFFL = 'Y'"

    return make_ars(
        tc_id=tc_id,
        reason=reason,
        method_name="Kaplan-Meier + Cox PH + log-rank",
        code_template="survfit(Surv(AVAL, 1-CNSR) ~ TRT01A); coxph(...); survdiff(...)",
        parameters={
            "endpoint": endpoint_name,
            "ci_method": arm_exp.get("ci_method", "log-log"),
            "population": pop_name,
            "n_subgroups": len(subgroups),
        },
        variables=[
            {"name": "AVAL", "dataset": dataset, "role": "analysis time"},
            {"name": "CNSR", "dataset": dataset, "role": "censoring"},
            {"name": "TRT01A", "dataset": "ADSL", "role": "treatment"},
            {"name": "SEX", "dataset": "ADSL", "role": "subgroup: sex"},
            {"name": "AGEGR1", "dataset": "ADSL", "role": "subgroup: age group"},
            {"name": "ECOG", "dataset": "ADSL", "role": "subgroup: ECOG"},
        ],
        population={"name": pop_name, "filter": pop_filter},
        dataset=dataset,
        result_groups=[
            {"id": "Experimental", "n": arm_exp.get("n_total", 0)},
            {"id": "Control", "n": arm_ctl.get("n_total", 0)},
        ],
        documentation=f"{endpoint_name} analysis: KM median + CI, Cox PH HR + CI, log-rank test, subgroup forest plots. {_ITT_DOC}",
        statistics=[
            {"name": f"median_{endpoint_name.lower().replace(' ', '_')}_experimental", "value": arm_exp.get(median_key), "unit": "months"},
            {"name": f"median_{endpoint_name.lower().replace(' ', '_')}_control", "value": arm_ctl.get(median_key), "unit": "months"},
            {"name": "median_ci_lower_experimental", "value": arm_exp.get("median_ci_lower"), "unit": "months"},
            {"name": "median_ci_upper_experimental", "value": arm_exp.get("median_ci_upper"), "unit": "months"},
            {"name": "median_ci_lower_control", "value": arm_ctl.get("median_ci_lower"), "unit": "months"},
            {"name": "median_ci_upper_control", "value": arm_ctl.get("median_ci_upper"), "unit": "months"},
            {"name": "hazard_ratio", "value": arm_exp.get("hazard_ratio")},
            {"name": "hr_ci_lower", "value": arm_exp.get("hr_ci_lower")},
            {"name": "hr_ci_upper", "value": arm_exp.get("hr_ci_upper")},
            {"name": "logrank_chisq", "value": arm_exp.get("logrank_chisq")},
            {"name": "logrank_p", "value": arm_exp.get("logrank_p")},
            {"name": "n_events_experimental", "value": arm_exp.get("n_events")},
            {"name": "n_events_control", "value": arm_ctl.get("n_events")},
            {"name": "n_total_experimental", "value": arm_exp.get("n_total")},
            {"name": "n_total_control", "value": arm_ctl.get("n_total")},
            {"name": "event_rate_experimental", "value": arm_exp.get("event_rate")},
            {"name": "event_rate_control", "value": arm_ctl.get("event_rate")},
            {"name": "n_censored_total", "value": censoring.get("n_censored")},
            {"name": "n_events_total", "value": censoring.get("n_events")},
            {"name": "censoring_rate", "value": censoring.get("censoring_rate")},
            {"name": "estimable", "value": arm_exp.get("estimable", True)},
        ] + [
            {"name": f"subgroup_hr_{sg.get('variable', '')}_{sg.get('level', '')}", "value": sg.get("hr")}
            for sg in subgroups
        ],
    )


def build_tc024(data: dict) -> dict:
    """TC-024: Overall Survival (OS)."""
    return _build_survival_tc(
        "TC-024",
        "Secondary efficacy: Overall Survival (OS) KM median, Cox HR, log-rank, subgroup forest",
        "Overall Survival",
        data,
        "median_os",
    )


def build_tc025(data: dict) -> dict:
    """TC-025: Best Overall Response (BOR) summary."""
    s = data.get("summary", {})
    by_arm = s.get("by_arm", {})
    arm_exp = by_arm.get("1", {})
    arm_ctl = by_arm.get("0", {})
    bor_dist = s.get("bor_distribution", {})

    return make_ars(
        tc_id="TC-025",
        reason="Efficacy: Best Overall Response (BOR) summary with ORR, DCR, Fisher exact test",
        method_name="Binomial proportion + Fisher exact test",
        code_template="fisher.test(matrix(c(orr, n-orr), nrow=2))",
        parameters={
            "endpoint": data.get("endpoint", "Best Overall Response"),
            "response_criteria": "RECIST 1.1 (CR + PR = ORR; CR + PR + SD = DCR)",
        },
        variables=[
            {"name": "BOR", "dataset": "ADRS", "role": "best overall response"},
            {"name": "TRT01A", "dataset": "ADSL", "role": "treatment"},
            {"name": "ITTFL", "dataset": "ADSL", "role": "ITT flag"},
        ],
        population={"name": "ITT", "filter": "ITTFL = 'Y'"},
        dataset="ADRS",
        result_groups=[
            {"id": "Experimental", "n": arm_exp.get("n_total", 0)},
            {"id": "Control", "n": arm_ctl.get("n_total", 0)},
        ],
        documentation=f"BOR summary: CR/PR/SD/PD/NE counts, ORR and DCR with 95% CI, ORR difference with Fisher exact and chi-square tests. {_ITT_DOC}",
        statistics=[
            {"name": "orr_rate_experimental", "value": arm_exp.get("orr_rate"), "unit": "proportion"},
            {"name": "orr_rate_control", "value": arm_ctl.get("orr_rate"), "unit": "proportion"},
            {"name": "orr_n_experimental", "value": arm_exp.get("orr_n")},
            {"name": "orr_n_control", "value": arm_ctl.get("orr_n")},
            {"name": "orr_ci_lower_experimental", "value": arm_exp.get("orr_ci_lower")},
            {"name": "orr_ci_upper_experimental", "value": arm_exp.get("orr_ci_upper")},
            {"name": "orr_ci_lower_control", "value": arm_ctl.get("orr_ci_lower")},
            {"name": "orr_ci_upper_control", "value": arm_ctl.get("orr_ci_upper")},
            {"name": "dcr_rate_experimental", "value": arm_exp.get("dcr_rate"), "unit": "proportion"},
            {"name": "dcr_rate_control", "value": arm_ctl.get("dcr_rate"), "unit": "proportion"},
            {"name": "dcr_n_experimental", "value": arm_exp.get("dcr_n")},
            {"name": "dcr_n_control", "value": arm_ctl.get("dcr_n")},
            {"name": "orr_difference", "value": s.get("orr_difference"), "unit": "proportion"},
            {"name": "orr_diff_ci_lower", "value": s.get("orr_diff_ci_lower")},
            {"name": "orr_diff_ci_upper", "value": s.get("orr_diff_ci_upper")},
            {"name": "fisher_exact_p", "value": s.get("fisher_exact_p")},
            {"name": "chi_square_p", "value": s.get("chi_square_p")},
            {"name": "n_total_experimental", "value": arm_exp.get("n_total")},
            {"name": "n_total_control", "value": arm_ctl.get("n_total")},
            {"name": "n_evaluable_experimental", "value": arm_exp.get("n_evaluable")},
            {"name": "n_evaluable_control", "value": arm_ctl.get("n_evaluable")},
        ] + [
            {"name": f"n_{bor.lower()}_experimental", "value": v.get("n_experimental")}
            for bor, v in bor_dist.items()
        ] + [
            {"name": f"n_{bor.lower()}_control", "value": v.get("n_control")}
            for bor, v in bor_dist.items()
        ],
    )


def build_tc026(data: dict) -> dict:
    """TC-026: Progression-Free Survival 2 (PFS2)."""
    return _build_survival_tc(
        "TC-026",
        "Secondary efficacy: PFS2 (Progression-Free Survival 2) KM median, Cox HR, log-rank, subgroup forest",
        "PFS2",
        data,
        "median_pfs2",
    )


def build_tc027(data: dict) -> dict:
    """TC-027: Duration of Stable Disease (DOSD)."""
    return _build_survival_tc(
        "TC-027",
        "Efficacy: Duration of Stable Disease (DOSD) in ITT subjects with BOR=SD",
        "DOSD",
        data,
        "median_dosd",
    )


def build_tc029(data: dict) -> dict:
    """TC-029: AE severity summary table by SOC, PT, and severity grade."""
    pop = data.get("population", {})
    n_exp = pop.get("n_experimental", 0)
    n_ctl = pop.get("n_control", 0)
    summary = data.get("summary", [])
    sev_summary = data.get("severity_summary", [])
    ae_table = data.get("ae_table", [])

    # Extract SOC count
    socs = set()
    for row in ae_table:
        soc = row.get("soc")
        if soc:
            socs.add(soc)

    # Summary categories
    any_ae = next((s for s in summary if "Any adverse event" in s.get("category", "")), {})
    sae = next((s for s in summary if "Serious" in s.get("category", "")), {})
    disc = next((s for s in summary if "discontinuation" in s.get("category", "")), {})

    # Grade 3+ severity
    g3 = next((g for g in sev_summary if g.get("grade") == 3), {})
    g4 = next((g for g in sev_summary if g.get("grade") == 4), {})
    g5 = next((g for g in sev_summary if g.get("grade") == 5), {})

    return make_ars(
        tc_id="TC-029",
        reason="Safety: adverse event summary by SOC, preferred term, and maximum severity grade",
        method_name="Frequency tabulation by SOC → PT → severity",
        code_template="aggregate(AEDECOD ~ AESOC + AETOXGR + TRT01A, data=ADAE)",
        parameters={
            "severity_grades": data.get("severity_grades", [1, 2, 3, 4, 5]),
            "hierarchy": "SOC → PT → severity grade",
        },
        variables=[
            {"name": "AESOC", "dataset": "ADAE", "role": "System Organ Class"},
            {"name": "AEDECOD", "dataset": "ADAE", "role": "Preferred Term"},
            {"name": "AETOXGR", "dataset": "ADAE", "role": "severity grade"},
            {"name": "TRT01A", "dataset": "ADSL", "role": "treatment"},
            {"name": "SAFFL", "dataset": "ADSL", "role": "safety flag"},
        ],
        population={"name": "Safety", "filter": "SAFFL = 'Y'"},
        dataset="ADAE",
        result_groups=[
            {"id": "Experimental", "n": n_exp},
            {"id": "Control", "n": n_ctl},
        ],
        documentation=f"AE severity summary: {len(socs)} SOCs, {len(ae_table)} table rows (SOC/PT × severity). {_ITT_DOC}",
        statistics=[
            {"name": "n_experimental", "value": n_exp},
            {"name": "n_control", "value": n_ctl},
            {"name": "n_socs", "value": len(socs)},
            {"name": "n_table_rows", "value": len(ae_table)},
            {"name": "n_any_ae_experimental", "value": any_ae.get("n_experimental")},
            {"name": "n_any_ae_control", "value": any_ae.get("n_control")},
            {"name": "n_sae_experimental", "value": sae.get("n_experimental")},
            {"name": "n_sae_control", "value": sae.get("n_control")},
            {"name": "n_ae_disc_experimental", "value": disc.get("n_experimental")},
            {"name": "n_ae_disc_control", "value": disc.get("n_control")},
            {"name": "n_grade3_experimental", "value": g3.get("n_experimental")},
            {"name": "n_grade3_control", "value": g3.get("n_control")},
            {"name": "n_grade4_experimental", "value": g4.get("n_experimental")},
            {"name": "n_grade4_control", "value": g4.get("n_control")},
            {"name": "n_grade5_experimental", "value": g5.get("n_experimental")},
            {"name": "n_grade5_control", "value": g5.get("n_control")},
        ],
    )


def build_tc030(data: dict) -> dict:
    """TC-030: ORR with subgroup interaction testing."""
    o = data.get("overall", {})
    n_exp = o.get("n_experimental", 0)
    n_ctl = o.get("n_control", 0)
    interactions = data.get("interaction_tests", [])

    return make_ars(
        tc_id="TC-030",
        reason="Efficacy: ORR by subgroup with interaction testing (logistic Wald, Breslow-Day)",
        method_name="Binomial proportion + logistic interaction + Breslow-Day",
        code_template="glm(BOR_RESP ~ TRT01A * SUBGROUP, family=binomial)",
        parameters={
            "ci_method": data.get("ci_method", "clopper-pearson"),
            "subgroups": [i.get("subgroup") for i in interactions],
            "interaction_method": "logistic_wald",
        },
        variables=[
            {"name": "BOR", "dataset": "ADRS", "role": "best overall response"},
            {"name": "TRT01A", "dataset": "ADSL", "role": "treatment"},
            {"name": "ITTFL", "dataset": "ADSL", "role": "ITT flag"},
            {"name": "SEX", "dataset": "ADSL", "role": "subgroup: sex"},
            {"name": "AGEGR1", "dataset": "ADSL", "role": "subgroup: age group"},
            {"name": "ECOG", "dataset": "ADSL", "role": "subgroup: ECOG"},
        ],
        population={"name": "ITT", "filter": "ITTFL = 'Y'"},
        dataset="ADRS",
        result_groups=[
            {"id": "Experimental", "n": n_exp},
            {"id": "Control", "n": n_ctl},
        ],
        documentation=f"ORR by subgroup (SEX, AGEGR1, ECOG) with Clopper-Pearson CI, ORR difference CI, and logistic Wald + Breslow-Day interaction tests. {_ITT_DOC}",
        statistics=[
            {"name": "orr_experimental", "value": o.get("orr_experimental"), "unit": "%"},
            {"name": "orr_control", "value": o.get("orr_control"), "unit": "%"},
            {"name": "orr_difference", "value": o.get("orr_difference"), "unit": "%"},
            {"name": "responders_experimental", "value": o.get("responders_experimental")},
            {"name": "responders_control", "value": o.get("responders_control")},
            {"name": "n_experimental", "value": n_exp},
            {"name": "n_control", "value": n_ctl},
            {"name": "ci_lower_experimental", "value": o.get("ci_lower_experimental"), "unit": "%"},
            {"name": "ci_upper_experimental", "value": o.get("ci_upper_experimental"), "unit": "%"},
            {"name": "ci_lower_control", "value": o.get("ci_lower_control"), "unit": "%"},
            {"name": "ci_upper_control", "value": o.get("ci_upper_control"), "unit": "%"},
        ] + [
            {"name": f"interaction_p_{iv.get('subgroup', f'sg{i}')}", "value": iv.get("interaction_p_value")}
            for i, iv in enumerate(interactions)
        ] + [
            {"name": f"interaction_or_{iv.get('subgroup', f'sg{i}')}", "value": iv.get("interaction_or")}
            for i, iv in enumerate(interactions)
        ] + [
            {"name": f"breslow_day_p_{iv.get('subgroup', f'sg{i}')}", "value": iv.get("breslow_day_p_value")}
            for i, iv in enumerate(interactions)
        ],
    )


def build_tc032(data: dict) -> dict:
    """TC-032: Immune-related AE (irAE) summary."""
    pop = data.get("population", {})
    n_exp = pop.get("n_experimental", 0)
    n_ctl = pop.get("n_control", 0)
    summary = data.get("summary", [])
    sev_summary = data.get("severity_summary", [])
    irae_table = data.get("irae_table", [])

    any_irae = next((s for s in summary if "Any immune-related" in s.get("category", "")), {})
    g3_irae = next((s for s in summary if "Grade" in s.get("category", "") and "3" in s.get("category", "")), {})
    disc_irae = next((s for s in summary if "discontinuation" in s.get("category", "")), {})
    steroids = next((s for s in summary if "corticosteroids" in s.get("category", "")), {})

    # irAE categories
    irae_cats = set()
    for row in irae_table:
        cat = row.get("irae_category")
        if cat:
            irae_cats.add(cat)

    # Grade 3+ severity
    g3 = next((g for g in sev_summary if g.get("grade") == 3), {})
    g4 = next((g for g in sev_summary if g.get("grade") == 4), {})
    g5 = next((g for g in sev_summary if g.get("grade") == 5), {})

    return make_ars(
        tc_id="TC-032",
        reason="Safety: immune-related adverse event (irAE) summary by category, PT, and severity",
        method_name="Frequency tabulation by irAE category → PT → severity",
        code_template="aggregate(AEDECOD ~ IRAE_CATEGORY + AETOXGR + TRT01A, data=ADAE)",
        parameters={
            "severity_grades": data.get("severity_grades", [1, 2, 3, 4, 5]),
            "hierarchy": "irAE category → PT → severity grade",
        },
        variables=[
            {"name": "AEDECOD", "dataset": "ADAE", "role": "Preferred Term"},
            {"name": "AETOXGR", "dataset": "ADAE", "role": "severity grade"},
            {"name": "TRT01A", "dataset": "ADSL", "role": "treatment"},
            {"name": "SAFFL", "dataset": "ADSL", "role": "safety flag"},
        ],
        population={"name": "Safety", "filter": "SAFFL = 'Y'"},
        dataset="ADAE",
        result_groups=[
            {"id": "Experimental", "n": n_exp},
            {"id": "Control", "n": n_ctl},
        ],
        documentation=f"irAE summary: {len(irae_cats)} irAE categories, {len(irae_table)} table rows. {_ITT_DOC}",
        statistics=[
            {"name": "n_experimental", "value": n_exp},
            {"name": "n_control", "value": n_ctl},
            {"name": "n_irae_categories", "value": len(irae_cats)},
            {"name": "n_table_rows", "value": len(irae_table)},
            {"name": "n_any_irae_experimental", "value": any_irae.get("n_experimental")},
            {"name": "n_any_irae_control", "value": any_irae.get("n_control")},
            {"name": "pct_any_irae_experimental", "value": any_irae.get("pct_experimental"), "unit": "%"},
            {"name": "pct_any_irae_control", "value": any_irae.get("pct_control"), "unit": "%"},
            {"name": "n_g3_irae_experimental", "value": g3_irae.get("n_experimental")},
            {"name": "n_g3_irae_control", "value": g3_irae.get("n_control")},
            {"name": "n_irae_disc_experimental", "value": disc_irae.get("n_experimental")},
            {"name": "n_irae_disc_control", "value": disc_irae.get("n_control")},
            {"name": "n_irae_steroids_experimental", "value": steroids.get("n_experimental")},
            {"name": "n_irae_steroids_control", "value": steroids.get("n_control")},
            {"name": "n_grade3_experimental", "value": g3.get("n_experimental")},
            {"name": "n_grade3_control", "value": g3.get("n_control")},
            {"name": "n_grade4_experimental", "value": g4.get("n_experimental")},
            {"name": "n_grade4_control", "value": g4.get("n_control")},
            {"name": "n_grade5_experimental", "value": g5.get("n_experimental")},
            {"name": "n_grade5_control", "value": g5.get("n_control")},
        ],
    )


def build_tc033(data: dict) -> dict:
    """TC-033: Dose intensity summary."""
    meta = data.get("metadata", {})
    n_exp = meta.get("n_experimental", 0)
    n_ctl = meta.get("n_control", 0)
    rdi = data.get("rdi_summary", {})
    rdi_exp = rdi.get("experimental", {})
    rdi_ctl = rdi.get("control", {})
    rdi_ge80 = data.get("rdi_ge80", {})
    rdi_ge80_exp = rdi_ge80.get("experimental", {})
    rdi_ge80_ctl = rdi_ge80.get("control", {})
    dose_red = data.get("dose_reduction", {})
    dose_red_exp = dose_red.get("experimental", {})
    dose_red_ctl = dose_red.get("control", {})
    dose_int = data.get("dose_interruption", {})
    dose_int_exp = dose_int.get("experimental", {})
    dose_int_ctl = dose_int.get("control", {})
    td = data.get("treatment_duration", {})
    td_exp = td.get("experimental", {})
    td_ctl = td.get("control", {})

    return make_ars(
        tc_id="TC-033",
        reason="Safety: dose intensity summary (RDI, dose reductions, interruptions, treatment duration)",
        method_name="Descriptive statistics for relative dose intensity",
        code_template="summary(RDI ~ TRT01A); table(DOSERED, TRT01A)",
        parameters={
            "rdi_threshold": meta.get("rdi_threshold", 80),
            "duration_unit": meta.get("duration_unit", "weeks"),
            "dose_unit": meta.get("dose_unit", "mg"),
        },
        variables=[
            {"name": "RDI", "dataset": "ADEX", "role": "relative dose intensity (%)"},
            {"name": "CUMDOSE", "dataset": "ADEX", "role": "cumulative dose"},
            {"name": "TREATDUR", "dataset": "ADEX", "role": "treatment duration"},
            {"name": "DOSERED", "dataset": "ADEX", "role": "dose reduction flag"},
            {"name": "DOSEINT", "dataset": "ADEX", "role": "dose interruption flag"},
            {"name": "TRT01A", "dataset": "ADSL", "role": "treatment"},
            {"name": "SAFFL", "dataset": "ADSL", "role": "safety flag"},
        ],
        population={"name": "Safety", "filter": "SAFFL = 'Y'"},
        dataset="ADEX",
        result_groups=[
            {"id": "Experimental", "n": n_exp},
            {"id": "Control", "n": n_ctl},
        ],
        documentation=f"Dose intensity: RDI mean/SD/median, RDI ≥80% count, dose reductions/interruptions, treatment duration. {_ITT_DOC}",
        statistics=[
            {"name": "mean_rdi_experimental", "value": rdi_exp.get("mean"), "unit": "%"},
            {"name": "mean_rdi_control", "value": rdi_ctl.get("mean"), "unit": "%"},
            {"name": "median_rdi_experimental", "value": rdi_exp.get("median"), "unit": "%"},
            {"name": "median_rdi_control", "value": rdi_ctl.get("median"), "unit": "%"},
            {"name": "sd_rdi_experimental", "value": rdi_exp.get("sd"), "unit": "%"},
            {"name": "sd_rdi_control", "value": rdi_ctl.get("sd"), "unit": "%"},
            {"name": "min_rdi_experimental", "value": rdi_exp.get("min"), "unit": "%"},
            {"name": "min_rdi_control", "value": rdi_ctl.get("min"), "unit": "%"},
            {"name": "max_rdi_experimental", "value": rdi_exp.get("max"), "unit": "%"},
            {"name": "max_rdi_control", "value": rdi_ctl.get("max"), "unit": "%"},
            {"name": "n_rdi_ge80_experimental", "value": rdi_ge80_exp.get("n")},
            {"name": "n_rdi_ge80_control", "value": rdi_ge80_ctl.get("n")},
            {"name": "pct_rdi_ge80_experimental", "value": rdi_ge80_exp.get("pct"), "unit": "%"},
            {"name": "pct_rdi_ge80_control", "value": rdi_ge80_ctl.get("pct"), "unit": "%"},
            {"name": "n_dose_reduction_experimental", "value": dose_red_exp.get("n")},
            {"name": "n_dose_reduction_control", "value": dose_red_ctl.get("n")},
            {"name": "n_dose_interruption_experimental", "value": dose_int_exp.get("n")},
            {"name": "n_dose_interruption_control", "value": dose_int_ctl.get("n")},
            {"name": "mean_duration_experimental", "value": td_exp.get("mean"), "unit": "weeks"},
            {"name": "mean_duration_control", "value": td_ctl.get("mean"), "unit": "weeks"},
            {"name": "median_duration_experimental", "value": td_exp.get("median"), "unit": "weeks"},
            {"name": "median_duration_control", "value": td_ctl.get("median"), "unit": "weeks"},
        ],
    )


def build_tc034(data: dict) -> dict:
    """TC-034: Sufficient follow-up assessment."""
    meta = data.get("metadata", {})
    n_exp = meta.get("n_experimental", 0)
    n_ctl = meta.get("n_control", 0)
    adequate = data.get("adequate_followup", {})
    adeq_exp = adequate.get("experimental", {})
    adeq_ctl = adequate.get("control", {})
    status = data.get("status_distribution", {})
    status_exp = status.get("experimental", {})
    status_ctl = status.get("control", {})
    rkm = data.get("reverse_km_followup", {})
    rkm_exp = rkm.get("experimental", {})
    rkm_ctl = rkm.get("control", {})
    fu_post = data.get("fu_post_dose", {})
    fu_post_exp = fu_post.get("experimental", {})
    fu_post_ctl = fu_post.get("control", {})
    fu_rand = data.get("fu_from_randomization", {})
    fu_rand_exp = fu_rand.get("experimental", {})
    fu_rand_ctl = fu_rand.get("control", {})

    return make_ars(
        tc_id="TC-034",
        reason="Data quality: sufficient follow-up assessment (adequate follow-up, reverse KM, follow-up duration)",
        method_name="Descriptive statistics + reverse Kaplan-Meier",
        code_template="summary(FU_POST_DOSE ~ TRT01A); survfit(Surv(FU_POST_DOSE, 1) ~ 1, type='reverse')",
        parameters={
            "followup_threshold_days": meta.get("followup_threshold_days", 90),
            "date_unit": meta.get("date_unit", "days"),
        },
        variables=[
            {"name": "FU_POST_DOSE", "dataset": "ADSL", "role": "follow-up post last dose (days)"},
            {"name": "FU_FROM_RAND", "dataset": "ADSL", "role": "follow-up from randomization (days)"},
            {"name": "ADEQUATE_FU", "dataset": "ADSL", "role": "adequate follow-up flag"},
            {"name": "STATUS", "dataset": "ADSL", "role": "patient status (ongoing/completed/discontinued/died)"},
            {"name": "TRT01A", "dataset": "ADSL", "role": "treatment"},
            {"name": "SAFFL", "dataset": "ADSL", "role": "safety flag"},
        ],
        population={"name": "Safety", "filter": "SAFFL = 'Y'"},
        dataset="ADSL",
        result_groups=[
            {"id": "Experimental", "n": n_exp},
            {"id": "Control", "n": n_ctl},
        ],
        documentation=f"Sufficient follow-up: adequate follow-up rate (≥{meta.get('followup_threshold_days', 90)} days), reverse KM median follow-up, status distribution. {_ITT_DOC}",
        statistics=[
            {"name": "n_adequate_followup_experimental", "value": adeq_exp.get("n")},
            {"name": "n_adequate_followup_control", "value": adeq_ctl.get("n")},
            {"name": "pct_adequate_followup_experimental", "value": adeq_exp.get("pct"), "unit": "%"},
            {"name": "pct_adequate_followup_control", "value": adeq_ctl.get("pct"), "unit": "%"},
            {"name": "n_ongoing_experimental", "value": status_exp.get("ongoing")},
            {"name": "n_ongoing_control", "value": status_ctl.get("ongoing")},
            {"name": "n_completed_experimental", "value": status_exp.get("completed")},
            {"name": "n_completed_control", "value": status_ctl.get("completed")},
            {"name": "n_discontinued_experimental", "value": status_exp.get("discontinued")},
            {"name": "n_discontinued_control", "value": status_ctl.get("discontinued")},
            {"name": "n_died_experimental", "value": status_exp.get("died")},
            {"name": "n_died_control", "value": status_ctl.get("died")},
            {"name": "median_reverse_km_followup_experimental", "value": rkm_exp.get("median"), "unit": "days"},
            {"name": "median_reverse_km_followup_control", "value": rkm_ctl.get("median"), "unit": "days"},
            {"name": "reverse_km_ci_lower_experimental", "value": rkm_exp.get("ci_lower"), "unit": "days"},
            {"name": "reverse_km_ci_upper_experimental", "value": rkm_exp.get("ci_upper"), "unit": "days"},
            {"name": "reverse_km_ci_lower_control", "value": rkm_ctl.get("ci_lower"), "unit": "days"},
            {"name": "reverse_km_ci_upper_control", "value": rkm_ctl.get("ci_upper"), "unit": "days"},
            {"name": "mean_fu_post_dose_experimental", "value": fu_post_exp.get("mean"), "unit": "days"},
            {"name": "mean_fu_post_dose_control", "value": fu_post_ctl.get("mean"), "unit": "days"},
            {"name": "median_fu_post_dose_experimental", "value": fu_post_exp.get("median"), "unit": "days"},
            {"name": "median_fu_post_dose_control", "value": fu_post_ctl.get("median"), "unit": "days"},
            {"name": "mean_fu_from_rand_experimental", "value": fu_rand_exp.get("mean"), "unit": "days"},
            {"name": "mean_fu_from_rand_control", "value": fu_rand_ctl.get("mean"), "unit": "days"},
            {"name": "median_fu_from_rand_experimental", "value": fu_rand_exp.get("median"), "unit": "days"},
            {"name": "median_fu_from_rand_control", "value": fu_rand_ctl.get("median"), "unit": "days"},
        ],
    )


# ─────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────

TC_BUILDERS = {
    "TC-001": build_tc001,
    "TC-002": build_tc002,
    "TC-019": build_tc019,
    "TC-023": build_tc023,
    "TC-024": build_tc024,
    "TC-025": build_tc025,
    "TC-026": build_tc026,
    "TC-027": build_tc027,
    "TC-029": build_tc029,
    "TC-030": build_tc030,
    "TC-032": build_tc032,
    "TC-033": build_tc033,
    "TC-034": build_tc034,
}


def main():
    ARS_DIR.mkdir(parents=True, exist_ok=True)

    print("╔" + "═" * 78 + "╗")
    print("║  ARS Envelope Generation — 13 Remaining Level 1 Test Cases            ║")
    print("╚" + "═" * 78 + "╝")
    print()

    results = []

    for tc_id, builder in sorted(TC_BUILDERS.items()):
        r_file = R_DIR / f"{tc_id}.json"
        py_file = PY_DIR / f"{tc_id}.json"

        if not r_file.exists():
            print(f"⚠  {tc_id}: R output not found at {r_file}")
            results.append((tc_id, "R_MISSING", 0, 0))
            continue
        if not py_file.exists():
            print(f"⚠  {tc_id}: Python output not found at {py_file}")
            results.append((tc_id, "PY_MISSING", 0, 0))
            continue

        with open(r_file) as f:
            r_data = json.load(f)
        with open(py_file) as f:
            py_data = json.load(f)

        # Build ARS envelopes
        r_ars = builder(r_data)
        py_ars = builder(py_data)

        # Override language-specific metadata
        r_ars["analysisResult"]["analysisMethod"]["parameters"]["language"] = "R"
        py_ars["analysisResult"]["analysisMethod"]["parameters"]["language"] = "Python"

        # Write ARS files
        r_ars_path = ARS_DIR / f"{tc_id}_R_ars.json"
        py_ars_path = ARS_DIR / f"{tc_id}_Py_ars.json"

        with open(r_ars_path, "w") as f:
            json.dump(r_ars, f, indent=2)
        with open(py_ars_path, "w") as f:
            json.dump(py_ars, f, indent=2)

        n_stats = len(r_ars["analysisResult"]["analysisResultsData"]["statistics"])
        n_vars = len(r_ars["analysisResult"]["analysisVariables"])
        print(f"✅ {tc_id}: ARS envelopes written ({n_stats} stats, {n_vars} vars)")
        results.append((tc_id, "OK", n_stats, n_vars))

    # Summary
    print()
    print("─" * 80)
    ok_count = sum(1 for r in results if r[1] == "OK")
    total_stats = sum(r[2] for r in results)
    total_vars = sum(r[3] for r in results)
    print(f"✅ {ok_count}/{len(TC_BUILDERS)} TCs: ARS envelopes generated")
    print(f"   Total statistics wrapped: {total_stats}")
    print(f"   Total variables documented: {total_vars}")
    print(f"   Output directory: {ARS_DIR}")

    # List all ARS files
    print()
    print("All ARS output files now in directory:")
    all_ars = sorted(ARS_DIR.glob("*_ars.json"))
    for f in all_ars:
        print(f"  {f.name}")
    print(f"Total: {len(all_ars)} ARS envelope files")


if __name__ == "__main__":
    main()
