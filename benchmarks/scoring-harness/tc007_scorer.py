#!/usr/bin/env python3
"""tc007_scorer.py — TC-007 Level 3 Regulatory Response Scorer

Scores agent-generated regulatory response memos against the TC-007 expert rubric.

Scoring structure (100 points total):
  - Statistical Analysis (40%): ITT/PP comparison, tipping point, sensitivity
  - Regulatory Compliance (20%): ICH E9(R1) estimand, formatting, language
  - Communication (20%): clarity, structure, tables/figures
  - Judgment (10%): appropriate conclusion
  - Completeness (10%): all required elements present

Usage:
    python tc007_scorer.py --expected reference/tc007_ground_truth.json \\
        --actual agent-output/tc007_response.json \\
        [--rubric-output scores.json]

The scorer performs:
  1. Auto-scorable numerical checks (30%): ITT HR, PP HR, tipping point N
  2. Structural checks (20%): required sections present
  3. Keyword/concept checks (20%): ICH E9(R1), estimand, sensitivity, tipping point
  4. Qualitative rubric (30%): LLM-as-judge prompt template (or manual scoring)
"""

import argparse
import json
import re
import sys
from pathlib import Path


# ─── Auto-Scorable Numerical Checks (30%) ───

NUMERICAL_CRITERIA = {
    "itt_hr_correct": {
        "weight": 0.05,
        "description": "ITT HR reported correctly (within tolerance of ground truth)",
        "tolerance": 0.05,  # relative tolerance
    },
    "pp_hr_correct": {
        "weight": 0.05,
        "description": "PP HR reported correctly (within tolerance of ground truth)",
        "tolerance": 0.05,
    },
    "itt_significance_correct": {
        "weight": 0.03,
        "description": "ITT significance assessment matches ground truth",
    },
    "pp_significance_correct": {
        "weight": 0.03,
        "description": "PP significance assessment matches ground truth",
    },
    "tipping_point_n_correct": {
        "weight": 0.05,
        "description": "Tipping point N reported correctly (within ±2 of ground truth)",
        "tolerance": 2,
    },
    "exclusion_n_correct": {
        "weight": 0.03,
        "description": "Number of PP exclusions reported correctly",
        "tolerance": 2,
    },
    "exclusion_arm_split_correct": {
        "weight": 0.03,
        "description": "Exclusion split by arm reported correctly",
        "tolerance": 3,
    },
    "event_rate_disparity_correct": {
        "weight": 0.03,
        "description": "Event rate disparity between excluded and included noted",
    },
}


# ─── Structural Checks (20%) ───

REQUIRED_SECTIONS = [
    ("reviewer_comment", ["reviewer comment", "reviewer query", "regulatory question"]),
    ("background", ["background", "study description", "study overview"]),
    ("discrepancy_analysis", ["discrepancy", "analysis of discrepancy", "itt vs pp", "itt/pp"]),
    ("tipping_point", ["tipping point", "tipping-point", "how many events"]),
    ("sensitivity_analyses", ["sensitivity analysis", "sensitivity analyses", "sensitivity"]),
    ("conclusion", ["conclusion", "overall conclusion", "summary and conclusion"]),
    ("response_memo_format", ["dear", "response to", "re:", "regarding"]),
]


# ─── Concept/Keyword Checks (20%) ───

CONCEPT_CRITERIA = {
    "ich_e9_r1_estimand": {
        "weight": 0.04,
        "description": "ICH E9(R1) estimand framework referenced",
        "keywords": ["estimand", "ich e9", "e9(r1)", "intercurrent", "treatment effect"],
        "min_matches": 2,
    },
    "itt_principle": {
        "weight": 0.03,
        "description": "ITT principle correctly explained",
        "keywords": ["intention to treat", "itt", "randomized", "all randomized", "primary analysis"],
        "min_matches": 2,
    },
    "pp_definition": {
        "weight": 0.03,
        "description": "Per-protocol population correctly defined",
        "keywords": ["per protocol", "per-protocol", "protocol deviation", "pp population", "major deviation"],
        "min_matches": 2,
    },
    "tipping_point_concept": {
        "weight": 0.03,
        "description": "Tipping point analysis concept correctly described",
        "keywords": ["tipping point", "reclassify", "shift", "how many", "negate", "reverse conclusion"],
        "min_matches": 2,
    },
    "sensitivity_methods": {
        "weight": 0.03,
        "description": "Appropriate sensitivity methods mentioned",
        "keywords": ["multiple imputation", "pattern mixture", "worst case", "best case", "tipping point", "jump to reference"],
        "min_matches": 2,
    },
    "imbalance_assessment": {
        "weight": 0.02,
        "description": "Exclusion imbalance assessed",
        "keywords": ["imbalance", "fisher", "exclusion pattern", "differential", "asymmetric"],
        "min_matches": 1,
    },
    "regulatory_language": {
        "weight": 0.02,
        "description": "Appropriate regulatory language used",
        "keywords": ["robust", "consistent with", "support", "conclusion is maintained", "primary conclusion"],
        "min_matches": 2,
    },
}


# ─── LLM-as-Judge Prompt Template (30%) ───

LLM_JUDGE_PROMPT = """You are an expert biostatistician reviewing a regulatory response memo
addressing an ITT vs. per-protocol (PP) discrepancy in a Phase III oncology trial.

Score the following memo on a 0-5 scale for each criterion:

1. **Statistical Rigor (10 pts)**: Is the analysis of the ITT/PP discrepancy
   statistically sound? Is the tipping point analysis correctly performed and
   interpreted? Are sensitivity analyses appropriate?

2. **Regulatory Appropriateness (6 pts)**: Is the response structured per
   regulatory expectations? Is the language appropriate for an FDA/EMA submission?

3. **Communication Clarity (6 pts)**: Is the explanation clear and accessible
   to a non-statistician reviewer? Are tables/figures used effectively?

4. **Judgment (5 pts)**: Is the conclusion appropriate given the evidence?
   Does the memo correctly assess whether the primary conclusion is robust?

5. **Completeness (3 pts)**: Are all required elements present (reviewer comment,
   background, discrepancy analysis, tipping point, sensitivity, conclusion)?

Ground truth analysis results:
{ground_truth_json}

Agent response memo:
{agent_memo}

For each criterion, provide:
- Score (0-5)
- Rationale (1-2 sentences)

Output as JSON:
{{
  "statistical_rigor": {{"score": 0-5, "rationale": "..."}},
  "regulatory_appropriateness": {{"score": 0-5, "rationale": "..."}},
  "communication_clarity": {{"score": 0-5, "rationale": "..."}},
  "judgment": {{"score": 0-5, "rationale": "..."}},
  "completeness": {{"score": 0-5, "rationale": "..."}}
}}
"""


def score_numerical(expected, actual):
    """Score auto-scorable numerical criteria."""
    scores = {}
    exp_analysis = expected.get("analysis", {})
    act_analysis = actual.get("analysis", {})

    for key, criterion in NUMERICAL_CRITERIA.items():
        weight = criterion["weight"]
        tol = criterion.get("tolerance", 0.05)

        if key == "itt_hr_correct":
            exp_val = exp_analysis.get("itt", {}).get("hr")
            act_val = act_analysis.get("itt", {}).get("hr")
            if exp_val is not None and act_val is not None:
                rel_err = abs(act_val - exp_val) / max(abs(exp_val), 1e-10)
                scores[key] = {"score": weight if rel_err <= tol else 0,
                               "max": weight, "detail": f"exp={exp_val}, act={act_val}, rel_err={rel_err:.4f}"}
            else:
                scores[key] = {"score": 0, "max": weight, "detail": "missing value"}

        elif key == "pp_hr_correct":
            exp_val = exp_analysis.get("pp", {}).get("hr")
            act_val = act_analysis.get("pp", {}).get("hr")
            if exp_val is not None and act_val is not None:
                rel_err = abs(act_val - exp_val) / max(abs(exp_val), 1e-10)
                scores[key] = {"score": weight if rel_err <= tol else 0,
                               "max": weight, "detail": f"exp={exp_val}, act={act_val}, rel_err={rel_err:.4f}"}
            else:
                scores[key] = {"score": 0, "max": weight, "detail": "missing value"}

        elif key == "itt_significance_correct":
            exp_sig = exp_analysis.get("discrepancy", {}).get("itt_significant")
            act_sig = act_analysis.get("discrepancy", {}).get("itt_significant")
            scores[key] = {"score": weight if exp_sig == act_sig else 0,
                          "max": weight, "detail": f"exp={exp_sig}, act={act_sig}"}

        elif key == "pp_significance_correct":
            exp_sig = exp_analysis.get("discrepancy", {}).get("pp_significant")
            act_sig = act_analysis.get("discrepancy", {}).get("pp_significant")
            scores[key] = {"score": weight if exp_sig == act_sig else 0,
                          "max": weight, "detail": f"exp={exp_sig}, act={act_sig}"}

        elif key == "tipping_point_n_correct":
            exp_val = exp_analysis.get("tipping_point", {}).get("n_shifted")
            act_val = act_analysis.get("tipping_point", {}).get("n_shifted")
            if exp_val is not None and act_val is not None:
                diff = abs(act_val - exp_val)
                scores[key] = {"score": weight if diff <= tol else 0,
                               "max": weight, "detail": f"exp={exp_val}, act={act_val}, diff={diff}"}
            else:
                scores[key] = {"score": 0, "max": weight, "detail": "missing value"}

        elif key == "exclusion_n_correct":
            exp_val = exp_analysis.get("exclusion_pattern", {}).get("n_excluded")
            act_val = act_analysis.get("exclusion_pattern", {}).get("n_excluded")
            if exp_val is not None and act_val is not None:
                diff = abs(act_val - exp_val)
                scores[key] = {"score": weight if diff <= tol else 0,
                               "max": weight, "detail": f"exp={exp_val}, act={act_val}, diff={diff}"}
            else:
                scores[key] = {"score": 0, "max": weight, "detail": "missing value"}

        elif key == "exclusion_arm_split_correct":
            exp_a = exp_analysis.get("exclusion_pattern", {}).get("excluded_active", 0)
            act_a = act_analysis.get("exclusion_pattern", {}).get("excluded_active", 0)
            diff = abs(act_a - exp_a)
            scores[key] = {"score": weight if diff <= tol else 0,
                          "max": weight, "detail": f"exp_active={exp_a}, act_active={act_a}, diff={diff}"}

        elif key == "event_rate_disparity_correct":
            exp_excl = exp_analysis.get("exclusion_pattern", {}).get("event_rate_excluded", 0)
            exp_incl = exp_analysis.get("exclusion_pattern", {}).get("event_rate_included", 0)
            exp_diff = abs(exp_excl - exp_incl)
            act_excl = act_analysis.get("exclusion_pattern", {}).get("event_rate_excluded")
            act_incl = act_analysis.get("exclusion_pattern", {}).get("event_rate_included")
            if act_excl is not None and act_incl is not None:
                act_diff = abs(act_excl - act_incl)
                rel_err = abs(act_diff - exp_diff) / max(exp_diff, 1e-10)
                scores[key] = {"score": weight if rel_err <= 0.15 else 0,
                               "max": weight, "detail": f"exp_diff={exp_diff:.4f}, act_diff={act_diff:.4f}"}
            else:
                scores[key] = {"score": 0, "max": weight, "detail": "missing value"}

    return scores


def score_structural(memo_text):
    """Score structural checks (sections present)."""
    memo_lower = memo_text.lower()
    scores = {}
    total_weight = 0.20  # 20% for all structural checks
    n_sections = len(REQUIRED_SECTIONS)
    weight_per = total_weight / n_sections

    for section_id, patterns in REQUIRED_SECTIONS:
        found = any(p in memo_lower for p in patterns)
        scores[section_id] = {
            "score": weight_per if found else 0,
            "max": weight_per,
            "detail": f"found={found}, patterns={patterns}"
        }

    return scores


def score_concepts(memo_text):
    """Score concept/keyword checks."""
    memo_lower = memo_text.lower()
    scores = {}
    for key, criterion in CONCEPT_CRITERIA.items():
        weight = criterion["weight"]
        keywords = criterion["keywords"]
        min_matches = criterion["min_matches"]
        matches = sum(1 for kw in keywords if kw.lower() in memo_lower)
        if matches >= min_matches:
            scores[key] = {"score": weight, "max": weight, "detail": f"matches={matches}/{len(keywords)}"}
        elif matches > 0:
            scores[key] = {"score": weight * 0.5, "max": weight, "detail": f"partial: matches={matches}/{len(keywords)}"}
        else:
            scores[key] = {"score": 0, "max": weight, "detail": f"no matches: {keywords}"}

    return scores


def generate_judge_prompt(ground_truth_json, agent_memo):
    """Generate the LLM-as-judge prompt for qualitative scoring."""
    return LLM_JUDGE_PROMPT.format(
        ground_truth_json=ground_truth_json,
        agent_memo=agent_memo
    )


def score(expected_path, actual_path, memo_path=None, rubric_out=None):
    """Score TC-007 response."""
    expected = json.loads(Path(expected_path).read_text())
    actual = json.loads(Path(actual_path).read_text())

    # Get memo text from file or from actual JSON
    if memo_path:
        memo_text = Path(memo_path).read_text()
    else:
        memo_text = actual.get("memo_text", json.dumps(actual, indent=2))

    # Numerical checks (30%)
    num_scores = score_numerical(expected, actual)
    num_total = sum(s["score"] for s in num_scores.values())
    num_max = sum(s["max"] for s in num_scores.values())

    # Structural checks (20%)
    struct_scores = score_structural(memo_text)
    struct_total = sum(s["score"] for s in struct_scores.values())
    struct_max = sum(s["max"] for s in struct_scores.values())

    # Concept checks (20%)
    concept_scores = score_concepts(memo_text)
    concept_total = sum(s["score"] for s in concept_scores.values())
    concept_max = sum(s["max"] for s in concept_scores.values())

    # LLM judge (30%) — not auto-scored, generate prompt
    judge_prompt = generate_judge_prompt(
        json.dumps(expected, indent=2),
        memo_text
    )

    # Auto-scored portion
    auto_score = num_total + struct_total + concept_total
    auto_max = num_max + struct_max + concept_max
    auto_pct = round(auto_score / auto_max, 4) if auto_max > 0 else 0

    result = {
        "tc_id": "TC-007",
        "scoring": {
            "numerical": {"scores": num_scores, "subtotal": round(num_total, 4), "max": round(num_max, 4)},
            "structural": {"scores": struct_scores, "subtotal": round(struct_total, 4), "max": round(struct_max, 4)},
            "concepts": {"scores": concept_scores, "subtotal": round(concept_total, 4), "max": round(concept_max, 4)},
            "llm_judge": {
                "weight": 0.30,
                "status": "pending",
                "prompt": judge_prompt,
                "note": "Run LLM-as-judge with the prompt above, then fill in qualitative scores."
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
    parser = argparse.ArgumentParser(description="TC-007 Regulatory Response Scorer")
    parser.add_argument("--expected", required=True, help="Path to ground truth JSON")
    parser.add_argument("--actual", required=True, help="Path to agent response JSON")
    parser.add_argument("--memo", type=str, default=None, help="Path to agent memo text (optional)")
    parser.add_argument("--rubric-output", type=str, default=None, help="Output path for scores")
    args = parser.parse_args()

    score(args.expected, args.actual, args.memo, args.rubric_output)


if __name__ == "__main__":
    main()
