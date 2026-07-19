#!/usr/bin/env python3
"""
ARS Envelope Generator for Remaining Test Cases (TC-011, 013, 014, 015, 016, 017, 018, 020)

Reads existing benchmark JSON outputs from cross-lang-results/r-output/ and
cross-lang-results/python-output/, wraps them in CDISC ARS v1.0 envelopes,
and writes to cross-lang-results/ars-output/.

This extends ARS coverage from 13 TCs to all 21 TCs that have --ars-output
support in their R/Python scripts (TC-001/002/003/006/012/019/021-035).

The 8 TCs covered here (TC-011/013/014/015/016/017/018/020) already produce
benchmark JSON outputs but don't yet have ARS envelopes generated.
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


def extract_n(data: dict, *paths, default=None):
    """Try multiple key paths to find n values."""
    for path in paths:
        obj = data
        try:
            for p in path:
                obj = obj[p]
            return obj
        except (KeyError, TypeError, IndexError):
            continue
    return default


# ─────────────────────────────────────────────────────
# Per-TC ARS builders
# ─────────────────────────────────────────────────────

def build_tc011(data: dict) -> dict:
    pop = data.get("population", {})
    n_exp = pop.get("n_experimental", 100)
    n_ctl = pop.get("n_control", 100)
    summary = data.get("summary", [])
    n_any_ae_exp = summary[0]["n_experimental"] if summary else n_exp
    n_any_ae_ctl = summary[0]["n_control"] if summary else n_ctl
    n_rows = len(data.get("ae_table", []))

    return make_ars(
        tc_id="TC-011",
        reason="Safety summary: adverse events by SOC and preferred term",
        method_name="Frequency tabulation",
        code_template="aggregate(AEDECOD ~ TRT01A, data=ADAE, FUN=length)",
        parameters={"sort": "descending frequency", "hierarchy": "SOC → PT"},
        variables=[
            {"name": "AESOC", "dataset": "ADAE", "role": "System Organ Class"},
            {"name": "AEDECOD", "dataset": "ADAE", "role": "Preferred Term"},
            {"name": "TRT01A", "dataset": "ADSL", "role": "treatment"},
            {"name": "SAFFL", "dataset": "ADSL", "role": "safety flag"},
        ],
        population={"name": "Safety", "filter": "SAFFL = 'Y'"},
        dataset="ADAE",
        result_groups=[
            {"id": "Experimental", "n": n_exp},
            {"id": "Control", "n": n_ctl},
        ],
        documentation=f"AE summary table with {n_rows} rows (SOC/PT hierarchy), sorted by frequency",
        statistics=[
            {"name": "n_experimental", "value": n_exp},
            {"name": "n_control", "value": n_ctl},
            {"name": "n_any_ae_experimental", "value": n_any_ae_exp},
            {"name": "n_any_ae_control", "value": n_any_ae_ctl},
            {"name": "n_table_rows", "value": n_rows},
        ],
    )


def build_tc013(data: dict) -> dict:
    s = data.get("summary", {})
    all_s = s.get("all", {})
    exp_s = s.get("experimental", {})
    ctl_s = s.get("control", {})

    return make_ars(
        tc_id="TC-013",
        reason="Efficacy: waterfall plot of best percentage change in tumor size (RECIST 1.1)",
        method_name="Descriptive statistics + RECIST response categorization",
        code_template="pct_change = (best - baseline) / baseline * 100",
        parameters={
            "response_criteria": "RECIST 1.1",
            "thresholds": {"CR": -100, "PR": -30, "PD": 20},
        },
        variables=[
            {"name": "BESTPCHG", "dataset": "ADRS", "role": "best percent change"},
            {"name": "BOR", "dataset": "ADRS", "role": "best overall response"},
            {"name": "TRT01A", "dataset": "ADSL", "role": "treatment"},
        ],
        population={"name": "ITT", "filter": "ITTFL = 'Y'"},
        dataset="ADRS",
        result_groups=[
            {"id": "Experimental", "n": exp_s.get("n", 100)},
            {"id": "Control", "n": ctl_s.get("n", 100)},
        ],
        documentation="Waterfall plot showing best % change from baseline in tumor size per subject",
        statistics=[
            {"name": "n_all", "value": all_s.get("n")},
            {"name": "orr_pct_all", "value": all_s.get("orr_pct")},
            {"name": "dcr_pct_all", "value": all_s.get("dcr_pct")},
            {"name": "n_cr_all", "value": all_s.get("n_cr")},
            {"name": "n_pr_all", "value": all_s.get("n_pr")},
            {"name": "n_sd_all", "value": all_s.get("n_sd")},
            {"name": "n_pd_all", "value": all_s.get("n_pd")},
            {"name": "median_best_pct_change_all", "value": all_s.get("median_best_pct_change")},
            {"name": "orr_pct_experimental", "value": exp_s.get("orr_pct")},
            {"name": "orr_pct_control", "value": ctl_s.get("orr_pct")},
            {"name": "dcr_pct_experimental", "value": exp_s.get("dcr_pct")},
            {"name": "dcr_pct_control", "value": ctl_s.get("dcr_pct")},
        ],
    )


def build_tc014(data: dict) -> dict:
    pop = data.get("population", {})
    summary = data.get("summary", {}).get("all", {})
    n_exp = pop.get("n_experimental", 100)
    n_ctl = pop.get("n_control", 100)

    return make_ars(
        tc_id="TC-014",
        reason="Data integrity: listing of key protocol deviations",
        method_name="Descriptive listing",
        code_template="subset(ADSL, PPFL != 'Y')",
        parameters={"sort": "TRT01A, USUBJID, PDDY"},
        variables=[
            {"name": "USUBJID", "dataset": "ADSL", "role": "subject identifier"},
            {"name": "TRT01A", "dataset": "ADSL", "role": "treatment"},
            {"name": "PPDECOD", "dataset": "ADSL", "role": "protocol deviation term"},
            {"name": "PPDY", "dataset": "ADSL", "role": "deviation day"},
        ],
        population={"name": "All Randomized", "filter": "RANDFL = 'Y'"},
        dataset="ADSL",
        result_groups=[
            {"id": "Experimental", "n": n_exp},
            {"id": "Control", "n": n_ctl},
        ],
        documentation="Listing of protocol deviations sorted by treatment, subject, and deviation day",
        statistics=[
            {"name": "n_experimental", "value": n_exp},
            {"name": "n_control", "value": n_ctl},
            {"name": "n_subjects_with_pd", "value": summary.get("n_subjects_with_pd")},
            {"name": "n_total_deviations", "value": summary.get("n_total_deviations")},
        ],
    )


def build_tc015(data: dict) -> dict:
    meta = data.get("metadata", {})
    median = data.get("overall_median", {})
    logrank = data.get("logrank", {})

    return make_ars(
        tc_id="TC-015",
        reason="Primary efficacy: KM survival curve with risk table and log-rank test",
        method_name="Kaplan-Meier + log-rank",
        code_template="survfit(Surv(AVAL, 1-CNSR) ~ TRT01A); survdiff(...)",
        parameters={
            "conf_type": "log-log",
            "time_unit": meta.get("time_unit", "months"),
        },
        variables=[
            {"name": "AVAL", "dataset": "ADTTE", "role": "analysis time"},
            {"name": "CNSR", "dataset": "ADTTE", "role": "censoring"},
            {"name": "TRT01A", "dataset": "ADSL", "role": "treatment"},
        ],
        population={"name": "ITT", "filter": "ITTFL = 'Y'"},
        dataset="ADTTE",
        result_groups=[
            {"id": "Experimental", "n": meta.get("n_experimental", 100)},
            {"id": "Control", "n": meta.get("n_control", 100)},
        ],
        documentation="KM curve with at-risk table at time points, log-rank test for treatment comparison",
        statistics=[
            {"name": "median_overall", "value": median.get("median"), "unit": "months"},
            {"name": "ci_lower", "value": median.get("ci_lower")},
            {"name": "ci_upper", "value": median.get("ci_upper")},
            {"name": "logrank_chisq", "value": logrank.get("chisq")},
            {"name": "logrank_p_value", "value": logrank.get("p_value")},
            {"name": "n_total", "value": meta.get("n_total")},
            {"name": "events_experimental", "value": meta.get("events_experimental")},
            {"name": "events_control", "value": meta.get("events_control")},
        ],
    )


def build_tc016(data: dict) -> dict:
    meta = data.get("metadata", {})
    td = data.get("treatment_duration", {})
    di = data.get("dose_intensity", {})
    dr = data.get("dose_reduction", {})

    return make_ars(
        tc_id="TC-016",
        reason="Safety: treatment exposure summary (duration, cumulative dose, dose intensity, reductions)",
        method_name="Descriptive statistics",
        code_template="summary(EXDUR ~ TRT01A); summary(CUMDOSE ~ TRT01A)",
        parameters={
            "duration_unit": meta.get("duration_unit", "weeks"),
            "dose_unit": meta.get("dose_unit", "mg"),
        },
        variables=[
            {"name": "EXDUR", "dataset": "ADEX", "role": "treatment duration"},
            {"name": "CUMDOSE", "dataset": "ADEX", "role": "cumulative dose"},
            {"name": "DOSINT", "dataset": "ADEX", "role": "dose intensity (%)"},
            {"name": "TRT01A", "dataset": "ADSL", "role": "treatment"},
            {"name": "SAFFL", "dataset": "ADSL", "role": "safety flag"},
        ],
        population={"name": "Safety", "filter": "SAFFL = 'Y'"},
        dataset="ADEX",
        result_groups=[
            {"id": "Experimental", "n": meta.get("n_experimental", 100)},
            {"id": "Control", "n": meta.get("n_control", 100)},
        ],
        documentation="Exposure summary: treatment duration, cumulative dose, relative dose intensity, dose reduction",
        statistics=[
            {"name": "mean_duration_experimental", "value": td.get("experimental", {}).get("mean"), "unit": "weeks"},
            {"name": "median_duration_experimental", "value": td.get("experimental", {}).get("median"), "unit": "weeks"},
            {"name": "mean_duration_control", "value": td.get("control", {}).get("mean"), "unit": "weeks"},
            {"name": "median_duration_control", "value": td.get("control", {}).get("median"), "unit": "weeks"},
            {"name": "mean_dose_intensity_experimental", "value": di.get("experimental", {}).get("mean"), "unit": "%"},
            {"name": "mean_dose_intensity_control", "value": di.get("control", {}).get("mean"), "unit": "%"},
            {"name": "n_dose_reduction_experimental", "value": dr.get("experimental", {}).get("n_yes")},
            {"name": "n_dose_reduction_control", "value": dr.get("control", {}).get("n_yes")},
        ],
    )


def build_tc017(data: dict) -> dict:
    meta = data.get("metadata", {})
    overall = data.get("shift_overall", {}).get("counts", {})

    # Compute shift counts
    n_low_to_high = 0
    n_high_to_low = 0
    n_stable = 0
    for base_cat in ("LOW", "NORMAL", "HIGH"):
        for end_cat in ("LOW", "NORMAL", "HIGH"):
            count = overall.get(base_cat, {}).get(end_cat, 0)
            if base_cat == "LOW" and end_cat == "HIGH":
                n_low_to_high = count
            elif base_cat == "HIGH" and end_cat == "LOW":
                n_high_to_low = count
            elif base_cat == end_cat:
                n_stable += count

    return make_ars(
        tc_id="TC-017",
        reason="Safety: laboratory shift table (baseline → post-baseline categories)",
        method_name="Shift tabulation",
        code_template="table(BASECAT, ENDCAT, TRT01A)",
        parameters={
            "lab_test": meta.get("lab_test", "Hemoglobin"),
            "lab_unit": meta.get("lab_unit", "g/L"),
            "categories": meta.get("categories", ["LOW", "NORMAL", "HIGH"]),
        },
        variables=[
            {"name": "LBSTRESN", "dataset": "ADLB", "role": "lab result"},
            {"name": "BASECAT", "dataset": "ADLB", "role": "baseline category"},
            {"name": "ENDCAT", "dataset": "ADLB", "role": "post-baseline category"},
            {"name": "TRT01A", "dataset": "ADSL", "role": "treatment"},
            {"name": "SAFFL", "dataset": "ADSL", "role": "safety flag"},
        ],
        population={"name": "Safety", "filter": "SAFFL = 'Y'"},
        dataset="ADLB",
        result_groups=[
            {"id": "Experimental", "n": meta.get("n_experimental", 100)},
            {"id": "Control", "n": meta.get("n_control", 100)},
        ],
        documentation=f"Lab shift table for {meta.get('lab_test', 'Hemoglobin')}: baseline → post-baseline category transitions",
        statistics=[
            {"name": "n_total", "value": meta.get("n_total")},
            {"name": "n_low_to_high", "value": n_low_to_high},
            {"name": "n_high_to_low", "value": n_high_to_low},
            {"name": "n_stable_category", "value": n_stable},
        ],
    )


def build_tc018(data: dict) -> dict:
    meta = data.get("metadata", {})
    visits = data.get("visits", {})
    visits_list = meta.get("visits", [])

    # Extract WEEK_12 change from baseline for stats
    week12 = visits.get("WEEK_12", {})
    exp_w12 = week12.get("experimental", {})
    ctl_w12 = week12.get("control", {})

    return make_ars(
        tc_id="TC-018",
        reason="Efficacy: change from baseline in tumor size by visit",
        method_name="Descriptive statistics (mean, SD, median, SE, CI)",
        code_template="t.test(CHG ~ TRT01A, data=subset(ADRS, AVISIT='WEEK_12'))",
        parameters={
            "endpoint": meta.get("endpoint", "Tumor Size"),
            "endpoint_unit": meta.get("endpoint_unit", "mm"),
            "visits": visits_list,
        },
        variables=[
            {"name": "AVAL", "dataset": "ADRS", "role": "analysis value"},
            {"name": "BASE", "dataset": "ADRS", "role": "baseline value"},
            {"name": "CHG", "dataset": "ADRS", "role": "change from baseline"},
            {"name": "AVISIT", "dataset": "ADRS", "role": "analysis visit"},
            {"name": "TRT01A", "dataset": "ADSL", "role": "treatment"},
        ],
        population={"name": "ITT", "filter": "ITTFL = 'Y'"},
        dataset="ADRS",
        result_groups=[
            {"id": "Experimental", "n": meta.get("n_experimental", 100)},
            {"id": "Control", "n": meta.get("n_control", 100)},
        ],
        documentation="Change from baseline summary by visit: mean, SD, median, SE, 95% CI per treatment arm",
        statistics=[
            {"name": "mean_chg_week12_experimental", "value": exp_w12.get("mean_chg"), "unit": "mm"},
            {"name": "mean_chg_week12_control", "value": ctl_w12.get("mean_chg"), "unit": "mm"},
            {"name": "median_chg_week12_experimental", "value": exp_w12.get("median_chg"), "unit": "mm"},
            {"name": "median_chg_week12_control", "value": ctl_w12.get("median_chg"), "unit": "mm"},
            {"name": "n_visits", "value": len(visits_list)},
        ],
    )


def build_tc020(data: dict) -> dict:
    overall = data.get("overall", {})
    interactions = data.get("interaction_pvalues", [])

    return make_ars(
        tc_id="TC-020",
        reason="Efficacy: ORR by subgroup with Cochran-Mantel-Haenszel interaction testing",
        method_name="Binomial proportion + CMH test",
        code_template="prop.test(x, n); mantelhaen.test(matrix)",
        parameters={
            "subgroups": [i.get("subgroup") for i in interactions],
            "response_definition": "CR + PR",
        },
        variables=[
            {"name": "BOR", "dataset": "ADRS", "role": "best overall response"},
            {"name": "TRT01A", "dataset": "ADSL", "role": "treatment"},
            {"name": "SEX", "dataset": "ADSL", "role": "subgroup: sex"},
            {"name": "AGEGR1", "dataset": "ADSL", "role": "subgroup: age group"},
            {"name": "ECOG", "dataset": "ADSL", "role": "subgroup: ECOG"},
        ],
        population={"name": "ITT", "filter": "ITTFL = 'Y'"},
        dataset="ADRS",
        result_groups=[
            {"id": "Experimental", "n": overall.get("n_experimental", 100)},
            {"id": "Control", "n": overall.get("n_control", 100)},
        ],
        documentation="ORR by subgroup (SEX, AGEGR1, ECOG) with CMH interaction p-values",
        statistics=[
            {"name": "orr_experimental", "value": overall.get("orr_experimental"), "unit": "%"},
            {"name": "orr_control", "value": overall.get("orr_control"), "unit": "%"},
            {"name": "orr_difference", "value": overall.get("orr_difference"), "unit": "%"},
            {"name": "responders_experimental", "value": overall.get("responders_experimental")},
            {"name": "responders_control", "value": overall.get("responders_control")},
            {"name": "n_experimental", "value": overall.get("n_experimental")},
            {"name": "n_control", "value": overall.get("n_control")},
        ] + [
            {"name": f"cmh_pvalue_{iv.get('subgroup', f'sg{i}')}", "value": iv.get("cmh_p_value")}
            for i, iv in enumerate(interactions)
        ] + [
            {"name": f"cmh_common_or_{iv.get('subgroup', f'sg{i}')}", "value": iv.get("cmh_common_or")}
            for i, iv in enumerate(interactions)
        ],
    )


# ─────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────

TC_BUILDERS = {
    "TC-011": build_tc011,
    "TC-013": build_tc013,
    "TC-014": build_tc014,
    "TC-015": build_tc015,
    "TC-016": build_tc016,
    "TC-017": build_tc017,
    "TC-018": build_tc018,
    "TC-020": build_tc020,
}


def main():
    ARS_DIR.mkdir(parents=True, exist_ok=True)

    print("╔" + "═" * 78 + "╗")
    print("║  ARS Envelope Generation — 8 Remaining Test Cases                       ║")
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
    print("ARS output files now in directory:")
    all_ars = sorted(ARS_DIR.glob("*_ars.json"))
    for f in all_ars:
        print(f"  {f.name}")
    print(f"Total: {len(all_ars)} ARS envelope files")


if __name__ == "__main__":
    main()
