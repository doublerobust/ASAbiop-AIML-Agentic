#!/usr/bin/env python3
"""katsu — TFL Scoring and Evaluation Harness for the ASA Biopharm Benchmark

Evaluate AI agent outputs against cross-validated ground truth for TFL
(Tables, Figures, Listings) benchmark test cases.

Supports:
- Numerical comparison with configurable tolerance
- Schema validation
- Cross-language ground truth verification
- Weighted scoring per test case
- Regulatory compliance checks (ADaM, TCG, CSR)

Usage:
  # Score an agent output (numerical only)
  python score.py score --tc TC-001 --agent agent.json --truth ground_truth.json

  # Score with full compliance checks
  python score.py score --tc TC-001 --agent agent.json --truth ground_truth.json \
      --compliance --tcg-check --csr-format

  # Score with safety/robustness checks
  python score.py score --tc TC-001 --agent agent.json --truth ground_truth.json \
      --safety --n-count --denom --edge

  # Score with all checks
  python score.py score --tc TC-001 --agent agent.json --truth ground_truth.json \
      --compliance --tcg-check --csr-format --safety

  # Verify cross-language consistency
  python score.py verify --tc TC-001 --r R.json --sas SAS.json --python Python.json

  # Validate schema
  python score.py validate --tc TC-001 --input output.json

  # Run compliance checks independently
  python score.py compliance --tc TC-001 --agent agent.json

  # Run safety checks independently
  python score.py check-safety --tc TC-001 --agent agent.json --package package.json

  # Run full evaluation (numerical + schema + compliance + safety)
  python score.py evaluate --tc TC-001 --agent agent.json --truth ground_truth.json \
      --compliance --safety
"""

import json
import sys
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

# Import compliance module (optional)
try:
    from scoring_harness.compliance import compute_compliance_score as _compute_compliance_score
    HAS_COMPLIANCE = True
except ImportError:
    try:
        from compliance import compute_compliance_score as _compute_compliance_score
        HAS_COMPLIANCE = True
    except ImportError:
        _compute_compliance_score = None
        HAS_COMPLIANCE = False

# Import safety module (optional)
try:
    from scoring_harness.safety import compute_safety_score as _compute_safety_score
    HAS_SAFETY = True
except ImportError:
    try:
        from safety import compute_safety_score as _compute_safety_score
        HAS_SAFETY = True
    except ImportError:
        _compute_safety_score = None
        HAS_SAFETY = False


# --------------------------------------------------------------------
# Tolerance Loading
# --------------------------------------------------------------------

def load_tolerances():
    """Load tolerance specs from tolerances.yaml."""
    tol_path = Path(__file__).parent / "tolerances.yaml"
    with open(tol_path) as f:
        return yaml.safe_load(f)


def load_schema(tc_id: str) -> dict:
    """Load JSON Schema for a test case."""
    schema_dir = Path(__file__).resolve().parent.parent / "references" / "output-schemas"
    schema_path = schema_dir / f"{tc_id.lower()}-output-schema.json"

    if schema_path.exists():
        with open(schema_path) as f:
            return json.load(f)
    return None


# --------------------------------------------------------------------
# Comparison Logic
# --------------------------------------------------------------------

def compare_numeric(value_a, value_b, tol, field_name=""):
    """Compare two numeric values with tolerance.

    Args:
        value_a: Agent value
        value_b: Ground truth value
        tol: Tolerance dict with 'absolute' and 'relative'
        field_name: Field name for reporting

    Returns:
        dict with score, pass, diff, note
    """
    if value_a is None and value_b is None:
        return {"score": 1.0, "pass": True, "diff": 0, "note": "both null \u2014 acceptable"}
    if value_a is None or value_b is None:
        return {"score": 0.0, "pass": False, "diff": None,
                "note": f"null mismatch: agent={value_a}, truth={value_b}"}

    value_a = float(value_a)
    value_b = float(value_b)

    abs_tol = tol.get("absolute", 0.05)
    rel_tol = tol.get("relative")

    abs_diff = abs(value_a - value_b)
    rel_diff = abs_diff / abs(value_b) if value_b != 0 else float("inf")

    within_abs = abs_diff <= abs_tol
    within_rel = True if rel_tol is None else rel_diff <= rel_tol

    passed = within_abs or within_rel

    if abs_tol == 0:
        passed = value_a == value_b
        score = 1.0 if passed else 0.0
        note = "exact match" if passed else f"exact mismatch: diff={abs_diff:.6f}"
    elif passed:
        score = 1.0
        note = f"within tolerance (abs={abs_diff:.6f} <= {abs_tol})"
    else:
        score = 0.0
        note = f"outside tolerance (abs={abs_diff:.6f} > {abs_tol})"

    return {"score": score, "pass": passed, "diff": round(abs_diff, 6), "note": note}


def compare_count(value_a, value_b):
    """Compare integer count values (exact match)."""
    if value_a is None and value_b is None:
        return {"score": 1.0, "pass": True, "diff": 0, "note": "both null"}
    if value_a is None or value_b is None:
        return {"score": 0.0, "pass": False, "diff": None,
                "note": f"null count: agent={value_a}, truth={value_b}"}

    value_a = int(value_a)
    value_b = int(value_b)
    passed = value_a == value_b
    return {
        "score": 1.0 if passed else 0.0,
        "pass": passed,
        "diff": abs(value_a - value_b),
        "note": "exact match" if passed else f"mismatch: {value_a} vs {value_b}"
    }


# --------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------

def score_tc001(agent_output: dict, ground_truth: dict, tolerances: dict) -> dict:
    """Score TC-001 (KM Median PFS) agent output against ground truth."""
    tol_spec = tolerances.get("TC-001", {}).get("tolerances", {})
    fields = ["median_pfs", "ci_lower", "ci_upper", "n_events", "n_total"]

    component_scores = {}
    total_weight = 0
    weighted_sum = 0

    for field in fields:
        field_tol = tol_spec.get(field, {"absolute": 0.05, "weight": 0.10})
        weight = field_tol.get("weight", 0.10)
        abs_tol = field_tol.get("absolute", 0.05)

        if field in ("n_events", "n_total"):
            result = compare_count(agent_output.get(field), ground_truth.get(field))
        else:
            result = compare_numeric(
                agent_output.get(field), ground_truth.get(field),
                field_tol, field
            )

        component_scores[field] = result
        score = result["score"]
        weighted_sum += score * weight
        total_weight += weight

    final_score = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0

    return {
        "test_case_id": "TC-001",
        "score": final_score,
        "component_scores": component_scores,
        "agent_language": agent_output.get("language", "unknown"),
        "ground_truth_language": ground_truth.get("language", "unknown"),
        "variant_id": agent_output.get("variant_id"),
    }


def score_tc003(agent_output: dict, ground_truth: dict, tolerances: dict) -> dict:
    """Score TC-003 (Stratified Log-Rank) agent output against ground truth."""
    tol_spec = tolerances.get("TC-003", {}).get("tolerances", {})
    fields = ["chi_square", "p_value", "n_events", "n_total"]

    component_scores = {}
    total_weight = 0
    weighted_sum = 0

    for field in fields:
        field_tol = tol_spec.get(field, {"absolute": 0.01, "weight": 0.25})
        weight = field_tol.get("weight", 0.25)

        if field in ("n_events", "n_total"):
            result = compare_count(agent_output.get(field), ground_truth.get(field))
        else:
            result = compare_numeric(
                agent_output.get(field), ground_truth.get(field),
                field_tol, field
            )

        component_scores[field] = result
        score = result["score"]
        weighted_sum += score * weight
        total_weight += weight

    final_score = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0

    return {
        "test_case_id": "TC-003",
        "score": final_score,
        "component_scores": component_scores,
        "agent_language": agent_output.get("language", "unknown"),
        "ground_truth_language": ground_truth.get("language", "unknown"),
        "variant_id": agent_output.get("variant_id"),
    }


def _age_by_arm_index(output: dict) -> dict:
    """Index age_by_arm rows by treatment arm for aligned comparison.

    Handles both the R key ('n') and pandas key ('count') for the arm count,
    and the R key ('sd') vs pandas ('std') for standard deviation.
    """
    idx = {}
    for row in output.get("age_by_arm", []) or []:
        arm = row.get("TRT01PN")
        idx[arm] = {
            "mean": row.get("mean"),
            "std": row.get("std", row.get("sd")),
            "median": row.get("median"),
            "n": row.get("n", row.get("count")),
        }
    return idx


def score_tc002(agent_output: dict, ground_truth: dict, tolerances: dict) -> dict:
    """Score TC-002 (Baseline Demographics Table) agent output against ground truth.

    NOTE: TC-002 output is NESTED (age_by_arm is a per-arm list; total_age is a
    dict). A previous version of this scorer looked for flat top-level 'mean',
    'std', 'median', 'n_total' keys that do not exist in the ground truth, so
    every continuous field scored 0. This version compares per-arm age stats
    (aligned by TRT01PN) plus the overall n, matching the real schema.
    """
    tol_spec = tolerances.get("TC-002", {}).get("tolerances", {})

    component_scores = {}
    total_weight = 0
    weighted_sum = 0

    # Per-arm continuous age stats, aligned by treatment arm
    agent_age = _age_by_arm_index(agent_output)
    truth_age = _age_by_arm_index(ground_truth)

    cont_fields = ["mean", "std", "median"]
    for arm in sorted(truth_age.keys(), key=lambda x: (x is None, x)):
        for field in cont_fields:
            field_tol = tol_spec.get(field, {"absolute": 0.05, "weight": 0.10})
            # Spread the per-field weight across the arms present
            weight = field_tol.get("weight", 0.10) / max(len(truth_age), 1)
            key = f"age_arm{arm}_{field}"
            result = compare_numeric(
                agent_age.get(arm, {}).get(field),
                truth_age.get(arm, {}).get(field),
                field_tol, key
            )
            component_scores[key] = result
            weighted_sum += result["score"] * weight
            total_weight += weight

    # Per-arm counts (exact match)
    for arm in sorted(truth_age.keys(), key=lambda x: (x is None, x)):
        weight = tol_spec.get("count", {}).get("weight", 0.20) / max(len(truth_age), 1)
        key = f"age_arm{arm}_n"
        result = compare_count(agent_age.get(arm, {}).get("n"),
                               truth_age.get(arm, {}).get("n"))
        component_scores[key] = result
        weighted_sum += result["score"] * weight
        total_weight += weight

    # Overall N (n_total)
    if "n_total" in ground_truth:
        weight = 0.10
        result = compare_count(agent_output.get("n_total"), ground_truth.get("n_total"))
        component_scores["n_total"] = result
        weighted_sum += result["score"] * weight
        total_weight += weight

    # Categorical counts
    agent_counts = agent_output.get("categorical_by_arm", [])
    truth_counts = ground_truth.get("categorical_by_arm", [])

    if agent_counts and truth_counts:
        agent_tuples = {(c.get("variable"), str(c.get("level")),
                        c.get("TRT01PN"), c.get("n"))
                       for c in agent_counts if "n" in c}
        truth_tuples = {(c.get("variable"), str(c.get("level")),
                        c.get("TRT01PN"), c.get("n"))
                       for c in truth_counts if "n" in c}

        common = agent_tuples & truth_tuples
        all_cells = agent_tuples | truth_tuples
        cat_score = len(common) / len(all_cells) if all_cells else 1.0

        component_scores["categorical_counts"] = {
            "score": cat_score,
            "pass": cat_score == 1.0,
            "note": f"{len(common)}/{len(all_cells)} categorical cells match exactly"
        }
        weighted_sum += cat_score * 0.20
        total_weight += 0.20

    final_score = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0

    return {
        "test_case_id": "TC-002",
        "score": final_score,
        "component_scores": component_scores,
        "agent_language": agent_output.get("language", "unknown"),
        "ground_truth_language": ground_truth.get("language", "unknown"),
        "variant_id": agent_output.get("variant_id"),
    }


# --------------------------------------------------------------------
# TC-011: AE Summary Table by SOC and PT
# --------------------------------------------------------------------

def _ae_table_index(output: dict) -> dict:
    """Index AE table rows by (soc, pt) for aligned comparison.

    Handles the nested structure where ae_table is a list of dicts with
    soc, pt, n_experimental, pct_experimental, n_control, pct_control.
    Summary rows have pt=None.
    """
    idx = {}
    for row in output.get("ae_table", []) or output.get("summary", []):
        soc = row.get("soc")
        pt = row.get("pt")
        idx[(soc, pt)] = {
            "n_experimental": row.get("n_experimental"),
            "pct_experimental": row.get("pct_experimental"),
            "n_control": row.get("n_control"),
            "pct_control": row.get("pct_control"),
        }
    return idx


def score_tc011(agent_output: dict, ground_truth: dict, tolerances: dict) -> dict:
    """Score TC-011 (AE Summary Table by SOC/PT).

    Compares summary rows (overall AE/SAE/discontinuation counts) and
    detailed SOC-level rows, both n(%) per arm.
    """
    tol_spec = tolerances.get("TC-011", {}).get("tolerances", {})
    component_scores = {}
    total_weight = 0
    weighted_sum = 0

    # Index both outputs by (soc, pt)
    agent_idx = _ae_table_index(agent_output)
    truth_idx = _ae_table_index(ground_truth)

    # Summary rows (Any AE, SAE, AE leading to discontinuation)
    summary_keys = [k for k in truth_idx if k[1] is None]
    n_summary = max(len(summary_keys), 1)

    for key in summary_keys:
        truth_row = truth_idx[key]
        agent_row = agent_idx.get(key, {})
        soc_label = key[0]

        # Counts (exact)
        for arm_field, label in [("n_experimental", f"{soc_label}_n_exp"),
                                 ("n_control", f"{soc_label}_n_ctl")]:
            w = tol_spec.get("summary_n", {}).get("weight", 0.25) / (n_summary * 2)
            r = compare_count(agent_row.get(arm_field), truth_row.get(arm_field))
            component_scores[label] = r
            weighted_sum += r["score"] * w
            total_weight += w

        # Percentages (tolerance)
        for arm_field, label in [("pct_experimental", f"{soc_label}_pct_exp"),
                                 ("pct_control", f"{soc_label}_pct_ctl")]:
            field_tol = {"absolute": tol_spec.get("summary_pct", {}).get("absolute", 0.1)}
            w = tol_spec.get("summary_pct", {}).get("weight", 0.15) / (n_summary * 2)
            r = compare_numeric(agent_row.get(arm_field), truth_row.get(arm_field),
                                field_tol, label)
            component_scores[label] = r
            weighted_sum += r["score"] * w
            total_weight += w

    # Detailed SOC-level rows (pt is not None or soc not in summary labels)
    detail_keys = [k for k in truth_idx if k not in summary_keys]
    n_detail = max(len(detail_keys), 1)

    for key in detail_keys:
        truth_row = truth_idx[key]
        agent_row = agent_idx.get(key, {})
        soc_label = key[0]

        for arm_field, label in [("n_experimental", f"{soc_label}_n_exp"),
                                 ("n_control", f"{soc_label}_n_ctl")]:
            w = tol_spec.get("ae_table_n", {}).get("weight", 0.30) / (n_detail * 2)
            r = compare_count(agent_row.get(arm_field), truth_row.get(arm_field))
            component_scores[label] = r
            weighted_sum += r["score"] * w
            total_weight += w

        for arm_field, label in [("pct_experimental", f"{soc_label}_pct_exp"),
                                 ("pct_control", f"{soc_label}_pct_ctl")]:
            field_tol = {"absolute": tol_spec.get("ae_table_pct", {}).get("absolute", 0.1)}
            w = tol_spec.get("ae_table_pct", {}).get("weight", 0.20) / (n_detail * 2)
            r = compare_numeric(agent_row.get(arm_field), truth_row.get(arm_field),
                                field_tol, label)
            component_scores[label] = r
            weighted_sum += r["score"] * w
            total_weight += w

    # N per arm from population block
    pop = ground_truth.get("population", {})
    agent_pop = agent_output.get("population", {})
    for field, label in [("n_experimental", "pop_n_exp"), ("n_control", "pop_n_ctl")]:
        w = tol_spec.get("n_per_arm", {}).get("weight", 0.10) / 2
        r = compare_count(agent_pop.get(field), pop.get(field))
        component_scores[label] = r
        weighted_sum += r["score"] * w
        total_weight += w

    final_score = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0

    return {
        "test_case_id": "TC-011",
        "score": final_score,
        "component_scores": component_scores,
        "agent_language": agent_output.get("language", "unknown"),
        "ground_truth_language": ground_truth.get("language", "unknown"),
        "variant_id": agent_output.get("variant_id"),
    }


# --------------------------------------------------------------------
# TC-012: Forest Plot — Subgroup Hazard Ratios
# --------------------------------------------------------------------

def _subgroup_index(output: dict) -> dict:
    """Index subgroup rows by (variable, value) for aligned comparison."""
    idx = {}
    for row in output.get("subgroups", []) or []:
        var = row.get("variable")
        val = row.get("value")
        idx[(var, val)] = {
            "hr": row.get("hr"),
            "ci_lower": row.get("ci_lower"),
            "ci_upper": row.get("ci_upper"),
            "n_experimental": row.get("n_experimental"),
            "n_control": row.get("n_control"),
            "events_experimental": row.get("events_experimental"),
            "events_control": row.get("events_control"),
        }
    return idx


def score_tc012(agent_output: dict, ground_truth: dict, tolerances: dict) -> dict:
    """Score TC-012 (Forest Plot — Subgroup HRs).

    Compares overall HR + CI and each subgroup HR + CI.
    """
    tol_spec = tolerances.get("TC-012", {}).get("tolerances", {})
    component_scores = {}
    total_weight = 0
    weighted_sum = 0

    # Overall HR + CI
    agent_overall = agent_output.get("overall", {})
    truth_overall = ground_truth.get("overall", {})

    hr_tol = {"absolute": tol_spec.get("overall_hr", {}).get("absolute", 0.05),
              "relative": tol_spec.get("overall_hr", {}).get("relative", 0.02)}
    w = tol_spec.get("overall_hr", {}).get("weight", 0.25)
    r = compare_numeric(agent_overall.get("hr"), truth_overall.get("hr"), hr_tol, "overall_hr")
    component_scores["overall_hr"] = r
    weighted_sum += r["score"] * w
    total_weight += w

    ci_tol = {"absolute": tol_spec.get("overall_ci", {}).get("absolute", 0.05)}
    w_ci = tol_spec.get("overall_ci", {}).get("weight", 0.15) / 2
    for field, label in [("ci_lower", "overall_ci_lower"), ("ci_upper", "overall_ci_upper")]:
        r = compare_numeric(agent_overall.get(field), truth_overall.get(field), ci_tol, label)
        component_scores[label] = r
        weighted_sum += r["score"] * w_ci
        total_weight += w_ci

    # Subgroup HRs + CIs
    agent_sg = _subgroup_index(agent_output)
    truth_sg = _subgroup_index(ground_truth)

    sg_keys = list(truth_sg.keys())
    n_sg = max(len(sg_keys), 1)

    sg_hr_w = tol_spec.get("subgroup_hr", {}).get("weight", 0.30) / n_sg
    sg_hr_tol = {"absolute": tol_spec.get("subgroup_hr", {}).get("absolute", 0.05),
                 "relative": tol_spec.get("subgroup_hr", {}).get("relative", 0.05)}

    sg_ci_w = tol_spec.get("subgroup_ci", {}).get("weight", 0.20) / (n_sg * 2)
    sg_ci_tol = {"absolute": tol_spec.get("subgroup_ci", {}).get("absolute", 0.05)}

    sg_n_w = tol_spec.get("subgroup_n", {}).get("weight", 0.10) / (n_sg * 2)

    for key in sg_keys:
        truth_row = truth_sg[key]
        agent_row = agent_sg.get(key, {})
        label_base = f"{key[0]}={key[1]}"

        # HR
        r = compare_numeric(agent_row.get("hr"), truth_row.get("hr"), sg_hr_tol, f"{label_base}_hr")
        component_scores[f"{label_base}_hr"] = r
        weighted_sum += r["score"] * sg_hr_w
        total_weight += sg_hr_w

        # CI lower/upper
        for ci_field, ci_label in [("ci_lower", "ci_l"), ("ci_upper", "ci_u")]:
            r = compare_numeric(agent_row.get(ci_field), truth_row.get(ci_field),
                                sg_ci_tol, f"{label_base}_{ci_label}")
            component_scores[f"{label_base}_{ci_label}"] = r
            weighted_sum += r["score"] * sg_ci_w
            total_weight += sg_ci_w

        # N per subgroup (exact)
        for n_field, n_label in [("n_experimental", "n_exp"), ("n_control", "n_ctl")]:
            r = compare_count(agent_row.get(n_field), truth_row.get(n_field))
            component_scores[f"{label_base}_{n_label}"] = r
            weighted_sum += r["score"] * sg_n_w
            total_weight += sg_n_w

    final_score = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0

    return {
        "test_case_id": "TC-012",
        "score": final_score,
        "component_scores": component_scores,
        "agent_language": agent_output.get("language", "unknown"),
        "ground_truth_language": ground_truth.get("language", "unknown"),
        "variant_id": agent_output.get("variant_id"),
    }


# --------------------------------------------------------------------
# TC-013: Waterfall Plot — Best % Tumor Change
# --------------------------------------------------------------------

def score_tc013(agent_output: dict, ground_truth: dict, tolerances: dict) -> dict:
    """Score TC-013 (Waterfall Plot — RECIST 1.1).

    Compares response category counts, ORR/DCR percentages, and
    median/mean best % change across all/experimental/control arms.
    """
    tol_spec = tolerances.get("TC-013", {}).get("tolerances", {})
    component_scores = {}
    total_weight = 0
    weighted_sum = 0

    agent_summary = agent_output.get("summary", {})
    truth_summary = ground_truth.get("summary", {})

    count_fields = [("n_cr", "n_cr"), ("n_pr", "n_pr"), ("n_sd", "n_sd"), ("n_pd", "n_pd")]
    pct_fields = [("orr_pct", "orr_pct"), ("dcr_pct", "dcr_pct")]
    change_fields = [("median_best_pct_change", "median_pct"), ("mean_best_pct_change", "mean_pct")]

    arms = ["all", "experimental", "control"]

    for arm in arms:
        truth_arm = truth_summary.get(arm, {})
        agent_arm = agent_summary.get(arm, {})
        if not truth_arm:
            continue

        # Response counts (exact)
        resp_w = tol_spec.get("response_n", {}).get("weight", 0.30) / (len(arms) * len(count_fields))
        for gt_field, label_suffix in count_fields:
            label = f"{arm}_{label_suffix}"
            r = compare_count(agent_arm.get(gt_field), truth_arm.get(gt_field))
            component_scores[label] = r
            weighted_sum += r["score"] * resp_w
            total_weight += resp_w

        # ORR / DCR percentages
        pct_tol = {"absolute": 0.1}
        orr_w = tol_spec.get("orr_pct", {}).get("weight", 0.15) / len(arms)
        dcr_w = tol_spec.get("dcr_pct", {}).get("weight", 0.15) / len(arms)
        weights_map = {"orr_pct": orr_w, "dcr_pct": dcr_w}

        for gt_field, label_suffix in pct_fields:
            label = f"{arm}_{label_suffix}"
            r = compare_numeric(agent_arm.get(gt_field), truth_arm.get(gt_field), pct_tol, label)
            component_scores[label] = r
            weighted_sum += r["score"] * weights_map[gt_field]
            total_weight += weights_map[gt_field]

        # Median / mean % change
        chg_tol = {"absolute": 0.1}
        med_w = tol_spec.get("median_pct_change", {}).get("weight", 0.20) / len(arms)
        mean_w = tol_spec.get("mean_pct_change", {}).get("weight", 0.20) / len(arms)
        chg_weights = {"median_best_pct_change": med_w, "mean_best_pct_change": mean_w}

        for gt_field, label_suffix in change_fields:
            label = f"{arm}_{label_suffix}"
            r = compare_numeric(agent_arm.get(gt_field), truth_arm.get(gt_field), chg_tol, label)
            component_scores[label] = r
            weighted_sum += r["score"] * chg_weights[gt_field]
            total_weight += chg_weights[gt_field]

    final_score = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0

    return {
        "test_case_id": "TC-013",
        "score": final_score,
        "component_scores": component_scores,
        "agent_language": agent_output.get("language", "unknown"),
        "ground_truth_language": ground_truth.get("language", "unknown"),
        "variant_id": agent_output.get("variant_id"),
    }


# --------------------------------------------------------------------
# TC-014: Protocol Deviation Listing
# --------------------------------------------------------------------

def score_tc014(agent_output: dict, ground_truth: dict, tolerances: dict) -> dict:
    """Score TC-014 (Listing of Key Protocol Deviations).

    Compares overall PD counts, by-category counts, by-severity counts,
    and N per arm.
    """
    tol_spec = tolerances.get("TC-014", {}).get("tolerances", {})
    component_scores = {}
    total_weight = 0
    weighted_sum = 0

    agent_summary = agent_output.get("summary", {})
    truth_summary = ground_truth.get("summary", {})

    arms = ["all", "experimental", "control"]

    for arm in arms:
        truth_arm = truth_summary.get(arm, {})
        agent_arm = agent_summary.get(arm, {})
        if not truth_arm:
            continue

        label_prefix = f"{arm}_"

        # n_subjects_with_pd (exact)
        w = tol_spec.get("n_subjects_with_pd", {}).get("weight", 0.25) / len(arms)
        r = compare_count(agent_arm.get("n_subjects_with_pd"),
                          truth_arm.get("n_subjects_with_pd"))
        component_scores[f"{label_prefix}n_subj_pd"] = r
        weighted_sum += r["score"] * w
        total_weight += w

        # n_total_deviations (exact)
        w = tol_spec.get("n_total_deviations", {}).get("weight", 0.20) / len(arms)
        r = compare_count(agent_arm.get("n_total_deviations"),
                          truth_arm.get("n_total_deviations"))
        component_scores[f"{label_prefix}n_total_dev"] = r
        weighted_sum += r["score"] * w
        total_weight += w

        # By-category counts (exact match per category)
        truth_cats = truth_arm.get("by_category", {})
        agent_cats = agent_arm.get("by_category", {})
        n_cats = max(len(truth_cats), 1)
        cat_w = tol_spec.get("by_category_n", {}).get("weight", 0.25) / (len(arms) * n_cats)

        for cat_name, cat_data in truth_cats.items():
            truth_n = cat_data.get("n_deviations")
            agent_n = agent_cats.get(cat_name, {}).get("n_deviations")
            label = f"{label_prefix}cat_{cat_name.replace(' ', '_')}"
            r = compare_count(agent_n, truth_n)
            component_scores[label] = r
            weighted_sum += r["score"] * cat_w
            total_weight += cat_w

        # By-severity counts (exact match per severity)
        truth_sev = truth_arm.get("by_severity", {})
        agent_sev = agent_arm.get("by_severity", {})
        n_sev = max(len(truth_sev), 1)
        sev_w = tol_spec.get("by_severity_n", {}).get("weight", 0.20) / (len(arms) * n_sev)

        for sev_name, truth_n in truth_sev.items():
            agent_n = agent_sev.get(sev_name)
            label = f"{label_prefix}sev_{sev_name}"
            r = compare_count(agent_n, truth_n)
            component_scores[label] = r
            weighted_sum += r["score"] * sev_w
            total_weight += sev_w

    # N per arm from population block
    pop = ground_truth.get("population", {})
    agent_pop = agent_output.get("population", {})
    pop_w = tol_spec.get("n_per_arm", {}).get("weight", 0.10) / 2
    for field, label in [("n_experimental", "pop_n_exp"), ("n_control", "pop_n_ctl")]:
        r = compare_count(agent_pop.get(field), pop.get(field))
        component_scores[label] = r
        weighted_sum += r["score"] * pop_w
        total_weight += pop_w

    final_score = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0

    return {
        "test_case_id": "TC-014",
        "score": final_score,
        "component_scores": component_scores,
        "agent_language": agent_output.get("language", "unknown"),
        "ground_truth_language": ground_truth.get("language", "unknown"),
        "variant_id": agent_output.get("variant_id"),
    }


# TC-015: KM Curve with Risk Table
def score_tc015(agent_output: dict, ground_truth: dict, tolerances: dict) -> dict:
    """Score TC-015 (KM Curve with Risk Table).

    Compares survival probabilities, n_at_risk, log-rank, and median.
    """
    tol_spec = tolerances.get("TC-015", {}).get("tolerances", {})
    component_scores = {}
    weighted_sum = 0.0
    total_weight = 0.0

    # Overall median
    gt_med = ground_truth.get("overall_median", {})
    ag_med = agent_output.get("overall_median", {})
    med_w = tol_spec.get("overall_median", {}).get("weight", 0.15)
    med_abs = tol_spec.get("overall_median", {}).get("absolute", 0.1)
    r = compare_numeric(ag_med.get("median"), gt_med.get("median"), {"absolute": med_abs})
    component_scores["overall_median"] = r
    weighted_sum += r["score"] * med_w
    total_weight += med_w

    # Log-rank
    gt_lr = ground_truth.get("logrank", {})
    ag_lr = agent_output.get("logrank", {})
    lr_w = tol_spec.get("logrank_chisq", {}).get("weight", 0.15)
    lr_abs = tol_spec.get("logrank_chisq", {}).get("absolute", 0.05)
    r = compare_numeric(ag_lr.get("chisq"), gt_lr.get("chisq"), {"absolute": lr_abs})
    component_scores["logrank_chisq"] = r
    weighted_sum += r["score"] * lr_w
    total_weight += lr_w

    lr_p_w = tol_spec.get("logrank_p", {}).get("weight", 0.10)
    lr_p_abs = tol_spec.get("logrank_p", {}).get("absolute", 0.005)
    r = compare_numeric(ag_lr.get("p_value"), gt_lr.get("p_value"), {"absolute": lr_p_abs})
    component_scores["logrank_p"] = r
    weighted_sum += r["score"] * lr_p_w
    total_weight += lr_p_w

    # Survival probabilities + n_at_risk per arm
    surv_w = tol_spec.get("survival_probs", {}).get("weight", 0.25) / 2
    surv_abs = tol_spec.get("survival_probs", {}).get("absolute", 0.01)
    nar_w = tol_spec.get("n_at_risk", {}).get("weight", 0.20) / 2
    nar_abs = tol_spec.get("n_at_risk", {}).get("absolute", 2)

    for arm_key, label_prefix in [("curve_experimental", "exp_"), ("curve_control", "ctl_")]:
        gt_curve = ground_truth.get(arm_key, {})
        ag_curve = agent_output.get(arm_key, {})
        gt_surv = gt_curve.get("survival", [])
        ag_surv = ag_curve.get("survival", [])
        gt_nar = gt_curve.get("n_at_risk", [])
        ag_nar = ag_curve.get("n_at_risk", [])

        # Average survival probability score across time points
        n_tp = len(gt_surv)
        if n_tp > 0:
            arm_surv_sum = 0.0
            for i in range(min(len(ag_surv), n_tp)):
                r = compare_numeric(ag_surv[i], gt_surv[i], {"absolute": surv_abs})
                arm_surv_sum += r["score"]
            avg_arm = arm_surv_sum / n_tp
            component_scores[f"{label_prefix}survival"] = {"score": round(avg_arm, 4), "pass": avg_arm >= 0.95}
            weighted_sum += avg_arm * surv_w
            total_weight += surv_w

        # Average n_at_risk score
        if len(gt_nar) > 0:
            arm_nar_sum = 0.0
            for i in range(min(len(ag_nar), len(gt_nar))):
                _tol = nar_abs; _a = ag_nar[i]; _b = gt_nar[i]; r = {"score": 1.0 if (_a is None and _b is None) or (_a is not None and _b is not None and abs(int(_a)-int(_b)) <= _tol) else 0.0, "pass": (_a is None and _b is None) or (_a is not None and _b is not None and abs(int(_a)-int(_b)) <= _tol), "diff": abs(int(_a)-int(_b)) if _a is not None and _b is not None else None}
                arm_nar_sum += r["score"]
            avg_nar = arm_nar_sum / len(gt_nar)
            component_scores[f"{label_prefix}n_at_risk"] = {"score": round(avg_nar, 4), "pass": avg_nar >= 0.95}
            weighted_sum += avg_nar * nar_w
            total_weight += nar_w

    # Metadata: n_total and events
    gt_meta = ground_truth.get("metadata", {})
    ag_meta = agent_output.get("metadata", {})
    n_w = tol_spec.get("n_total", {}).get("weight", 0.05)
    r = compare_count(ag_meta.get("n_total"), gt_meta.get("n_total"))
    component_scores["n_total"] = r
    weighted_sum += r["score"] * n_w
    total_weight += n_w

    ev_w = tol_spec.get("events_total", {}).get("weight", 0.10)
    gt_events = gt_meta.get("events_experimental", 0) + gt_meta.get("events_control", 0)
    ag_events = ag_meta.get("events_experimental", 0) + ag_meta.get("events_control", 0)
    r = compare_count(ag_events, gt_events)
    component_scores["events_total"] = r
    weighted_sum += r["score"] * ev_w
    total_weight += ev_w

    final_score = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0
    return {
        "test_case_id": "TC-015",
        "score": final_score,
        "component_scores": component_scores,
        "agent_language": agent_output.get("language", "unknown"),
        "ground_truth_language": ground_truth.get("language", "unknown"),
        "variant_id": agent_output.get("variant_id"),
    }


# TC-016: Exposure Summary Table
def score_tc016(agent_output: dict, ground_truth: dict, tolerances: dict) -> dict:
    """Score TC-016 (Exposure Summary Table).

    Compares continuous summary stats for duration, dose, intensity; categorical for dose reduction.
    """
    tol_spec = tolerances.get("TC-016", {}).get("tolerances", {})
    component_scores = {}
    weighted_sum = 0.0
    total_weight = 0.0

    cont_fields = [
        ("treatment_duration", "duration_stats", ["mean", "sd", "median", "min", "max"]),
        ("cumulative_dose", "cumdose_stats", ["mean", "sd", "median"]),
        ("dose_intensity", "doseint_stats", ["mean", "sd", "median"]),
    ]

    for tc_field, tol_key, stat_keys in cont_fields:
        gt_block = ground_truth.get(tc_field, {})
        ag_block = agent_output.get(tc_field, {})
        field_w = tol_spec.get(tol_key, {}).get("weight", 0.20) / 2  # per arm
        field_abs = tol_spec.get(tol_key, {}).get("absolute", 0.5)

        for arm in ["experimental", "control"]:
            gt_arm = gt_block.get(arm, {})
            ag_arm = ag_block.get(arm, {})
            for sk in stat_keys:
                r = compare_numeric(ag_arm.get(sk), gt_arm.get(sk), {"absolute": field_abs})
                label = f"{tc_field}_{arm}_{sk}"
                # Normalize weight per stat per arm
                per_w = field_w / len(stat_keys)
                component_scores[label] = r
                weighted_sum += r["score"] * per_w
                total_weight += per_w

    # Dose reduction (categorical)
    gt_dr = ground_truth.get("dose_reduction", {})
    ag_dr = agent_output.get("dose_reduction", {})
    dr_n_w = tol_spec.get("dose_reduction_n", {}).get("weight", 0.15) / 2
    dr_n_abs = tol_spec.get("dose_reduction_n", {}).get("absolute", 2)
    dr_pct_w = tol_spec.get("dose_reduction_pct", {}).get("weight", 0.10) / 2
    dr_pct_abs = tol_spec.get("dose_reduction_pct", {}).get("absolute", 1.0)

    for arm in ["experimental", "control"]:
        gt_arm = gt_dr.get(arm, {})
        ag_arm = ag_dr.get(arm, {})
        _tol = dr_n_abs; _a = ag_arm.get("n_yes"); _b = gt_arm.get("n_yes"); r = {"score": 1.0 if (_a is None and _b is None) or (_a is not None and _b is not None and abs(int(_a)-int(_b)) <= _tol) else 0.0, "pass": (_a is None and _b is None) or (_a is not None and _b is not None and abs(int(_a)-int(_b)) <= _tol), "diff": abs(int(_a)-int(_b)) if _a is not None and _b is not None else None}
        component_scores[f"dose_reduction_{arm}_n"] = r
        weighted_sum += r["score"] * dr_n_w
        total_weight += dr_n_w

        r = compare_numeric(ag_arm.get("pct_yes"), gt_arm.get("pct_yes"), {"absolute": dr_pct_abs})
        component_scores[f"dose_reduction_{arm}_pct"] = r
        weighted_sum += r["score"] * dr_pct_w
        total_weight += dr_pct_w

    # N per arm
    gt_meta = ground_truth.get("metadata", {})
    ag_meta = agent_output.get("metadata", {})
    n_w = tol_spec.get("n_per_arm", {}).get("weight", 0.05) / 2
    for field, label in [("n_experimental", "n_exp"), ("n_control", "n_ctl")]:
        r = compare_count(ag_meta.get(field), gt_meta.get(field))
        component_scores[label] = r
        weighted_sum += r["score"] * n_w
        total_weight += n_w

    final_score = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0
    return {
        "test_case_id": "TC-016",
        "score": final_score,
        "component_scores": component_scores,
        "agent_language": agent_output.get("language", "unknown"),
        "ground_truth_language": ground_truth.get("language", "unknown"),
        "variant_id": agent_output.get("variant_id"),
    }


# TC-017: Laboratory Shift Table
def score_tc017(agent_output: dict, ground_truth: dict, tolerances: dict) -> dict:
    """Score TC-017 (Lab Shift Table).

    Compares 3×3 shift cell counts and summary counts across overall/exp/control.
    """
    tol_spec = tolerances.get("TC-017", {}).get("tolerances", {})
    component_scores = {}
    weighted_sum = 0.0
    total_weight = 0.0

    cats = ["LOW", "NORMAL", "HIGH"]
    shift_keys = ["shift_overall", "shift_experimental", "shift_control"]

    # Shift counts (3x3 per block, 3 blocks)
    sc_w = tol_spec.get("shift_counts", {}).get("weight", 0.40) / (3 * 9)  # per cell per block
    sc_abs = tol_spec.get("shift_counts", {}).get("absolute", 2)

    for sk in shift_keys:
        gt_block = ground_truth.get(sk, {})
        ag_block = agent_output.get(sk, {})
        gt_counts = gt_block.get("counts", {})
        ag_counts = ag_block.get("counts", {})

        for bl in cats:
            for pb in cats:
                gt_v = gt_counts.get(bl, {}).get(pb)
                ag_v = ag_counts.get(bl, {}).get(pb)
                _tol = sc_abs; _a = ag_v; _b = gt_v; r = {"score": 1.0 if (_a is None and _b is None) or (_a is not None and _b is not None and abs(int(_a)-int(_b)) <= _tol) else 0.0, "pass": (_a is None and _b is None) or (_a is not None and _b is not None and abs(int(_a)-int(_b)) <= _tol), "diff": abs(int(_a)-int(_b)) if _a is not None and _b is not None else None}
                label = f"{sk}_{bl}_to_{pb}"
                component_scores[label] = r
                weighted_sum += r["score"] * sc_w
                total_weight += sc_w

    # Summary counts
    summary_fields = ["n_stable_normal", "n_low_to_normal", "n_normal_to_low", "n_normal_to_high", "n_high_to_normal"]
    su_w = tol_spec.get("summary_counts", {}).get("weight", 0.25) / (3 * len(summary_fields))
    su_abs = tol_spec.get("summary_counts", {}).get("absolute", 2)

    for sk in shift_keys:
        gt_block = ground_truth.get(sk, {})
        ag_block = agent_output.get(sk, {})
        for sf in summary_fields:
            _tol = su_abs; _a = ag_block.get(sf); _b = gt_block.get(sf); r = {"score": 1.0 if (_a is None and _b is None) or (_a is not None and _b is not None and abs(int(_a)-int(_b)) <= _tol) else 0.0, "pass": (_a is None and _b is None) or (_a is not None and _b is not None and abs(int(_a)-int(_b)) <= _tol), "diff": abs(int(_a)-int(_b)) if _a is not None and _b is not None else None}
            label = f"{sk}_{sf}"
            component_scores[label] = r
            weighted_sum += r["score"] * su_w
            total_weight += su_w

    # N per arm
    gt_meta = ground_truth.get("metadata", {})
    ag_meta = agent_output.get("metadata", {})
    n_w = tol_spec.get("n_per_arm", {}).get("weight", 0.10) / 2
    for field, label in [("n_experimental", "n_exp"), ("n_control", "n_ctl")]:
        r = compare_count(ag_meta.get(field), gt_meta.get(field))
        component_scores[label] = r
        weighted_sum += r["score"] * n_w
        total_weight += n_w

    n_total_w = tol_spec.get("n_total", {}).get("weight", 0.05)
    r = compare_count(ag_meta.get("n_total"), gt_meta.get("n_total"))
    component_scores["n_total"] = r
    weighted_sum += r["score"] * n_total_w
    total_weight += n_total_w

    final_score = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0
    return {
        "test_case_id": "TC-017",
        "score": final_score,
        "component_scores": component_scores,
        "agent_language": agent_output.get("language", "unknown"),
        "ground_truth_language": ground_truth.get("language", "unknown"),
        "variant_id": agent_output.get("variant_id"),
    }


# TC-018: Change from Baseline Table
def score_tc018(agent_output: dict, ground_truth: dict, tolerances: dict) -> dict:
    """Score TC-018 (Change from Baseline Table).

    Compares visit-wise mean/sd/median change, CI, p-values, and N.
    """
    tol_spec = tolerances.get("TC-018", {}).get("tolerances", {})
    component_scores = {}
    weighted_sum = 0.0
    total_weight = 0.0

    gt_visits = ground_truth.get("visits", {})
    ag_visits = agent_output.get("visits", {})
    n_visits = len(gt_visits)

    if n_visits == 0:
        return {"test_case_id": "TC-018", "score": 0.0, "component_scores": {}, "error": "No visits in ground truth"}

    # Weights per visit per arm
    mean_w = tol_spec.get("mean_chg", {}).get("weight", 0.25) / (n_visits * 2)
    mean_abs = tol_spec.get("mean_chg", {}).get("absolute", 0.5)
    sd_w = tol_spec.get("sd_chg", {}).get("weight", 0.15) / (n_visits * 2)
    sd_abs = tol_spec.get("sd_chg", {}).get("absolute", 0.5)
    med_w = tol_spec.get("median_chg", {}).get("weight", 0.10) / (n_visits * 2)
    med_abs = tol_spec.get("median_chg", {}).get("absolute", 0.5)
    ci_w = tol_spec.get("ci_bounds", {}).get("weight", 0.15) / (n_visits * 2 * 2)  # lower+upper per arm
    ci_abs = tol_spec.get("ci_bounds", {}).get("absolute", 1.0)
    p_w = tol_spec.get("p_values", {}).get("weight", 0.20) / n_visits
    p_abs = tol_spec.get("p_values", {}).get("absolute", 0.01)
    n_w = tol_spec.get("n_per_visit", {}).get("weight", 0.10) / (n_visits * 2)

    for visit_name, gt_vd in gt_visits.items():
        ag_vd = ag_visits.get(visit_name, {})
        for arm in ["experimental", "control"]:
            gt_arm = gt_vd.get(arm, {})
            ag_arm = ag_vd.get(arm, {})

            r = compare_numeric(ag_arm.get("mean_chg"), gt_arm.get("mean_chg"), {"absolute": mean_abs})
            component_scores[f"{visit_name}_{arm}_mean_chg"] = r
            weighted_sum += r["score"] * mean_w
            total_weight += mean_w

            r = compare_numeric(ag_arm.get("sd_chg"), gt_arm.get("sd_chg"), {"absolute": sd_abs})
            component_scores[f"{visit_name}_{arm}_sd_chg"] = r
            weighted_sum += r["score"] * sd_w
            total_weight += sd_w

            r = compare_numeric(ag_arm.get("median_chg"), gt_arm.get("median_chg"), {"absolute": med_abs})
            component_scores[f"{visit_name}_{arm}_median_chg"] = r
            weighted_sum += r["score"] * med_w
            total_weight += med_w

            for bound in ["ci_lower", "ci_upper"]:
                r = compare_numeric(ag_arm.get(bound), gt_arm.get(bound), {"absolute": ci_abs})
                component_scores[f"{visit_name}_{arm}_{bound}"] = r
                weighted_sum += r["score"] * ci_w
                total_weight += ci_w

            r = compare_count(ag_arm.get("n"), gt_arm.get("n"))
            component_scores[f"{visit_name}_{arm}_n"] = r
            weighted_sum += r["score"] * n_w
            total_weight += n_w

        # P-value
        r = compare_numeric(ag_vd.get("p_value"), gt_vd.get("p_value"), {"absolute": p_abs})
        component_scores[f"{visit_name}_p_value"] = r
        weighted_sum += r["score"] * p_w
        total_weight += p_w

    # N per arm
    gt_meta = ground_truth.get("metadata", {})
    ag_meta = agent_output.get("metadata", {})
    arm_w = tol_spec.get("n_per_arm", {}).get("weight", 0.05) / 2
    for field, label in [("n_experimental", "n_exp"), ("n_control", "n_ctl")]:
        r = compare_count(ag_meta.get(field), gt_meta.get(field))
        component_scores[label] = r
        weighted_sum += r["score"] * arm_w
        total_weight += arm_w

    final_score = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0
    return {
        "test_case_id": "TC-018",
        "score": final_score,
        "component_scores": component_scores,
        "agent_language": agent_output.get("language", "unknown"),
        "ground_truth_language": ground_truth.get("language", "unknown"),
        "variant_id": agent_output.get("variant_id"),
    }


# --------------------------------------------------------------------
# TC-019: Concomitant Medications Summary Table
# --------------------------------------------------------------------

def score_tc019(agent_output: dict, ground_truth: dict, tolerances: dict) -> dict:
    """Score TC-019: Concomitant Medications Summary Table.

    Compares summary row counts, ATC class-level counts/pcts,
    and medication-level counts/pcts.
    """
    tol_spec = tolerances.get("TC-019", {}).get("tolerances", {})
    component_scores = {}
    weighted_sum = 0.0
    total_weight = 0.0

    # Summary rows (Any CM)
    ag_summary = agent_output.get("summary_rows", [])
    gt_summary = ground_truth.get("summary_rows", [])
    summary_n_tol = tol_spec.get("summary_n", {})
    summary_pct_tol = tol_spec.get("summary_pct", {})

    for i in range(min(len(ag_summary), len(gt_summary))):
        ag_s = ag_summary[i] if i < len(ag_summary) else {}
        gt_s = gt_summary[i] if i < len(gt_summary) else {}

        for field, label in [("n_experimental", "summary_n_exp"), ("n_control", "summary_n_ctrl")]:
            r = compare_count(ag_s.get(field), gt_s.get(field))
            component_scores[f"{label}_row{i}"] = r
            weighted_sum += r["score"] * summary_n_tol.get("weight", 0.25)
            total_weight += summary_n_tol.get("weight", 0.25)

        for field, label in [("pct_experimental", "summary_pct_exp"), ("pct_control", "summary_pct_ctrl")]:
            r = compare_numeric(ag_s.get(field), gt_s.get(field), summary_pct_tol, label)
            component_scores[f"{label}_row{i}"] = r
            weighted_sum += r["score"] * summary_pct_tol.get("weight", 0.15)
            total_weight += summary_pct_tol.get("weight", 0.15)

    # Detailed rows (ATC class + medication level)
    ag_detail = agent_output.get("detailed_rows", [])
    gt_detail = ground_truth.get("detailed_rows", [])
    atc_n_tol = tol_spec.get("atc_class_n", {})
    atc_pct_tol = tol_spec.get("atc_class_pct", {})
    med_n_tol = tol_spec.get("medication_n", {})
    med_pct_tol = tol_spec.get("medication_pct", {})

    for i in range(min(len(ag_detail), len(gt_detail))):
        ag_d = ag_detail[i] if i < len(ag_detail) else {}
        gt_d = gt_detail[i] if i < len(gt_detail) else {}

        is_med_row = "medication" in gt_d and gt_d.get("medication")

        if is_med_row:
            for field, label in [("n_experimental", f"med_n_exp_{i}"), ("n_control", f"med_n_ctrl_{i}")]:
                r = compare_count(ag_d.get(field), gt_d.get(field))
                component_scores[label] = r
                weighted_sum += r["score"] * med_n_tol.get("weight", 0.10)
                total_weight += med_n_tol.get("weight", 0.10)

            for field, label in [("pct_experimental", f"med_pct_exp_{i}"), ("pct_control", f"med_pct_ctrl_{i}")]:
                r = compare_numeric(ag_d.get(field), gt_d.get(field), med_pct_tol, label)
                component_scores[label] = r
                weighted_sum += r["score"] * med_pct_tol.get("weight", 0.05)
                total_weight += med_pct_tol.get("weight", 0.05)
        else:
            for field, label in [("n_experimental", f"atc_n_exp_{i}"), ("n_control", f"atc_n_ctrl_{i}")]:
                r = compare_count(ag_d.get(field), gt_d.get(field))
                component_scores[label] = r
                weighted_sum += r["score"] * atc_n_tol.get("weight", 0.25)
                total_weight += atc_n_tol.get("weight", 0.25)

            for field, label in [("pct_experimental", f"atc_pct_exp_{i}"), ("pct_control", f"atc_pct_ctrl_{i}")]:
                r = compare_numeric(ag_d.get(field), gt_d.get(field), atc_pct_tol, label)
                component_scores[label] = r
                weighted_sum += r["score"] * atc_pct_tol.get("weight", 0.15)
                total_weight += atc_pct_tol.get("weight", 0.15)

    # N per arm
    arm_w = tol_spec.get("n_per_arm", {}).get("weight", 0.05) / 2
    for field, label in [("n_experimental", "n_exp"), ("n_control", "n_ctrl")]:
        r = compare_count(agent_output.get(field), ground_truth.get(field))
        component_scores[label] = r
        weighted_sum += r["score"] * arm_w
        total_weight += arm_w

    final_score = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0
    return {
        "test_case_id": "TC-019",
        "score": final_score,
        "component_scores": component_scores,
        "agent_language": agent_output.get("language", "unknown"),
        "ground_truth_language": ground_truth.get("language", "unknown"),
        "variant_id": agent_output.get("variant_id"),
    }


# --------------------------------------------------------------------
# TC-020: ORR by Subgroup
# --------------------------------------------------------------------

def score_tc020(agent_output: dict, ground_truth: dict, tolerances: dict) -> dict:
    """Score TC-020: ORR by Subgroup.

    Compares overall ORR, subgroup-level ORR, responder counts,
    and CMH interaction p-values.
    """
    tol_spec = tolerances.get("TC-020", {}).get("tolerances", {})
    component_scores = {}
    weighted_sum = 0.0
    total_weight = 0.0

    # Overall
    ag_ov = agent_output.get("overall", {})
    gt_ov = ground_truth.get("overall", {})

    for field, tol_key, label in [
        ("orr_experimental", "overall_orr_exp", "orr_exp"),
        ("orr_control", "overall_orr_ctrl", "orr_ctrl"),
        ("orr_difference", "overall_orr_diff", "orr_diff"),
    ]:
        tol = tol_spec.get(tol_key, {})
        r = compare_numeric(ag_ov.get(field), gt_ov.get(field), tol, label)
        component_scores[f"overall_{label}"] = r
        weighted_sum += r["score"] * tol.get("weight", 0.10)
        total_weight += tol.get("weight", 0.10)

    # Responder counts
    res_tol = tol_spec.get("responder_counts", {})
    for field, label in [("responders_experimental", "resp_exp"), ("responders_control", "resp_ctrl")]:
        r = compare_count(ag_ov.get(field), gt_ov.get(field))
        component_scores[f"overall_{label}"] = r
        weighted_sum += r["score"] * res_tol.get("weight", 0.10)
        total_weight += res_tol.get("weight", 0.10)

    # Subgroup-level
    ag_sgs = agent_output.get("subgroups", [])
    gt_sgs = ground_truth.get("subgroups", [])

    for i in range(min(len(ag_sgs), len(gt_sgs))):
        ag_s = ag_sgs[i] if i < len(ag_sgs) else {}
        gt_s = gt_sgs[i] if i < len(gt_sgs) else {}

        for field, tol_key, label in [
            ("orr_experimental", "subgroup_orr_exp", f"sg_{i}_orr_exp"),
            ("orr_control", "subgroup_orr_ctrl", f"sg_{i}_orr_ctrl"),
            ("orr_difference", "subgroup_orr_diff", f"sg_{i}_orr_diff"),
        ]:
            tol = tol_spec.get(tol_key, {})
            r = compare_numeric(ag_s.get(field), gt_s.get(field), tol, label)
            component_scores[label] = r
            weighted_sum += r["score"] * tol.get("weight", 0.10)
            total_weight += tol.get("weight", 0.10)

        # N per subgroup per arm
        sg_n_tol = tol_spec.get("subgroup_n", {})
        for field, label in [("n_experimental", f"sg_{i}_n_exp"), ("n_control", f"sg_{i}_n_ctrl")]:
            r = compare_count(ag_s.get(field), gt_s.get(field))
            component_scores[label] = r
            weighted_sum += r["score"] * sg_n_tol.get("weight", 0.10)
            total_weight += sg_n_tol.get("weight", 0.10)

    # Interaction p-values
    ag_ints = agent_output.get("interaction_pvalues", [])
    gt_ints = ground_truth.get("interaction_pvalues", [])
    int_tol = tol_spec.get("interaction_p", {})

    for i in range(min(len(ag_ints), len(gt_ints))):
        ag_i = ag_ints[i] if i < len(ag_ints) else {}
        gt_i = gt_ints[i] if i < len(gt_ints) else {}
        r = compare_numeric(ag_i.get("cmh_p_value"), gt_i.get("cmh_p_value"), int_tol, f"int_p_{i}")
        component_scores[f"int_p_{i}"] = r
        weighted_sum += r["score"] * int_tol.get("weight", 0.10)
        total_weight += int_tol.get("weight", 0.10)

    final_score = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0
    return {
        "test_case_id": "TC-020",
        "score": final_score,
        "component_scores": component_scores,
        "agent_language": agent_output.get("language", "unknown"),
        "ground_truth_language": ground_truth.get("language", "unknown"),
        "variant_id": agent_output.get("variant_id"),
    }


def score_tc021(agent_output: dict, ground_truth: dict, tolerances: dict) -> dict:
    """Score TC-021 (TTP KM Median) agent output against ground truth.

    Same structure as TC-001 but uses median_ttp and endpoint=TTP.
    """
    tol_spec = tolerances.get("TC-021", {}).get("tolerances", {})
    fields = ["median_ttp", "ci_lower", "ci_upper", "n_events", "n_total"]

    component_scores = {}
    total_weight = 0
    weighted_sum = 0

    for field in fields:
        field_tol = tol_spec.get(field, {"absolute": 0.05, "weight": 0.10})
        weight = field_tol.get("weight", 0.10)
        abs_tol = field_tol.get("absolute", 0.05)

        if field in ("n_events", "n_total"):
            result = compare_count(agent_output.get(field), ground_truth.get(field))
        else:
            result = compare_numeric(
                agent_output.get(field), ground_truth.get(field),
                field_tol, field
            )

        component_scores[field] = result
        score = result["score"]
        weighted_sum += score * weight
        total_weight += weight

    final_score = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0

    return {
        "test_case_id": "TC-021",
        "score": final_score,
        "component_scores": component_scores,
        "agent_language": agent_output.get("language", "unknown"),
        "ground_truth_language": ground_truth.get("language", "unknown"),
        "variant_id": agent_output.get("variant_id"),
    }


def score_tc022(agent_output: dict, ground_truth: dict, tolerances: dict) -> dict:
    """Score TC-022 (DOR KM Median) agent output against ground truth.

    Same structure as TC-021 but uses median_dor and endpoint=DOR.
    Fields: median_dor, ci_lower, ci_upper, n_responders, n_events, n_total.
    """
    tol_spec = tolerances.get("TC-022", {}).get("tolerances", {})
    fields = ["median_dor", "ci_lower", "ci_upper", "n_responders", "n_events", "n_total"]

    component_scores = {}
    total_weight = 0
    weighted_sum = 0

    for field in fields:
        field_tol = tol_spec.get(field, {"absolute": 0.05, "weight": 0.10})
        weight = field_tol.get("weight", 0.10)
        abs_tol = field_tol.get("absolute", 0.05)

        if field in ("n_responders", "n_events", "n_total"):
            result = compare_count(agent_output.get(field), ground_truth.get(field))
        else:
            result = compare_numeric(
                agent_output.get(field), ground_truth.get(field),
                field_tol, field
            )

        component_scores[field] = result
        score = result["score"]
        weighted_sum += score * weight
        total_weight += weight

    final_score = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0

    return {
        "test_case_id": "TC-022",
        "score": final_score,
        "component_scores": component_scores,
        "agent_language": agent_output.get("language", "unknown"),
        "ground_truth_language": ground_truth.get("language", "unknown"),
        "variant_id": agent_output.get("variant_id"),
    }


def score_tc023(agent_output: dict, ground_truth: dict, tolerances: dict) -> dict:
    """Score TC-023 (Disease Control Rate) agent output against ground truth.

    Compares overall DCR, subgroup-level DCR, disease control counts,
    and BOR distribution. Same structure as TC-020 but for DCR.
    """
    tol_spec = tolerances.get("TC-023", {}).get("tolerances", {})
    component_scores = {}
    weighted_sum = 0.0
    total_weight = 0.0

    # Overall
    ag_ov = agent_output.get("overall", {})
    gt_ov = ground_truth.get("overall", {})

    for field, tol_key, label in [
        ("dcr_experimental", "overall_dcr_exp", "dcr_exp"),
        ("dcr_control", "overall_dcr_ctrl", "dcr_ctrl"),
        ("dcr_difference", "overall_dcr_diff", "dcr_diff"),
    ]:
        tol = tol_spec.get(tol_key, {})
        r = compare_numeric(ag_ov.get(field), gt_ov.get(field), tol, label)
        component_scores[f"overall_{label}"] = r
        weighted_sum += r["score"] * tol.get("weight", 0.10)
        total_weight += tol.get("weight", 0.10)

    # Disease control counts
    dc_tol = tol_spec.get("dc_counts", {})
    for field, label in [("disease_controlled_exp", "dc_exp"), ("disease_controlled_ctrl", "dc_ctrl")]:
        r = compare_count(ag_ov.get(field), gt_ov.get(field))
        component_scores[f"overall_{label}"] = r
        weighted_sum += r["score"] * dc_tol.get("weight", 0.10)
        total_weight += dc_tol.get("weight", 0.10)

    # Subgroup-level
    ag_sgs = agent_output.get("subgroups", [])
    gt_sgs = ground_truth.get("subgroups", [])

    for i in range(min(len(ag_sgs), len(gt_sgs))):
        ag_s = ag_sgs[i] if i < len(ag_sgs) else {}
        gt_s = gt_sgs[i] if i < len(gt_sgs) else {}

        for field, tol_key, label in [
            ("dcr_experimental", "subgroup_dcr_exp", f"sg_{i}_dcr_exp"),
            ("dcr_control", "subgroup_dcr_ctrl", f"sg_{i}_dcr_ctrl"),
            ("dcr_difference", "subgroup_dcr_diff", f"sg_{i}_dcr_diff"),
        ]:
            tol = tol_spec.get(tol_key, {})
            r = compare_numeric(ag_s.get(field), gt_s.get(field), tol, label)
            component_scores[label] = r
            weighted_sum += r["score"] * tol.get("weight", 0.10)
            total_weight += tol.get("weight", 0.10)

        # Subgroup N counts
        sg_n_tol = tol_spec.get("subgroup_n", {})
        for field, label in [("n_experimental", f"sg_{i}_n_exp"), ("n_control", f"sg_{i}_n_ctrl")]:
            r = compare_count(ag_s.get(field), gt_s.get(field))
            component_scores[label] = r
            weighted_sum += r["score"] * sg_n_tol.get("weight", 0.10)
            total_weight += sg_n_tol.get("weight", 0.10)

    # BOR distribution
    bor_tol = tol_spec.get("bor_counts", {})
    ag_bor = agent_output.get("bor_distribution", [])
    gt_bor = ground_truth.get("bor_distribution", [])
    for i in range(min(len(ag_bor), len(gt_bor))):
        r = compare_count(ag_bor[i].get("n"), gt_bor[i].get("n"))
        component_scores[f"bor_{i}"] = r
        weighted_sum += r["score"] * bor_tol.get("weight", 0.10)
        total_weight += bor_tol.get("weight", 0.10)

    final_score = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0

    return {
        "test_case_id": "TC-023",
        "score": final_score,
        "component_scores": component_scores,
        "agent_language": agent_output.get("language", "unknown"),
        "ground_truth_language": ground_truth.get("language", "unknown"),
        "variant_id": agent_output.get("variant_id"),
    }


# --------------------------------------------------------------------
# TC-024: Overall Survival (OS) KM Median
# --------------------------------------------------------------------

def score_tc024(agent_output: dict, ground_truth: dict, tolerances: dict) -> dict:
    """Score TC-024 (Overall Survival) agent output against ground truth.

    Compares median OS, HR, log-rank p-value, event rates, and subgroup medians.
    Similar structure to TC-001 but for OS endpoint.
    """
    tol_spec = tolerances.get("TC-024", {}).get("tolerances", {})
    component_scores = {}
    weighted_sum = 0.0
    total_weight = 0.0

    # Compare both arms
    for arm_key, arm_label in [("arm_control", "ctrl"), ("arm_experimental", "exp")]:
        ag_arm = agent_output.get(arm_key, {})
        gt_arm = ground_truth.get(arm_key, {})

        for field, tol_key, label in [
            ("median_os", f"{arm_label}_median_os", f"{arm_label}_median"),
            ("hazard_ratio", f"{arm_label}_hr", f"{arm_label}_hr"),
            ("event_rate", f"{arm_label}_event_rate", f"{arm_label}_event_rate"),
            ("logrank_p", f"{arm_label}_logrank_p", f"{arm_label}_logrank_p"),
        ]:
            tol = tol_spec.get(tol_key, {})
            r = compare_numeric(ag_arm.get(field), gt_arm.get(field), tol, label)
            component_scores[label] = r
            weighted_sum += r["score"] * tol.get("weight", 0.10)
            total_weight += tol.get("weight", 0.10)

        # N counts
        for field, label in [("n_events", f"{arm_label}_n_events"), ("n_total", f"{arm_label}_n_total")]:
            r = compare_count(ag_arm.get(field), gt_arm.get(field))
            component_scores[label] = r
            weighted_sum += r["score"] * 0.05
            total_weight += 0.05

    # Censoring summary
    ag_cens = agent_output.get("censoring_summary", {})
    gt_cens = ground_truth.get("censoring_summary", {})
    cens_tol = tol_spec.get("censoring_rate", {})
    r = compare_numeric(ag_cens.get("censoring_rate"), gt_cens.get("censoring_rate"), cens_tol, "censoring_rate")
    component_scores["censoring_rate"] = r
    weighted_sum += r["score"] * cens_tol.get("weight", 0.05)
    total_weight += cens_tol.get("weight", 0.05)

    # Subgroup medians
    ag_sgs = agent_output.get("subgroups", [])
    gt_sgs = ground_truth.get("subgroups", [])
    sg_tol = tol_spec.get("subgroup_median", {})
    for i in range(min(len(ag_sgs), len(gt_sgs))):
        ag_s = ag_sgs[i] if i < len(ag_sgs) else {}
        gt_s = gt_sgs[i] if i < len(gt_sgs) else {}
        for field, label in [("median_exp", f"sg_{i}_median_exp"), ("median_ctrl", f"sg_{i}_median_ctrl")]:
            r = compare_numeric(ag_s.get(field), gt_s.get(field), sg_tol, label)
            component_scores[label] = r
            weighted_sum += r["score"] * sg_tol.get("weight", 0.03)
            total_weight += sg_tol.get("weight", 0.03)

    final_score = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0

    return {
        "test_case_id": "TC-024",
        "score": final_score,
        "component_scores": component_scores,
        "agent_language": agent_output.get("language", "unknown"),
        "ground_truth_language": ground_truth.get("language", "unknown"),
        "variant_id": agent_output.get("variant_id"),
    }


# --------------------------------------------------------------------
# TC-025: Best Overall Response (BOR) Summary
# --------------------------------------------------------------------

def score_tc025(agent_output: dict, ground_truth: dict, tolerances: dict) -> dict:
    """Score TC-025 (BOR Summary) agent output against ground truth.

    Compares BOR counts, ORR, DCR, Fisher exact p-value, and ORR difference.
    Cross-TFL consistency with TC-020 (ORR) and TC-023 (DCR).
    """
    tol_spec = tolerances.get("TC-025", {}).get("tolerances", {})
    component_scores = {}
    weighted_sum = 0.0
    total_weight = 0.0

    ag_summary = agent_output.get("summary", {})
    gt_summary = ground_truth.get("summary", {})

    # By-arm comparison
    for arm_key in ["0", "1"]:
        ag_arm = ag_summary.get("by_arm", {}).get(arm_key, {})
        gt_arm = gt_summary.get("by_arm", {}).get(arm_key, {})
        arm_label = "ctrl" if arm_key == "0" else "exp"

        # BOR counts
        ag_bor = ag_arm.get("bor_counts", {})
        gt_bor = gt_arm.get("bor_counts", {})
        bor_tol = tol_spec.get("bor_counts", {})
        for bor_val in ["CR", "PR", "SD", "PD", "NE"]:
            r = compare_count(ag_bor.get(bor_val), gt_bor.get(bor_val))
            component_scores[f"{arm_label}_bor_{bor_val}"] = r
            weighted_sum += r["score"] * bor_tol.get("weight", 0.05)
            total_weight += bor_tol.get("weight", 0.05)

        # ORR and DCR
        for field, tol_key, label in [
            ("orr_rate", f"{arm_label}_orr_rate", f"{arm_label}_orr"),
            ("dcr_rate", f"{arm_label}_dcr_rate", f"{arm_label}_dcr"),
        ]:
            tol = tol_spec.get(tol_key, {})
            r = compare_numeric(ag_arm.get(field), gt_arm.get(field), tol, label)
            component_scores[label] = r
            weighted_sum += r["score"] * tol.get("weight", 0.08)
            total_weight += tol.get("weight", 0.08)

        # N total
        r = compare_count(ag_arm.get("n_total"), gt_arm.get("n_total"))
        component_scores[f"{arm_label}_n_total"] = r
        weighted_sum += r["score"] * 0.03
        total_weight += 0.03

    # ORR difference and tests
    for field, tol_key, label in [
        ("orr_difference", "orr_difference", "orr_diff"),
        ("fisher_exact_p", "fisher_p", "fisher_p"),
    ]:
        tol = tol_spec.get(tol_key, {})
        r = compare_numeric(ag_summary.get(field), gt_summary.get(field), tol, label)
        component_scores[label] = r
        weighted_sum += r["score"] * tol.get("weight", 0.06)
        total_weight += tol.get("weight", 0.06)

    final_score = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0

    return {
        "test_case_id": "TC-025",
        "score": final_score,
        "component_scores": component_scores,
        "agent_language": agent_output.get("language", "unknown"),
        "ground_truth_language": ground_truth.get("language", "unknown"),
        "variant_id": agent_output.get("variant_id"),
    }


# --------------------------------------------------------------------
# TC-026: Time to Second Progression (PFS2)
# --------------------------------------------------------------------

def score_tc026(agent_output: dict, ground_truth: dict, tolerances: dict) -> dict:
    """Score TC-026 (PFS2) agent output against ground truth.

    Compares median PFS2, HR, log-rank p-value, event rates, CI bounds,
    and subgroup medians. Similar structure to TC-024 but for PFS2 endpoint.
    """
    tol_spec = tolerances.get("TC-026", {}).get("tolerances", {})
    component_scores = {}
    weighted_sum = 0.0
    total_weight = 0.0

    for arm_key, arm_label in [("arm_control", "ctrl"), ("arm_experimental", "exp")]:
        ag_arm = agent_output.get(arm_key, {})
        gt_arm = ground_truth.get(arm_key, {})

        for field, tol_key, label in [
            ("median_pfs2", f"{arm_label}_median_pfs2", f"{arm_label}_median"),
            ("median_ci_lower", f"{arm_label}_median_ci_lower", f"{arm_label}_ci_lower"),
            ("median_ci_upper", f"{arm_label}_median_ci_upper", f"{arm_label}_ci_upper"),
            ("hazard_ratio", "hr", f"{arm_label}_hr"),
            ("logrank_p", "logrank_p", f"{arm_label}_logrank_p"),
        ]:
            tol = tol_spec.get(tol_key, {})
            r = compare_numeric(ag_arm.get(field), gt_arm.get(field), tol, label)
            component_scores[label] = r
            weighted_sum += r["score"] * tol.get("weight", 0.10)
            total_weight += tol.get("weight", 0.10)

        for field, label in [("n_events", f"{arm_label}_n_events"), ("n_total", f"{arm_label}_n_total")]:
            tol = tol_spec.get(label, {})
            r = compare_count(ag_arm.get(field), gt_arm.get(field))
            component_scores[label] = r
            weighted_sum += r["score"] * tol.get("weight", 0.04)
            total_weight += tol.get("weight", 0.04)

    # Censoring summary
    ag_cens = agent_output.get("censoring_summary", {})
    gt_cens = ground_truth.get("censoring_summary", {})
    cens_tol = tol_spec.get("censoring_rate", {})
    r = compare_numeric(ag_cens.get("censoring_rate"), gt_cens.get("censoring_rate"), cens_tol, "censoring_rate")
    component_scores["censoring_rate"] = r
    weighted_sum += r["score"] * cens_tol.get("weight", 0.04)
    total_weight += cens_tol.get("weight", 0.04)

    # Subgroup medians
    ag_sgs = agent_output.get("subgroups", [])
    gt_sgs = ground_truth.get("subgroups", [])
    for i in range(min(len(ag_sgs), len(gt_sgs))):
        ag_s = ag_sgs[i] if i < len(ag_sgs) else {}
        gt_s = gt_sgs[i] if i < len(gt_sgs) else {}
        for field, label in [("median_exp", f"sg_{i}_median_exp"), ("median_ctrl", f"sg_{i}_median_ctrl")]:
            sg_tol = {"absolute": 0.05}
            r = compare_numeric(ag_s.get(field), gt_s.get(field), sg_tol, label)
            component_scores[label] = r
            weighted_sum += r["score"] * 0.02
            total_weight += 0.02

    final_score = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0

    return {
        "test_case_id": "TC-026",
        "score": final_score,
        "component_scores": component_scores,
        "agent_language": agent_output.get("language", "unknown"),
        "ground_truth_language": ground_truth.get("language", "unknown"),
        "variant_id": agent_output.get("variant_id"),
    }


def score_tc027(agent_output: dict, ground_truth: dict, tolerances: dict) -> dict:
    """Score TC-027 (DOSD) agent output against ground truth.

    Compares median DOSD, HR, log-rank p-value, event rates, CI bounds,
    and subgroup medians. Similar structure to TC-022 (DOR) but for
    the Duration of Stable Disease endpoint (BOR=SD subset).
    """
    tol_spec = tolerances.get("TC-027", {}).get("tolerances", {})
    component_scores = {}
    weighted_sum = 0.0
    total_weight = 0.0

    for arm_key, arm_label in [("arm_control", "ctrl"), ("arm_experimental", "exp")]:
        ag_arm = agent_output.get(arm_key, {})
        gt_arm = ground_truth.get(arm_key, {})

        for field, tol_key, label in [
            ("median_dosd", f"{arm_label}_median_dosd", f"{arm_label}_median"),
            ("median_ci_lower", f"{arm_label}_median_ci_lower", f"{arm_label}_ci_lower"),
            ("median_ci_upper", f"{arm_label}_median_ci_upper", f"{arm_label}_ci_upper"),
            ("hazard_ratio", "hr", f"{arm_label}_hr"),
            ("logrank_p", "logrank_p", f"{arm_label}_logrank_p"),
        ]:
            tol = tol_spec.get(tol_key, {})
            r = compare_numeric(ag_arm.get(field), gt_arm.get(field), tol, label)
            component_scores[label] = r
            weighted_sum += r["score"] * tol.get("weight", 0.10)
            total_weight += tol.get("weight", 0.10)

        for field, label in [("n_sd", f"{arm_label}_n_sd"), ("n_events", f"{arm_label}_n_events"), ("n_total", f"{arm_label}_n_total")]:
            tol = tol_spec.get(label, {})
            r = compare_count(ag_arm.get(field), gt_arm.get(field))
            component_scores[label] = r
            weighted_sum += r["score"] * tol.get("weight", 0.03)
            total_weight += tol.get("weight", 0.03)

    # Censoring summary
    ag_cens = agent_output.get("censoring_summary", {})
    gt_cens = ground_truth.get("censoring_summary", {})
    cens_tol = tol_spec.get("censoring_rate", {})
    r = compare_numeric(ag_cens.get("censoring_rate"), gt_cens.get("censoring_rate"), cens_tol, "censoring_rate")
    component_scores["censoring_rate"] = r
    weighted_sum += r["score"] * cens_tol.get("weight", 0.04)
    total_weight += cens_tol.get("weight", 0.04)

    # Subgroup medians
    ag_sgs = agent_output.get("subgroups", [])
    gt_sgs = ground_truth.get("subgroups", [])
    for i in range(min(len(ag_sgs), len(gt_sgs))):
        ag_s = ag_sgs[i] if i < len(ag_sgs) else {}
        gt_s = gt_sgs[i] if i < len(gt_sgs) else {}
        for field, label in [("median_exp", f"sg_{i}_median_exp"), ("median_ctrl", f"sg_{i}_median_ctrl")]:
            sg_tol = {"absolute": 0.05}
            r = compare_numeric(ag_s.get(field), gt_s.get(field), sg_tol, label)
            component_scores[label] = r
            weighted_sum += r["score"] * 0.02
            total_weight += 0.02

    final_score = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0

    return {
        "test_case_id": "TC-027",
        "score": final_score,
        "component_scores": component_scores,
        "agent_language": agent_output.get("language", "unknown"),
        "ground_truth_language": ground_truth.get("language", "unknown"),
        "variant_id": agent_output.get("variant_id"),
    }


# --------------------------------------------------------------------
# TC-028: Change in Tumor Size by Cycle (Longitudinal)
# --------------------------------------------------------------------

def score_tc028(agent_output: dict, ground_truth: dict, tolerances: dict) -> dict:
    """Score TC-028 (Change in Tumor Size by Cycle) agent output.

    Compares visit-wise summary statistics (mean, median, SE, N assessed)
    for each cycle and arm, plus overall arm-level best/worst % change
    summaries.
    """
    tol_spec = tolerances.get("TC-028", {}).get("tolerances", {})
    component_scores = {}
    weighted_sum = 0.0
    total_weight = 0.0

    ag_visits = agent_output.get("visit_summaries", {})
    gt_visits = ground_truth.get("visit_summaries", {})

    # Visit-wise comparison for each cycle and arm
    for cycle in gt_visits:
        gt_cycle = gt_visits.get(cycle, {})
        ag_cycle = ag_visits.get(cycle, {})
        for arm_key, arm_label in [("experimental", "exp"), ("control", "ctrl")]:
            gt_arm = gt_cycle.get(arm_key, {})
            ag_arm = ag_cycle.get(arm_key, {})

            # Mean % change
            tol = tol_spec.get(f"{arm_label}_mean_pct_change", {})
            r = compare_numeric(ag_arm.get("mean_pct_change"), gt_arm.get("mean_pct_change"),
                               tol, f"{cycle}_{arm_label}_mean_pct")
            component_scores[f"{cycle}_{arm_label}_mean_pct"] = r
            weighted_sum += r["score"] * tol.get("weight", 0.025)
            total_weight += tol.get("weight", 0.025)

            # Median % change
            tol = tol_spec.get(f"{arm_label}_median_pct_change", {})
            r = compare_numeric(ag_arm.get("median_pct_change"), gt_arm.get("median_pct_change"),
                               tol, f"{cycle}_{arm_label}_median_pct")
            component_scores[f"{cycle}_{arm_label}_median_pct"] = r
            weighted_sum += r["score"] * tol.get("weight", 0.017)
            total_weight += tol.get("weight", 0.017)

            # SE
            tol = tol_spec.get("se_pct_change", {})
            r = compare_numeric(ag_arm.get("se_pct_change"), gt_arm.get("se_pct_change"),
                               tol, f"{cycle}_{arm_label}_se_pct")
            component_scores[f"{cycle}_{arm_label}_se_pct"] = r
            weighted_sum += r["score"] * tol.get("weight", 0.013)
            total_weight += tol.get("weight", 0.013)

            # N assessed (exact match)
            tol = tol_spec.get("n_assessed", {})
            r = compare_count(ag_arm.get("n_assessed"), gt_arm.get("n_assessed"))
            component_scores[f"{cycle}_{arm_label}_n_assessed"] = r
            weighted_sum += r["score"] * tol.get("weight", 0.017)
            total_weight += tol.get("weight", 0.017)

    # Overall arm-level summaries
    ag_overall = agent_output.get("overall_summary", {})
    gt_overall = ground_truth.get("overall_summary", {})
    for arm_key, arm_label in [("experimental", "exp"), ("control", "ctrl")]:
        ag_arm = ag_overall.get(arm_key, {})
        gt_arm = gt_overall.get(arm_key, {})

        # Mean best % change
        tol = tol_spec.get(f"overall_mean_best_{arm_label}", {})
        r = compare_numeric(ag_arm.get("mean_best_pct_change"), gt_arm.get("mean_best_pct_change"),
                           tol, f"overall_{arm_label}_mean_best")
        component_scores[f"overall_{arm_label}_mean_best"] = r
        weighted_sum += r["score"] * tol.get("weight", 0.10)
        total_weight += tol.get("weight", 0.10)

        # Median best % change
        tol = tol_spec.get(f"overall_median_best_{arm_label}", {})
        r = compare_numeric(ag_arm.get("median_best_pct_change"), gt_arm.get("median_best_pct_change"),
                           tol, f"overall_{arm_label}_median_best")
        component_scores[f"overall_{arm_label}_median_best"] = r
        weighted_sum += r["score"] * tol.get("weight", 0.05)
        total_weight += tol.get("weight", 0.05)

        # N per arm
        tol = tol_spec.get("n_per_arm", {})
        r = compare_count(ag_arm.get("n_subjects"), gt_arm.get("n_subjects"))
        component_scores[f"overall_{arm_label}_n_subjects"] = r
        weighted_sum += r["score"] * tol.get("weight", 0.02)
        total_weight += tol.get("weight", 0.02)

    final_score = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0

    return {
        "test_case_id": "TC-028",
        "score": final_score,
        "component_scores": component_scores,
        "agent_language": agent_output.get("language", agent_output.get("metadata", {}).get("language", "unknown")),
        "ground_truth_language": ground_truth.get("language", ground_truth.get("metadata", {}).get("language", "unknown")),
        "variant_id": agent_output.get("variant_id"),
    }


# --------------------------------------------------------------------
# TC-029: Adverse Event Summary Table by SOC, PT, and Severity
# --------------------------------------------------------------------

def _ae_severity_table_index(output: dict) -> dict:
    """Index AE severity table rows by (soc, pt, severity) for aligned comparison.

    Handles rows with category in {soc, soc_severity, pt, pt_severity}.
    Summary rows and severity_summary are handled separately.
    """
    idx = {}
    for row in output.get("ae_table", []) or []:
        soc = row.get("soc")
        pt = row.get("pt")
        sev = row.get("severity")
        cat = row.get("category")
        idx[(soc, pt, sev, cat)] = {
            "n_experimental": row.get("n_experimental"),
            "pct_experimental": row.get("pct_experimental"),
            "n_control": row.get("n_control"),
            "pct_control": row.get("pct_control"),
        }
    return idx


def score_tc029(agent_output: dict, ground_truth: dict, tolerances: dict) -> dict:
    """Score TC-029 (AE Summary by SOC, PT, and Severity).

    Compares:
    - Severity summary (grade 1-5 per arm, n and pct)
    - Overall summary rows (Any AE, SAE, discontinuation)
    - Detailed AE table (SOC/PT/severity cells, n and pct)
    - N per arm from population block
    """
    tol_spec = tolerances.get("TC-029", {}).get("tolerances", {})
    component_scores = {}
    total_weight = 0
    weighted_sum = 0

    # --- Severity summary (grade 1-5) ---
    ag_sev = agent_output.get("severity_summary", []) or []
    gt_sev = ground_truth.get("severity_summary", []) or []
    gt_sev_idx = {s.get("grade"): s for s in gt_sev}
    ag_sev_idx = {s.get("grade"): s for s in ag_sev}

    for grade in [1, 2, 3, 4, 5]:
        gt_row = gt_sev_idx.get(grade, {})
        ag_row = ag_sev_idx.get(grade, {})

        # Counts (exact match)
        for arm_field, label in [("n_experimental", f"sev_g{grade}_n_exp"),
                                 ("n_control", f"sev_g{grade}_n_ctl")]:
            w = tol_spec.get("severity_n", {}).get("weight", 0.20) / 10  # 5 grades x 2 arms
            r = compare_count(ag_row.get(arm_field), gt_row.get(arm_field))
            component_scores[label] = r
            weighted_sum += r["score"] * w
            total_weight += w

        # Percentages (tolerance)
        for arm_field, label in [("pct_experimental", f"sev_g{grade}_pct_exp"),
                                 ("pct_control", f"sev_g{grade}_pct_ctl")]:
            field_tol = {"absolute": tol_spec.get("severity_pct", {}).get("absolute", 0.1)}
            w = tol_spec.get("severity_pct", {}).get("weight", 0.10) / 10
            r = compare_numeric(ag_row.get(arm_field), gt_row.get(arm_field),
                                field_tol, label)
            component_scores[label] = r
            weighted_sum += r["score"] * w
            total_weight += w

    # --- Overall summary rows (Any AE, SAE, discontinuation) ---
    ag_summary = agent_output.get("summary", []) or []
    gt_summary = ground_truth.get("summary", []) or []
    gt_sum_idx = {s.get("category"): s for s in gt_summary}
    ag_sum_idx = {s.get("category"): s for s in ag_summary}

    n_summary = max(len(gt_summary), 1)
    for cat in gt_sum_idx:
        gt_row = gt_sum_idx[cat]
        ag_row = ag_sum_idx.get(cat, {})

        for arm_field, label in [("n_experimental", f"sum_{cat[:10]}_n_exp"),
                                 ("n_control", f"sum_{cat[:10]}_n_ctl")]:
            w = tol_spec.get("summary_n", {}).get("weight", 0.15) / (n_summary * 2)
            r = compare_count(ag_row.get(arm_field), gt_row.get(arm_field))
            component_scores[label] = r
            weighted_sum += r["score"] * w
            total_weight += w

        for arm_field, label in [("pct_experimental", f"sum_{cat[:10]}_pct_exp"),
                                 ("pct_control", f"sum_{cat[:10]}_pct_ctl")]:
            field_tol = {"absolute": tol_spec.get("summary_pct", {}).get("absolute", 0.1)}
            w = tol_spec.get("summary_pct", {}).get("weight", 0.10) / (n_summary * 2)
            r = compare_numeric(ag_row.get(arm_field), gt_row.get(arm_field),
                                field_tol, label)
            component_scores[label] = r
            weighted_sum += r["score"] * w
            total_weight += w

    # --- Detailed AE table (SOC/PT/severity cells) ---
    ag_idx = _ae_severity_table_index(agent_output)
    gt_idx = _ae_severity_table_index(ground_truth)

    n_detail = max(len(gt_idx), 1)
    for key, gt_row in gt_idx.items():
        ag_row = ag_idx.get(key, {})
        soc_label = str(key[0])[:20] if key[0] else "?"
        pt_label = str(key[1])[:15] if key[1] else "None"
        sev_label = str(key[2]) if key[2] is not None else "NA"
        cat_label = str(key[3])[:5] if key[3] else "?"
        label_base = f"{soc_label}_{pt_label}_g{sev_label}_{cat_label}"

        for arm_field, suffix in [("n_experimental", "n_exp"), ("n_control", "n_ctl")]:
            w = tol_spec.get("ae_table_n", {}).get("weight", 0.25) / (n_detail * 2)
            r = compare_count(ag_row.get(arm_field), gt_row.get(arm_field))
            component_scores[f"{label_base}_{suffix}"] = r
            weighted_sum += r["score"] * w
            total_weight += w

        for arm_field, suffix in [("pct_experimental", "pct_exp"), ("pct_control", "pct_ctl")]:
            field_tol = {"absolute": tol_spec.get("ae_table_pct", {}).get("absolute", 0.1)}
            w = tol_spec.get("ae_table_pct", {}).get("weight", 0.10) / (n_detail * 2)
            r = compare_numeric(ag_row.get(arm_field), gt_row.get(arm_field),
                                field_tol, f"{label_base}_{suffix}")
            component_scores[f"{label_base}_{suffix}"] = r
            weighted_sum += r["score"] * w
            total_weight += w

    # --- N per arm from population block ---
    pop = ground_truth.get("population", {})
    agent_pop = agent_output.get("population", {})
    for field, label in [("n_experimental", "pop_n_exp"), ("n_control", "pop_n_ctl")]:
        w = tol_spec.get("n_per_arm", {}).get("weight", 0.10) / 2
        r = compare_count(agent_pop.get(field), pop.get(field))
        component_scores[label] = r
        weighted_sum += r["score"] * w
        total_weight += w

    final_score = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0

    return {
        "test_case_id": "TC-029",
        "score": final_score,
        "component_scores": component_scores,
        "agent_language": agent_output.get("language", agent_output.get("metadata", {}).get("language", "unknown")),
        "ground_truth_language": ground_truth.get("language", ground_truth.get("metadata", {}).get("language", "unknown")),
        "variant_id": agent_output.get("variant_id"),
    }


# --------------------------------------------------------------------
# TC-033: Dose Intensity Summary (Level 1)
# --------------------------------------------------------------------

def score_tc033(agent_output: dict, ground_truth: dict, tolerances: dict) -> dict:
    """Score TC-033 (Dose Intensity Summary).

    Compares RDI summary stats (mean, SD, median, min, max),
    % subjects with RDI >= 80%, dose reduction counts/pct,
    dose interruption counts/pct, and treatment duration summary.
    """
    tol_spec = tolerances.get("TC-033", {}).get("tolerances", {})
    component_scores = {}
    weighted_sum = 0.0
    total_weight = 0.0

    def _score_numeric(agent_val, truth_val, tol, key):
        """Score a numeric value with absolute and relative tolerance."""
        if agent_val is None or truth_val is None:
            return 0.0, False, f"{key}: missing value"
        abs_tol = tol.get("absolute", 0.01)
        rel_tol = tol.get("relative", 0.0)
        abs_diff = abs(agent_val - truth_val)
        rel_diff = abs_diff / max(abs(truth_val), 1e-10)
        passed = abs_diff <= abs_tol or rel_diff <= rel_tol
        score = 1.0 if passed else max(0.0, 1.0 - abs_diff / max(abs_tol, 1e-10))
        return score, passed, f"{key}: agent={agent_val:.4f} truth={truth_val:.4f} diff={abs_diff:.6f}"

    def _score_summary(agent_sum, truth_sum, tol, prefix):
        """Score a continuous summary block (mean, sd, median, min, max, q1, q3)."""
        results = {}
        for field in ["mean", "sd", "median", "min", "max", "q1", "q3"]:
            sub_tol = tol.get(prefix, tol)
            s, p, note = _score_numeric(
                agent_sum.get(field), truth_sum.get(field), sub_tol, f"{prefix}.{field}"
            )
            results[f"{prefix}.{field}"] = {"score": s, "pass": p, "note": note}
        return results

    # --- RDI summary by arm ---
    for arm in ["experimental", "control"]:
        arm_tol = tol_spec.get(f"rdi_summary_{arm}", tol_spec.get("rdi_summary", {}))
        arm_results = _score_summary(
            agent_output.get("rdi_summary", {}).get(arm, {}),
            ground_truth.get("rdi_summary", {}).get(arm, {}),
            arm_tol,
            f"rdi_{arm}",
        )
        weight = arm_tol.get("weight", 0.10)
        for k, v in arm_results.items():
            component_scores[k] = v
            weighted_sum += v["score"] * (weight / len(arm_results))
            total_weight += weight / len(arm_results)

    # --- RDI >= 80% counts/pct ---
    for arm in ["experimental", "control"]:
        for metric in ["n", "pct"]:
            tol_key = f"rdi_ge80_{arm}_{metric}"
            sub_tol = tol_spec.get(tol_key, {})
            s, p, note = _score_numeric(
                agent_output.get("rdi_ge80", {}).get(arm, {}).get(metric),
                ground_truth.get("rdi_ge80", {}).get(arm, {}).get(metric),
                sub_tol,
                f"rdi_ge80.{arm}.{metric}",
            )
            component_scores[f"rdi_ge80.{arm}.{metric}"] = {"score": s, "pass": p, "note": note}
            w = sub_tol.get("weight", 0.05)
            weighted_sum += s * w
            total_weight += w

    # --- Dose reduction counts/pct ---
    for arm in ["experimental", "control"]:
        for metric in ["n", "pct"]:
            tol_key = f"dose_reduction_{arm}_{metric}"
            sub_tol = tol_spec.get(tol_key, {})
            s, p, note = _score_numeric(
                agent_output.get("dose_reduction", {}).get(arm, {}).get(metric),
                ground_truth.get("dose_reduction", {}).get(arm, {}).get(metric),
                sub_tol,
                f"dose_reduction.{arm}.{metric}",
            )
            component_scores[f"dose_reduction.{arm}.{metric}"] = {"score": s, "pass": p, "note": note}
            w = sub_tol.get("weight", 0.05)
            weighted_sum += s * w
            total_weight += w

    # --- Dose interruption counts/pct ---
    for arm in ["experimental", "control"]:
        for metric in ["n", "pct"]:
            tol_key = f"dose_interruption_{arm}_{metric}"
            sub_tol = tol_spec.get(tol_key, {})
            s, p, note = _score_numeric(
                agent_output.get("dose_interruption", {}).get(arm, {}).get(metric),
                ground_truth.get("dose_interruption", {}).get(arm, {}).get(metric),
                sub_tol,
                f"dose_interruption.{arm}.{metric}",
            )
            component_scores[f"dose_interruption.{arm}.{metric}"] = {"score": s, "pass": p, "note": note}
            w = sub_tol.get("weight", 0.05)
            weighted_sum += s * w
            total_weight += w

    # --- Treatment duration summary ---
    for arm in ["experimental", "control"]:
        arm_tol = tol_spec.get(f"treatdur_{arm}", tol_spec.get("treatment_duration", {}))
        arm_results = _score_summary(
            agent_output.get("treatment_duration", {}).get(arm, {}),
            ground_truth.get("treatment_duration", {}).get(arm, {}),
            arm_tol,
            f"treatdur_{arm}",
        )
        weight = arm_tol.get("weight", 0.05)
        for k, v in arm_results.items():
            component_scores[k] = v
            weighted_sum += v["score"] * (weight / len(arm_results))
            total_weight += weight / len(arm_results)

    # --- N per arm ---
    for arm_key, arm_label in [("n_total", "total"), ("n_experimental", "exp"), ("n_control", "ctl")]:
        tol_key = f"n_{arm_label}"
        sub_tol = tol_spec.get(tol_key, {})
        s, p, note = _score_numeric(
            agent_output.get("metadata", {}).get(arm_key),
            ground_truth.get("metadata", {}).get(arm_key),
            sub_tol,
            f"metadata.{arm_key}",
        )
        component_scores[f"metadata.{arm_key}"] = {"score": s, "pass": p, "note": note}
        w = sub_tol.get("weight", 0.02)
        weighted_sum += s * w
        total_weight += w

    overall = weighted_sum / total_weight if total_weight > 0 else 0.0

    return {
        "test_case_id": "TC-033",
        "score": round(overall, 4),
        "component_scores": component_scores,
        "agent_language": agent_output.get("language", agent_output.get("metadata", {}).get("language", "unknown")),
        "ground_truth_language": ground_truth.get("language", ground_truth.get("metadata", {}).get("language", "unknown")),
        "variant_id": agent_output.get("variant_id"),
    }


# --------------------------------------------------------------------
# TC-030: ORR by Subgroup with Interaction Test (Level 1)
# --------------------------------------------------------------------

def score_tc030(agent_output: dict, ground_truth: dict, tolerances: dict) -> dict:
    """Score TC-030: ORR by Subgroup with Interaction Test.

    Compares overall ORR, subgroup-level ORR with Clopper-Pearson CIs,
    logistic regression interaction p-values, interaction ORs, and
    Breslow-Day test p-values.
    """
    tol_spec = tolerances.get("TC-030", {}).get("tolerances", {})
    component_scores = {}
    weighted_sum = 0.0
    total_weight = 0.0

    # Overall ORR
    ag_ov = agent_output.get("overall", {})
    gt_ov = ground_truth.get("overall", {})

    for field, tol_key, label in [
        ("orr_experimental", "overall_orr_exp", "orr_exp"),
        ("orr_control", "overall_orr_ctrl", "orr_ctrl"),
        ("orr_difference", "overall_orr_diff", "orr_diff"),
    ]:
        tol = tol_spec.get(tol_key, {})
        r = compare_numeric(ag_ov.get(field), gt_ov.get(field), tol, label)
        component_scores[f"overall_{label}"] = r
        weighted_sum += r["score"] * tol.get("weight", 0.08)
        total_weight += tol.get("weight", 0.08)

    # Responder counts (exact match)
    res_tol = tol_spec.get("responder_counts", {})
    for field, label in [("responders_experimental", "resp_exp"), ("responders_control", "resp_ctrl")]:
        r = compare_count(ag_ov.get(field), gt_ov.get(field))
        component_scores[f"overall_{label}"] = r
        weighted_sum += r["score"] * res_tol.get("weight", 0.05)
        total_weight += res_tol.get("weight", 0.05)

    # Overall CI bounds (Clopper-Pearson)
    ci_tol = tol_spec.get("overall_ci", {})
    for field, label in [
        ("ci_lower_experimental", "ci_lo_exp"),
        ("ci_upper_experimental", "ci_hi_exp"),
        ("ci_lower_control", "ci_lo_ctrl"),
        ("ci_upper_control", "ci_hi_ctrl"),
    ]:
        r = compare_numeric(ag_ov.get(field), gt_ov.get(field), ci_tol, label)
        component_scores[f"overall_{label}"] = r
        weighted_sum += r["score"] * ci_tol.get("weight", 0.03)
        total_weight += ci_tol.get("weight", 0.03)

    # Subgroup-level
    ag_sgs = agent_output.get("subgroups", [])
    gt_sgs = ground_truth.get("subgroups", [])

    for i in range(min(len(ag_sgs), len(gt_sgs))):
        ag_s = ag_sgs[i] if i < len(ag_sgs) else {}
        gt_s = gt_sgs[i] if i < len(gt_sgs) else {}

        for field, tol_key, label in [
            ("orr_experimental", "subgroup_orr_exp", f"sg_{i}_orr_exp"),
            ("orr_control", "subgroup_orr_ctrl", f"sg_{i}_orr_ctrl"),
            ("orr_difference", "subgroup_orr_diff", f"sg_{i}_orr_diff"),
        ]:
            tol = tol_spec.get(tol_key, {})
            r = compare_numeric(ag_s.get(field), gt_s.get(field), tol, label)
            component_scores[label] = r
            weighted_sum += r["score"] * tol.get("weight", 0.05)
            total_weight += tol.get("weight", 0.05)

        # N per subgroup per arm (exact match)
        sg_n_tol = tol_spec.get("subgroup_n", {})
        for field, label in [("n_experimental", f"sg_{i}_n_exp"), ("n_control", f"sg_{i}_n_ctrl")]:
            r = compare_count(ag_s.get(field), gt_s.get(field))
            component_scores[label] = r
            weighted_sum += r["score"] * sg_n_tol.get("weight", 0.03)
            total_weight += sg_n_tol.get("weight", 0.03)

        # Subgroup CI bounds (Clopper-Pearson)
        sg_ci_tol = tol_spec.get("subgroup_ci", {})
        for field, label in [
            ("ci_lower_experimental", f"sg_{i}_ci_lo_exp"),
            ("ci_upper_experimental", f"sg_{i}_ci_hi_exp"),
            ("ci_lower_control", f"sg_{i}_ci_lo_ctrl"),
            ("ci_upper_control", f"sg_{i}_ci_hi_ctrl"),
        ]:
            r = compare_numeric(ag_s.get(field), gt_s.get(field), sg_ci_tol, label)
            component_scores[label] = r
            weighted_sum += r["score"] * sg_ci_tol.get("weight", 0.02)
            total_weight += sg_ci_tol.get("weight", 0.02)

    # Interaction tests (logistic regression)
    ag_ints = agent_output.get("interaction_tests", [])
    gt_ints = ground_truth.get("interaction_tests", [])

    for i in range(min(len(ag_ints), len(gt_ints))):
        ag_i = ag_ints[i] if i < len(ag_ints) else {}
        gt_i = gt_ints[i] if i < len(gt_ints) else {}

        # Interaction p-value
        int_tol = tol_spec.get("interaction_p", {})
        r = compare_numeric(ag_i.get("interaction_p_value"), gt_i.get("interaction_p_value"), int_tol, f"int_p_{i}")
        component_scores[f"int_p_{i}"] = r
        weighted_sum += r["score"] * int_tol.get("weight", 0.08)
        total_weight += int_tol.get("weight", 0.08)

        # Interaction OR
        or_tol = tol_spec.get("interaction_or", {})
        r = compare_numeric(ag_i.get("interaction_or"), gt_i.get("interaction_or"), or_tol, f"int_or_{i}")
        component_scores[f"int_or_{i}"] = r
        weighted_sum += r["score"] * or_tol.get("weight", 0.05)
        total_weight += or_tol.get("weight", 0.05)

        # Breslow-Day p-value
        bd_tol = tol_spec.get("breslow_day_p", {})
        r = compare_numeric(ag_i.get("breslow_day_p_value"), gt_i.get("breslow_day_p_value"), bd_tol, f"bd_p_{i}")
        component_scores[f"bd_p_{i}"] = r
        weighted_sum += r["score"] * bd_tol.get("weight", 0.05)
        total_weight += bd_tol.get("weight", 0.05)

    final_score = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0
    return {
        "test_case_id": "TC-030",
        "score": final_score,
        "component_scores": component_scores,
        "agent_language": agent_output.get("language", "unknown"),
        "ground_truth_language": ground_truth.get("language", "unknown"),
        "variant_id": agent_output.get("variant_id"),
    }


# --------------------------------------------------------------------
# TC-032: Immune-Related Adverse Event Summary (Level 1)
# --------------------------------------------------------------------

def _irae_table_index(output: dict) -> dict:
    """Index irAE table rows by (irae_category, pt, severity, category) for aligned comparison.

    Handles rows with category in {category, category_severity, pt, pt_severity}.
    Summary rows, severity_summary, and onset_summary are handled separately.
    """
    idx = {}
    for row in output.get("irae_table", []) or []:
        cat_name = row.get("irae_category")
        pt = row.get("pt")
        sev = row.get("severity")
        cat = row.get("category")
        idx[(cat_name, pt, sev, cat)] = {
            "n_experimental": row.get("n_experimental"),
            "pct_experimental": row.get("pct_experimental"),
            "n_control": row.get("n_control"),
            "pct_control": row.get("pct_control"),
        }
    return idx


def score_tc032(agent_output: dict, ground_truth: dict, tolerances: dict) -> dict:
    """Score TC-032 (Immune-Related AE Summary).

    Compares:
    - Severity summary (grade 1-5 per arm, n and pct)
    - Overall summary rows (Any irAE, Grade >=3, discontinuation, corticosteroids)
    - Detailed irAE table (category/PT/severity cells, n and pct)
    - Onset summary (median time-to-onset per category)
    - N per arm from population block
    """
    tol_spec = tolerances.get("TC-032", {}).get("tolerances", {})
    component_scores = {}
    total_weight = 0
    weighted_sum = 0

    # --- Severity summary (grade 1-5) ---
    ag_sev = agent_output.get("severity_summary", []) or []
    gt_sev = ground_truth.get("severity_summary", []) or []
    gt_sev_idx = {s.get("grade"): s for s in gt_sev}
    ag_sev_idx = {s.get("grade"): s for s in ag_sev}

    for grade in [1, 2, 3, 4, 5]:
        gt_row = gt_sev_idx.get(grade, {})
        ag_row = ag_sev_idx.get(grade, {})

        for arm_field, label in [("n_experimental", f"sev_g{grade}_n_exp"),
                                 ("n_control", f"sev_g{grade}_n_ctl")]:
            w = tol_spec.get("severity_n", {}).get("weight", 0.15) / 10
            r = compare_count(ag_row.get(arm_field), gt_row.get(arm_field))
            component_scores[label] = r
            weighted_sum += r["score"] * w
            total_weight += w

        for arm_field, label in [("pct_experimental", f"sev_g{grade}_pct_exp"),
                                 ("pct_control", f"sev_g{grade}_pct_ctl")]:
            field_tol = {"absolute": tol_spec.get("severity_pct", {}).get("absolute", 0.1)}
            w = tol_spec.get("severity_pct", {}).get("weight", 0.10) / 10
            r = compare_numeric(ag_row.get(arm_field), gt_row.get(arm_field),
                                field_tol, label)
            component_scores[label] = r
            weighted_sum += r["score"] * w
            total_weight += w

    # --- Overall summary rows ---
    ag_summary = agent_output.get("summary", []) or []
    gt_summary = ground_truth.get("summary", []) or []
    gt_sum_idx = {s.get("category"): s for s in gt_summary}
    ag_sum_idx = {s.get("category"): s for s in ag_summary}

    n_summary = max(len(gt_summary), 1)
    for cat in gt_sum_idx:
        gt_row = gt_sum_idx[cat]
        ag_row = ag_sum_idx.get(cat, {})

        for arm_field, label in [("n_experimental", f"sum_{cat[:10]}_n_exp"),
                                 ("n_control", f"sum_{cat[:10]}_n_ctl")]:
            w = tol_spec.get("summary_n", {}).get("weight", 0.15) / (n_summary * 2)
            r = compare_count(ag_row.get(arm_field), gt_row.get(arm_field))
            component_scores[label] = r
            weighted_sum += r["score"] * w
            total_weight += w

        for arm_field, label in [("pct_experimental", f"sum_{cat[:10]}_pct_exp"),
                                 ("pct_control", f"sum_{cat[:10]}_pct_ctl")]:
            field_tol = {"absolute": tol_spec.get("summary_pct", {}).get("absolute", 0.1)}
            w = tol_spec.get("summary_pct", {}).get("weight", 0.10) / (n_summary * 2)
            r = compare_numeric(ag_row.get(arm_field), gt_row.get(arm_field),
                                field_tol, label)
            component_scores[label] = r
            weighted_sum += r["score"] * w
            total_weight += w

    # --- Detailed irAE table ---
    ag_idx = _irae_table_index(agent_output)
    gt_idx = _irae_table_index(ground_truth)

    n_detail = max(len(gt_idx), 1)
    for key, gt_row in gt_idx.items():
        ag_row = ag_idx.get(key, {})
        cat_label = str(key[0])[:20] if key[0] else "?"
        pt_label = str(key[1])[:15] if key[1] else "None"
        sev_label = str(key[2]) if key[2] is not None else "NA"
        cat_type = str(key[3])[:5] if key[3] else "?"
        label_base = f"{cat_label}_{pt_label}_g{sev_label}_{cat_type}"

        for arm_field, suffix in [("n_experimental", "n_exp"), ("n_control", "n_ctl")]:
            w = tol_spec.get("irae_table_n", {}).get("weight", 0.25) / (n_detail * 2)
            r = compare_count(ag_row.get(arm_field), gt_row.get(arm_field))
            component_scores[f"{label_base}_{suffix}"] = r
            weighted_sum += r["score"] * w
            total_weight += w

        for arm_field, suffix in [("pct_experimental", "pct_exp"), ("pct_control", "pct_ctl")]:
            field_tol = {"absolute": tol_spec.get("irae_table_pct", {}).get("absolute", 0.1)}
            w = tol_spec.get("irae_table_pct", {}).get("weight", 0.10) / (n_detail * 2)
            r = compare_numeric(ag_row.get(arm_field), gt_row.get(arm_field),
                                field_tol, f"{label_base}_{suffix}")
            component_scores[f"{label_base}_{suffix}"] = r
            weighted_sum += r["score"] * w
            total_weight += w

    # --- Onset summary ---
    ag_onset = agent_output.get("onset_summary", []) or []
    gt_onset = ground_truth.get("onset_summary", []) or []
    gt_onset_idx = {o.get("irae_category"): o for o in gt_onset}
    ag_onset_idx = {o.get("irae_category"): o for o in ag_onset}

    n_onset = max(len(gt_onset), 1)
    for cat_name in gt_onset_idx:
        gt_o = gt_onset_idx[cat_name]
        ag_o = ag_onset_idx.get(cat_name, {})

        for field, suffix in [("median_onset_experimental", "onset_exp"),
                              ("median_onset_control", "onset_ctl")]:
            field_tol = {"absolute": tol_spec.get("onset_median", {}).get("absolute", 2)}
            w = tol_spec.get("onset_median", {}).get("weight", 0.10) / n_onset
            r = compare_numeric(ag_o.get(field), gt_o.get(field),
                                field_tol, f"{cat_name[:15]}_{suffix}")
            component_scores[f"{cat_name[:15]}_{suffix}"] = r
            weighted_sum += r["score"] * w
            total_weight += w

    # --- N per arm from population block ---
    pop = ground_truth.get("population", {})
    agent_pop = agent_output.get("population", {})
    for field, label in [("n_experimental", "pop_n_exp"), ("n_control", "pop_n_ctl")]:
        w = tol_spec.get("n_per_arm", {}).get("weight", 0.05) / 2
        r = compare_count(agent_pop.get(field), pop.get(field))
        component_scores[label] = r
        weighted_sum += r["score"] * w
        total_weight += w

    final_score = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0

    return {
        "test_case_id": "TC-032",
        "score": final_score,
        "component_scores": component_scores,
        "agent_language": agent_output.get("language", agent_output.get("metadata", {}).get("language", "unknown")),
        "ground_truth_language": ground_truth.get("language", ground_truth.get("metadata", {}).get("language", "unknown")),
        "variant_id": agent_output.get("variant_id"),
    }


# --------------------------------------------------------------------
# TC-034: Sufficient Follow-up Assessment (Level 1)
# --------------------------------------------------------------------

def score_tc034(agent_output: dict, ground_truth: dict, tolerances: dict) -> dict:
    """Score TC-034 (Sufficient Follow-up Assessment).

    Compares:
    - Adequate follow-up N and pct by arm
    - Status distribution (ongoing, completed, discontinued, died) by arm
    - Reverse KM median follow-up by arm
    - Follow-up post-dose summary (mean, sd, median, min, max) by arm
    - Follow-up from randomization summary by arm
    - N per arm from metadata
    """
    tol_spec = tolerances.get("TC-034", {}).get("tolerances", {})
    component_scores = {}
    weighted_sum = 0.0
    total_weight = 0.0

    # --- Adequate follow-up N and pct ---
    for arm in ["experimental", "control"]:
        for metric in ["n", "pct"]:
            tol_key = f"adequate_fu_{arm}_{metric}"
            sub_tol = tol_spec.get(tol_key, {})
            if metric == "n":
                r = compare_count(
                    agent_output.get("adequate_followup", {}).get(arm, {}).get(metric),
                    ground_truth.get("adequate_followup", {}).get(arm, {}).get(metric),
                )
            else:
                field_tol = {"absolute": sub_tol.get("absolute", 0.1)}
                r = compare_numeric(
                    agent_output.get("adequate_followup", {}).get(arm, {}).get(metric),
                    ground_truth.get("adequate_followup", {}).get(arm, {}).get(metric),
                    field_tol, f"adequate_fu.{arm}.{metric}",
                )
            component_scores[f"adequate_fu.{arm}.{metric}"] = r
            w = sub_tol.get("weight", 0.10)
            weighted_sum += r["score"] * w
            total_weight += w

    # --- Status distribution ---
    for arm in ["experimental", "control"]:
        for status_label in ["ongoing", "completed", "discontinued", "died"]:
            tol_key = f"status_{arm}"
            sub_tol = tol_spec.get(tol_key, {})
            r = compare_count(
                agent_output.get("status_distribution", {}).get(arm, {}).get(status_label),
                ground_truth.get("status_distribution", {}).get(arm, {}).get(status_label),
            )
            component_scores[f"status.{arm}.{status_label}"] = r
            w = sub_tol.get("weight", 0.05) / 4
            weighted_sum += r["score"] * w
            total_weight += w

    # --- Reverse KM median follow-up ---
    for arm in ["experimental", "control"]:
        sub_tol = tol_spec.get(f"reverse_km_{arm}", tol_spec.get("reverse_km", {}))
        agent_km = agent_output.get("reverse_km_followup", {}).get(arm, {})
        truth_km = ground_truth.get("reverse_km_followup", {}).get(arm, {})
        for field in ["median", "ci_lower", "ci_upper"]:
            field_tol = {"absolute": sub_tol.get("absolute", 5)}
            r = compare_numeric(
                agent_km.get(field),
                truth_km.get(field),
                field_tol,
                f"reverse_km.{arm}.{field}",
            )
            component_scores[f"reverse_km.{arm}.{field}"] = r
            w = sub_tol.get("weight", 0.10) / 3
            weighted_sum += r["score"] * w
            total_weight += w

    # --- Follow-up post-dose summary ---
    for arm in ["experimental", "control"]:
        arm_tol = tol_spec.get(f"fu_post_dose_{arm}", tol_spec.get("fu_post_dose", {}))
        for field in ["mean", "sd", "median", "min", "max", "q1", "q3"]:
            field_tol = {"absolute": arm_tol.get("absolute", 0.5)}
            r = compare_numeric(
                agent_output.get("fu_post_dose", {}).get(arm, {}).get(field),
                ground_truth.get("fu_post_dose", {}).get(arm, {}).get(field),
                field_tol,
                f"fu_post_dose.{arm}.{field}",
            )
            component_scores[f"fu_post_dose.{arm}.{field}"] = r
            w = arm_tol.get("weight", 0.05) / 7
            weighted_sum += r["score"] * w
            total_weight += w

    # --- Follow-up from randomization summary ---
    for arm in ["experimental", "control"]:
        arm_tol = tol_spec.get(f"fu_rand_{arm}", tol_spec.get("fu_from_rand", {}))
        for field in ["mean", "sd", "median", "min", "max", "q1", "q3"]:
            field_tol = {"absolute": arm_tol.get("absolute", 0.5)}
            r = compare_numeric(
                agent_output.get("fu_from_randomization", {}).get(arm, {}).get(field),
                ground_truth.get("fu_from_randomization", {}).get(arm, {}).get(field),
                field_tol,
                f"fu_rand.{arm}.{field}",
            )
            component_scores[f"fu_rand.{arm}.{field}"] = r
            w = arm_tol.get("weight", 0.05) / 7
            weighted_sum += r["score"] * w
            total_weight += w

    # --- N per arm from metadata ---
    for arm_key, arm_label in [("n_total", "total"), ("n_experimental", "exp"), ("n_control", "ctl")]:
        tol_key = f"n_{arm_label}"
        sub_tol = tol_spec.get(tol_key, {})
        r = compare_count(
            agent_output.get("metadata", {}).get(arm_key),
            ground_truth.get("metadata", {}).get(arm_key),
        )
        component_scores[f"metadata.{arm_key}"] = r
        w = sub_tol.get("weight", 0.02)
        weighted_sum += r["score"] * w
        total_weight += w

    overall = weighted_sum / total_weight if total_weight > 0 else 0.0

    return {
        "test_case_id": "TC-034",
        "score": round(overall, 4),
        "component_scores": component_scores,
        "agent_language": agent_output.get("language", agent_output.get("metadata", {}).get("language", "unknown")),
        "ground_truth_language": ground_truth.get("language", ground_truth.get("metadata", {}).get("language", "unknown")),
        "variant_id": agent_output.get("variant_id"),
    }


# --------------------------------------------------------------------
# TC-031: Time-to-First-Treatment (Level 1)
# --------------------------------------------------------------------

def score_tc031(agent_output: dict, ground_truth: dict, tolerances: dict) -> dict:
    """Score TC-031 (Time-to-First-Treatment).

    Compares:
    - KM median TTT by arm (median, CI, n_events, n_total)
    - Log-rank test (chisq, p_value)
    - Cox HR (hr, hr_lower, hr_upper, p_value)
    - TTT summary statistics by arm (mean, sd, median, min, max, q1, q3)
    - Received treatment counts by arm (n_received, n_censored, pct_received)
    - N per arm from metadata
    """
    tol_spec = tolerances.get("TC-031", {}).get("tolerances", {})
    component_scores = {}
    weighted_sum = 0.0
    total_weight = 0.0

    # --- KM median TTT per arm ---
    for arm in ["experimental", "control"]:
        km_tol = tol_spec.get(f"km_{arm}", tol_spec.get("km", {}))
        agent_km = agent_output.get("km_median_ttt", {}).get(arm, {})
        truth_km = ground_truth.get("km_median_ttt", {}).get(arm, {})

        # Median and CI
        for field in ["median", "ci_lower", "ci_upper"]:
            field_tol = {"absolute": km_tol.get("absolute", 2)}
            r = compare_numeric(
                agent_km.get(field), truth_km.get(field),
                field_tol, f"km_median_ttt.{arm}.{field}",
            )
            component_scores[f"km_median_ttt.{arm}.{field}"] = r
            w = km_tol.get("weight", 0.10) / 3
            weighted_sum += r["score"] * w
            total_weight += w

        # n_events and n_total
        for field in ["n_events", "n_total"]:
            r = compare_count(agent_km.get(field), truth_km.get(field))
            component_scores[f"km_median_ttt.{arm}.{field}"] = r
            w = km_tol.get("weight", 0.10) / 5
            weighted_sum += r["score"] * w
            total_weight += w

    # --- Log-rank test ---
    lr_tol = tol_spec.get("logrank", {})
    agent_lr = agent_output.get("logrank_test", {})
    truth_lr = ground_truth.get("logrank_test", {})
    for field in ["chisq", "p_value"]:
        field_tol = {"absolute": lr_tol.get("absolute", 0.01)}
        r = compare_numeric(
            agent_lr.get(field), truth_lr.get(field),
            field_tol, f"logrank.{field}",
        )
        component_scores[f"logrank.{field}"] = r
        w = lr_tol.get("weight", 0.06) / 2
        weighted_sum += r["score"] * w
        total_weight += w

    # --- Cox HR ---
    cox_tol = tol_spec.get("cox_hr", {})
    agent_cox = agent_output.get("cox_hr", {})
    truth_cox = ground_truth.get("cox_hr", {})
    for field in ["hr", "hr_lower", "hr_upper", "p_value"]:
        field_tol = {"absolute": cox_tol.get("absolute", 0.05)}
        r = compare_numeric(
            agent_cox.get(field), truth_cox.get(field),
            field_tol, f"cox_hr.{field}",
        )
        component_scores[f"cox_hr.{field}"] = r
        w = cox_tol.get("weight", 0.08) / 4
        weighted_sum += r["score"] * w
        total_weight += w

    # --- TTT summary statistics ---
    for arm in ["experimental", "control"]:
        arm_tol = tol_spec.get(f"ttt_summary_{arm}", tol_spec.get("ttt_summary", {}))
        for field in ["mean", "sd", "median", "min", "max", "q1", "q3"]:
            field_tol = {"absolute": arm_tol.get("absolute", 0.5)}
            r = compare_numeric(
                agent_output.get("ttt_summary", {}).get(arm, {}).get(field),
                ground_truth.get("ttt_summary", {}).get(arm, {}).get(field),
                field_tol, f"ttt_summary.{arm}.{field}",
            )
            component_scores[f"ttt_summary.{arm}.{field}"] = r
            w = arm_tol.get("weight", 0.05) / 7
            weighted_sum += r["score"] * w
            total_weight += w

    # --- Received treatment counts ---
    for arm in ["experimental", "control"]:
        rx_tol = tol_spec.get(f"received_{arm}", tol_spec.get("received", {}))
        agent_rx = agent_output.get("received_treatment", {}).get(arm, {})
        truth_rx = ground_truth.get("received_treatment", {}).get(arm, {})

        for field in ["n_received", "n_censored"]:
            r = compare_count(agent_rx.get(field), truth_rx.get(field))
            component_scores[f"received_treatment.{arm}.{field}"] = r
            w = rx_tol.get("weight", 0.04) / 2
            weighted_sum += r["score"] * w
            total_weight += w

        # pct_received
        field_tol = {"absolute": rx_tol.get("absolute", 0.1)}
        r = compare_numeric(
            agent_rx.get("pct_received"), truth_rx.get("pct_received"),
            field_tol, f"received_treatment.{arm}.pct_received",
        )
        component_scores[f"received_treatment.{arm}.pct_received"] = r
        w = rx_tol.get("weight", 0.04) / 3
        weighted_sum += r["score"] * w
        total_weight += w

    # --- N per arm from metadata ---
    for arm_key, arm_label in [("n_total", "total"), ("n_experimental", "exp"), ("n_control", "ctl")]:
        tol_key = f"n_{arm_label}"
        sub_tol = tol_spec.get(tol_key, {})
        r = compare_count(
            agent_output.get("metadata", {}).get(arm_key),
            ground_truth.get("metadata", {}).get(arm_key),
        )
        component_scores[f"metadata.{arm_key}"] = r
        w = sub_tol.get("weight", 0.02)
        weighted_sum += r["score"] * w
        total_weight += w

    overall = weighted_sum / total_weight if total_weight > 0 else 0.0

    return {
        "test_case_id": "TC-031",
        "score": round(overall, 4),
        "component_scores": component_scores,
        "agent_language": agent_output.get("language", agent_output.get("metadata", {}).get("language", "unknown")),
        "ground_truth_language": ground_truth.get("language", ground_truth.get("metadata", {}).get("language", "unknown")),
        "variant_id": agent_output.get("variant_id"),
    }


# --------------------------------------------------------------------
# TC-006: Blinded Sample Size Re-Estimation at Interim (Level 2)
# --------------------------------------------------------------------

def score_tc006(agent_output: dict, ground_truth: dict, tolerances: dict) -> dict:
    """Score TC-006 (Blinded SSR at Interim) agent output.

    Compares current status, blinded estimation, and per-scenario
    computations (control median, events needed, total N, conditional power)
    across 3 HR scenarios (optimistic=0.70, original=0.75, pessimistic=0.80).
    """
    tol_spec = tolerances.get("TC-006", {}).get("tolerances", {})
    component_scores = {}
    weighted_sum = 0.0
    total_weight = 0.0

    # --- Current status ---
    ag_cs = agent_output.get("current_status", {})
    gt_cs = ground_truth.get("current_status", {})

    # Enrollment pct
    tol = tol_spec.get("enrollment_pct", {})
    r = compare_numeric(ag_cs.get("enrollment_pct"), gt_cs.get("enrollment_pct"),
                       tol, "enrollment_pct")
    component_scores["enrollment_pct"] = r
    weighted_sum += r["score"] * tol.get("weight", 0.02)
    total_weight += tol.get("weight", 0.02)

    # Information fraction
    tol = tol_spec.get("information_fraction", {})
    r = compare_numeric(ag_cs.get("information_fraction"), gt_cs.get("information_fraction"),
                       tol, "information_fraction")
    component_scores["information_fraction"] = r
    weighted_sum += r["score"] * tol.get("weight", 0.05)
    total_weight += tol.get("weight", 0.05)

    # --- Blinded estimation ---
    ag_be = agent_output.get("blinded_estimation", {})
    gt_be = ground_truth.get("blinded_estimation", {})

    # Pooled median PFS
    tol = tol_spec.get("pooled_median_pfs", {})
    r = compare_numeric(ag_be.get("pooled_median_pfs"), gt_be.get("pooled_median_pfs"),
                       tol, "pooled_median_pfs")
    component_scores["pooled_median_pfs"] = r
    weighted_sum += r["score"] * tol.get("weight", 0.05)
    total_weight += tol.get("weight", 0.05)

    # Estimated event rate monthly
    tol = tol_spec.get("estimated_event_rate_monthly", {})
    r = compare_numeric(ag_be.get("estimated_event_rate_monthly"),
                        gt_be.get("estimated_event_rate_monthly"),
                       tol, "estimated_event_rate_monthly")
    component_scores["estimated_event_rate_monthly"] = r
    weighted_sum += r["score"] * tol.get("weight", 0.05)
    total_weight += tol.get("weight", 0.05)

    # Lambda
    tol = tol_spec.get("lambda", {})
    r = compare_numeric(ag_be.get("lambda"), gt_be.get("lambda"),
                       tol, "lambda")
    component_scores["lambda"] = r
    weighted_sum += r["score"] * tol.get("weight", 0.03)
    total_weight += tol.get("weight", 0.03)

    # --- Per-scenario comparisons ---
    ag_scenarios = agent_output.get("scenarios", {})
    gt_scenarios = ground_truth.get("scenarios", {})

    for scenario_name in ["optimistic", "original", "pessimistic"]:
        ag_s = ag_scenarios.get(scenario_name, {})
        gt_s = gt_scenarios.get(scenario_name, {})

        # Control median
        tol = tol_spec.get("control_median", {})
        r = compare_numeric(ag_s.get("control_median_pfs"),
                            gt_s.get("control_median_pfs"),
                           tol, f"{scenario_name}_control_median")
        component_scores[f"{scenario_name}_control_median"] = r
        weighted_sum += r["score"] * tol.get("weight", 0.10) / 3
        total_weight += tol.get("weight", 0.10) / 3

        # Events needed
        tol = tol_spec.get("events_needed", {})
        r = compare_numeric(ag_s.get("events_needed"),
                            gt_s.get("events_needed"),
                           tol, f"{scenario_name}_events_needed")
        component_scores[f"{scenario_name}_events_needed"] = r
        weighted_sum += r["score"] * tol.get("weight", 0.10) / 3
        total_weight += tol.get("weight", 0.10) / 3

        # Total N needed
        tol = tol_spec.get("total_n_needed", {})
        r = compare_numeric(ag_s.get("total_n_needed"),
                            gt_s.get("total_n_needed"),
                           tol, f"{scenario_name}_total_n_needed")
        component_scores[f"{scenario_name}_total_n_needed"] = r
        weighted_sum += r["score"] * tol.get("weight", 0.10) / 3
        total_weight += tol.get("weight", 0.10) / 3

        # Conditional power
        tol = tol_spec.get("conditional_power", {})
        r = compare_numeric(ag_s.get("conditional_power"),
                            gt_s.get("conditional_power"),
                           tol, f"{scenario_name}_conditional_power")
        component_scores[f"{scenario_name}_conditional_power"] = r
        weighted_sum += r["score"] * tol.get("weight", 0.10) / 3
        total_weight += tol.get("weight", 0.10) / 3

    final_score = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0

    return {
        "test_case_id": "TC-006",
        "score": final_score,
        "component_scores": component_scores,
        "agent_language": agent_output.get("language", agent_output.get("metadata", {}).get("language", "unknown")),
        "ground_truth_language": ground_truth.get("language", ground_truth.get("metadata", {}).get("language", "unknown")),
        "variant_id": agent_output.get("variant_id"),
    }


# --------------------------------------------------------------------
# Efficiency Helpers
# --------------------------------------------------------------------

def load_efficiency_config() -> dict:
    """Load efficiency configuration from efficiency.yaml."""
    eff_path = Path(__file__).parent / "efficiency.yaml"
    with open(eff_path) as f:
        return yaml.safe_load(f)


def compute_efficiency_score(
    accuracy_score: float,
    total_cost: float,
    total_time_s: float,
    language: str = "unknown",
    retry_count: int = 0,
    human_review_minutes: float = 0,
    tc_level: str = "level_1"
) -> dict:
    """Compute operational efficiency scores from raw metrics.

    Three component scores + composite:
    1. COST efficiency: (accuracy / max(total_cost, 0.01)) normalized
    2. TIME efficiency: (accuracy / max(total_time_s/60, 0.1)) normalized
    3. RELIABILITY score: deducts for retries and errors
    4. COMPOSITE: weighted average of the three

    Args:
        accuracy_score: Numerical correctness score (0-1)
        total_cost: Total monetary cost in USD
        total_time_s: Total wall-clock time in seconds
        language: "R", "SAS", or "Python"
        retry_count: Number of API retries
        human_review_minutes: Human review time in minutes
        tc_level: "level_1", "level_2", or "level_3"

    Returns:
        Dict with component scores and composite
    """
    # Load config for language adjustments and scoring weights
    config = load_efficiency_config()
    lang_adj = config.get("language_adjustments", {}).get(language.upper(), {})
    time_factor = lang_adj.get("time_factor", 1.0)
    validation_overhead = lang_adj.get("validation_overhead_min", 0)

    scoring_weights = config.get("scoring_weights", {}).get("default", {})
    cost_weight = scoring_weights.get("cost_efficiency", 0.40)
    time_weight = scoring_weights.get("time_efficiency", 0.35)
    reliability_weight = scoring_weights.get("reliability", 0.25)

    targets = config.get("efficiency_targets", {}).get(tc_level, {})
    cost_target = targets.get("cost_target_usd", 0.10)
    time_target = targets.get("time_target_min", 2.0)

    # Avoid division by zero
    cost_safe = max(total_cost, 0.001)
    time_safe = max(total_time_s / 60, 0.01)  # Convert to minutes

    # Language-adjusted time
    adjusted_time = time_safe * time_factor

    # Raw efficiency
    cost_efficiency_raw = accuracy_score / cost_safe  # points per dollar
    time_efficiency_raw = accuracy_score / adjusted_time  # points per minute

    # Normalize to 0-1 using sigmoid-like transform
    cost_scale = cost_target
    cost_efficiency = 1 / (1 + (cost_efficiency_raw / max(cost_scale, 0.01)) ** (-1))
    time_scale = time_target
    time_efficiency = 1 / (1 + (time_efficiency_raw / max(time_scale, 0.01)) ** (-1))

    # Reliability penalty
    retry_penalty = min(retry_count * 0.05, 0.25)  # Max 25% penalty
    reliability = max(0.0, 1.0 - retry_penalty if retry_count > 0 else 1.0)

    # Composite
    composite = (
        cost_weight * cost_efficiency
        + time_weight * time_efficiency
        + reliability_weight * reliability
    )

    return {
        "cost_efficiency_score": round(cost_efficiency, 4),
        "cost_efficiency_raw": round(cost_efficiency_raw, 4),
        "total_cost_usd": round(total_cost, 6),
        "time_efficiency_score": round(time_efficiency, 4),
        "time_efficiency_raw": round(time_efficiency_raw, 4),
        "total_time_minutes": round(total_time_s / 60, 2),
        "adjusted_time_minutes": round(adjusted_time, 2),
        "language_adjustment_factor": time_factor,
        "validation_overhead_min": validation_overhead,
        "reliability_score": round(reliability, 4),
        "retry_count": retry_count,
        "composite_efficiency_score": round(composite, 4),
        "scoring_weights_used": {
            "cost": cost_weight,
            "time": time_weight,
            "reliability": reliability_weight
        }
    }


# --------------------------------------------------------------------
# Compliance Helpers
# --------------------------------------------------------------------

def _run_compliance_check(agent_output: dict, tc: str, do_compliance: bool,
                          do_tcg: bool, do_csr: bool) -> dict:
    """Run compliance checks and return compliance result dict."""
    if not HAS_COMPLIANCE:
        console.print("[yellow]Compliance module not available; skipping checks[/yellow]")
        return None
    if not do_compliance and not do_tcg and not do_csr:
        return None

    try:
        cr = _compute_compliance_score(
            agent_output, tc,
            check_adam=do_compliance,
            check_tcg=do_tcg,
            check_csr=do_csr,
        )
        return cr
    except Exception as e:
        console.print(f"[red]Compliance check error: {e}[/red]")
        return None


def _print_compliance_report(cr: dict):
    """Print compliance results as a Rich table."""
    if cr is None:
        return

    table = Table(title="Regulatory Compliance")
    table.add_column("Component", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Passed", justify="center")
    table.add_column("Failed", justify="center")

    for comp_name in ["adam_compliance", "tcg_compliance", "csr_compliance"]:
        comp = cr.get(comp_name, {})
        sc = comp.get("score")
        if sc is not None:
            pf = len(comp.get("passed", []))
            ff = len(comp.get("failed", []))
            pass_str = "\u2705" if sc >= 0.8 else "\u26a0\ufe0f" if sc >= 0.5 else "\u274c"
            table.add_row(
                comp_name,
                f"{sc:.4f}",
                f"{pass_str} {pf}",
                str(ff)
            )
        else:
            table.add_row(comp_name, "\u2014", "skipped", "\u2014")

    table.add_row(
        "[bold]TOTAL COMPLIANCE[/bold]",
        f"[bold]{cr.get('total_compliance_score', 0):.4f}[/bold]",
        "",
        ""
    )

    console.print(table)


# --------------------------------------------------------------------
# Safety Helpers
# --------------------------------------------------------------------

def _run_safety_check(agent_output: dict, tc: str, tfl_package: dict = None,
                      run_2: dict = None,
                      check_n: bool = True, check_denom: bool = True,
                      check_cross: bool = False, check_edge: bool = True,
                      check_stability: bool = False) -> dict:
    """Run safety and robustness checks on an agent output."""
    if not HAS_SAFETY:
        console.print("[yellow]Safety module not available; skipping checks[/yellow]")
        return None
    if not check_n and not check_denom and not check_cross and not check_edge and not check_stability:
        return None

    try:
        sr = _compute_safety_score(
            agent_output, tc,
            tfl_package=tfl_package,
            run_2=run_2,
            check_n=check_n,
            check_denom=check_denom,
            check_cross=check_cross,
            check_edge=check_edge,
            check_stability=check_stability,
        )
        return sr
    except Exception as e:
        console.print(f"[red]Safety check error: {e}[/red]")
        return None


def _print_safety_report(sr: dict):
    """Print safety results as a Rich table and panel."""
    if sr is None:
        return

    console.print(Panel(f"[bold]Safety & Robustness Score: {sr.get('total_safety_score', 0):.4f}[/bold]"))

    table = Table(title="Safety & Robustness")
    table.add_column("Component", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Passed", justify="center")
    table.add_column("Failed", justify="center")

    for comp_name in ["n_count_consistency", "denominator_correctness",
                      "cross_tfl_agreement", "edge_case_handling",
                      "output_stability"]:
        comp = sr.get(comp_name, {})
        sc = comp.get("score")
        if sc is not None:
            pf = comp.get("passed", [])
            ff = comp.get("failed", [])
            pass_str = "\u2705" if sc >= 0.8 else "\u26a0\ufe0f" if sc >= 0.5 else "\u274c"
            table.add_row(
                comp_name,
                f"{sc:.4f}",
                f"{pass_str} {len(pf)}",
                str(len(ff))
            )

            # Show first 3 failed checks inline
            for rid in ff[:3]:
                table.add_row("", "", "", f"  \u274c {rid}")
        else:
            table.add_row(comp_name, "\u2014", "skipped", "\u2014")

    table.add_row(
        "[bold]TOTAL SAFETY[/bold]",
        f"[bold]{sr.get('total_safety_score', 0):.4f}[/bold]",
        "",
        ""
    )

    console.print(table)

    # Show discrepancies if any
    for comp_name in ["cross_tfl_agreement", "output_stability"]:
        comp = sr.get(comp_name, {})
        disc = comp.get("discrepancies", comp.get("unstable_fields", []))
        if disc:
            console.print(f"[yellow]\u26a0\ufe0f  {comp_name} details:[/yellow]")
            for d in disc[:5]:
                console.print(f"    {d}")


# --------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------

@click.group()
def cli():
    """katsu \u2014 TFL Scoring and Evaluation Harness."""
    pass


@cli.command()
@click.option("--tc", required=True, help="Test case ID (e.g., TC-001)")
@click.option("--agent", required=True, type=click.Path(exists=True),
              help="Agent output JSON")
@click.option("--truth", required=True, type=click.Path(exists=True),
              help="Ground truth JSON")
@click.option("--output", type=click.Path(), help="Output report path")
@click.option("--compliance", is_flag=True, default=False,
              help="Include ADaM compliance checks")
@click.option("--tcg-check", is_flag=True, default=False,
              help="Include FDA TCG checklist checks")
@click.option("--csr-format", is_flag=True, default=False,
              help="Include ICH E3 CSR formatting checks")
@click.option("--safety", is_flag=True, default=False,
              help="Include safety/robustness checks")
@click.option("--n-count", "n_count_flag", is_flag=True, default=False,
              help="Include N-count consistency checks (requires --safety)")
@click.option("--denom", is_flag=True, default=False,
              help="Include denominator correctness checks (requires --safety)")
@click.option("--cross-tfl", "cross_tfl_flag", is_flag=True, default=False,
              help="Include cross-TFL agreement checks (requires --safety + --package)")
@click.option("--edge", is_flag=True, default=False,
              help="Include edge case handling checks (requires --safety)")
@click.option("--stability", is_flag=True, default=False,
              help="Include output stability checks (requires --safety + --run2)")
@click.option("--package", "package_path", type=click.Path(exists=True),
              help="TFL package JSON (for cross-TFL checks)")
@click.option("--run2", "run2_path", type=click.Path(exists=True),
              help="Second run output JSON (for stability check)")
def score(tc, agent, truth, output, compliance, tcg_check, csr_format,
          safety, n_count_flag, denom, cross_tfl_flag,
          edge, stability, package_path, run2_path):
    """Score an agent output against ground truth."""
    with open(agent) as f:
        agent_out = json.load(f)
    with open(truth) as f:
        truth_out = json.load(f)

    tolerances = load_tolerances()
    scorers = {
        "TC-001": score_tc001,
        "TC-002": score_tc002,
        "TC-003": score_tc003,
        "TC-011": score_tc011,
        "TC-012": score_tc012,
        "TC-013": score_tc013,
        "TC-014": score_tc014,
        "TC-015": score_tc015,
        "TC-016": score_tc016,
        "TC-017": score_tc017,
        "TC-018": score_tc018,
        "TC-019": score_tc019,
        "TC-020": score_tc020,
        "TC-021": score_tc021,
        "TC-022": score_tc022,
        "TC-023": score_tc023,
        "TC-024": score_tc024,
        "TC-025": score_tc025,
        "TC-026": score_tc026,
        "TC-027": score_tc027,
        "TC-028": score_tc028,
        "TC-029": score_tc029,
        "TC-033": score_tc033,
        "TC-030": score_tc030,
        "TC-032": score_tc032,
        "TC-034": score_tc034,
        "TC-031": score_tc031,
        "TC-006": score_tc006,
    }

    scorer = scorers.get(tc)
    if scorer is None:
        console.print(f"[red]No scorer available for {tc}[/red]")
        sys.exit(1)

    result = scorer(agent_out, truth_out, tolerances)

    # Print numerical scoring report
    table = Table(title=f"Scoring Report: {tc}")
    table.add_column("Component", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Pass", justify="center")
    table.add_column("Note")

    for field, comp in result["component_scores"].items():
        pass_str = "\u2705" if comp["pass"] else "\u274c"
        table.add_row(
            field,
            f"{comp['score']:.2f}",
            pass_str,
            comp.get("note", "")
        )

    table.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold]{result['score']:.4f}[/bold]",
        "",
        ""
    )

    console.print(Panel(f"[bold]Agent:[/bold] {result['agent_language']} "
                        f"[bold]| Ground Truth:[/bold] {result['ground_truth_language']}"))
    console.print(table)

    # Compliance section
    if compliance or tcg_check or csr_format:
        cr = _run_compliance_check(agent_out, tc, compliance, tcg_check, csr_format)
        if cr:
            _print_compliance_report(cr)
            # Add compliance to result dict
            result["compliance"] = cr

    # Safety section
    if safety or n_count_flag or denom or cross_tfl_flag or edge or stability:
        # Load TFL package and run_2 if provided
        tfl_pkg = None
        if package_path:
            with open(package_path) as f:
                tfl_pkg = json.load(f)

        run2_data = None
        if run2_path:
            with open(run2_path) as f:
                run2_data = json.load(f)

        # Default sub-checks: if --safety alone, run all applicable
        do_n = n_count_flag or safety
        do_denom = denom or safety
        do_cross = cross_tfl_flag or safety
        do_edge = edge or safety
        do_stability = stability or safety

        sr = _run_safety_check(
            agent_out, tc,
            tfl_package=tfl_pkg,
            run_2=run2_data,
            check_n=do_n,
            check_denom=do_denom,
            check_cross=do_cross,
            check_edge=do_edge,
            check_stability=do_stability,
        )
        if sr:
            _print_safety_report(sr)
            result["safety"] = sr

    if output:
        with open(output, "w") as f:
            json.dump(result, f, indent=2)
        console.print(f"[green]Report written to: {output}[/green]")


@cli.command()
@click.option("--tc", required=True, help="Test case ID")
@click.option("--r", "r_path", required=True, type=click.Path(exists=True),
              help="R ground-truth output JSON")
@click.option("--python", "python_path", required=True, type=click.Path(exists=True),
              help="Python ground-truth output JSON")
@click.option("--sas", "sas_path", required=False, type=click.Path(exists=True),
              help="SAS ground-truth output JSON (optional; SAS is reference-only "
                   "for several TCs and may be unavailable)")
@click.option("--output", type=click.Path(), help="Verification report path")
def verify(tc, r_path, python_path, sas_path, output):
    """Verify cross-language consistency of ground truth.

    IMPORTANT: meaningful verification requires that all inputs were computed on
    the SAME shared dataset (e.g. each TC script run with --data shared.csv).
    Independently generated outputs use different RNG streams and will not match.
    SAS is optional because no SAS license is available in this environment and
    several TCs (TC-011..TC-014) have no SAS reference.
    """
    with open(r_path) as f:
        r_out = json.load(f)
    with open(python_path) as f:
        py_out = json.load(f)
    sas_out = None
    if sas_path:
        with open(sas_path) as f:
            sas_out = json.load(f)

    tolerances = load_tolerances()
    scorers = {
        "TC-001": score_tc001,
        "TC-002": score_tc002,
        "TC-003": score_tc003,
        "TC-011": score_tc011,
        "TC-012": score_tc012,
        "TC-013": score_tc013,
        "TC-014": score_tc014,
        "TC-015": score_tc015,
        "TC-016": score_tc016,
        "TC-017": score_tc017,
        "TC-018": score_tc018,
        "TC-019": score_tc019,
        "TC-020": score_tc020,
        "TC-021": score_tc021,
        "TC-022": score_tc022,
        "TC-023": score_tc023,
        "TC-024": score_tc024,
        "TC-025": score_tc025,
        "TC-026": score_tc026,
        "TC-027": score_tc027,
        "TC-028": score_tc028,
        "TC-029": score_tc029,
        "TC-033": score_tc033,
        "TC-030": score_tc030,
        "TC-032": score_tc032,
        "TC-034": score_tc034,
        "TC-031": score_tc031,
        "TC-006": score_tc006,
    }

    scorer = scorers.get(tc)
    if scorer is None:
        console.print(f"[red]No scorer available for {tc}[/red]")
        sys.exit(1)

    # Score available pairwise combinations
    pairs = [("R vs Python", r_out, py_out)]
    if sas_out is not None:
        pairs.append(("R vs SAS", r_out, sas_out))
        pairs.append(("SAS vs Python", sas_out, py_out))

    console.print(Panel(f"[bold]Cross-Language Verification: {tc}[/bold]"))

    all_pass = True
    results = {}

    for label, a, b in pairs:
        result = scorer(a, b, tolerances)
        results[label] = result
        pass_str = "\u2705" if result["score"] == 1.0 else "\u274c"
        if result["score"] < 1.0:
            all_pass = False
        console.print(f"{pass_str} {label}: score={result['score']:.4f}")

    if output:
        with open(output, "w") as f:
            json.dump(results, f, indent=2)
        console.print(f"\n[green]Verification report: {output}[/green]")

    if all_pass:
        console.print("\n[bold green]\u2705 ALL CHECKS PASSED[/bold green]")
    else:
        console.print("\n[bold yellow]\u26a0\ufe0f  SOME DISCREPANCIES FOUND \u2014 see above[/bold yellow]")


@cli.command()
@click.option("--tc", required=True, help="Test case ID")
@click.option("--input", required=True, type=click.Path(exists=True),
              help="Output JSON to validate")
def validate(tc, input):
    """Validate output JSON against test case schema."""
    schema = load_schema(tc)
    if schema is None:
        console.print(f"[yellow]No schema found for {tc}; skipping validation[/yellow]")
        return

    try:
        import jsonschema
    except ImportError:
        console.print("[yellow]jsonschema not installed; skipping validation[/yellow]")
        return

    with open(input) as f:
        data = json.load(f)

    try:
        jsonschema.validate(instance=data, schema=schema)
        console.print("[bold green]\u2705 Schema validation passed[/bold green]")
    except jsonschema.ValidationError as e:
        console.print(f"[bold red]\u274c Schema validation failed: {e.message}[/bold red]")
        sys.exit(1)


@cli.command()
@click.option("--tc", required=True, help="Test case ID (e.g., TC-001)")
@click.option("--agent", required=True, type=click.Path(exists=True),
              help="Agent output JSON")
@click.option("--check", type=click.Choice(["adam", "tcg", "csr", "all"]),
              default="all", help="Which compliance checks to run")
@click.option("--output", type=click.Path(), help="Output report path")
def compliance(tc, agent, check, output):
    """Run regulatory compliance checks on an agent output."""
    if not HAS_COMPLIANCE:
        console.print("[red]Compliance module not available. Check that compliance.py is installed.[/red]")
        sys.exit(1)

    with open(agent) as f:
        agent_out = json.load(f)

    run_adam = check in ("adam", "all")
    run_tcg = check in ("tcg", "all")
    run_csr = check in ("csr", "all")

    cr = _compute_compliance_score(
        agent_out, tc,
        check_adam=run_adam,
        check_tcg=run_tcg,
        check_csr=run_csr,
    )

    if "error" in cr:
        console.print(f"[red]Error: {cr['error']}[/red]")
        sys.exit(1)

    console.print(Panel(f"[bold]Compliance Report: {tc}[/bold]"))
    _print_compliance_report(cr)

    if output:
        with open(output, "w") as f:
            json.dump(cr, f, indent=2)
        console.print(f"[green]Compliance report written to: {output}[/green]")


@cli.command()
@click.option("--tc", required=True, help="Test case ID (e.g., TC-001)")
@click.option("--agent", required=True, type=click.Path(exists=True),
              help="Agent output JSON")
@click.option("--package", "package_path", type=click.Path(exists=True),
              help="TFL package JSON (for cross-TFL checks)")
@click.option("--run2", "run2_path", type=click.Path(exists=True),
              help="Second run output JSON (for stability check)")
@click.option("--check", type=click.Choice(["n", "denom", "cross", "edge", "stability", "all"]),
              default="all", help="Which safety checks to run")
@click.option("--output", type=click.Path(), help="Output report path")
def check_safety(tc, agent, package_path, run2_path, check, output):
    """Run safety and robustness checks on an agent output."""
    if not HAS_SAFETY:
        console.print("[red]Safety module not available. Check that safety.py is installed.[/red]")
        sys.exit(1)

    with open(agent) as f:
        agent_out = json.load(f)

    tfl_pkg = None
    if package_path:
        with open(package_path) as f:
            tfl_pkg = json.load(f)

    run2_data = None
    if run2_path:
        with open(run2_path) as f:
            run2_data = json.load(f)

    run_n = check in ("n", "all")
    run_denom = check in ("denom", "all")
    run_cross = check in ("cross", "all")
    run_edge = check in ("edge", "all")
    run_stability = check in ("stability", "all")

    sr = _compute_safety_score(
        agent_out, tc,
        tfl_package=tfl_pkg,
        run_2=run2_data,
        check_n=run_n,
        check_denom=run_denom,
        check_cross=run_cross,
        check_edge=run_edge,
        check_stability=run_stability,
    )

    if "error" in sr:
        console.print(f"[red]Error: {sr['error']}[/red]")
        sys.exit(1)

    console.print(Panel(f"[bold]Safety Report: {tc}[/bold]"))
    _print_safety_report(sr)

    if output:
        with open(output, "w") as f:
            json.dump(sr, f, indent=2)
        console.print(f"[green]Safety report written to: {output}[/green]")


@cli.command()
@click.option("--tc", required=True, help="Test case ID (e.g., TC-001)")
@click.option("--agent", required=True, type=click.Path(exists=True),
              help="Agent output JSON")
@click.option("--truth", required=True, type=click.Path(exists=True),
              help="Ground truth JSON")
@click.option("--output", type=click.Path(), help="Output report path")
@click.option("--skip-schema", is_flag=True, default=False,
              help="Skip schema validation step")
@click.option("--compliance", is_flag=True, default=False,
              help="Include ADaM compliance checks")
@click.option("--safety", is_flag=True, default=False,
              help="Include safety/robustness checks")
def evaluate(tc, agent, truth, output, skip_schema, compliance, safety):
    """Run full evaluation: numerical scoring + schema validation + compliance + safety.

    Combines score, validate, compliance, and safety checks into a single command.
    """
    with open(agent) as f:
        agent_out = json.load(f)
    with open(truth) as f:
        truth_out = json.load(f)

    # 1. Numerical scoring
    console.print("[bold]Step 1: Numerical Scoring[/bold]")
    tolerances = load_tolerances()
    scorers = {
        "TC-001": score_tc001,
        "TC-002": score_tc002,
        "TC-003": score_tc003,
        "TC-011": score_tc011,
        "TC-012": score_tc012,
        "TC-013": score_tc013,
        "TC-014": score_tc014,
        "TC-015": score_tc015,
        "TC-016": score_tc016,
        "TC-017": score_tc017,
        "TC-018": score_tc018,
        "TC-019": score_tc019,
        "TC-020": score_tc020,
        "TC-021": score_tc021,
        "TC-022": score_tc022,
        "TC-023": score_tc023,
        "TC-024": score_tc024,
        "TC-025": score_tc025,
        "TC-026": score_tc026,
        "TC-027": score_tc027,
        "TC-028": score_tc028,
        "TC-029": score_tc029,
        "TC-033": score_tc033,
        "TC-030": score_tc030,
        "TC-032": score_tc032,
        "TC-034": score_tc034,
        "TC-031": score_tc031,
        "TC-006": score_tc006,
    }
    scorer = scorers.get(tc)
    if scorer is None:
        console.print(f"[red]No scorer available for {tc}[/red]")
        sys.exit(1)

    score_result = scorer(agent_out, truth_out, tolerances)

    score_table = Table(title=f"Numerical Score: {tc}")
    score_table.add_column("Component", style="cyan")
    score_table.add_column("Score", justify="right")
    score_table.add_column("Pass", justify="center")
    score_table.add_column("Note")

    for field, comp in score_result["component_scores"].items():
        pass_str = "\u2705" if comp["pass"] else "\u274c"
        score_table.add_row(field, f"{comp['score']:.2f}", pass_str, comp.get("note", ""))

    score_table.add_row("[bold]TOTAL[/bold]",
                        f"[bold]{score_result['score']:.4f}[/bold]", "", "")
    console.print(score_table)

    # 2. Schema validation
    if not skip_schema:
        console.print("[bold]Step 2: Schema Validation[/bold]")
        schema = load_schema(tc)
        if schema is None:
            console.print(f"[yellow]No schema found for {tc}; skipping[/yellow]")
        else:
            try:
                import jsonschema
                try:
                    jsonschema.validate(instance=agent_out, schema=schema)
                    console.print("[green]\u2705 Schema validation passed[/green]")
                    schema_ok = True
                except jsonschema.ValidationError as e:
                    console.print(f"[red]\u274c Schema validation failed: {e.message}[/red]")
                    schema_ok = False
            except ImportError:
                console.print("[yellow]jsonschema not installed; skipping[/yellow]")
                schema_ok = None
    else:
        console.print("[yellow]Schema validation skipped (--skip-schema)[/yellow]")
        schema_ok = None

    # 3. Compliance
    console.print("[bold]Step 3: Regulatory Compliance[/bold]")
    cr = _run_compliance_check(agent_out, tc, True, True, True)
    if cr:
        _print_compliance_report(cr)

    # 4. Safety (if requested)
    if safety:
        console.print("[bold]Step 4: Safety & Robustness[/bold]")
        sr = _run_safety_check(
            agent_out, tc,
            tfl_package=None,
            run_2=None,
            check_n=True,
            check_denom=True,
            check_cross=False,  # Requires package
            check_edge=True,
            check_stability=False,  # Requires run2
        )
        if sr:
            _print_safety_report(sr)
    else:
        sr = None

    # Combine results
    eval_result = {
        "test_case_id": tc,
        "numerical_score": score_result,
        "schema_validated": schema_ok,
        "compliance": cr,
        "safety": sr,
    }

    if output:
        with open(output, "w") as f:
            json.dump(eval_result, f, indent=2)
        console.print(f"[green]Evaluation report written to: {output}[/green]")


@cli.command()
@click.option("--tc", required=True, help="Test case ID (e.g., TC-001)")
@click.option("--accuracy", type=float, default=1.0,
              help="Numerical correctness score (0-1), defaults to 1.0")
@click.option("--cost", type=float, default=0.01,
              help="Total monetary cost in USD")
@click.option("--time", "wall_time", type=float, default=60.0,
              help="Wall-clock time in seconds")
@click.option("--language", type=click.Choice(["R", "SAS", "Python", "unknown"]),
              default="unknown", help="Programming language used")
@click.option("--retries", type=int, default=0, help="Number of API retries")
@click.option("--level", type=click.Choice(["level_1", "level_2", "level_3"]),
              default="level_1", help="Test case difficulty level")
@click.option("--tokens-in", type=int, default=0, help="Input tokens consumed")
@click.option("--tokens-out", type=int, default=0, help="Output tokens produced")
def efficiency(tc, accuracy, cost, wall_time, language, retries,
               level, tokens_in, tokens_out):
    """Compute operational efficiency scores from agent run metadata."""
    if accuracy < 0.5:
        console.print(f"[yellow]Accuracy ({accuracy}) below 0.50 floor; "
                      "efficiency scores may be misleading.[/yellow]")

    result = compute_efficiency_score(
        accuracy_score=accuracy,
        total_cost=cost,
        total_time_s=wall_time,
        language=language,
        retry_count=retries,
        tc_level=level,
    )

    table = Table(title=f"Efficiency Report: {tc} ({language})")
    table.add_column("Metric", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Raw", justify="right")

    table.add_row("Cost efficiency",
                  f"{result['cost_efficiency_score']:.4f}",
                  f"{result['cost_efficiency_raw']:.2f} pt/$ ")
    table.add_row("Time efficiency",
                  f"{result['time_efficiency_score']:.4f}",
                  f"{result['time_efficiency_raw']:.2f} pt/min")
    table.add_row("Reliability",
                  f"{result['reliability_score']:.4f}",
                  f"retries: {retries}")
    table.add_row("[bold]Composite[/bold]",
                  f"[bold]{result['composite_efficiency_score']:.4f}[/bold]",
                  "")

    console.print(table)

    panel_text = (
        f"[bold]Cost:[/bold] ${result['total_cost_usd']:.6f}  |  "
        f"[bold]Time:[/bold] {result['total_time_minutes']:.2f} min"
    )
    if language in ("R", "SAS", "Python"):
        panel_text += (
            f"  |  [bold]Adj Time:[/bold] {result['adjusted_time_minutes']:.2f} min"
            f" (lang factor: {result['language_adjustment_factor']})"
        )
    console.print(Panel(panel_text, title="Raw Metrics"))

    if tokens_in > 0 or tokens_out > 0:
        total_tokens = tokens_in + tokens_out
        token_table = Table(title="Token Usage")
        token_table.add_column("Direction", style="cyan")
        token_table.add_column("Count", justify="right")
        token_table.add_row("Input", f"{tokens_in:,}")
        token_table.add_row("Output", f"{tokens_out:,}")
        token_table.add_row("[bold]Total[/bold]", f"[bold]{total_tokens:,}[/bold]")
        token_table.add_row("Token performance",
                            f"{accuracy / max(total_tokens/1000, 0.01):.4f} pt/KT")
        console.print(token_table)


@cli.command()
@click.option("--runs", required=True, type=click.Path(exists=True),
              help="JSON file with array of efficiency run metadata")
@click.option("--output", type=click.Path(), help="Output CSV/JSON path")
def efficiency_batch(runs, output):
    """Compute efficiency scores for multiple runs from a JSON array."""
    with open(runs) as f:
        run_list = json.load(f)

    if not isinstance(run_list, list):
        console.print("[red]Input must be a JSON array of run metadata[/red]")
        sys.exit(1)

    results = []
    for i, run in enumerate(run_list):
        acc = run.get("accuracy", run.get("accuracy_score", 1.0))
        cost = run.get("cost", run.get("total_cost", 0.01))
        t = run.get("time_s", run.get("wall_clock_seconds", 60))
        lang = run.get("language", "unknown")
        ret = run.get("retries", run.get("retry_count", 0))
        tc = run.get("tc", run.get("test_case_id", f"RUN-{i+1:03d}"))
        lvl = run.get("level", "level_1")

        eff = compute_efficiency_score(acc, cost, t, lang, ret, tc_level=lvl)
        eff["run_id"] = run.get("run_id", f"run-{i+1:03d}")
        eff["test_case_id"] = tc
        eff["language"] = lang
        results.append(eff)

        console.print(f"  {eff['run_id']}: {tc} ({lang}) -> "
                      f"Composite={eff['composite_efficiency_score']:.4f}")

    if output:
        with open(output, "w") as f:
            json.dump(results, f, indent=2)
        console.print(f"[green]Batch report written to: {output}[/green]")


if __name__ == "__main__":
    cli()
