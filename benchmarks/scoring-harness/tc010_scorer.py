#!/usr/bin/env python3
"""tc010_scorer.py — TC-010 Level 3 CSR Statistical Sections Scorer

Scores agent-generated CSR statistical sections (Sections 9 and 11) against the
TC-010 expert rubric.

Scoring structure (100 points total):
  - Numerical (auto-scorable) (30%): PFS median, HR, log-rank p; OS median, HR;
    ORR/DCR counts and percentages; disposition counts; safety AE counts
  - Structural sections (20%): 8 required CSR sections present (Section 9 methods,
    Section 11.1 disposition, 11.2 demographics, 11.4.1 primary PFS,
    11.4.1.1 sensitivity, 11.4.1.2 subgroup forest, 11.4.2 OS, 11.4.3 ORR/DCR,
    11.5 safety)
  - Concept/keyword checks (20%): ICH E3, ITT, Kaplan-Meier, Cox PH, log-rank,
    RECIST 1.1, hazard ratio, median survival, risk difference, sensitivity
  - Qualitative rubric (30%): LLM-as-judge prompt template (or manual scoring)

Usage:
    python tc010_scorer.py --expected <ground_truth.json> --actual <agent-output.json> \
        [--report-doc agent-csr.md] [--rubric-output scores.json]
"""

import argparse
import json
from pathlib import Path


# ─── Auto-Scorable Numerical Checks (30%) ───

NUMERICAL_CRITERIA = {
    # Weights sum to exactly 0.30 (30%) so total max = 0.30+0.20+0.20+0.30 = 1.00.
    "pfs_median_active": {
        "weight": 0.035,
        "description": "PFS median (Active arm, days) within tolerance of ground truth",
        "tolerance": 15,  # ±15 days
    },
    "pfs_median_placebo": {
        "weight": 0.035,
        "description": "PFS median (Placebo arm, days) within tolerance of ground truth",
        "tolerance": 15,
    },
    "pfs_cox_hr": {
        "weight": 0.040,
        "description": "PFS Cox hazard ratio (Active vs Placebo) within tolerance",
        "tolerance": 0.10,  # ±0.10
    },
    "os_cox_hr": {
        "weight": 0.030,
        "description": "OS Cox hazard ratio (Active vs Placebo) within tolerance",
        "tolerance": 0.10,
    },
    "orr_active_pct": {
        "weight": 0.030,
        "description": "ORR percentage (Active arm) within tolerance",
        "tolerance": 5.0,  # ±5 percentage points
    },
    "orr_placebo_pct": {
        "weight": 0.025,
        "description": "ORR percentage (Placebo arm) within tolerance",
        "tolerance": 5.0,
    },
    "dcr_active_pct": {
        "weight": 0.025,
        "description": "DCR percentage (Active arm) within tolerance",
        "tolerance": 5.0,
    },
    "disposition_n_completed_active": {
        "weight": 0.030,
        "description": "Completed subject count (Active) within tolerance",
        "tolerance": 5,
    },
    "safety_n_any_ae_active": {
        "weight": 0.025,
        "description": "Any AE subject count (Active) within tolerance",
        "tolerance": 10,
    },
    "safety_pct_grade3_plus_active": {
        "weight": 0.025,
        "description": "Grade 3+ AE percentage (Active) within tolerance",
        "tolerance": 5.0,
    },
}


# ─── Structural Section Checks (20%) ───

REQUIRED_SECTIONS = [
    ("section_9_statistical_methods", [
        "statistical methods", "analysis populations", "itt population",
        "kaplan-meier", "cox proportional hazards", "log-rank", "alpha",
    ]),
    ("section_11_1_disposition", [
        "patient disposition", "subject disposition", "randomized", "discontinued",
        "completed", "protocol deviations",
    ]),
    ("section_11_2_demographics", [
        "demographics", "baseline characteristics", "age", "sex", "ecog",
        "disease stage", "race",
    ]),
    ("section_11_4_1_primary_pfs", [
        "progression-free survival", "pfs", "median pfs", "hazard ratio",
        "log-rank", "primary endpoint",
    ]),
    ("section_11_4_1_1_sensitivity", [
        "sensitivity analysis", "sensitivity", "robustness", "censoring",
    ]),
    ("section_11_4_1_2_subgroup", [
        "subgroup", "forest plot", "subgroup analysis", "sex", "age group",
        "ecog", "disease stage",
    ]),
    ("section_11_4_2_os", [
        "overall survival", "os ", "median os", "overall survival benefit",
    ]),
    ("section_11_4_3_orr_dcr", [
        "objective response", "orr", "disease control", "dcr", "recist",
        "best overall response", "complete response", "partial response",
    ]),
    ("section_11_5_safety", [
        "safety results", "adverse event", "ae summary", "serious adverse",
        "grade 3", "deaths", "laboratory",
    ]),
]


# ─── Concept/Keyword Checks (20%) ───

CONCEPT_CRITERIA = {
    "ich_e3_compliance": {
        "weight": 0.03,
        "description": "ICH E3 structure and formatting referenced",
        "keywords": ["ich e3", "clinical study report", "csr", "section 9", "section 11",
                      "section 11.1", "section 11.2", "section 11.4", "section 11.5"],
        "min_matches": 3,
    },
    "itt_population_concept": {
        "weight": 0.03,
        "description": "ITT as sole primary analysis population (no per-protocol analysis for Phase III oncology)",
        "keywords": ["intent-to-treat", "itt", "itt population", "all randomized",
                      "primary analysis population", "intention-to-treat"],
        "min_matches": 2,
    },
    "kaplan_meier_method": {
        "weight": 0.025,
        "description": "Kaplan-Meier estimation method correctly described",
        "keywords": ["kaplan-meier", "kaplan meier", "product-limit", "survival curve",
                      "median survival", "confidence interval", "median pfs"],
        "min_matches": 2,
    },
    "cox_ph_method": {
        "weight": 0.025,
        "description": "Cox proportional hazards model correctly described",
        "keywords": ["cox proportional hazards", "cox ph", "hazard ratio", "cox model",
                      "proportional hazards", "efron", "95% ci"],
        "min_matches": 2,
    },
    "recist_response_criteria": {
        "weight": 0.025,
        "description": "RECIST 1.1 response criteria correctly referenced",
        "keywords": ["recist 1.1", "recist", "complete response", "partial response",
                      "stable disease", "progressive disease", "best overall response", "bor"],
        "min_matches": 2,
    },
    "sensitivity_analysis_concept": {
        "weight": 0.02,
        "description": "Sensitivity analysis rationale and methodology correctly described",
        "keywords": ["sensitivity analysis", "robustness", "informative censoring",
                      "censoring assumption", "non-progression", "withdrawal"],
        "min_matches": 2,
    },
    "risk_difference_concept": {
        "weight": 0.02,
        "description": "Risk difference and Fisher's exact test for binary endpoints",
        "keywords": ["risk difference", "fisher", "fisher's exact", "95% ci",
                      "confidence interval", "odds ratio"],
        "min_matches": 2,
    },
    "safety_reporting_standards": {
        "weight": 0.015,
        "description": "Safety reporting standards (MedDRA, CTCAE grading) referenced",
        "keywords": ["meddra", "ctcae", "system organ class", "soc", "preferred term",
                      "adverse event", "serious adverse event", "sae", "grade"],
        "min_matches": 3,
    },
    "regulatory_population_note": {
        "weight": 0.01,
        "description": "Correctly states ITT as sole primary population (no per-protocol for Phase III oncology)",
        "keywords": ["itt", "intent-to-treat", "all randomized", "sole primary",
                      "no per-protocol", "per-protocol", "primary analysis"],
        "min_matches": 2,
    },
}


# ─── LLM-as-Judge Prompt Template (30%) ───

LLM_JUDGE_PROMPT = """You are an expert biostatistician and regulatory submission reviewer
evaluating a Clinical Study Report (CSR) statistical sections draft for a Phase III oncology
trial of Drug X (Active) vs Placebo. The CSR must follow ICH E3 structure (Sections 9 and 11).

Score the CSR draft on a 0-5 scale for each criterion:

1. **Statistical Methods Accuracy (8 pts)**: Are the analysis methods (Section 9) correctly
   described? Are ITT and safety populations defined? Is the Kaplan-Meier method, Cox PH
   model (Efron ties), log-rank test, and multiplicity approach correctly stated? Is it
   correctly stated that ITT is the sole primary analysis population with NO per-protocol
   analysis (per FDA/EMA standards for Phase III oncology)?

2. **Efficacy Results Presentation (8 pts)**: Are the primary PFS results (median, HR, 95% CI,
   log-rank p) correctly reported? Are secondary endpoints (OS, ORR, DCR) presented with
   appropriate statistics? Is the sensitivity analysis included and consistent with the
   primary result? Are subgroup forest plot results presented?

3. **Safety Results Completeness (6 pts)**: Is the AE summary complete (any AE, SAE, Grade 3+,
   discontinuations, deaths)? Are AEs presented by SOC/PT? Are lab abnormalities reported?
   Is the safety narrative consistent with the data?

4. **ICH E3 Structure and Cross-Referencing (4 pts)**: Does the CSR follow ICH E3 section
   numbering (9, 11.1, 11.2, 11.4, 11.5)? Are all TFL references accurate? Are tables and
   figures properly numbered? Is the narrative internally consistent?

5. **Regulatory and Interpretive Quality (4 pts)**: Are conclusions supported by the data?
   Are potential limitations (e.g., baseline imbalances) acknowledged? Is the interpretation
   clinically sound and regulatory-appropriate?

Ground truth analysis:
{ground_truth_json}

Agent CSR draft:
{agent_report}

For each criterion, provide:
- Score (0-5)
- Rationale (1-2 sentences)

Output as JSON:
{{
  "statistical_methods_accuracy": {{"score": 0-5, "rationale": "..."}},
  "efficacy_results_presentation": {{"score": 0-5, "rationale": "..."}},
  "safety_results_completeness": {{"score": 0-5, "rationale": "..."}},
  "ich_e3_structure": {{"score": 0-5, "rationale": "..."}},
  "regulatory_interpretive_quality": {{"score": 0-5, "rationale": "..."}}
}}
"""


def _get(d, *keys, default=None):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def score_numerical(expected, actual):
    """Score auto-scorable numerical criteria (30%)."""
    scores = {}
    for key, criterion in NUMERICAL_CRITERIA.items():
        weight = criterion["weight"]
        tol = criterion.get("tolerance", 5.0)

        if key == "pfs_median_active":
            exp = _get(expected, "section_11_4_efficacy", "primary_pfs", "by_arm", "Active", "median")
            act = _get(actual, "section_11_4_efficacy", "primary_pfs", "by_arm", "Active", "median")
        elif key == "pfs_median_placebo":
            exp = _get(expected, "section_11_4_efficacy", "primary_pfs", "by_arm", "Placebo", "median")
            act = _get(actual, "section_11_4_efficacy", "primary_pfs", "by_arm", "Placebo", "median")
        elif key == "pfs_cox_hr":
            exp = _get(expected, "section_11_4_efficacy", "primary_pfs", "cox", "hr")
            act = _get(actual, "section_11_4_efficacy", "primary_pfs", "cox", "hr")
        elif key == "os_cox_hr":
            exp = _get(expected, "section_11_4_efficacy", "secondary_os", "cox", "hr")
            act = _get(actual, "section_11_4_efficacy", "secondary_os", "cox", "hr")
        elif key == "orr_active_pct":
            exp = _get(expected, "section_11_4_efficacy", "secondary_orr_dcr", "by_arm", "Active", "orr_pct")
            act = _get(actual, "section_11_4_efficacy", "secondary_orr_dcr", "by_arm", "Active", "orr_pct")
        elif key == "orr_placebo_pct":
            exp = _get(expected, "section_11_4_efficacy", "secondary_orr_dcr", "by_arm", "Placebo", "orr_pct")
            act = _get(actual, "section_11_4_efficacy", "secondary_orr_dcr", "by_arm", "Placebo", "orr_pct")
        elif key == "dcr_active_pct":
            exp = _get(expected, "section_11_4_efficacy", "secondary_orr_dcr", "by_arm", "Active", "dcr_pct")
            act = _get(actual, "section_11_4_efficacy", "secondary_orr_dcr", "by_arm", "Active", "dcr_pct")
        elif key == "disposition_n_completed_active":
            exp = _get(expected, "section_11_1_disposition", "by_arm", "Active", "n_completed")
            act = _get(actual, "section_11_1_disposition", "by_arm", "Active", "n_completed")
        elif key == "safety_n_any_ae_active":
            exp = _get(expected, "section_11_5_safety", "by_arm", "Active", "n_any_ae")
            act = _get(actual, "section_11_5_safety", "by_arm", "Active", "n_any_ae")
        elif key == "safety_pct_grade3_plus_active":
            exp = _get(expected, "section_11_5_safety", "by_arm", "Active", "pct_grade3_plus")
            act = _get(actual, "section_11_5_safety", "by_arm", "Active", "pct_grade3_plus")
        else:
            scores[key] = {"score": 0, "max": weight, "detail": "unknown criterion"}
            continue

        if exp is None or act is None:
            scores[key] = {"score": 0, "max": weight, "detail": f"missing: exp={exp}, act={act}"}
        else:
            diff = abs(act - exp)
            ok = diff <= tol
            scores[key] = {"score": weight if ok else 0, "max": weight,
                           "detail": f"exp={exp}, act={act}, diff={diff:.4f}, tol={tol}"}
    return scores


def score_structural(report_text):
    """Score structural section checks (20%)."""
    text_lower = report_text.lower()
    scores = {}
    total_weight = 0.20
    n = len(REQUIRED_SECTIONS)
    weight_per = total_weight / n
    for section_id, patterns in REQUIRED_SECTIONS:
        matches = sum(1 for p in patterns if p in text_lower)
        found = matches >= max(2, len(patterns) // 2)
        scores[section_id] = {
            "score": weight_per if found else (round(weight_per * 0.3, 4) if matches > 0 else 0),
            "max": weight_per,
            "detail": f"matches={matches}/{len(patterns)}, found={found}",
        }
    return scores


def score_concepts(report_text):
    """Score concept/keyword checks (20%)."""
    text_lower = report_text.lower()
    scores = {}
    for key, criterion in CONCEPT_CRITERIA.items():
        weight = criterion["weight"]
        kws = criterion["keywords"]
        min_matches = criterion["min_matches"]
        matches = sum(1 for kw in kws if kw.lower() in text_lower)
        if matches >= min_matches:
            scores[key] = {"score": weight, "max": weight, "detail": f"matches={matches}/{len(kws)}"}
        elif matches > 0:
            scores[key] = {"score": round(weight * 0.5, 4), "max": weight,
                           "detail": f"partial: matches={matches}/{len(kws)}"}
        else:
            scores[key] = {"score": 0, "max": weight, "detail": f"no matches: {kws}"}
    return scores


def generate_judge_prompt(ground_truth_json, agent_report):
    return LLM_JUDGE_PROMPT.format(ground_truth_json=ground_truth_json, agent_report=agent_report)


def score(expected_path, actual_path, report_doc_path=None, rubric_out=None):
    expected = json.loads(Path(expected_path).read_text())
    actual = json.loads(Path(actual_path).read_text())

    if report_doc_path:
        report_text = Path(report_doc_path).read_text()
    else:
        report_text = actual.get("report_text", json.dumps(actual, indent=2))

    num_scores = score_numerical(expected, actual)
    num_total = sum(s["score"] for s in num_scores.values())
    num_max = sum(s["max"] for s in num_scores.values())

    struct_scores = score_structural(report_text)
    struct_total = sum(s["score"] for s in struct_scores.values())
    struct_max = sum(s["max"] for s in struct_scores.values())

    concept_scores = score_concepts(report_text)
    concept_total = sum(s["score"] for s in concept_scores.values())
    concept_max = sum(s["max"] for s in concept_scores.values())

    judge_prompt = generate_judge_prompt(json.dumps(expected, indent=2), report_text)

    auto_score = num_total + struct_total + concept_total
    auto_max = num_max + struct_max + concept_max
    auto_pct = round(auto_score / auto_max, 4) if auto_max > 0 else 0

    result = {
        "tc_id": "TC-010",
        "scoring": {
            "numerical": {"scores": num_scores, "subtotal": round(num_total, 4), "max": round(num_max, 4)},
            "structural": {"scores": struct_scores, "subtotal": round(struct_total, 4), "max": round(struct_max, 4)},
            "concepts": {"scores": concept_scores, "subtotal": round(concept_total, 4), "max": round(concept_max, 4)},
            "llm_judge": {
                "weight": 0.30,
                "status": "pending",
                "prompt": judge_prompt,
                "note": "Run LLM-as-judge with the prompt above, then fill in qualitative scores.",
            },
            "auto_scored_total": round(auto_score, 4),
            "auto_scored_max": round(auto_max, 4),
            "auto_scored_pct": auto_pct,
        },
        "total_score_note": (
            f"Auto-scored: {auto_score:.4f}/{auto_max:.4f} ({auto_pct:.2%}). "
            f"LLM-judge portion (30%) pending. Total = auto_scored + llm_judge_score."
        ),
    }

    if rubric_out:
        Path(rubric_out).write_text(json.dumps(result, indent=2))
        print(f"Wrote scores to: {rubric_out}")
    else:
        print(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description="TC-010 CSR Statistical Sections Scorer")
    parser.add_argument("--expected", required=True, help="Path to ground truth JSON")
    parser.add_argument("--actual", required=True, help="Path to agent response JSON")
    parser.add_argument("--report-doc", type=str, default=None, help="Path to agent CSR text (optional)")
    parser.add_argument("--rubric-output", type=str, default=None, help="Output path for scores")
    args = parser.parse_args()
    score(args.expected, args.actual, args.report_doc, args.rubric_output)


if __name__ == "__main__":
    main()
