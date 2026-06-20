#!/usr/bin/env python3
"""safety.py — Safety & Robustness Checks for the TFL Benchmark

Evaluates AI agent TFL outputs for:
  1. N-count consistency (intra-TFL and cross-TFL)
  2. Denominator/population correctness
  3. Cross-TFL data agreement
  4. Edge case resilience
  5. Output stability (repeated-run consistency)

Each check returns: {"passed": [rule_ids], "failed": [rule_ids], "score": float}
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml

# --------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------

def load_safety_rules(tc_id: str = None) -> dict:
    """Load safety check rules from safety.yaml."""
    rules_path = Path(__file__).parent / "safety.yaml"
    with open(rules_path) as f:
        all_rules = yaml.safe_load(f)
    if tc_id:
        return {"n_count": all_rules.get("n_count_rules", {}).get(tc_id, {}),
                "denominator": all_rules.get("denominator_rules", {}).get(tc_id, {}),
                "cross_pairs": all_rules.get("cross_tfl_pairs", []),
                "edge": all_rules.get("edge_case_expectations", {}),
                "weights": all_rules.get("scoring_weights", {})}
    return all_rules


# --------------------------------------------------------------------
# N-Count Consistency Checks
# --------------------------------------------------------------------

DENOM_RULES = {
    "TC-001": {"expected_pop": "ITT", "expected_flag": "ITTFL"},
    "TC-002": {"expected_pop": "SAFETY", "expected_flag": "SAFFL"},
    "TC-003": {"expected_pop": "ITT", "expected_flag": "ITTFL"},
    "TC-011": {"expected_pop": "SAFETY", "expected_flag": "SAFFL"},
    "TC-012": {"expected_pop": "ITT", "expected_flag": "ITTFL"},
    "TC-013": {"expected_pop": "ITT", "expected_flag": "ITTFL"},
    "TC-014": {"expected_pop": "SAFETY", "expected_flag": "SAFFL"},
}


def check_n_count_consistency(tfl_output: dict, tc_id: str = "TC-001") -> dict:
    """Check N-count consistency within a single TFL output.
    
    Validates:
      - n_events <= n_total (R-COUNT-05)
      - Arm-level N sums match overall N (R-COUNT-02)
      - Censored + events = N (R-COUNT-06)
    
    Returns: {"passed": [rule_ids], "failed": [rule_ids], "score": float}
    """
    rules = load_safety_rules(tc_id)
    n_rules = rules.get("n_count", {}).get("rules", [])

    n_total = tfl_output.get("n_total") or tfl_output.get("n")
    n_events = tfl_output.get("n_events")
    n_censored = tfl_output.get("n_censored")

    passed = []
    failed = []

    if n_total is not None and n_events is not None:
        if isinstance(n_events, (int, float)) and isinstance(n_total, (int, float)):
            if n_events <= n_total:
                passed.append("N-001_EVENTS_LE_TOTAL")
            else:
                failed.append("N-001_EVENTS_LE_TOTAL")
        else:
            failed.append("N-001_EVENTS_LE_TOTAL")

    # Censored + events = N
    if n_censored is not None and n_events is not None and n_total is not None:
        if isinstance(n_censored, (int, float)):
            if abs(n_censored + n_events - n_total) < 0.1:
                passed.append("N-002_CENSORED_EVENTS")
            else:
                failed.append("N-002_CENSORED_EVENTS")

    # Arm-level sums
    arms = tfl_output.get("by_arm", [])
    if arms and n_total is not None:
        arm_sum = sum(a.get("n", a.get("n_total", 0)) for a in arms if isinstance(a, dict))
        if abs(arm_sum - n_total) < 0.1:
            passed.append("N-003_ARM_SUM")
        else:
            failed.append("N-003_ARM_SUM")

    # Per-stratum N for TC-003
    strata = tfl_output.get("by_stratum", [])
    if strata and n_total is not None:
        stratum_sum = sum(s.get("n", s.get("n_total", 0)) for s in strata if isinstance(s, dict))
        if abs(stratum_sum - n_total) < 0.1:
            passed.append("N-004_STRATUM_SUM")
        else:
            failed.append("N-004_STRATUM_SUM")

    total = len(passed) + len(failed)
    score = round(len(passed) / max(total, 1), 4)

    return {"passed": passed, "failed": failed, "score": score}


# --------------------------------------------------------------------
# Denominator / Population Correctness
# --------------------------------------------------------------------

def check_denominator_consistency(tfl_output: dict, tc_id: str = "TC-001") -> dict:
    """Check that the agent used the correct population as denominator.
    
    Returns: {"passed": [rule_ids], "failed": [rule_ids], "score": float}
    """
    rule = DENOM_RULES.get(tc_id)
    if not rule:
        return {"passed": ["DENOM_SKIPPED"], "failed": [], "score": 1.0}

    passed = []
    failed = []

    actual_pop = (tfl_output.get("population", "") or "").upper()
    actual_flag = (tfl_output.get("population_flag", "") or "").upper()
    output_text = json.dumps(tfl_output).upper() if isinstance(tfl_output, dict) else str(tfl_output).upper()

    expected_pop = rule["expected_pop"]
    expected_flag = rule["expected_flag"]

    # Check population text
    pop_in_text = expected_pop in output_text
    flag_in_text = expected_flag in output_text

    if pop_in_text:
        passed.append(f"DENOM-POP-{expected_pop}")
    else:
        failed.append(f"DENOM-POP-{expected_pop}")

    if flag_in_text:
        passed.append(f"DENOM-FLAG-{expected_flag}")
    else:
        failed.append(f"DENOM-FLAG-{expected_flag}")

    # Specific check: expected flag value
    if expected_flag in actual_flag:
        passed.append(f"DENOM-FLAG-VAL-{expected_flag}")
    else:
        # Check via text
        val_pattern = expected_flag + r"\s*[=:]\s*['\"]?Y"
        import re
        if re.search(val_pattern, output_text):
            passed.append(f"DENOM-FLAG-VAL-{expected_flag}")
        else:
            failed.append(f"DENOM-FLAG-VAL-{expected_flag}")

    total = len(passed) + len(failed)
    score = round(len(passed) / max(total, 1), 4)

    return {"passed": passed, "failed": failed, "score": score}


# --------------------------------------------------------------------
# Cross-TFL Agreement
# --------------------------------------------------------------------

def check_cross_tfl_agreement(tfl_package: dict) -> dict:
    """Check shared statistics agree across multiple TFL outputs.
    
    Args:
        tfl_package: Dict keyed by test case ID with output dicts
    
    Returns: {"passed": [check_ids], "failed": [check_ids], "score": float,
              "discrepancies": [str]}
    """
    if not isinstance(tfl_package, dict) or len(tfl_package) < 2:
        return {"passed": ["CROSS_SKIPPED_too_few_TFLs"], "failed": [],
                "score": 1.0, "discrepancies": []}

    passed = []
    failed = []
    discrepancies = []
    
    rules = load_safety_rules(None)
    pairs = rules.get("cross_tfl_pairs", [])

    for pair in pairs:
        src = tfl_package.get(pair.get("source"))
        tgt = tfl_package.get(pair.get("target"))
        if not src or not tgt:
            continue

        for field in pair.get("shared_fields", []):
            sv = src.get(field)
            tv = tgt.get(field)
            if sv is not None and tv is not None:
                check_id = f"CROSS-{pair['source']}-{pair['target']}-{field}"
                if sv == tv:
                    passed.append(check_id)
                else:
                    failed.append(check_id)
                    discrepancies.append(
                        f"{check_id}: {pair['source']}.{field}={sv}"
                        f" != {pair['target']}.{field}={tv}"
                    )

    # Always check event count consistency between TC-001 and TC-003 if both present
    tc001 = tfl_package.get("TC-001", {})
    tc003 = tfl_package.get("TC-003", {})
    
    for field in ["n_events", "n_total"]:
        v1 = tc001.get(field)
        v3 = tc003.get(field)
        if v1 is not None and v3 is not None and v1 != v3:
            cid = f"CROSS-TC001-TC003-{field}"
            if cid not in failed:
                failed.append(cid)
                discrepancies.append(f"{cid}: TC-001.{field}={v1} != TC-003.{field}={v3}")

    total = len(passed) + len(failed)
    score = round(len(passed) / max(total, 1), 4)

    return {"passed": passed, "failed": failed, "score": score,
            "discrepancies": discrepancies}


# --------------------------------------------------------------------
# Edge Case Resilience
# --------------------------------------------------------------------

def check_edge_case_handling(tfl_output: dict, edge_case_id: str = None) -> dict:
    """Check that the agent handles edge cases gracefully.
    
    Args:
        tfl_output: Agent TFL output
        edge_case_id: Optional specific edge case ID (EC-001, EC-007, etc.)
    
    Returns: {"passed": [check_ids], "failed": [check_ids], "score": float}
    """
    output_text = json.dumps(tfl_output).upper() if isinstance(tfl_output, dict) else str(tfl_output).upper()
    passed = []
    failed = []

    # Check for crash indicators
    has_crashed = (
        "ERROR" in output_text
        or "TRACEBACK" in output_text
        or tfl_output.get("status") == "error"
        or tfl_output.get("error") is not None
    )

    if has_crashed:
        return {"passed": [], "failed": ["EDGE-CRASH"],
                "score": 0.0, "note": "Agent output contains error/crash indicators"}

    # Graceful handling signals
    has_warning = "WARNING" in output_text or "FLAG" in output_text
    handles_na = any(
        str(tfl_output.get(f, "")).upper() in ("NA", "N/A", "NE", "NONE", "NONE", "N/A (NOT ESTIMABLE)")
        for f in ["ci_upper", "median_pfs", "p_value", "ci_lower"]
    )

    if handles_na:
        passed.append("EDGE-NA_HANDLING")
        passed.append("EDGE-GRACEFUL")
    else:
        # If null/None but handled via Python None
        none_fields = sum(1 for f in ["ci_upper", "median_pfs"]
                         if tfl_output.get(f) is None)
        if none_fields > 0:
            passed.append("EDGE-NA_HANDLING")
            passed.append("EDGE-GRACEFUL")
        else:
            failed.append("EDGE-NA_HANDLING")

    if has_warning:
        passed.append("EDGE-WARNING")
    else:
        # Not required to have a warning, but bonus
        passed.append("EDGE-WARNING_OPTIONAL")

    # Summary: output should not be empty
    if tfl_output and not has_crashed:
        passed.append("EDGE-VALID_OUTPUT")
    else:
        failed.append("EDGE-VALID_OUTPUT")

    total = len(passed) + len(failed)
    score = round(len(passed) / max(total, 1), 4)

    return {"passed": passed, "failed": failed, "score": score}


# --------------------------------------------------------------------
# Output Stability (Repeated-Run)
# --------------------------------------------------------------------

def check_output_stability(run_1: dict, run_2: dict) -> dict:
    """Compare two run outputs for deterministic stability.
    
    Returns: {"passed": [field_names], "failed": [field_names],
              "score": float, "unstable": [str]}
    """
    NUMERIC_FIELDS = [
        "median_pfs", "ci_lower", "ci_upper",
        "n_events", "n_total", "n_censored",
        "chi_square", "p_value", "df",
        "mean", "std", "median", "min", "max"
    ]

    passed = []
    failed = []
    unstable = []

    for field in NUMERIC_FIELDS:
        v1 = run_1.get(field)
        v2 = run_2.get(field)
        if v1 is not None and v2 is not None:
            if v1 == v2:
                passed.append(f"STABLE-{field}")
            else:
                failed.append(f"STABLE-{field}")
                unstable.append(f"{field}: {v1} vs {v2}")

    # If same variant_id or seed, expect full determinism
    if run_1.get("variant_id") == run_2.get("variant_id"):
        seed_ok = run_1.get("seed") == run_2.get("seed")
        if not seed_ok:
            failed.append("STABLE-SEED_MISMATCH")

    total = len(passed) + len(failed)
    score = round(len(passed) / max(total, 1), 4)

    return {"passed": passed, "failed": failed, "score": score,
            "unstable_fields": unstable}


# --------------------------------------------------------------------
# Composite Safety Score
# --------------------------------------------------------------------

def compute_safety_score(tfl_output: dict, tc_id: str,
                         tfl_package: dict = None,
                         run_2: dict = None,
                         check_n: bool = True,
                         check_denom: bool = True,
                         check_cross: bool = False,
                         check_edge: bool = True,
                         check_stability: bool = False) -> dict:
    """Compute weighted composite safety & robustness score.
    
    Returns dict with:
      - n_count_consistency: dict
      - denominator_correctness: dict
      - cross_tfl_agreement: dict (only if tfl_package provided)
      - edge_case_handling: dict
      - output_stability: dict (only if run_2 provided)
      - total_safety_score: float
    """
    result = {"test_case_id": tc_id}

    # 1. N-count consistency
    if check_n:
        result["n_count_consistency"] = check_n_count_consistency(tfl_output, tc_id)
    else:
        result["n_count_consistency"] = {"passed": [], "failed": [], "score": None}

    # 2. Denominator correctness
    if check_denom:
        result["denominator_correctness"] = check_denominator_consistency(tfl_output, tc_id)
    else:
        result["denominator_correctness"] = {"passed": [], "failed": [], "score": None}

    # 3. Cross-TFL agreement
    if check_cross and tfl_package:
        result["cross_tfl_agreement"] = check_cross_tfl_agreement(tfl_package)
    else:
        result["cross_tfl_agreement"] = {"passed": ["CROSS_SKIPPED"],
                                          "failed": [], "score": None}

    # 4. Edge case handling
    if check_edge:
        result["edge_case_handling"] = check_edge_case_handling(tfl_output)
    else:
        result["edge_case_handling"] = {"passed": [], "failed": [], "score": None}

    # 5. Output stability
    if check_stability and run_2:
        result["output_stability"] = check_output_stability(tfl_output, run_2)
    else:
        result["output_stability"] = {"passed": [], "failed": [], "score": None}

    # Weighted composite
    weights = {
        "n_count_consistency": 0.30,
        "denominator_correctness": 0.35,
        "cross_tfl_agreement": 0.15,
        "edge_case_handling": 0.20,
        "output_stability": 0.00,  # Only if available
    }

    total_weight = 0
    weighted_sum = 0
    for key, weight in weights.items():
        component = result.get(key, {})
        score = component.get("score")
        if score is not None:
            weighted_sum += score * weight
            total_weight += weight

    result["total_safety_score"] = round(weighted_sum / max(total_weight, 1), 4)

    return result


# --------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TFL Benchmark — Safety & Robustness Checks")
    parser.add_argument("--tc", required=True, help="Test case ID (e.g., TC-001)")
    parser.add_argument("--output", required=True, help="Agent output JSON file")
    parser.add_argument("--package", help="TFL package JSON (for cross-TFL checks)")
    parser.add_argument("--run2", help="Second run output JSON (for stability check)")
    parser.add_argument("--check", nargs="+",
                        choices=["n", "denom", "cross", "edge", "stability", "all"],
                        default=["all"], help="Which checks to run")
    args = parser.parse_args()

    with open(args.output) as f:
        agent_output = json.load(f)

    tfl_package = None
    if args.package:
        with open(args.package) as f:
            tfl_package = json.load(f)

    run_2 = None
    if args.run2:
        with open(args.run2) as f:
            run_2 = json.load(f)

    checks = args.check
    if "all" in checks:
        checks = ["n", "denom", "cross", "edge", "stability"]

    result = compute_safety_score(
        agent_output, args.tc,
        tfl_package=tfl_package,
        run_2=run_2,
        check_n="n" in checks,
        check_denom="denom" in checks,
        check_cross="cross" in checks,
        check_edge="edge" in checks,
        check_stability="stability" in checks,
    )

    print("")
    print("=" * 60)
    print(f"  SAFETY & ROBUSTNESS REPORT — {args.tc}")
    print("=" * 60)
    print(f"  Total Safety Score: {result['total_safety_score']:.4f}")
    print("=" * 60)

    for component_name in ["n_count_consistency", "denominator_correctness",
                           "cross_tfl_agreement", "edge_case_handling",
                           "output_stability"]:
        data = result.get(component_name, {})
        score = data.get("score")
        if score is not None:
            pf = data.get("passed", [])
            ff = data.get("failed", [])
            status = "\u2705" if score >= 0.8 else "\u26a0\ufe0f" if score >= 0.5 else "\u274c"
            print(f"")
            print(f"  {status} {component_name}: {score:.4f} "
                  f"({len(pf)} passed, {len(ff)} failed)")
            for rid in pf:
                print(f"    \u2705 {rid}")
            for rid in ff:
                print(f"    \u274c {rid}")
            disc = data.get("discrepancies", data.get("unstable_fields", []))
            if disc:
                print(f"    \u26a0\ufe0f  Details:")
                for d in disc[:5]:
                    print(f"       {d}")
        else:
            print(f"")
            print(f"  \u2b1c {component_name}: skipped")

    print("")
    print("=" * 60)
    print("")
