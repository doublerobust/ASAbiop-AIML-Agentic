#!/usr/bin/env python3
"""TC-004 SAP Section Drafting — Auto-Scorer.

Scores agent-generated SAP sections against the TC-004 rubric.

Two scoring tiers:
1. Auto-scorable (40%): structural checks — section presence, keyword
   extraction, numeric validation, method count, subgroup count.
2. LLM-as-judge (40%): semantic evaluation via structured prompt.
   Human review (20%) is handled externally.

Usage:
    python tc004_scorer.py --expected reference/sap-reference.json \\
        --actual agent-output/sap-draft.json \\
        --judge-model gpt-4o

    python tc004_scorer.py --expected reference/sap-reference.json \\
        --actual agent-output/sap-draft.json
        # auto-score only (no LLM judge)
"""

import argparse
import json
import re
import sys
from pathlib import Path

# ─────────────────────────────────────────────────────
# TC-004 Auto-Scorable Rubric (40% of total)
# ─────────────────────────────────────────────────────

AUTO_CRITERIA = {
    "sections_present": {
        "weight": 0.08,
        "description": "All 7 required sections present",
        "required_sections": [
            "Analysis Population",
            "Primary Endpoint",   # also matches "Endpoint Definition"
            "Statistical Hypothesis",
            "Analysis Method",
            "Intercurrent Events",
            "Sensitivity",
            "Subgroup",
        ],
    },
    "estimand_5_attributes": {
        "weight": 0.08,
        "description": "ICH E9(R1) estimand with 5 attributes",
        "attributes": ["population", "variable", "intercurrent", "summary measure", "treatment"],
    },
    "hypothesis_stated": {
        "weight": 0.04,
        "description": "H₀ and H₁ correctly stated",
        "patterns": [r"H[₀0].*HR\s*=\s*1", r"H[₁1].*HR\s*≠\s*1", r"H[₁1].*HR\s*!=\s*1", r"null.*hypothesis.*HR\s*=\s*1", r"alternative.*hypothesis.*HR\s*≠\s*1"],
    },
    "alpha_power_match": {
        "weight": 0.04,
        "description": "Alpha=0.05 and power=90% match design spec",
        "alpha": 0.05,
        "power": 0.90,
    },
    "stratified_logrank": {
        "weight": 0.04,
        "description": "Stratified log-rank specified with correct strata",
        "keywords": ["stratified", "log-rank", "log rank"],
        "strata": ["PD-L1", "ECOG"],
    },
    "sensitivity_count": {
        "weight": 0.04,
        "description": "At least 2 sensitivity analyses listed",
        "min_count": 2,
    },
    "obf_alpha_spending": {
        "weight": 0.04,
        "description": "O'Brien-Fleming alpha spending function mentioned",
        "keywords": ["O'Brien-Fleming", "OBF", "O\u2019Brien-Fleming", "alpha spending"],
    },
    "subgroup_count": {
        "weight": 0.04,
        "description": "Subgroup analysis plan with ≥3 subgroups",
        "min_count": 3,
        "subgroup_keywords": ["PD-L1", "ECOG", "age", "sex", "histology", "region"],
    },
}


def _extract_text(obj):
    """Recursively extract all text from a JSON-like structure."""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, list):
        return " ".join(_extract_text(x) for x in obj)
    if isinstance(obj, dict):
        return " ".join(_extract_text(v) for v in obj.values())
    return str(obj)


def _flatten_sections(sections):
    """Normalize sections into a list of {title, content} dicts."""
    if isinstance(sections, list):
        return sections
    if isinstance(sections, dict):
        return [{"title": k, "content": v} for k, v in sections.items()]
    return []


def score_sections_present(full_text, sections):
    """Check all 7 required sections are present."""
    required = AUTO_CRITERIA["sections_present"]["required_sections"]
    found = 0
    for req in required:
        for sec in sections:
            title = sec.get("title", "") if isinstance(sec, dict) else str(sec)
            content = sec.get("content", "") if isinstance(sec, dict) else ""
            if req.lower() in title.lower() or req.lower() in content.lower():
                found += 1
                break
        else:
            if req.lower() in full_text.lower():
                found += 1
    score = found / len(required)
    details = {f"section_{req}": found > 0 for i, req in enumerate(required)
               for found in [sum(1 for s in sections
                                if isinstance(s, dict) and
                                (req.lower() in s.get("title", "").lower() or
                                 req.lower() in s.get("content", "").lower()))]}
    return score, {"sections_found": found, "sections_required": len(required)}


def score_estimand(full_text, estimand):
    """Check for 5 ICH E9(R1) estimand attributes."""
    attrs = AUTO_CRITERIA["estimand_5_attributes"]["attributes"]
    if isinstance(estimand, dict):
        # Direct key match
        found = sum(1 for a in attrs
                    if any(a.lower() in k.lower() for k in estimand.keys()))
        if found == 5:
            return 1.0, {"attributes_found": 5}
    # Fall back to text search
    found = sum(1 for a in attrs if a.lower() in full_text.lower())
    score = found / 5
    return score, {"attributes_found": found, "attributes_required": 5}


def score_hypothesis(full_text):
    """Check H₀ and H₁ are correctly stated."""
    patterns = AUTO_CRITERIA["hypothesis_stated"]["patterns"]
    found = 0
    for p in patterns:
        if re.search(p, full_text, re.IGNORECASE):
            found += 1
    score = found / len(patterns)
    return score, {"hypotheses_found": found}


def score_alpha_power(full_text, input_params):
    """Check alpha and power match design spec."""
    alpha = AUTO_CRITERIA["alpha_power_match"]["alpha"]
    power = AUTO_CRITERIA["alpha_power_match"]["power"]
    alpha_found = bool(re.search(r"alpha\s*[:=]\s*0\.05|α\s*=\s*0\.05|two.sided.*0\.05", full_text, re.IGNORECASE))
    power_found = bool(re.search(r"90\s*%|power\s*[:=]\s*0?\.?90|power\s*of\s*90|90\s*percent\s*power", full_text, re.IGNORECASE))
    score = (alpha_found + power_found) / 2
    return score, {"alpha_found": alpha_found, "power_found": power_found}


def score_stratified_logrank(full_text):
    """Check stratified log-rank with correct strata."""
    keywords = AUTO_CRITERIA["stratified_logrank"]["keywords"]
    strata = AUTO_CRITERIA["stratified_logrank"]["strata"]
    kw_found = sum(1 for k in keywords if k.lower() in full_text.lower())
    strata_found = sum(1 for s in strata if s.lower() in full_text.lower())
    score = (kw_found / len(keywords) + strata_found / len(strata)) / 2
    return score, {"keywords_found": kw_found, "strata_found": strata_found}


def score_sensitivity_count(full_text):
    """Count sensitivity analyses mentioned."""
    min_count = AUTO_CRITERIA["sensitivity_count"]["min_count"]
    # Look for "sensitivity" section and count listed analyses
    sens_keywords = [
        "unstratified", "per-protocol", "as-treated",
        "RMST", "restricted mean", "tipping point", "Cox",
        "bootstrap", "jackknife",
    ]
    found = sum(1 for k in sens_keywords if k.lower() in full_text.lower())
    score = min(found, min_count) / min_count
    return score, {"sensitivity_analyses_found": found}


def score_obf(full_text):
    """Check O'Brien-Fleming alpha spending function."""
    keywords = AUTO_CRITERIA["obf_alpha_spending"]["keywords"]
    found = any(k.lower() in full_text.lower() for k in keywords)
    score = 1.0 if found else 0.0
    return score, {"obf_found": found}


def score_subgroup_count(full_text):
    """Count pre-specified subgroups."""
    min_count = AUTO_CRITERIA["subgroup_count"]["min_count"]
    subgroup_keywords = AUTO_CRITERIA["subgroup_count"]["subgroup_keywords"]
    found = sum(1 for k in subgroup_keywords if k.lower() in full_text.lower())
    score = min(found, min_count) / min_count
    return score, {"subgroups_found": found}


def auto_score(actual_output):
    """Run all auto-scorable checks. Returns (score, details)."""
    full_text = _extract_text(actual_output)
    sections = _flatten_sections(actual_output.get("sections", actual_output))
    estimand = actual_output.get("estimand", {})

    results = {}
    total_score = 0.0

    checks = [
        ("sections_present", lambda: score_sections_present(full_text, sections)),
        ("estimand_5_attributes", lambda: score_estimand(full_text, estimand)),
        ("hypothesis_stated", lambda: score_hypothesis(full_text)),
        ("alpha_power_match", lambda: score_alpha_power(full_text, actual_output)),
        ("stratified_logrank", lambda: score_stratified_logrank(full_text)),
        ("sensitivity_count", lambda: score_sensitivity_count(full_text)),
        ("obf_alpha_spending", lambda: score_obf(full_text)),
        ("subgroup_count", lambda: score_subgroup_count(full_text)),
    ]

    for name, fn in checks:
        s, d = fn()
        weight = AUTO_CRITERIA[name]["weight"]
        results[name] = {"score": s, "weight": weight, "details": d}
        total_score += s * weight

    # Auto-score is out of 40% — normalize to 0-1 for the auto portion
    auto_weight_sum = sum(AUTO_CRITERIA[k]["weight"] for k in AUTO_CRITERIA)
    normalized = total_score / auto_weight_sum if auto_weight_sum > 0 else 0

    return {
        "auto_score": round(total_score, 4),
        "auto_score_normalized": round(normalized, 4),
        "auto_weight": auto_weight_sum,
        "criteria": results,
    }


# ─────────────────────────────────────────────────────
# LLM-as-Judge Prompt Template (40% of total)
# ─────────────────────────────────────────────────────

LLM_JUDGE_PROMPT = """You are an expert biostatistician evaluating a draft SAP "Primary Efficacy Analysis" section for a Phase 3 oncology trial. Score each criterion on a 0-1 scale with 0.1 increments. Be strict — this is a regulatory document.

## Trial Design Context
- Indication: {indication}
- Primary Endpoint: {endpoint}
- Design: 1:1 randomization, superiority
- Sample Size: {sample_size}
- Target HR: {target_hr}
- Alpha: 0.05 (two-sided), Power: 90%
- Group Sequential: O'Brien-Fleming
- Stratification: {stratification}
- Primary Method: Stratified log-rank test

## Agent Output (SAP Draft)
{agent_output}

## Scoring Criteria

### Criterion 1: ITT Population Definition (weight: 4%)
- 1.0: ITT defined as all randomized subjects, handling of discontinuations clearly described
- 0.5: ITT mentioned but discontinuation handling incomplete
- 0.0: ITT not defined or incorrect

### Criterion 2: Intercurrent Events Strategy (weight: 6%)
- 1.0: Treatment switching, death, loss to follow-up all addressed with ITT principle
- 0.5: Some intercurrent events addressed but not all
- 0.0: Intercurrent events not discussed

### Criterion 3: Estimand Attributes per ICH E9(R1) (weight: 6%)
- 1.0: All 5 attributes (population, variable, intercurrent events, summary measure, treatment) correctly mapped
- 0.5: 3-4 attributes present
- 0.0: <3 attributes or incorrect mapping

### Criterion 4: Statistical Reasoning (weight: 6%)
- 1.0: Method choice justified, assumptions stated (PH, independent censoring), appropriate
- 0.5: Method stated but reasoning incomplete
- 0.0: Incorrect method or no reasoning

### Criterion 5: Sensitivity Analysis Justification (weight: 4%)
- 1.0: Sensitivity analyses appropriate, justify primary, address departures from assumptions
- 0.5: Sensitivity analyses listed but not justified
- 0.0: No sensitivity analyses or inappropriate choices

### Criterion 6: Multiplicity Control (weight: 4%)
- 1.0: Multiplicity for secondary endpoints addressed (hierarchical, Hochberg, etc.)
- 0.5: Mentioned but strategy unclear
- 0.0: Not addressed

### Criterion 7: Sample Size / Futility (weight: 4%)
- 1.0: Sample size justification and interim futility boundaries discussed
- 0.5: One of two discussed
- 0.0: Neither discussed

### Criterion 8: ICH E9/E9(R1) Terminology (weight: 6%)
- 1.0: Correct and consistent use of ICH E9(R1) terms (estimand, intercurrent events, treatment policy strategy, etc.)
- 0.5: Some correct usage but inconsistent
- 0.0: Pre-E9(R1) terminology or incorrect usage

## Output Format
Return a JSON object with the following structure:
```json
{{
  "scores": {{
    "itt_population": {{"score": 0.0, "rationale": "..."}},
    "intercurrent_events": {{"score": 0.0, "rationale": "..."}},
    "estimand_attributes": {{"score": 0.0, "rationale": "..."}},
    "statistical_reasoning": {{"score": 0.0, "rationale": "..."}},
    "sensitivity_justification": {{"score": 0.0, "rationale": "..."}},
    "multiplicity_control": {{"score": 0.0, "rationale": "..."}},
    "sample_size_futility": {{"score": 0.0, "rationale": "..."}},
    "e9_terminology": {{"score": 0.0, "rationale": "..."}}
  }},
  "overall_llm_score": 0.0,
  "overall_assessment": "..."
}}
```
"""


def build_judge_prompt(actual_output, input_params=None):
    """Build the LLM judge prompt for TC-004."""
    params = input_params or {}
    agent_text = json.dumps(actual_output, indent=2) if isinstance(actual_output, dict) else str(actual_output)
    return LLM_JUDGE_PROMPT.format(
        indication=params.get("indication", "First-line metastatic NSCLC"),
        endpoint=params.get("endpoint", "Overall survival (OS)"),
        sample_size=params.get("sample_size", 600),
        target_hr=params.get("target_hr", 0.75),
        stratification=", ".join(params.get("stratification", ["PD-L1", "ECOG"])),
        agent_output=agent_text,
    )


def score_tc004(actual_output, expected_output=None, input_params=None,
                judge_callback=None):
    """Full TC-004 scoring: auto + optional LLM judge.

    Args:
        actual_output: Agent's SAP draft (dict with 'sections' and optionally 'estimand')
        expected_output: Reference SAP (not used for auto-score; for LLM judge context)
        input_params: Trial design parameters for the prompt
        judge_callback: Callable(prompt_str) -> dict with LLM judge response

    Returns:
        dict with total_score, auto_score, llm_judge_score (if judge provided)
    """
    auto_result = auto_score(actual_output)

    result = {
        "test_case_id": "TC-004",
        "auto_score": auto_result["auto_score"],
        "auto_score_normalized": auto_result["auto_score_normalized"],
        "auto_criteria": auto_result["criteria"],
    }

    if judge_callback is not None:
        prompt = build_judge_prompt(actual_output, input_params)
        try:
            judge_result = judge_callback(prompt)
            llm_score = judge_result.get("overall_llm_score", 0.0)
            llm_weight = 0.40
            auto_weight = 0.40
            human_weight = 0.20

            result["llm_judge_score"] = round(llm_score, 4)
            result["llm_judge_details"] = judge_result.get("scores", {})

            # Total without human review (auto + LLM only, rescaled to 0-1)
            auto_contribution = auto_result["auto_score"]  # already weighted at 0.40 max
            llm_contribution = llm_score * llm_weight
            partial_total = auto_contribution + llm_contribution
            partial_max = auto_weight + llm_weight

            result["partial_score"] = round(partial_total / partial_max, 4)
            result["partial_score_note"] = "Auto + LLM only; human review (20%) not included"
        except Exception as e:
            result["llm_judge_error"] = str(e)
            result["partial_score"] = round(auto_result["auto_score"] / 0.40, 4)
    else:
        result["partial_score"] = round(auto_result["auto_score"] / 0.40, 4)
        result["partial_score_note"] = "Auto-score only; LLM judge and human review not included"

    return result


# ─────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="TC-004 SAP Drafting Scorer")
    parser.add_argument("--actual", required=True, help="Path to agent SAP output JSON")
    parser.add_argument("--expected", default=None, help="Path to reference SAP JSON")
    parser.add_argument("--input-params", default=None, help="Path to trial design params JSON")
    parser.add_argument("--judge-model", default=None,
                        help="LLM model for judge (e.g., gpt-4o). If omitted, auto-score only.")
    parser.add_argument("--output", default=None, help="Output path for score JSON")
    args = parser.parse_args()

    with open(args.actual) as f:
        actual_output = json.load(f)

    input_params = None
    if args.input_params:
        with open(args.input_params) as f:
            input_params = json.load(f)

    # LLM judge callback (placeholder — wire to actual LLM API)
    judge_callback = None
    if args.judge_model:
        def judge_callback(prompt):
            # Placeholder: integrate with OpenAI/Anthropic API
            # For now, return a default neutral score
            print(f"[LLM Judge] Model: {args.judge_model}", file=sys.stderr)
            print(f"[LLM Judge] Prompt length: {len(prompt)} chars", file=sys.stderr)
            print("[LLM Judge] NOTE: API integration not yet configured. Returning default scores.", file=sys.stderr)
            return {
                "scores": {
                    "itt_population": {"score": 0.0, "rationale": "LLM judge not configured"},
                    "intercurrent_events": {"score": 0.0, "rationale": "LLM judge not configured"},
                    "estimand_attributes": {"score": 0.0, "rationale": "LLM judge not configured"},
                    "statistical_reasoning": {"score": 0.0, "rationale": "LLM judge not configured"},
                    "sensitivity_justification": {"score": 0.0, "rationale": "LLM judge not configured"},
                    "multiplicity_control": {"score": 0.0, "rationale": "LLM judge not configured"},
                    "sample_size_futility": {"score": 0.0, "rationale": "LLM judge not configured"},
                    "e9_terminology": {"score": 0.0, "rationale": "LLM judge not configured"},
                },
                "overall_llm_score": 0.0,
                "overall_assessment": "LLM judge API not yet configured",
            }

    result = score_tc004(actual_output, input_params=input_params,
                         judge_callback=judge_callback)

    output_json = json.dumps(result, indent=2)
    if args.output:
        Path(args.output).write_text(output_json)
        print(f"TC-004 score written to {args.output}")
    else:
        print(output_json)


if __name__ == "__main__":
    main()
