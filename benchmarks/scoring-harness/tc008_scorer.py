#!/usr/bin/env python3
"""tc008_scorer.py — TC-008 Level 3 Dose-Finding Study Design Scorer

Scores agent-generated dose-finding study designs against the TC-008 expert rubric.

Scoring structure (100 points total):
  - Design Correctness (35%): method selection, BOIN boundaries, dose levels, stopping rules
  - Simulation OCs (30%): P(select MTD), E[DLTs], E[N], P(early stop)
  - Expansion Cohort (15%): RP2D identification, expansion design
  - Regulatory & Statistical Appropriateness (20%): DLT definition, ethics, sample size

Usage:
    python tc008_scorer.py --expected reference/tc008_ground_truth.json \\
        --actual agent-output/tc008_response.json \\
        [--design-doc agent-design.md] \\
        [--rubric-output scores.json]

The scorer performs:
  1. Auto-scorable numerical checks (30%): BOIN boundaries, OC metrics
  2. Design structure checks (20%): required design sections present
  3. Concept/keyword checks (20%): BOIN, DLT, MTD, simulation, OCs
  4. Qualitative rubric (30%): LLM-as-judge prompt template (or manual scoring)
"""

import argparse
import json
import re
import sys
from pathlib import Path


# ─── Auto-Scorable Numerical Checks (30%) ───

NUMERICAL_CRITERIA = {
    "escalation_boundary_correct": {
        "weight": 0.04,
        "description": "BOIN escalation boundary (lambda_e = phi/(1+phi)) correct",
        "tolerance": 0.01,  # absolute tolerance
    },
    "deescalation_boundary_correct": {
        "weight": 0.04,
        "description": "BOIN de-escalation boundary (lambda_d = phi/(1-phi)) correct",
        "tolerance": 0.01,
    },
    "n_doses_correct": {
        "weight": 0.02,
        "description": "Number of dose levels correct (5-7 range)",
        "tolerance": 2,
    },
    "target_dlt_rate_correct": {
        "weight": 0.03,
        "description": "Target DLT rate correct (within tolerance)",
        "tolerance": 0.05,
    },
    "prob_select_mtd_directional": {
        "weight": 0.05,
        "description": "P(select true MTD) is the highest among all doses",
    },
    "prob_select_mtd_value": {
        "weight": 0.04,
        "description": "P(select true MTD) within tolerance of ground truth",
        "tolerance": 0.10,  # ±0.10 absolute tolerance
    },
    "expected_dlts_correct": {
        "weight": 0.04,
        "description": "Expected number of DLTs within tolerance",
        "tolerance": 2.0,  # ±2 DLTs
    },
    "expected_sample_size_correct": {
        "weight": 0.04,
        "description": "Expected sample size within tolerance",
        "tolerance": 3.0,  # ±3 patients
    },
}


# ─── Design Structure Checks (20%) ───

REQUIRED_SECTIONS = [
    ("protocol_synopsis", ["protocol synopsis", "study title", "study design"]),
    ("dose_escalation_method", ["dose escalation method", "boin", "crm", "ewoc", "escalation method"]),
    ("dose_levels", ["dose level", "dose levels", "dose escalation table"]),
    ("stopping_rules", ["stopping rule", "stopping rules", "stopping criteria", "stop if"]),
    ("simulation_operating_characteristics", ["operating characteristic", "simulation", "oc", "probability of selecting"]),
    ("expansion_cohort", ["expansion cohort", "expansion", "rpd", "rp2d", "recommended phase 2"]),
    ("statistical_considerations", ["statistical consideration", "dlt definition", "sample size justification"]),
    ("references", ["reference", "references", "bibliography"]),
]


# ─── Concept/Keyword Checks (20%) ───

CONCEPT_CRITERIA = {
    "boin_method": {
        "weight": 0.04,
        "description": "BOIN method correctly identified and justified",
        "keywords": ["boin", "bayesian optimal interval", "optimal interval design"],
        "min_matches": 1,
    },
    "dlt_definition": {
        "weight": 0.03,
        "description": "Dose-limiting toxicity (DLT) properly defined",
        "keywords": ["dose limiting toxicity", "dlt", "grade 3", "grade 4", "cycle 1", "observation period"],
        "min_matches": 2,
    },
    "mtd_concept": {
        "weight": 0.03,
        "description": "Maximum tolerated dose (MTD) concept correctly used",
        "keywords": ["maximum tolerated dose", "mtd", "recommended phase 2 dose", "rp2d", "rpd"],
        "min_matches": 2,
    },
    "simulation_oc_concepts": {
        "weight": 0.03,
        "description": "Operating characteristics from simulation properly described",
        "keywords": ["operating characteristic", "probability of selecting", "expected number", "simulation", "simulated trial"],
        "min_matches": 2,
    },
    "cohort_design": {
        "weight": 0.03,
        "description": "Cohort-based escalation design described",
        "keywords": ["cohort", "cohort size", "escalation", "de-escalation", "enroll"],
        "min_matches": 2,
    },
    "safety_monitoring": {
        "weight": 0.02,
        "description": "Safety monitoring and stopping for toxicity mentioned",
        "keywords": ["safety monitoring", "stop", "toxic", "dsmb", "safety", "tolerability"],
        "min_matches": 2,
    },
    "regulatory_standards": {
        "weight": 0.02,
        "description": "Regulatory standards referenced (ICH, FDA)",
        "keywords": ["ich", "fda", "gcp", "declaration of helsinki", "good clinical practice"],
        "min_matches": 1,
    },
}


# ─── LLM-as-Judge Prompt Template (30%) ───

LLM_JUDGE_PROMPT = """You are an expert biostatistician specializing in early-phase oncology trial design.
Review the following Phase I dose-finding study design for [Investigational Agent].

Score the following design document on a 0-5 scale for each criterion:

1. **Statistical Design Rigor (10 pts)**: Is the BOIN (or alternative) dose-escalation
   method correctly specified and justified? Are the dose levels, DLT rates, and
   escalation/de-escalation boundaries appropriate? Are the stopping rules sound?

2. **Simulation Quality (8 pts)**: Are the operating characteristics from the simulation
   (P(select MTD), E[DLTs], E[N], P(early stop)) correctly computed and reported?
   Is the simulation methodology sound (adequate number of trials, proper seed)?

3. **Expansion Cohort Design (5 pts)**: Is the expansion cohort at the RP2D well-designed?
   Is the RP2D correctly identified from the simulation? Is the expansion cohort size
   and monitoring plan appropriate?

4. **Regulatory & Clinical Appropriateness (4 pts)**: Does the design adhere to ICH
   guidelines and FDA expectations for first-in-human oncology trials? Is the DLT
   definition clinically appropriate? Is the sample size justified?

5. **Communication Clarity (3 pts)**: Is the design document clearly written, well-
   organized, and accessible to clinical and regulatory reviewers?

Ground truth design and simulation results:
{ground_truth_json}

Agent design document:
{agent_design}

For each criterion, provide:
- Score (0-5)
- Rationale (1-2 sentences)

Output as JSON:
{{
  "statistical_design_rigor": {{"score": 0-5, "rationale": "..."}},
  "simulation_quality": {{"score": 0-5, "rationale": "..."}},
  "expansion_cohort_design": {{"score": 0-5, "rationale": "..."}},
  "regulatory_appropriateness": {{"score": 0-5, "rationale": "..."}},
  "communication_clarity": {{"score": 0-5, "rationale": "..."}}
}}
"""


def score_numerical(expected, actual):
    """Score auto-scorable numerical criteria."""
    scores = {}
    exp_design = expected.get("design", {})
    act_design = actual.get("design", {})
    exp_sim = expected.get("simulation", {}).get("operating_characteristics", {})
    act_sim = actual.get("simulation", {}).get("operating_characteristics", {})

    # True MTD index: dose with DLT rate closest to target from below
    exp_rates = exp_design.get("true_dlt_rates", [])
    target = exp_design.get("target_dlt_rate", 0.30)
    if exp_rates:
        mtd_idx = max((i for i, r in enumerate(exp_rates) if r <= target), default=0)
    else:
        mtd_idx = 0

    for key, criterion in NUMERICAL_CRITERIA.items():
        weight = criterion["weight"]
        tol = criterion.get("tolerance", 0.05)

        if key == "escalation_boundary_correct":
            exp_val = exp_design.get("escalation_boundary")
            act_val = act_design.get("escalation_boundary")
            if exp_val is not None and act_val is not None:
                diff = abs(act_val - exp_val)
                scores[key] = {"score": weight if diff <= tol else 0,
                               "max": weight, "detail": f"exp={exp_val}, act={act_val}, diff={diff:.6f}"}
            else:
                scores[key] = {"score": 0, "max": weight, "detail": "missing value"}

        elif key == "deescalation_boundary_correct":
            exp_val = exp_design.get("deescalation_boundary")
            act_val = act_design.get("deescalation_boundary")
            if exp_val is not None and act_val is not None:
                diff = abs(act_val - exp_val)
                scores[key] = {"score": weight if diff <= tol else 0,
                               "max": weight, "detail": f"exp={exp_val}, act={act_val}, diff={diff:.6f}"}
            else:
                scores[key] = {"score": 0, "max": weight, "detail": "missing value"}

        elif key == "n_doses_correct":
            exp_val = exp_design.get("n_doses")
            act_val = act_design.get("n_doses")
            if exp_val is not None and act_val is not None:
                diff = abs(act_val - exp_val)
                scores[key] = {"score": weight if diff <= tol else 0,
                               "max": weight, "detail": f"exp={exp_val}, act={act_val}, diff={diff}"}
            else:
                scores[key] = {"score": 0, "max": weight, "detail": "missing value"}

        elif key == "target_dlt_rate_correct":
            exp_val = exp_design.get("target_dlt_rate")
            act_val = act_design.get("target_dlt_rate")
            if exp_val is not None and act_val is not None:
                diff = abs(act_val - exp_val)
                scores[key] = {"score": weight if diff <= tol else 0,
                               "max": weight, "detail": f"exp={exp_val}, act={act_val}, diff={diff:.4f}"}
            else:
                scores[key] = {"score": 0, "max": weight, "detail": "missing value"}

        elif key == "prob_select_mtd_directional":
            act_probs = act_sim.get("prob_select_rpd", [])
            if act_probs and mtd_idx < len(act_probs):
                is_max = act_probs[mtd_idx] == max(act_probs)
                scores[key] = {"score": weight if is_max else 0,
                               "max": weight, "detail": f"MTD_idx={mtd_idx}, P={act_probs[mtd_idx]}, max={max(act_probs)}"}
            else:
                scores[key] = {"score": 0, "max": weight, "detail": "missing prob_select_rpd"}

        elif key == "prob_select_mtd_value":
            exp_probs = exp_sim.get("prob_select_rpd", [])
            act_probs = act_sim.get("prob_select_rpd", [])
            if exp_probs and act_probs and mtd_idx < len(exp_probs) and mtd_idx < len(act_probs):
                diff = abs(act_probs[mtd_idx] - exp_probs[mtd_idx])
                scores[key] = {"score": weight if diff <= tol else 0,
                               "max": weight, "detail": f"exp={exp_probs[mtd_idx]}, act={act_probs[mtd_idx]}, diff={diff:.4f}"}
            else:
                scores[key] = {"score": 0, "max": weight, "detail": "missing values"}

        elif key == "expected_dlts_correct":
            exp_val = exp_sim.get("expected_n_dlts")
            act_val = act_sim.get("expected_n_dlts")
            if exp_val is not None and act_val is not None:
                diff = abs(act_val - exp_val)
                scores[key] = {"score": weight if diff <= tol else 0,
                               "max": weight, "detail": f"exp={exp_val}, act={act_val}, diff={diff:.4f}"}
            else:
                scores[key] = {"score": 0, "max": weight, "detail": "missing value"}

        elif key == "expected_sample_size_correct":
            exp_val = exp_sim.get("expected_sample_size")
            act_val = act_sim.get("expected_sample_size")
            if exp_val is not None and act_val is not None:
                diff = abs(act_val - exp_val)
                scores[key] = {"score": weight if diff <= tol else 0,
                               "max": weight, "detail": f"exp={exp_val}, act={act_val}, diff={diff:.4f}"}
            else:
                scores[key] = {"score": 0, "max": weight, "detail": "missing value"}

    return scores


def score_structural(design_text):
    """Score structural checks (sections present)."""
    text_lower = design_text.lower()
    scores = {}
    total_weight = 0.20
    n_sections = len(REQUIRED_SECTIONS)
    weight_per = total_weight / n_sections

    for section_id, patterns in REQUIRED_SECTIONS:
        found = any(p in text_lower for p in patterns)
        scores[section_id] = {
            "score": weight_per if found else 0,
            "max": weight_per,
            "detail": f"found={found}, patterns={patterns}"
        }

    return scores


def score_concepts(design_text):
    """Score concept/keyword checks."""
    text_lower = design_text.lower()
    scores = {}
    for key, criterion in CONCEPT_CRITERIA.items():
        weight = criterion["weight"]
        keywords = criterion["keywords"]
        min_matches = criterion["min_matches"]
        matches = sum(1 for kw in keywords if kw.lower() in text_lower)
        if matches >= min_matches:
            scores[key] = {"score": weight, "max": weight, "detail": f"matches={matches}/{len(keywords)}"}
        elif matches > 0:
            scores[key] = {"score": weight * 0.5, "max": weight, "detail": f"partial: matches={matches}/{len(keywords)}"}
        else:
            scores[key] = {"score": 0, "max": weight, "detail": f"no matches: {keywords}"}

    return scores


def generate_judge_prompt(ground_truth_json, agent_design):
    """Generate the LLM-as-judge prompt for qualitative scoring."""
    return LLM_JUDGE_PROMPT.format(
        ground_truth_json=ground_truth_json,
        agent_design=agent_design
    )


def score(expected_path, actual_path, design_doc_path=None, rubric_out=None):
    """Score TC-008 response."""
    expected = json.loads(Path(expected_path).read_text())
    actual = json.loads(Path(actual_path).read_text())

    # Get design doc text from file or from actual JSON
    if design_doc_path:
        design_text = Path(design_doc_path).read_text()
    else:
        design_text = actual.get("design_text", json.dumps(actual, indent=2))

    # Numerical checks (30%)
    num_scores = score_numerical(expected, actual)
    num_total = sum(s["score"] for s in num_scores.values())
    num_max = sum(s["max"] for s in num_scores.values())

    # Structural checks (20%)
    struct_scores = score_structural(design_text)
    struct_total = sum(s["score"] for s in struct_scores.values())
    struct_max = sum(s["max"] for s in struct_scores.values())

    # Concept checks (20%)
    concept_scores = score_concepts(design_text)
    concept_total = sum(s["score"] for s in concept_scores.values())
    concept_max = sum(s["max"] for s in concept_scores.values())

    # LLM judge (30%) — not auto-scored, generate prompt
    judge_prompt = generate_judge_prompt(
        json.dumps(expected, indent=2),
        design_text
    )

    # Auto-scored portion
    auto_score = num_total + struct_total + concept_total
    auto_max = num_max + struct_max + concept_max
    auto_pct = round(auto_score / auto_max, 4) if auto_max > 0 else 0

    result = {
        "tc_id": "TC-008",
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
    parser = argparse.ArgumentParser(description="TC-008 Dose-Finding Study Design Scorer")
    parser.add_argument("--expected", required=True, help="Path to ground truth JSON")
    parser.add_argument("--actual", required=True, help="Path to agent response JSON")
    parser.add_argument("--design-doc", type=str, default=None, help="Path to agent design doc text (optional)")
    parser.add_argument("--rubric-output", type=str, default=None, help="Output path for scores")
    args = parser.parse_args()

    score(args.expected, args.actual, args.design_doc, args.rubric_output)


if __name__ == "__main__":
    main()
