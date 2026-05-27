#!/usr/bin/env python3
"""katsu — TFL Scoring and Evaluation Harness for the ASA Biopharm Benchmark

Evaluate AI agent outputs against cross-validated ground truth for TFL
(Tables, Figures, Listings) benchmark test cases.

Supports:
- Numerical comparison with configurable tolerance
- Schema validation
- Cross-language ground truth verification
- Weighted scoring per test case

Usage:
  # Score an agent output
  python score.py score --tc TC-001 --agent agent.json --truth ground_truth.json

  # Verify cross-language consistency
  python score.py verify --tc TC-001 --r R.json --sas SAS.json --python Python.json

  # Validate schema
  python score.py validate --tc TC-001 --input output.json
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

# ─────────────────────────────────────────────────────
# Tolerance Loading
# ─────────────────────────────────────────────────────

def load_tolerances():
    """Load tolerance specs from tolerances.yaml."""
    tol_path = Path(__file__).parent / "tolerances.yaml"
    with open(tol_path) as f:
        return yaml.safe_load(f)


def load_schema(tc_id: str) -> dict:
    """Load JSON Schema for a test case."""
    schema_dir = Path(__file__).resolve().parent.parent / "references" / "output-schemas"
    tc_name = tc_id.lower().replace("-", "_")
    schema_path = schema_dir / f"{tc_id.lower()}-output-schema.json"

    if not schema_path.exists():
        # Try alternative naming
        schema_path = schema_dir / f"{tc_id.lower()}-output-schema.json"

    if schema_path.exists():
        with open(schema_path) as f:
            return json.load(f)
    return None


# ─────────────────────────────────────────────────────
# Comparison Logic
# ─────────────────────────────────────────────────────

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
    # Handle NA/null cases
    if value_a is None and value_b is None:
        return {"score": 1.0, "pass": True, "diff": 0, "note": "both null — acceptable"}
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
        # Exact match
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


# ─────────────────────────────────────────────────────
# Scoring
# ─────────────────────────────────────────────────────

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


def score_tc002(agent_output: dict, ground_truth: dict, tolerances: dict) -> dict:
    """Score TC-002 (Baseline Demographics Table) agent output against ground truth."""
    tol_spec = tolerances.get("TC-002", {}).get("tolerances", {})

    component_scores = {}
    total_weight = 0
    weighted_sum = 0

    # Continuous fields (age stats)
    cont_fields = ["mean", "std", "median"]
    for field in cont_fields:
        field_tol = tol_spec.get(field, {"absolute": 0.05, "weight": 0.10})
        weight = field_tol.get("weight", 0.10)
        result = compare_numeric(
            agent_output.get(field), ground_truth.get(field),
            field_tol, field
        )
        component_scores[field] = result
        weighted_sum += result["score"] * weight
        total_weight += weight

    # Counts (exact match)
    count_fields = ["n_total"]
    for field in count_fields:
        field_tol = tol_spec.get(field, {"absolute": 0, "weight": 0.10})
        weight = field_tol.get("weight", 0.10)
        result = compare_count(agent_output.get(field), ground_truth.get(field))
        component_scores[field] = result
        weighted_sum += result["score"] * weight
        total_weight += weight

    # Categorical counts
    agent_counts = agent_output.get("categorical_by_arm", [])
    truth_counts = ground_truth.get("categorical_by_arm", [])

    if agent_counts and truth_counts:
        # Simple comparison: flatten and compare counts
        agent_tuples = {(c.get("variable"), c.get("level"),
                        c.get("TRT01PN"), c.get("n"))
                       for c in agent_counts if "n" in c}
        truth_tuples = {(c.get("variable"), c.get("level"),
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


# ─────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────

@click.group()
def cli():
    """katsu — TFL Scoring and Evaluation Harness."""
    pass


@cli.command()
@click.option("--tc", required=True, help="Test case ID (e.g., TC-001)")
@click.option("--agent", required=True, type=click.Path(exists=True),
              help="Agent output JSON")
@click.option("--truth", required=True, type=click.Path(exists=True),
              help="Ground truth JSON")
@click.option("--output", type=click.Path(), help="Output report path")
def score(tc, agent, truth, output):
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
    }

    scorer = scorers.get(tc)
    if scorer is None:
        console.print(f"[red]No scorer available for {tc}[/red]")
        sys.exit(1)

    result = scorer(agent_out, truth_out, tolerances)

    # Print report
    table = Table(title=f"Scoring Report: {tc}")
    table.add_column("Component", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Pass", justify="center")
    table.add_column("Note")

    for field, comp in result["component_scores"].items():
        pass_str = "✅" if comp["pass"] else "❌"
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

    if output:
        with open(output, "w") as f:
            json.dump(result, f, indent=2)
        console.print(f"[green]Report written to: {output}[/green]")


@cli.command()
@click.option("--tc", required=True, help="Test case ID")
@click.option("--r", "r_path", required=True, type=click.Path(exists=True))
@click.option("--sas", "sas_path", required=True, type=click.Path(exists=True))
@click.option("--python", "python_path", required=True, type=click.Path(exists=True))
@click.option("--output", type=click.Path(), help="Verification report path")
def verify(tc, r_path, sas_path, python_path, output):
    """Verify cross-language consistency of ground truth."""
    with open(r_path) as f:
        r_out = json.load(f)
    with open(sas_path) as f:
        sas_out = json.load(f)
    with open(python_path) as f:
        py_out = json.load(f)

    tolerances = load_tolerances()
    scorers = {
        "TC-001": score_tc001,
        "TC-002": score_tc002,
        "TC-003": score_tc003,
    }

    scorer = scorers.get(tc)
    if scorer is None:
        console.print(f"[red]No scorer available for {tc}[/red]")
        sys.exit(1)

    # Score all pairwise combinations
    pairs = [
        ("R vs SAS", r_out, sas_out),
        ("R vs Python", r_out, py_out),
        ("SAS vs Python", sas_out, py_out),
    ]

    console.print(Panel(f"[bold]Cross-Language Verification: {tc}[/bold]"))

    all_pass = True
    results = {}

    for label, a, b in pairs:
        result = scorer(a, b, tolerances)
        results[label] = result
        pass_str = "✅" if result["score"] == 1.0 else "❌"
        if result["score"] < 1.0:
            all_pass = False
        console.print(f"{pass_str} {label}: score={result['score']:.4f}")

    if output:
        with open(output, "w") as f:
            json.dump(results, f, indent=2)
        console.print(f"\n[green]Verification report: {output}[/green]")

    if all_pass:
        console.print("\n[bold green]✅ ALL CHECKS PASSED[/bold green]")
    else:
        console.print("\n[bold yellow]⚠️  SOME DISCREPANCIES FOUND — see above[/bold yellow]")


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
        console.print("[bold green]✅ Schema validation passed[/bold green]")
    except jsonschema.ValidationError as e:
        console.print(f"[bold red]❌ Schema validation failed: {e.message}[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    cli()
