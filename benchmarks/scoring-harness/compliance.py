#!/usr/bin/env python3
"""compliance.py — Regulatory Compliance Checks for the TFL Benchmark

Evaluates AI agent TFL outputs against:
  1. ADaM variable mapping correctness (check_adam_compliance)
  2. FDA Study Data TCG v6.0 checklist items (check_tcg_compliance)
  3. ICH E3 CSR appendix formatting requirements (check_csr_formatting)

Each check returns: {"passed": [rule_ids], "failed": [rule_ids], "score": float}
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml

# --------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------

def load_compliance_rules(tc_id: str = None) -> dict:
    """Load compliance rule specifications from compliance.yaml."""
    rules_path = Path(__file__).parent / "compliance.yaml"
    with open(rules_path) as f:
        all_rules = yaml.safe_load(f)
    if tc_id:
        return all_rules.get(tc_id, {})
    return all_rules


def load_tolerances():
    """Load numerical tolerance specs (shared with score.py)."""
    tol_path = Path(__file__).parent / "tolerances.yaml"
    with open(tol_path) as f:
        return yaml.safe_load(f)


# --------------------------------------------------------------------
# ADaM Variable Mapping Checks
# --------------------------------------------------------------------

def check_adam_compliance(output: dict, tc_id: str = "TC-001") -> dict:
    """Check ADaM variable mapping compliance for a test case.

    Validates:
      - Required variables are present
      - Population flag is correct (ITTFL/SAFFL = Y)
      - Treatment variable is correct (TRT01PN)
      - Censoring variable (CNSR = 0/1)
      - Strata variables present if applicable

    Returns: {"passed": [rule_ids], "failed": [rule_ids], "score": float}
    """
    rules = load_compliance_rules(tc_id)
    if not rules:
        return {"passed": [], "failed": ["no_rules"], "score": 0.0}

    adam_mapping = rules.get("adam_mapping", {})
    required_vars = adam_mapping.get("required_variables", [])
    population_flag = adam_mapping.get("population_flag")
    population_value = adam_mapping.get("population_value")
    treatment_var = adam_mapping.get("treatment_variable")
    strata_vars = adam_mapping.get("strata_variables", [])

    passed = []
    failed = []

    # Extract variables used from the output
    variables_used = set()
    if "adam_variables" in output:
        variables_used = set(v.upper() for v in output["adam_variables"])
    elif "variables" in output:
        variables_used = set(v.upper() for v in output["variables"])
    else:
        # Scan text fields
        text_fields = [
            str(output.get(k, "")) for k in
            ["description", "method", "method_description", "analysis_description", "population"]
        ]
        combined = " ".join(text_fields).upper()
        for var in required_vars:
            if var.upper() in combined:
                variables_used.add(var.upper())

    # Check required variables present
    for var in required_vars:
        var_upper = var.upper()
        if var_upper in variables_used:
            passed.append("ADAM-" + var_upper)
        else:
            # Also check if variable name appears directly in output keys
            if var_upper in [k.upper() for k in output.keys()]:
                variables_used.add(var_upper)
                passed.append("ADAM-" + var_upper)
            else:
                failed.append("ADAM-" + var_upper)

    # Check population flag
    if population_flag and population_value:
        pop_ok = _check_population_filter(output, population_flag, population_value)
        pop_rule_id = "ADAM-POP-" + population_flag.upper()
        if pop_ok:
            passed.append(pop_rule_id)
        else:
            failed.append(pop_rule_id)

    # Check treatment variable
    if treatment_var:
        tv_upper = treatment_var.upper()
        if tv_upper in variables_used or any(tv_upper in k.upper() for k in output.keys()):
            passed.append("ADAM-TRT-" + tv_upper)
        else:
            failed.append("ADAM-TRT-" + tv_upper)

    # Check CNSR values 0/1
    if "CNSR" in required_vars or "CNSR" in variables_used:
        if "cnsr_values" in output or "cnsr_valid" in output:
            passed.append("ADAM-CNSR-VALID")
        else:
            text = str(output).upper()
            if "CNSR=0" in text or "CNSR=1" in text or "0=EVENT" in text or "1=CENSOR" in text:
                passed.append("ADAM-CNSR-VALID")
            else:
                failed.append("ADAM-CNSR-VALID")

    # Check strata variables for TC-003
    if strata_vars:
        for sv in strata_vars:
            sv_upper = sv.upper()
            if sv_upper in variables_used:
                passed.append("ADAM-STRATA-" + sv_upper)
            else:
                failed.append("ADAM-STRATA-" + sv_upper)

    total = len(passed) + len(failed)
    score = round(len(passed) / total, 4) if total > 0 else 1.0

    return {
        "passed": passed,
        "failed": failed,
        "score": score
    }


def _check_population_filter(output: dict, flag: str, expected_value: str) -> bool:
    """Check that the correct population filter was applied."""
    pop_text = str(output.get("population", "")).upper()
    flag_upper = flag.upper()
    val_upper = expected_value.upper()

    if "population_flag" in output and "population_value" in output:
        return (
            output["population_flag"].upper() == flag_upper
            and str(output["population_value"]).upper() == val_upper
        )

    # Check using regex patterns
    patterns = [
        flag_upper + r"\s*=\s*['\"]?" + val_upper,
        flag_upper + r"\s*[:=]\s*" + val_upper,
        "population.*" + flag_upper,
    ]
    for pat in patterns:
        if re.search(pat, pop_text, re.IGNORECASE):
            return True

    filter_text = str(output.get("filter_description", "")).upper()
    if flag_upper in filter_text and val_upper in filter_text:
        return True

    return False


# --------------------------------------------------------------------
# FDA Study Data TCG v6.0 Checklist
# --------------------------------------------------------------------

TCG_RULES_REGISTRY = [
    {"id": "TCG-01", "check_fn": lambda o: "population" in str(o).lower() or "ittfl" in str(o).lower() or "saffl" in str(o).lower()},
    {"id": "TCG-02", "check_fn": lambda o: "trt01pn" in str(o).lower() or "trt01p" in str(o).lower()},
    {"id": "TCG-03", "check_fn": lambda o: "cnsr" in str(o).lower() or ("event" in str(o).lower() and "censor" in str(o).lower())},
    {"id": "TCG-04", "check_fn": lambda o: "aval" in str(o).lower()},
    {"id": "TCG-05", "check_fn": lambda o: "method" in str(o).lower() or "method_description" in o},
    {"id": "TCG-06", "check_fn": lambda o: "software_version" in o or "software" in o or "version" in str(o).lower()},
]

TCG_RULES_BY_ID = {r["id"]: r for r in TCG_RULES_REGISTRY}


def check_tcg_compliance(output: dict, tc_id: str = "TC-001") -> dict:
    """Check FDA Study Data TCG compliance for a test case.

    Validates:
      - Population filter
      - Treatment variable
      - Event/censoring handling
      - Analysis time variable
      - Statistical method documented
      - Software version documented

    Returns: {"passed": [rule_ids], "failed": [rule_ids], "score": float}
    """
    rules = load_compliance_rules(tc_id)
    if not rules:
        return {"passed": [], "failed": ["no_rules"], "score": 0.0}

    tcg_rules = rules.get("tcg_rules", [])
    passed = []
    failed = []

    for rule in tcg_rules:
        rule_id = rule.get("id", "")
        if not rule_id:
            continue
        rule_def = TCG_RULES_BY_ID.get(rule_id)
        if rule_def:
            try:
                passing = rule_def["check_fn"](output)
            except Exception:
                passing = False
            if passing:
                passed.append(rule_id)
            else:
                failed.append(rule_id)
        else:
            failed.append(rule_id)

    score = round(len(passed) / (len(passed) + len(failed)), 4) if (len(passed) + len(failed)) > 0 else 1.0

    return {
        "passed": passed,
        "failed": failed,
        "score": score
    }


# --------------------------------------------------------------------
# ICH E3 CSR Appendix Formatting Checks
# --------------------------------------------------------------------

CSR_RULES_REGISTRY = [
    {"id": "CSR-01", "check_fn": lambda o: bool(re.search(r"Table\s+\d{2,3}-\d+", str(o), re.IGNORECASE))},
    {"id": "CSR-02", "check_fn": lambda o: bool(re.search(r"population|ITT|SAFETY|PP", str(o), re.IGNORECASE))},
    {"id": "CSR-03", "check_fn": lambda o: "footnote" in str(o).lower() or "footnotes" in str(o).lower()},
    {"id": "CSR-04", "check_fn": lambda o: "p_value_type" in o or "sided" in str(o).lower() or "two-sided" in str(o).lower()},
    {"id": "CSR-05", "check_fn": lambda o: "ci_method" in o or "conf_method" in o or "log-log" in str(o).lower() or "confidence interval" in str(o).lower()},
]

CSR_RULES_BY_ID = {r["id"]: r for r in CSR_RULES_REGISTRY}


def check_csr_formatting(output: dict, tc_id: str = "TC-001") -> dict:
    """Check ICH E3 CSR appendix formatting compliance for a test case.

    Validates:
      - Table numbering
      - Title includes population/endpoint
      - Footnotes documented
      - p-value type documented
      - CI method documented

    Returns: {"passed": [rule_ids], "failed": [rule_ids], "score": float}
    """
    rules = load_compliance_rules(tc_id)
    if not rules:
        return {"passed": [], "failed": ["no_rules"], "score": 0.0}

    csr_rules = rules.get("csr_rules", [])
    passed = []
    failed = []

    output_text = json.dumps(output) if isinstance(output, dict) else str(output)

    for rule in csr_rules:
        rule_id = rule.get("id", "")
        if not rule_id:
            continue
        rule_def = CSR_RULES_BY_ID.get(rule_id)
        if rule_def:
            try:
                passing = rule_def["check_fn"](output)
                if not passing:
                    passing = rule_def["check_fn"]({"_text": output_text})
            except Exception:
                passing = False
            if passing:
                passed.append(rule_id)
            else:
                failed.append(rule_id)
        else:
            failed.append(rule_id)

    score = round(len(passed) / (len(passed) + len(failed)), 4) if (len(passed) + len(failed)) > 0 else 1.0

    return {
        "passed": passed,
        "failed": failed,
        "score": score
    }


# --------------------------------------------------------------------
# Composite Compliance Score (exported)
# --------------------------------------------------------------------

def compute_compliance_score(output: dict, tc_id: str,
                             check_adam: bool = True,
                             check_tcg: bool = True,
                             check_csr: bool = False) -> dict:
    """Compute a weighted composite compliance score for a test case output.

    Returns dict with:
      - adam_compliance: dict of checks/pass/score
      - tcg_compliance: dict of checks/pass/score
      - csr_compliance: dict of checks/pass/score
      - total_compliance_score: float 0-1
    """
    result = {
        "test_case_id": tc_id,
    }

    # 1. ADaM mapping
    if check_adam:
        result["adam_compliance"] = check_adam_compliance(output, tc_id)
    else:
        result["adam_compliance"] = {"passed": [], "failed": [], "score": None}

    # 2. FDA TCG checklist
    if check_tcg:
        result["tcg_compliance"] = check_tcg_compliance(output, tc_id)
    else:
        result["tcg_compliance"] = {"passed": [], "failed": [], "score": None}

    # 3. ICH E3 CSR formatting
    if check_csr:
        result["csr_compliance"] = check_csr_formatting(output, tc_id)
    else:
        result["csr_compliance"] = {"passed": [], "failed": [], "score": None}

    # Weighted composite
    weights = {
        "adam_compliance": 0.40,
        "tcg_compliance": 0.35,
        "csr_compliance": 0.25,
    }

    total_weight = 0
    weighted_sum = 0
    for key, weight in weights.items():
        component = result.get(key, {})
        score = component.get("score")
        if score is not None:
            weighted_sum += score * weight
            total_weight += weight

    result["total_compliance_score"] = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0

    return result


# --------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TFL Benchmark — Regulatory Compliance Checks")
    parser.add_argument("--tc", required=True, help="Test case ID (e.g., TC-001)")
    parser.add_argument("--output", required=True, help="Agent output JSON file")
    parser.add_argument("--check", choices=["adam", "tcg", "csr", "all"],
                        default="all", help="Which compliance checks to run")
    args = parser.parse_args()

    with open(args.output) as f:
        agent_output = json.load(f)

    run_adam = args.check in ("adam", "all")
    run_tcg = args.check in ("tcg", "all")
    run_csr = args.check in ("csr", "all")

    result = compute_compliance_score(
        agent_output, args.tc,
        check_adam=run_adam,
        check_tcg=run_tcg,
        check_csr=run_csr,
    )

    if "error" in result:
        print(f"ERROR: {result['error']}")
        sys.exit(1)

    print("")
    print("=" * 60)
    print(f"  COMPLIANCE REPORT — {args.tc}")
    print("=" * 60)
    print(f"  Total Compliance Score: {result['total_compliance_score']:.4f}")
    print("=" * 60)

    for component_name in ["adam_compliance", "tcg_compliance", "csr_compliance"]:
        data = result.get(component_name, {})
        score = data.get("score")
        if score is not None:
            pf = data.get("passed", [])
            ff = data.get("failed", [])
            status = "\u2705" if score >= 0.8 else "\u26a0\ufe0f" if score >= 0.5 else "\u274c"
            print(f"")
            print(f"  {status} {component_name}: {score:.4f} ({len(pf)} passed, {len(ff)} failed)")
            for rid in pf:
                print(f"    \u2705 {rid}")
            for rid in ff:
                print(f"    \u274c {rid}")
        else:
            print(f"")
            print(f"  \u2b1c {component_name}: skipped")

    print("")
    print("=" * 60)
    print("")
