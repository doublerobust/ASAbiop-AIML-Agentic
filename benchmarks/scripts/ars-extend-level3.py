#!/usr/bin/env python3
"""
ARS Envelope Generator for Level 3 Test Cases (TC-007, TC-008, TC-009, TC-010)

Reads existing benchmark JSON outputs from cross-lang-results/r-output/ and
cross-lang-results/python-output/, wraps them in CDISC ARS v1.0 envelopes,
and writes to cross-lang-results/ars-output/.

This extends ARS coverage from 21 TCs (Level 1 + Level 2) to all 4 Level 3 TCs,
completing ARS coverage across the full 35-TC test case library (25 TCs with ARS
envelopes).

The 4 Level 3 TCs covered here:
  - TC-007: Regulatory Response to ITT vs. PP Discrepancy
  - TC-008: End-to-End Dose-Finding Study Design with BOIN
  - TC-009: Safety Signal Evaluation and DMC Report
  - TC-010: CSR Statistical Sections (ICH E3)

Note: TC-007/008 result JSONs use lowercase filenames (tc-007-results.json);
TC-009/010 use uppercase (TC-009.json). Both conventions are handled here.
"""

import json
from pathlib import Path
from typing import Any

BENCH_DIR = Path(__file__).parent.parent
R_DIR = BENCH_DIR / "cross-lang-results" / "r-output"
PY_DIR = BENCH_DIR / "cross-lang-results" / "python-output"
ARS_DIR = BENCH_DIR / "cross-lang-results" / "ars-output"


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

def build_tc007(data: dict) -> dict:
    """TC-007: Regulatory Response to ITT vs. PP Discrepancy.

    Scenario: Phase III oncology superiority trial where ITT is significant but
    a per-protocol (PP) analysis is not. The agent must analyze the discrepancy
    (differential exclusion pattern), perform tipping-point and sensitivity
    analyses, and draft a regulatory response memo. ITT remains the sole primary
    analysis population per FDA/EMA standards; PP is computed here only as a
    supportive/sensitivity analysis to respond to a regulatory reviewer query.
    """
    analysis = data.get("analysis", {})
    itt = analysis.get("itt", {})
    pp = analysis.get("pp", {})
    disc = analysis.get("discrepancy", {})
    excl = analysis.get("exclusion_pattern", {})
    tip = analysis.get("tipping_point", {})
    sens = analysis.get("sensitivity_analyses", {})
    worst = sens.get("worst_case", {})
    best = sens.get("best_case", {})

    return make_ars(
        tc_id="TC-007",
        reason="Regulatory response: analyze ITT vs per-protocol discrepancy, "
               "tipping point, and sensitivity analyses",
        method_name="Cox PH (Efron ties) + log-rank + tipping-point analysis",
        code_template="coxph(Surv(AVAL, 1-CNSR) ~ TRT01PN, data=ADTTE); survdiff(...)",
        parameters={
            "ties": "Efron",
            "itt_primary": True,
            "pp_role": "supportive sensitivity (regulatory query response)",
            "tipping_point_method": "reclassify censored↔event in excluded Active subjects",
        },
        variables=[
            {"name": "AVAL", "dataset": "ADTTE", "role": "analysis time (PFS)"},
            {"name": "CNSR", "dataset": "ADTTE", "role": "censoring (0=event)"},
            {"name": "TRT01PN", "dataset": "ADSL", "role": "treatment (numeric)"},
            {"name": "ITTFL", "dataset": "ADSL", "role": "ITT flag"},
            {"name": "PPFL", "dataset": "ADSL", "role": "per-protocol flag (supportive)"},
        ],
        population={
            "name": "ITT (primary) + PP (supportive)",
            "filter": "ITTFL = 'Y' (primary); PPFL = 'Y' (supportive sensitivity)",
        },
        dataset="ADTTE",
        result_groups=[
            {"id": "ITT", "n": itt.get("n")},
            {"id": "PP", "n": pp.get("n")},
        ],
        documentation="Level 3 regulatory response scenario. ITT is the sole "
                       "primary analysis population for the superiority claim "
                       "(FDA/EMA standard). PP, tipping-point, and worst/best-case "
                       "analyses are supportive sensitivity analyses performed to "
                       "respond to a regulatory reviewer's query about the ITT/PP "
                       "discrepancy. Differential exclusion (Active excludes "
                       "censored/well subjects; Placebo excludes event/ill "
                       "subjects) drives the discrepancy.",
        statistics=[
            {"name": "itt_n", "value": itt.get("n")},
            {"name": "itt_hr", "value": itt.get("hr")},
            {"name": "itt_hr_ci_lower", "value": itt.get("hr_ci_lower")},
            {"name": "itt_hr_ci_upper", "value": itt.get("hr_ci_upper")},
            {"name": "itt_logrank_p", "value": itt.get("logrank_p")},
            {"name": "itt_wald_p", "value": itt.get("wald_p")},
            {"name": "itt_significant", "value": disc.get("itt_significant")},
            {"name": "pp_n", "value": pp.get("n")},
            {"name": "pp_hr", "value": pp.get("hr")},
            {"name": "pp_hr_ci_lower", "value": pp.get("hr_ci_lower")},
            {"name": "pp_hr_ci_upper", "value": pp.get("hr_ci_upper")},
            {"name": "pp_logrank_p", "value": pp.get("logrank_p")},
            {"name": "pp_significant", "value": disc.get("pp_significant")},
            {"name": "hr_difference", "value": disc.get("hr_difference")},
            {"name": "n_excluded", "value": excl.get("n_excluded")},
            {"name": "excluded_active", "value": excl.get("excluded_active")},
            {"name": "excluded_placebo", "value": excl.get("excluded_placebo")},
            {"name": "excl_events_active", "value": excl.get("excl_events_active")},
            {"name": "excl_events_placebo", "value": excl.get("excl_events_placebo")},
            {"name": "event_imbalance_fisher_p", "value": excl.get("event_imbalance_fisher_p")},
            {"name": "tipping_n_shifted", "value": tip.get("n_shifted")},
            {"name": "tipping_hr", "value": tip.get("hr_at_tipping")},
            {"name": "tipping_p", "value": tip.get("p_at_tipping")},
            {"name": "worst_case_hr", "value": worst.get("hr")},
            {"name": "worst_case_p", "value": worst.get("p_value")},
            {"name": "best_case_hr", "value": best.get("hr")},
            {"name": "best_case_p", "value": best.get("p_value")},
        ],
    )


def build_tc008(data: dict) -> dict:
    """TC-008: End-to-End Dose-Finding Study Design with BOIN.

    Phase I dose-finding design. ITT/PP distinction does not apply — all treated
    patients are the analysis set. The agent selects BOIN as the dose-escalation
    method, defines dose levels, specifies stopping rules, designs an expansion
    cohort at RP2D, and simulates operating characteristics over 2,000 trials.
    """
    design = data.get("design", {})
    sim = data.get("simulation", {})
    oc = sim.get("operating_characteristics", {})
    expansion = data.get("expansion_cohort", {})
    true_rates = design.get("true_dlt_rates", [])
    prob_select = oc.get("prob_select_rpd", [])

    return make_ars(
        tc_id="TC-008",
        reason="Phase I dose-finding study design with BOIN and simulation "
               "operating characteristics",
        method_name="BOIN (Bayesian Optimal Interval) + Monte Carlo simulation",
        code_template="boin(dlt_data, dose_levels, target=0.30, cohort=3, max_n=30)",
        parameters={
            "target_dlt_rate": design.get("target_dlt_rate"),
            "n_doses": design.get("n_doses"),
            "cohort_size": design.get("cohort_size"),
            "max_n": design.get("max_n"),
            "escalation_boundary": design.get("escalation_boundary"),
            "deescalation_boundary": design.get("deescalation_boundary"),
            "n_sim": sim.get("n_sim"),
            "seed": sim.get("seed"),
            "expansion_cohort_size": design.get("expansion_cohort_size"),
        },
        variables=[
            {"name": "DLT", "dataset": "ADXD", "role": "dose-limiting toxicity (0/1)"},
            {"name": "DOSE", "dataset": "ADSL", "role": "dose level assigned"},
            {"name": "USUBJID", "dataset": "ADSL", "role": "subject identifier"},
        ],
        population={
            "name": "All treated patients (Phase I)",
            "filter": "SAFFL = 'Y' (all who received any study drug)",
        },
        dataset="ADXD",
        # Dose levels are the result groups. This is a *design* test case — no
        # actual patient allocation exists yet. Per-dose sample sizes are
        # stochastic (BOIN allocates adaptively); we set n=0 to indicate the
        # design stage. Expected total N (29.74) and selection probabilities
        # are captured in the statistics block.
        result_groups=[
            {"id": f"Dose_{i+1}", "n": 0} for i in range(design.get("n_doses", 5))
        ],
        documentation="Level 3 Phase I dose-finding design. ITT/PP distinction "
                       "does not apply — all treated patients form the analysis set. "
                       f"BOIN identifies Dose {expansion.get('rpd')} "
                       f"({expansion.get('rpd_dose')} mg) as RP2D with "
                       f"{prob_select[expansion.get('rpd',3)-1] if prob_select and len(prob_select) >= expansion.get('rpd',3) else None} "
                       "selection probability. True DLT rates: "
                       f"{true_rates}. Dose {expansion.get('rpd')} (true rate "
                       f"{true_rates[expansion.get('rpd',3)-1] if true_rates and len(true_rates) >= expansion.get('rpd',3) else None}) "
                       "is the true MTD (closest to target 0.30).",
        statistics=[
            {"name": "target_dlt_rate", "value": design.get("target_dlt_rate")},
            {"name": "n_doses", "value": design.get("n_doses")},
            {"name": "cohort_size", "value": design.get("cohort_size")},
            {"name": "max_n", "value": design.get("max_n")},
            {"name": "escalation_boundary", "value": design.get("escalation_boundary")},
            {"name": "deescalation_boundary", "value": design.get("deescalation_boundary")},
            {"name": "n_sim", "value": sim.get("n_sim")},
            {"name": "prob_select_dose1", "value": prob_select[0] if len(prob_select) > 0 else None},
            {"name": "prob_select_dose2", "value": prob_select[1] if len(prob_select) > 1 else None},
            {"name": "prob_select_dose3_mtd", "value": prob_select[2] if len(prob_select) > 2 else None},
            {"name": "prob_select_dose4", "value": prob_select[3] if len(prob_select) > 3 else None},
            {"name": "prob_select_dose5", "value": prob_select[4] if len(prob_select) > 4 else None},
            {"name": "prob_no_safe_dose", "value": oc.get("prob_no_safe_dose")},
            {"name": "expected_n_dlts", "value": oc.get("expected_n_dlts")},
            {"name": "expected_sample_size", "value": oc.get("expected_sample_size")},
            {"name": "prob_early_stop", "value": oc.get("prob_early_stop")},
            {"name": "rpd_dose_level", "value": expansion.get("rpd")},
            {"name": "rpd_dose_mg", "value": expansion.get("rpd_dose"), "unit": "mg"},
            {"name": "expansion_cohort_size", "value": expansion.get("n_expansion")},
            {"name": "expected_dlt_rate_at_rpd", "value": expansion.get("expected_dlt_rate_at_rpd")},
        ],
    )


def build_tc009(data: dict) -> dict:
    """TC-009: Safety Signal Evaluation and DMC Report.

    8-domain safety analysis for an Independent Data Monitoring Committee (DMC)
    report. Phase III oncology — safety analysis set is all randomized subjects
    who received any study treatment (SAFFL=Y). No per-protocol analysis;
    ITT is sole primary population per FDA/EMA standards.
    """
    sd = data.get("study_design", {})
    overview = data.get("ae_overview", {})
    by_arm = overview.get("by_arm", {})
    active_ov = by_arm.get("Active", {})
    placebo_ov = by_arm.get("Placebo", {})
    g3 = data.get("grade3_plus", {})
    g3_by = g3.get("by_arm", {})
    hys = data.get("lab_abnormalities", {}).get("hys_law", {})
    qtc = data.get("lab_abnormalities", {}).get("qtc_prolongation", {})
    irae = data.get("ae_special_interest", {}).get("irae", {})
    ttg3 = data.get("time_to_grade3", {})
    rec = data.get("recommendation", {})
    sig = rec.get("signals_summary", {})

    return make_ars(
        tc_id="TC-009",
        reason="Safety signal evaluation and DMC report — 8-domain safety analysis "
               "with totality-of-evidence recommendation",
        method_name="AE frequency + exposure-adjusted rates + KM/Cox PH + "
                    "MGPS disproportionality + Fisher exact",
        code_template="survfit(Surv(TTG3, 1-CNSR) ~ TRT01A); coxph(...); "
                      "fisher.test(matrix); mgps(ADAE)",
        parameters={
            "n_domains": 8,
            "ae_hierarchy": "SOC → PT (MedDRA)",
            "km_ci_method": "Brookmeyer-Crowley (log-log transform)",
            "cox_ties": "Efron",
            "mgps_threshold": "EBGM >= 2.0 AND observed >= 3",
            "signal_definition": "risk difference 95% CI excludes 0 OR MGPS EBGM >= 2.0",
        },
        variables=[
            {"name": "AESOC", "dataset": "ADAE", "role": "System Organ Class"},
            {"name": "AEDECOD", "dataset": "ADAE", "role": "Preferred Term"},
            {"name": "AESER", "dataset": "ADAE", "role": "serious AE flag"},
            {"name": "AESEV", "dataset": "ADAE", "role": "severity (Grade 3+)"},
            {"name": "AVAL", "dataset": "ADTTE", "role": "time to first Grade 3+ AE"},
            {"name": "CNSR", "dataset": "ADTTE", "role": "censoring"},
            {"name": "TRT01A", "dataset": "ADSL", "role": "treatment"},
            {"name": "SAFFL", "dataset": "ADSL", "role": "safety flag"},
            {"name": "LBSTRESN", "dataset": "ADLB", "role": "lab result (Hy's Law / QTc)"},
        ],
        population={
            "name": "Safety (SAFFL=Y)",
            "filter": "SAFFL = 'Y' — all randomized who received any study treatment",
        },
        dataset="ADAE",
        result_groups=[
            {"id": "Active", "n": sd.get("n_per_arm", {}).get("Active")},
            {"id": "Placebo", "n": sd.get("n_per_arm", {}).get("Placebo")},
        ],
        documentation="Level 3 DMC safety report. 8 domains: (1) AE overview, "
                       "(2) exposure-adjusted AE rates, (3) Grade 3+ AEs, "
                       "(4) lab abnormalities (Hy's Law, QTc), (5) time-to-first "
                       "Grade 3+ AE (KM + Cox PH + log-rank), (6) irAE, "
                       "(7) MGPS disproportionality, (8) DMC recommendation. "
                       "Phase III oncology — ITT is sole primary population; "
                       "no per-protocol analysis per FDA/EMA standards.",
        statistics=[
            {"name": "n_total", "value": sd.get("n_subjects")},
            {"name": "n_active", "value": sd.get("n_per_arm", {}).get("Active")},
            {"name": "n_placebo", "value": sd.get("n_per_arm", {}).get("Placebo")},
            {"name": "any_ae_active", "value": active_ov.get("n_any_ae")},
            {"name": "any_ae_placebo", "value": placebo_ov.get("n_any_ae")},
            {"name": "sae_active", "value": active_ov.get("n_sae")},
            {"name": "sae_placebo", "value": placebo_ov.get("n_sae")},
            {"name": "disc_active", "value": active_ov.get("n_disc")},
            {"name": "disc_placebo", "value": placebo_ov.get("n_disc")},
            {"name": "died_active", "value": active_ov.get("n_died")},
            {"name": "died_placebo", "value": placebo_ov.get("n_died")},
            {"name": "g3_active", "value": g3_by.get("Active", {}).get("n")},
            {"name": "g3_placebo", "value": g3_by.get("Placebo", {}).get("n")},
            {"name": "g3_risk_difference", "value": g3.get("risk_difference")},
            {"name": "g3_fisher_p", "value": g3.get("fisher_p")},
            {"name": "hys_law_active", "value": hys.get("n_active")},
            {"name": "hys_law_placebo", "value": hys.get("n_placebo")},
            {"name": "hys_law_fisher_p", "value": hys.get("fisher_p")},
            {"name": "qtc_active", "value": qtc.get("n_active")},
            {"name": "qtc_placebo", "value": qtc.get("n_placebo")},
            {"name": "qtc_fisher_p", "value": qtc.get("fisher_p")},
            {"name": "irae_active", "value": irae.get("n_active")},
            {"name": "irae_placebo", "value": irae.get("n_placebo")},
            {"name": "irae_fisher_p", "value": irae.get("fisher_p")},
            {"name": "ttg3_median_active", "value": ttg3.get("median_active", {}).get("median"), "unit": "days"},
            {"name": "ttg3_median_placebo", "value": ttg3.get("median_placebo", {}).get("median"), "unit": "days"},
            {"name": "ttg3_cox_hr", "value": ttg3.get("cox_hr")},
            {"name": "ttg3_cox_ci_lower", "value": ttg3.get("cox_ci", {}).get("lower")},
            {"name": "ttg3_cox_ci_upper", "value": ttg3.get("cox_ci", {}).get("upper")},
            {"name": "ttg3_logrank_p", "value": ttg3.get("logrank_p")},
            {"name": "n_signals", "value": sig.get("n_signals")},
            {"name": "signal_hys_law", "value": sig.get("hys_law")},
            {"name": "signal_qtc", "value": sig.get("qtc")},
            {"name": "signal_irae", "value": sig.get("irae")},
            {"name": "signal_grade3_plus", "value": sig.get("grade3_plus")},
            {"name": "recommendation", "value": rec.get("overall")},
        ],
    )


def build_tc010(data: dict) -> dict:
    """TC-010: CSR Statistical Sections (ICH E3).

    ICH E3-compliant CSR Sections 9 (Statistical Methods) and 11 (Statistical
    Results). Phase III oncology superiority trial — ITT is the sole primary
    analysis population. No per-protocol analysis per FDA/EMA standards.
    """
    sd = data.get("study_design", {})
    disp = data.get("section_11_1_disposition", {})
    demo = data.get("section_11_2_demographics", {})
    eff = data.get("section_11_4_efficacy", {})
    pfs = eff.get("primary_pfs", {})
    osr = eff.get("secondary_os", {})
    orr = eff.get("secondary_orr_dcr", {})
    safety = data.get("section_11_5_safety", {})
    sby = safety.get("by_arm", {})

    return make_ars(
        tc_id="TC-010",
        reason="ICH E3 CSR statistical sections — disposition, demographics, "
               "primary/secondary efficacy, subgroup forest, sensitivity, safety",
        method_name="KM + Cox PH (Efron) + log-rank + RECIST 1.1 + descriptive stats",
        code_template="survfit(Surv(AVAL, 1-CNSR) ~ TRT01A); coxph(...); "
                      "prop.test(x, n); t.test(AGE ~ TRT01A)",
        parameters={
            "csr_standard": "ICH E3",
            "primary_endpoint": sd.get("primary_endpoint"),
            "secondary_endpoints": sd.get("secondary_endpoints"),
            "km_ci_method": "Brookmeyer-Crowley (log-log transform)",
            "cox_ties": "Efron",
            "response_criteria": "RECIST 1.1",
            "itt_primary": True,
            "pp_analysis": "not performed (FDA/EMA oncology standard)",
        },
        variables=[
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
        population={
            "name": "ITT (primary) + Safety (secondary)",
            "filter": "ITTFL = 'Y' (primary efficacy); SAFFL = 'Y' (safety)",
        },
        dataset="ADTTE/ADRS/ADAE",
        result_groups=[
            {"id": "Active", "n": sd.get("n_subjects", 400) // 2 if sd.get("n_subjects") else None},
            {"id": "Placebo", "n": sd.get("n_subjects", 400) // 2 if sd.get("n_subjects") else None},
        ],
        documentation="Level 3 ICH E3 CSR statistical sections. Phase III "
                       "oncology superiority trial — ITT is the sole primary "
                       "analysis population; no per-protocol analysis performed "
                       "per FDA/EMA standards. Covers Section 9 (methods) and "
                       "Section 11 (disposition, demographics, primary PFS, "
                       "secondary OS/ORR/DCR, subgroup forest, sensitivity, safety).",
        statistics=[
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
    )


# ─────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────

# (tc_id, builder, r_filename, py_filename)
TC_BUILDERS = [
    ("TC-007", build_tc007, "tc-007-results.json", "tc-007-results.json"),
    ("TC-008", build_tc008, "tc-008-results.json", "tc-008-results.json"),
    ("TC-009", build_tc009, "TC-009.json", "TC-009.json"),
    ("TC-010", build_tc010, "TC-010.json", "TC-010.json"),
]


def main():
    ARS_DIR.mkdir(parents=True, exist_ok=True)

    print("╔" + "═" * 78 + "╗")
    print("║  ARS Envelope Generation — 4 Level 3 Test Cases                         ║")
    print("╚" + "═" * 78 + "╝")
    print()

    results = []

    for tc_id, builder, r_name, py_name in TC_BUILDERS:
        r_file = R_DIR / r_name
        py_file = PY_DIR / py_name

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
    print(f"✅ {ok_count}/{len(TC_BUILDERS)} Level 3 TCs: ARS envelopes generated")
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
