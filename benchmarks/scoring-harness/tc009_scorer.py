#!/usr/bin/env python3
"""tc009_scorer.py — TC-009 Level 3 Safety Signal Evaluation & DMC Report Scorer

Scores agent-generated DMC safety reports against the TC-009 expert rubric.

Scoring structure (100 points total):
  - Numerical (auto-scorable) (30%): AE counts, risk differences, Hy's Law / QTc /
    irAE / Grade 3+ counts, KM median, Cox HR, recommendation
  - Structural sections (20%): 8 required DMC report sections present
  - Concept/keyword checks (20%): Hy's Law, QTc, irAE, MGPS, exposure-adjusted,
    DMC recommendation, Cox/KM/log-rank
  - Qualitative rubric (30%): LLM-as-judge prompt template (or manual scoring)

Usage:
    python tc009_scorer.py --expected <ground_truth.json> --actual <agent-output.json> \\
        [--report-doc agent-dmc-report.md] [--rubric-output scores.json]

The scorer performs:
  1. Auto-scorable numerical checks (30%): counts, RDs, HR, median, recommendation
  2. Structural section checks (20%): required DMC report sections present
  3. Concept/keyword checks (20%): domain concepts present
  4. Qualitative rubric (30%): LLM-as-judge prompt template (manual/LLM scoring)
"""

import argparse
import json
import math
from pathlib import Path


# ─── Auto-Scorable Numerical Checks (30%) ───

NUMERICAL_CRITERIA = {
    "hys_law_active_count": {
        "weight": 0.05,
        "description": "Hy's Law case count (Active arm) within tolerance of ground truth",
        "tolerance": 2,  # ±2 subjects
    },
    "grade3_plus_risk_difference": {
        "weight": 0.05,
        "description": "Grade 3+ AE risk difference (Active − Placebo) within tolerance",
        "tolerance": 0.05,  # ±0.05 (5 percentage points)
    },
    "grade3_plus_active_count": {
        "weight": 0.03,
        "description": "Grade 3+ AE subject count (Active) within tolerance",
        "tolerance": 15,
    },
    "cox_hr_value": {
        "weight": 0.04,
        "description": "Cox PH hazard ratio (Active vs Placebo, time-to-first Grade 3+) within tolerance",
        "tolerance": 0.15,
    },
    "ttg3_median_active": {
        "weight": 0.04,
        "description": "Time-to-first Grade 3+ AE median (Active, days) within tolerance",
        "tolerance": 15,  # ±15 days
    },
    "irae_active_count": {
        "weight": 0.03,
        "description": "Immune-related AE (irAE) subject count (Active) within tolerance",
        "tolerance": 20,
    },
    "sae_active_count": {
        "weight": 0.03,
        "description": "SAE subject count (Active) within tolerance",
        "tolerance": 15,
    },
    "recommendation_correct": {
        "weight": 0.03,
        "description": "Overall DMC recommendation matches ground-truth action",
    },
}


# ─── Structural Section Checks (20%) ───

REQUIRED_SECTIONS = [
    ("ae_overview", ["ae overview", "adverse event overview", "overall ae", "any ae", "sae", "serious adverse event"]),
    ("exposure_adjusted", ["exposure-adjusted", "patient-year", "per 100 patient", "exposure adjusted", "incidence rate"]),
    ("grade3_plus_events", ["grade 3", "grade 3+", "grade >=3", "severe adverse", "high-grade"]),
    ("lab_abnormalities_hys_law", ["hy's law", "hepatotoxicity", "drug-induced liver", "dili", "alt", "ast", "bilirubin", "qtc"]),
    ("time_to_event", ["time-to-event", "time to event", "time-to-first", "kaplan-meier", "km", "log-rank", "cox"]),
    ("ae_special_interest", ["special interest", "irae", "immune-related", "immune related"]),
    ("signal_detection", ["signal detection", "disproportionality", "mgps", "empirical bayes", "ebgm", "pharmacovigilance"]),
    ("recommendation_dmc_action", ["recommendation", "dmc", "data monitoring", "continue", "modify", "pause", "monitoring plan"]),
]


# ─── Concept/Keyword Checks (20%) ───

CONCEPT_CRITERIA = {
    "hys_law_concept": {
        "weight": 0.03,
        "description": "Hy's Law (hepatotoxicity / DILI risk) correctly identified and interpreted",
        "keywords": ["hy's law", "hepatotoxicity", "drug-induced liver injury", "dili", "alt >3x", "ast >3x", "bilirubin >2x", "temple's corollary"],
        "min_matches": 2,
    },
    "qtc_concept": {
        "weight": 0.025,
        "description": "QTc prolongation cardiac risk correctly identified",
        "keywords": ["qtc", "qt prolongation", "cardiac", "ecg", "electrocardiogram", "ventricular repolarization", "torsades"],
        "min_matches": 2,
    },
    "irae_concept": {
        "weight": 0.025,
        "description": "Immune-related adverse events (irAEs) correctly identified",
        "keywords": ["immune-related", "irae", "immune-related adverse", "checkpoint", "immunotherapy", "autoimmune", "corticosteroid"],
        "min_matches": 2,
    },
    "signal_detection_concept": {
        "weight": 0.03,
        "description": "Statistical signal detection (disproportionality / MGPS) correctly applied",
        "keywords": ["empirical bayes", "mgps", "ebgm", "disproportionality", "signal detection", "observed vs expected", "reporting odds ratio"],
        "min_matches": 2,
    },
    "exposure_adjusted_concept": {
        "weight": 0.025,
        "description": "Exposure-adjusted AE incidence rates (per 100 patient-years) correctly computed",
        "keywords": ["patient-year", "patient years", "exposure-adjusted", "per 100", "incidence rate", "person-time", "py"],
        "min_matches": 2,
    },
    "dmc_recommendation_concept": {
        "weight": 0.03,
        "description": "DMC recommendation framework (continue/modify/pause) with totality-of-evidence rationale",
        "keywords": ["dmc", "data monitoring committee", "dsmb", "recommendation", "totality of evidence", "continue", "modify", "pause", "enhanced monitoring", "stopping rule"],
        "min_matches": 3,
    },
    "cox_km_concept": {
        "weight": 0.025,
        "description": "Time-to-event methods (Kaplan-Meier, log-rank, Cox PH) correctly applied",
        "keywords": ["kaplan-meier", "kaplan meier", "log-rank", "logrank", "cox proportional hazards", "cox ph", "hazard ratio", "median time"],
        "min_matches": 2,
    },
    "regulatory_safety_standards": {
        "weight": 0.01,
        "description": "Regulatory/safety reporting standards referenced (ICH, FDA, MedDRA)",
        "keywords": ["ich", "fda", "meddra", "ctcae", "naranjo", "good pharmacovigilance", "ich e2a", "ich e2d"],
        "min_matches": 1,
    },
}


# ─── LLM-as-Judge Prompt Template (30%) ───

LLM_JUDGE_PROMPT = """You are an expert biostatistician and pharmacovigilance reviewer serving on a Phase 3 oncology Data Monitoring Committee (DMC).
Review the following safety signal evaluation and DMC report for [Investigational Agent] vs Placebo.

Score the report on a 0-5 scale for each criterion:

1. **Signal Detection Rigor (8 pts)**: Are all 8 safety areas (AE overview, exposure-adjusted
   rates, Grade 3+ events, lab abnormalities/Hy's Law/QTc, time-to-first Grade 3+ AE,
   irAE, statistical signal detection/MGPS, and recommendation) covered with correct
   statistics? Are risk differences, Fisher exact p-values, and 95% CIs appropriately
   reported? Is the Hy's Law / DILI assessment clinically sound?

2. **Time-to-Event Analysis (6 pts)**: Is the time-to-first Grade 3+ AE analysis
   (Kaplan-Meier median, log-rank test, Cox proportional hazards HR + 95% CI) correctly
   performed and interpreted? Is the Active-vs-Placebo hazard ratio correctly estimated?

3. **Signal Detection Methodology (6 pts)**: Is the Empirical Bayes / MGPS (EBGM)
   disproportionality analysis correctly applied? Are the risk-difference signals
   (95% CI excludes 0) correctly identified? Is the threshold logic sound?

4. **Recommendation Appropriateness (6 pts)**: Is the overall DMC recommendation
   (Continue / Modify / Pause) appropriate given the totality of evidence? Are the
   recommended monitoring/mitigation actions (Hy's Law monitoring, ECG/QTc monitoring,
   irAE management guidelines) clinically appropriate and actionable?

5. **Communication Clarity (4 pts)**: Is the report clearly organized, with all required
   sections, appropriate tables, and accessible to DMC members and regulators?

Ground truth safety analysis:
{ground_truth_json}

Agent DMC report:
{agent_report}

For each criterion, provide:
- Score (0-5)
- Rationale (1-2 sentences)

Output as JSON:
{{
  "signal_detection_rigor": {{"score": 0-5, "rationale": "..."}},
  "time_to_event_analysis": {{"score": 0-5, "rationale": "..."}},
  "signal_detection_methodology": {{"score": 0-5, "rationale": "..."}},
  "recommendation_appropriateness": {{"score": 0-5, "rationale": "..."}},
  "communication_clarity": {{"score": 0-5, "rationale": "..."}}
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
        tol = criterion.get("tolerance", 0.05)

        if key == "hys_law_active_count":
            exp = _get(expected, "lab_abnormalities", "hys_law", "n_active")
            act = _get(actual, "lab_abnormalities", "hys_law", "n_active")
        elif key == "grade3_plus_risk_difference":
            exp = _get(expected, "grade3_plus", "risk_difference")
            act = _get(actual, "grade3_plus", "risk_difference")
        elif key == "grade3_plus_active_count":
            exp = _get(expected, "grade3_plus", "by_arm", "Active", "n")
            act = _get(actual, "grade3_plus", "by_arm", "Active", "n")
        elif key == "cox_hr_value":
            exp = _get(expected, "time_to_grade3", "cox_hr")
            act = _get(actual, "time_to_grade3", "cox_hr")
        elif key == "ttg3_median_active":
            exp = _get(expected, "time_to_grade3", "median_active", "median")
            act = _get(actual, "time_to_grade3", "median_active", "median")
        elif key == "irae_active_count":
            exp = _get(expected, "ae_special_interest", "irae", "n_active")
            act = _get(actual, "ae_special_interest", "irae", "n_active")
        elif key == "sae_active_count":
            exp = _get(expected, "ae_overview", "by_arm", "Active", "n_sae")
            act = _get(actual, "ae_overview", "by_arm", "Active", "n_sae")
        elif key == "recommendation_correct":
            exp = _get(expected, "recommendation", "overall")
            act = _get(actual, "recommendation", "overall")
            scores[key] = {"score": weight if (exp and act and exp == act) else 0,
                           "max": weight, "detail": f"exp={exp}, act={act}"}
            continue
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
        found = any(p in text_lower for p in patterns)
        scores[section_id] = {"score": weight_per if found else 0,
                              "max": weight_per,
                              "detail": f"found={found}, patterns={patterns}"}
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
            scores[key] = {"score": round(weight * 0.5, 4), "max": weight, "detail": f"partial: matches={matches}/{len(kws)}"}
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
        "tc_id": "TC-009",
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
    parser = argparse.ArgumentParser(description="TC-009 Safety Signal Evaluation & DMC Report Scorer")
    parser.add_argument("--expected", required=True, help="Path to ground truth JSON")
    parser.add_argument("--actual", required=True, help="Path to agent response JSON")
    parser.add_argument("--report-doc", type=str, default=None, help="Path to agent DMC report text (optional)")
    parser.add_argument("--rubric-output", type=str, default=None, help="Output path for scores")
    args = parser.parse_args()
    score(args.expected, args.actual, args.report_doc, args.rubric_output)


if __name__ == "__main__":
    main()
