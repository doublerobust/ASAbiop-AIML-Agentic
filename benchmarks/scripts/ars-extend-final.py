#!/usr/bin/env python3
"""
ARS Envelope Generator for Final Test Cases (TC-006, TC-028, TC-031)

Reads existing benchmark JSON outputs from cross-lang-results/r-output/ and
cross-lang-results/python-output/, wraps them in CDISC ARS v1.0 envelopes,
and writes to cross-lang-results/ars-output/.

This closes the ARS coverage gap across the full 35-TC test case library.
After this script, all TCs with numerical ground truth outputs (33 of 35)
have ARS envelopes. TC-004 and TC-005 are qualitative Level 2 tasks (SAP
text drafting and TFL QC error review) that do not produce numerical
statistics suitable for ARS envelopes.

  - TC-006: Blinded Sample Size Re-Estimation at Interim (Level 2)
  - TC-028: Change in Tumor Size by Cycle — Longitudinal (Level 1)
  - TC-031: Time-to-First-Treatment (Level 1)
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


# ─────────────────────────────────────────────────────────────
# Per-TC ARS builders
# ─────────────────────────────────────────────────────────────

def build_tc006(data: dict) -> dict:
    """TC-006: Blinded Sample Size Re-Estimation at Interim (Level 2).

    Phase III oncology superiority trial. ITT is the sole primary analysis
    population per FDA/EMA standards; no per-protocol analysis is performed.
    Blinded SSR at interim uses pooled event rate and Schoenfeld formula
    to re-estimate sample size under optimistic/original/pessimistic HR
    scenarios without unblinding.
    """
    inp = data.get("input_parameters", {})
    cur = data.get("current_status", {})
    be = data.get("blinded_estimation", {})
    sc = data.get("scenarios", {})
    opt = sc.get("optimistic", {})
    orig = sc.get("original", {})
    pess = sc.get("pessimistic", {})

    return make_ars(
        tc_id="TC-006",
        reason="Blinded sample size re-estimation at interim: pooled event "
               "rate, conditional power, and enrollment adequacy assessment",
        method_name="Schoenfeld formula + blinded pooled median + "
                    "conditional power under assumed HR",
        code_template="ssr_blinded(pooled_median, events, hr_scenarios, "
                      "accrual_rate, alpha=0.05, power=0.90)",
        parameters={
            "enrolled": inp.get("enrolled"),
            "events_observed": inp.get("events_observed"),
            "pooled_median_pfs": inp.get("pooled_median_pfs"),
            "accrual_rate": inp.get("accrual_rate"),
            "original_hr": inp.get("original_hr"),
            "original_events": inp.get("original_events"),
            "planned_n": inp.get("planned_n"),
            "alpha": inp.get("alpha"),
            "power": inp.get("power"),
            "blinded": True,
            "itt_primary": True,
            "pp_analysis": "not performed (FDA/EMA oncology standard)",
        },
        variables=[
            {"name": "AVAL", "dataset": "ADTTE", "role": "PFS time"},
            {"name": "CNSR", "dataset": "ADTTE", "role": "censoring (0=event)"},
            {"name": "ITTFL", "dataset": "ADSL", "role": "ITT flag"},
            {"name": "TRT01A", "dataset": "ADSL", "role": "treatment (blinded)"},
        ],
        population={
            "name": "ITT (blinded pooled)",
            "filter": "ITTFL = 'Y' — blinded analysis, treatment arms pooled",
        },
        dataset="ADTTE",
        result_groups=[
            {"id": "Pooled (blinded)", "n": inp.get("enrolled")},
        ],
        documentation="Level 2 blinded sample size re-estimation. Phase III "
                       "oncology superiority trial — ITT is the sole primary "
                       "analysis population per FDA/EMA standards; no "
                       "per-protocol analysis is performed. Blinded SSR uses "
                       "pooled event data (no unblinding) to assess whether "
                       "the planned sample size is adequate under optimistic, "
                       "original, and pessimistic HR scenarios. Conditional "
                       "power is computed under each assumed HR.",
        statistics=[
            {"name": "enrolled", "value": cur.get("enrolled")},
            {"name": "planned_n", "value": cur.get("planned_n")},
            {"name": "enrollment_pct", "value": cur.get("enrollment_pct"), "unit": "%"},
            {"name": "events_observed", "value": cur.get("events_observed")},
            {"name": "original_events", "value": cur.get("original_events")},
            {"name": "information_fraction", "value": cur.get("information_fraction")},
            {"name": "accrual_rate", "value": cur.get("accrual_rate")},
            {"name": "pooled_median_pfs", "value": be.get("pooled_median_pfs"), "unit": "months"},
            {"name": "estimated_event_rate_monthly", "value": be.get("estimated_event_rate_monthly")},
            {"name": "lambda", "value": be.get("lambda")},
            {"name": "optimistic_hr", "value": opt.get("hr")},
            {"name": "optimistic_events_needed", "value": opt.get("events_needed")},
            {"name": "optimistic_total_n_needed", "value": opt.get("total_n_needed")},
            {"name": "optimistic_incremental_n", "value": opt.get("incremental_n")},
            {"name": "optimistic_conditional_power", "value": opt.get("conditional_power")},
            {"name": "optimistic_recommendation", "value": opt.get("recommendation")},
            {"name": "original_hr", "value": orig.get("hr")},
            {"name": "original_events_needed", "value": orig.get("events_needed")},
            {"name": "original_total_n_needed", "value": orig.get("total_n_needed")},
            {"name": "original_incremental_n", "value": orig.get("incremental_n")},
            {"name": "original_conditional_power", "value": orig.get("conditional_power")},
            {"name": "original_recommendation", "value": orig.get("recommendation")},
            {"name": "pessimistic_hr", "value": pess.get("hr")},
            {"name": "pessimistic_events_needed", "value": pess.get("events_needed")},
            {"name": "pessimistic_total_n_needed", "value": pess.get("total_n_needed")},
            {"name": "pessimistic_incremental_n", "value": pess.get("incremental_n")},
            {"name": "pessimistic_conditional_power", "value": pess.get("conditional_power")},
            {"name": "pessimistic_recommendation", "value": pess.get("recommendation")},
            {"name": "overall_recommendation", "value": data.get("overall_recommendation")},
        ],
    )


def build_tc028(data: dict) -> dict:
    """TC-028: Change in Tumor Size by Cycle — Longitudinal (Level 1).

    Computes percentage change from baseline in tumor size (SLD) at each
    treatment cycle (C1D1 through C6D1). Phase III oncology — ITT is sole
    primary population per FDA/EMA standards; no per-protocol analysis.
    """
    params = data.get("parameters", {})
    cycles = data.get("cycles", [])
    vs = data.get("visit_summaries", {})
    overall = data.get("overall_summary", {})

    # Extract visit-wise statistics for C2D1–C6D1 (C1D1 is baseline, 0% change)
    stats = []
    for cycle in cycles[1:]:  # Skip C1D1 (baseline)
        cv = vs.get(cycle, {})
        exp = cv.get("experimental", {})
        ctl = cv.get("control", {})
        suffix = cycle.lower().replace("c", "").replace("d", "d")
        stats.extend([
            {"name": f"{cycle}_n_assessed_experimental", "value": exp.get("n_assessed")},
            {"name": f"{cycle}_n_missing_experimental", "value": exp.get("n_missing")},
            {"name": f"{cycle}_mean_pct_change_experimental", "value": exp.get("mean_pct_change"), "unit": "%"},
            {"name": f"{cycle}_median_pct_change_experimental", "value": exp.get("median_pct_change"), "unit": "%"},
            {"name": f"{cycle}_n_assessed_control", "value": ctl.get("n_assessed")},
            {"name": f"{cycle}_n_missing_control", "value": ctl.get("n_missing")},
            {"name": f"{cycle}_mean_pct_change_control", "value": ctl.get("mean_pct_change"), "unit": "%"},
            {"name": f"{cycle}_median_pct_change_control", "value": ctl.get("median_pct_change"), "unit": "%"},
        ])

    # Overall summary statistics
    exp_ov = overall.get("experimental", {})
    ctl_ov = overall.get("control", {})
    stats.extend([
        {"name": "mean_best_pct_change_experimental", "value": exp_ov.get("mean_best_pct_change"), "unit": "%"},
        {"name": "median_best_pct_change_experimental", "value": exp_ov.get("median_best_pct_change"), "unit": "%"},
        {"name": "mean_worst_pct_change_experimental", "value": exp_ov.get("mean_worst_pct_change"), "unit": "%"},
        {"name": "median_worst_pct_change_experimental", "value": exp_ov.get("median_worst_pct_change"), "unit": "%"},
        {"name": "mean_n_assessments_experimental", "value": exp_ov.get("mean_n_assessments")},
        {"name": "mean_best_pct_change_control", "value": ctl_ov.get("mean_best_pct_change"), "unit": "%"},
        {"name": "median_best_pct_change_control", "value": ctl_ov.get("median_best_pct_change"), "unit": "%"},
        {"name": "mean_worst_pct_change_control", "value": ctl_ov.get("mean_worst_pct_change"), "unit": "%"},
        {"name": "median_worst_pct_change_control", "value": ctl_ov.get("median_worst_pct_change"), "unit": "%"},
        {"name": "mean_n_assessments_control", "value": ctl_ov.get("mean_n_assessments")},
    ])

    n_exp = params.get("n_subjects", 150) // 2
    n_ctl = params.get("n_subjects", 150) - n_exp

    return make_ars(
        tc_id="TC-028",
        reason="Longitudinal tumor size change: % change from baseline in SLD "
               "at each treatment cycle with visit-wise summary statistics",
        method_name="Descriptive statistics + longitudinal % change from baseline",
        code_template="tumor_pct_change = (SLD - SLD_baseline) / SLD_baseline * 100; "
                      "summary_stats(pct_change ~ cycle + arm)",
        parameters={
            "n_subjects": params.get("n_subjects"),
            "seed": params.get("seed"),
            "cycles": cycles,
            "baseline_cycle": data.get("baseline_cycle", "C1D1"),
            "itt_primary": True,
            "pp_analysis": "not performed (FDA/EMA oncology standard)",
        },
        variables=[
            {"name": "SLD", "dataset": "ADTR", "role": "sum of longest diameters (mm)"},
            {"name": "AVISIT", "dataset": "ADTR", "role": "visit/cycle"},
            {"name": "TRT01A", "dataset": "ADSL", "role": "treatment"},
            {"name": "ITTFL", "dataset": "ADSL", "role": "ITT flag"},
            {"name": "USUBJID", "dataset": "ADSL", "role": "subject identifier"},
        ],
        population={
            "name": "ITT",
            "filter": "ITTFL = 'Y' — all randomized subjects with tumor assessments",
        },
        dataset="ADTR",
        result_groups=[
            {"id": "Experimental", "n": n_exp},
            {"id": "Control", "n": n_ctl},
        ],
        documentation="Level 1 longitudinal tumor size analysis. Phase III "
                       "oncology superiority trial — ITT is the sole primary "
                       "analysis population per FDA/EMA standards; no "
                       "per-protocol analysis is performed. Computes "
                       "percentage change from baseline in SLD at each "
                       "treatment cycle (C2D1–C6D1) with visit-wise summary "
                       "statistics by arm. Overall summary includes best/worst "
                       "% change and mean number of assessments.",
        statistics=stats,
    )


def build_tc031(data: dict) -> dict:
    """TC-031: Time-to-First-Treatment (Level 1).

    Time from randomization to first dose of study treatment. Subjects who
    never receive treatment are censored at their follow-up time. Phase III
    oncology — ITT is sole primary population per FDA/EMA standards; no
    per-protocol analysis.
    """
    meta = data.get("metadata", {})
    km = data.get("km_median_ttt", {})
    lr = data.get("logrank_test", {})
    cox = data.get("cox_hr", {})
    summ = data.get("ttt_summary", {})
    recv = data.get("received_treatment", {})

    exp_km = km.get("experimental", {})
    ctl_km = km.get("control", {})
    exp_sum = summ.get("experimental", {})
    ctl_sum = summ.get("control", {})
    exp_recv = recv.get("experimental", {})
    ctl_recv = recv.get("control", {})

    return make_ars(
        tc_id="TC-031",
        reason="Time-to-first-treatment: KM median, log-rank, Cox HR, and "
               "treatment receipt rates by arm",
        method_name="Kaplan-Meier + log-rank + Cox PH (Efron ties)",
        code_template="survfit(Surv(TTT, 1-CNSR) ~ TRT01A); survdiff(...); "
                      "coxph(Surv(TTT, 1-CNSR) ~ TRT01PN)",
        parameters={
            "n_total": meta.get("n_total"),
            "population": meta.get("population"),
            "time_unit": meta.get("time_unit"),
            "censoring_rule": meta.get("censoring_rule"),
            "itt_primary": True,
            "pp_analysis": "not performed (FDA/EMA oncology standard)",
        },
        variables=[
            {"name": "TTT_DAYS", "dataset": "ADSL", "role": "time-to-first-treatment (days)"},
            {"name": "CNSR_TTT", "dataset": "ADSL", "role": "censoring (1=censored)"},
            {"name": "RECEIVED_TX", "dataset": "ADSL", "role": "treatment received flag"},
            {"name": "TRT01A", "dataset": "ADSL", "role": "treatment arm"},
            {"name": "ITTFL", "dataset": "ADSL", "role": "ITT flag"},
            {"name": "RANDDT", "dataset": "ADSL", "role": "randomization date"},
            {"name": "FIRSTDOSEDT", "dataset": "ADSL", "role": "first dose date"},
        ],
        population={
            "name": "ITT",
            "filter": "ITTFL = 'Y' — all randomized subjects",
        },
        dataset="ADSL",
        result_groups=[
            {"id": "Experimental", "n": meta.get("n_experimental")},
            {"id": "Control", "n": meta.get("n_control")},
        ],
        documentation="Level 1 time-to-first-treatment analysis. Phase III "
                       "oncology superiority trial — ITT is the sole primary "
                       "analysis population per FDA/EMA standards; no "
                       "per-protocol analysis is performed. Time from "
                       "randomization to first dose of study treatment; "
                       "subjects who never receive treatment are censored at "
                       "their follow-up time. KM median with CI, log-rank "
                       "test, Cox HR with CI, and treatment receipt rates.",
        statistics=[
            {"name": "n_total", "value": meta.get("n_total")},
            {"name": "n_experimental", "value": meta.get("n_experimental")},
            {"name": "n_control", "value": meta.get("n_control")},
            {"name": "km_median_experimental", "value": exp_km.get("median"), "unit": "days"},
            {"name": "km_ci_lower_experimental", "value": exp_km.get("ci_lower"), "unit": "days"},
            {"name": "km_ci_upper_experimental", "value": exp_km.get("ci_upper"), "unit": "days"},
            {"name": "n_events_experimental", "value": exp_km.get("n_events")},
            {"name": "estimable_experimental", "value": exp_km.get("estimable")},
            {"name": "km_median_control", "value": ctl_km.get("median"), "unit": "days"},
            {"name": "km_ci_lower_control", "value": ctl_km.get("ci_lower"), "unit": "days"},
            {"name": "km_ci_upper_control", "value": ctl_km.get("ci_upper"), "unit": "days"},
            {"name": "n_events_control", "value": ctl_km.get("n_events")},
            {"name": "estimable_control", "value": ctl_km.get("estimable")},
            {"name": "logrank_chisq", "value": lr.get("chisq")},
            {"name": "logrank_df", "value": lr.get("df")},
            {"name": "logrank_p_value", "value": lr.get("p_value")},
            {"name": "cox_hr", "value": cox.get("hr")},
            {"name": "cox_hr_lower", "value": cox.get("hr_lower")},
            {"name": "cox_hr_upper", "value": cox.get("hr_upper")},
            {"name": "cox_p_value", "value": cox.get("p_value")},
            {"name": "mean_ttt_experimental", "value": exp_sum.get("mean"), "unit": "days"},
            {"name": "median_ttt_experimental", "value": exp_sum.get("median"), "unit": "days"},
            {"name": "sd_ttt_experimental", "value": exp_sum.get("sd"), "unit": "days"},
            {"name": "min_ttt_experimental", "value": exp_sum.get("min"), "unit": "days"},
            {"name": "max_ttt_experimental", "value": exp_sum.get("max"), "unit": "days"},
            {"name": "mean_ttt_control", "value": ctl_sum.get("mean"), "unit": "days"},
            {"name": "median_ttt_control", "value": ctl_sum.get("median"), "unit": "days"},
            {"name": "sd_ttt_control", "value": ctl_sum.get("sd"), "unit": "days"},
            {"name": "min_ttt_control", "value": ctl_sum.get("min"), "unit": "days"},
            {"name": "max_ttt_control", "value": ctl_sum.get("max"), "unit": "days"},
            {"name": "n_received_experimental", "value": exp_recv.get("n_received")},
            {"name": "n_censored_experimental", "value": exp_recv.get("n_censored")},
            {"name": "pct_received_experimental", "value": exp_recv.get("pct_received"), "unit": "%"},
            {"name": "n_received_control", "value": ctl_recv.get("n_received")},
            {"name": "n_censored_control", "value": ctl_recv.get("n_censored")},
            {"name": "pct_received_control", "value": ctl_recv.get("pct_received"), "unit": "%"},
        ],
    )


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

TC_BUILDERS = [
    ("TC-006", build_tc006, "TC-006.json", "TC-006.json"),
    ("TC-028", build_tc028, "TC-028.json", "TC-028.json"),
    ("TC-031", build_tc031, "TC-031.json", "TC-031.json"),
]


def main():
    ARS_DIR.mkdir(parents=True, exist_ok=True)

    print("╔" + "═" * 78 + "╗")
    print("║  ARS Envelope Generation — 3 Final Test Cases (TC-006, TC-028, TC-031)  ║")
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

        # Write files
        r_out = ARS_DIR / f"{tc_id}_R_ars.json"
        py_out = ARS_DIR / f"{tc_id}_Py_ars.json"

        with open(r_out, "w") as f:
            json.dump(r_ars, f, indent=2)
        with open(py_out, "w") as f:
            json.dump(py_ars, f, indent=2)

        r_stats = len(r_ars["analysisResult"]["analysisResultsData"]["statistics"])
        py_stats = len(py_ars["analysisResult"]["analysisResultsData"]["statistics"])

        print(f"✅ {tc_id}: R={r_stats} stats, Python={py_stats} stats "
              f"→ {r_out.name}, {py_out.name}")
        results.append((tc_id, "OK", r_stats, py_stats))

    print()
    print("╔" + "═" * 78 + "╗")
    print("║  Summary                                                              ║")
    print("╚" + "═" * 78 + "╝")
    for tc_id, status, r_stats, py_stats in results:
        if status == "OK":
            print(f"  {tc_id}: ✅ {r_stats} R stats, {py_stats} Python stats")
        else:
            print(f"  {tc_id}: ⚠ {status}")

    total_r = sum(r for _, s, r, _ in results if s == "OK")
    total_py = sum(p for _, s, _, p in results if s == "OK")
    print(f"\n  Total: {total_r} R statistics, {total_py} Python statistics")
    print(f"  Files: {len(results) * 2} ARS envelopes generated")


if __name__ == "__main__":
    main()