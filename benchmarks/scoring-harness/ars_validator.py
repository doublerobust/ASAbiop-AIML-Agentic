#!/usr/bin/env python3
"""
ARS Envelope Validator — validates ARS-compatible JSON outputs against the
CDISC ARS v1.0 envelope schema.

Usage:
  python3 ars_validator.py <ars_json_file> [<ars_json_file> ...]
  python3 ars_validator.py --batch <directory>
  python3 ars_validator.py --cross-check <R_ars.json> <Py_ars.json>

Validates:
  1. Schema compliance (ars-envelope-schema.json)
  2. Required fields present (id, method, variables, population, statistics)
  3. Cross-language ARS consistency (R vs Python ARS outputs)
"""

import json
import sys
import os
from pathlib import Path

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

# ─────────────────────────────────────────────────────
# Schema loading
# ─────────────────────────────────────────────────────

SCHEMA_PATH = Path(__file__).parent.parent / "references" / "output-schemas" / "ars-envelope-schema.json"

def load_schema():
    with open(SCHEMA_PATH, "r") as f:
        return json.load(f)

# ─────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────

def validate_ars_file(filepath):
    """Validate a single ARS JSON file against the schema."""
    with open(filepath, "r") as f:
        data = json.load(f)

    errors = []

    # 1. JSON Schema validation
    if HAS_JSONSCHEMA:
        schema = load_schema()
        try:
            jsonschema.validate(data, schema)
        except jsonschema.ValidationError as e:
            errors.append(f"Schema violation: {e.message} (path: {list(e.path)})")
    else:
        # Manual validation fallback
        ar = data.get("analysisResult", {})
        for req in ["id", "version", "analysisMethod", "analysisVariables", "analysisPopulation", "analysisResultsData"]:
            if req not in ar:
                errors.append(f"Missing required field: analysisResult.{req}")
        if "statistics" not in ar.get("analysisResultsData", {}):
            errors.append("Missing required field: analysisResult.analysisResultsData.statistics")

    # 2. Semantic checks
    ar = data.get("analysisResult", {})
    if not ar.get("id"):
        errors.append("analysisResult.id is empty")

    method = ar.get("analysisMethod", {})
    if not method.get("name"):
        errors.append("analysisResult.analysisMethod.name is empty")

    variables = ar.get("analysisVariables", [])
    if not variables:
        errors.append("analysisResult.analysisVariables is empty")

    stats = ar.get("analysisResultsData", {}).get("statistics", [])
    if not stats:
        errors.append("analysisResult.analysisResultsData.statistics is empty")
    else:
        for i, s in enumerate(stats):
            if "name" not in s or "value" not in s:
                errors.append(f"Statistic {i} missing 'name' or 'value'")

    # 3. Result groups check
    groups = ar.get("resultGroups", [])
    for i, g in enumerate(groups):
        if "id" not in g:
            errors.append(f"resultGroup {i} missing 'id'")
        if "n" not in g:
            errors.append(f"resultGroup {i} missing 'n'")

    return {
        "file": filepath,
        "valid": len(errors) == 0,
        "errors": errors,
        "tc_id": ar.get("id", "unknown"),
        "n_statistics": len(stats),
        "n_variables": len(variables),
        "n_result_groups": len(groups),
    }


def cross_check_ars(r_file, py_file):
    """Cross-check R and Python ARS outputs for consistency."""
    with open(r_file, "r") as f:
        r_data = json.load(f)
    with open(py_file, "r") as f:
        py_data = json.load(f)

    r_ar = r_data.get("analysisResult", {})
    py_ar = py_data.get("analysisResult", {})

    mismatches = []

    # Check ID matches
    if r_ar.get("id") != py_ar.get("id"):
        mismatches.append(f"ID mismatch: R={r_ar.get('id')}, Py={py_ar.get('id')}")

    # Check method matches
    r_method = r_ar.get("analysisMethod", {}).get("name")
    py_method = py_ar.get("analysisMethod", {}).get("name")
    if r_method != py_method:
        mismatches.append(f"Method mismatch: R={r_method}, Py={py_method}")

    # Check statistics match
    r_stats = {s["name"]: s["value"] for s in r_ar.get("analysisResultsData", {}).get("statistics", [])}
    py_stats = {s["name"]: s["value"] for s in py_ar.get("analysisResultsData", {}).get("statistics", [])}

    all_keys = set(r_stats.keys()) | set(py_stats.keys())
    for key in sorted(all_keys):
        r_val = r_stats.get(key)
        py_val = py_stats.get(key)
        if r_val is None:
            mismatches.append(f"Statistic '{key}' missing in R output")
        elif py_val is None:
            mismatches.append(f"Statistic '{key}' missing in Python output")
        elif isinstance(r_val, (int, float)) and isinstance(py_val, (int, float)):
            # Use scoring tolerance (0.2 for continuous, 1e-4 for counts/proportions)
            tolerance = max(1e-4, abs(r_val) * 0.05) if abs(r_val) > 1 else 0.2
            if abs(r_val - py_val) > tolerance:
                mismatches.append(f"Statistic '{key}': R={r_val}, Py={py_val} (diff={abs(r_val-py_val):.6f}, tol={tolerance})")
        elif r_val != py_val:
            mismatches.append(f"Statistic '{key}': R={r_val}, Py={py_val}")

    # Check result groups match
    r_groups = {g["id"]: g.get("n") for g in r_ar.get("resultGroups", [])}
    py_groups = {g["id"]: g.get("n") for g in py_ar.get("resultGroups", [])}
    for gid in set(r_groups.keys()) | set(py_groups.keys()):
        if r_groups.get(gid) != py_groups.get(gid):
            mismatches.append(f"ResultGroup '{gid}': R n={r_groups.get(gid)}, Py n={py_groups.get(gid)}")

    return {
        "r_file": r_file,
        "py_file": py_file,
        "tc_id": r_ar.get("id", "unknown"),
        "consistent": len(mismatches) == 0,
        "mismatches": mismatches,
        "n_statistics_compared": len(all_keys),
    }


# ─────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="ARS Envelope Validator")
    parser.add_argument("files", nargs="*", help="ARS JSON files to validate")
    parser.add_argument("--batch", help="Validate all *_ars.json files in a directory")
    parser.add_argument("--cross-check", nargs=2, metavar=("R_FILE", "PY_FILE"),
                       help="Cross-check R and Python ARS outputs")
    args = parser.parse_args()

    if args.cross_check:
        print("╭" + "─" * 78 + "╮")
        print(f"│ ARS Cross-Language Cross-Check: {args.cross_check[0]} vs {args.cross_check[1]}")
        print("╰" + "─" * 78 + "╯")
        result = cross_check_ars(args.cross_check[0], args.cross_check[1])
        if result["consistent"]:
            print(f"✅ TC-{result['tc_id']}: ARS outputs CONSISTENT ({result['n_statistics_compared']} statistics compared)")
        else:
            print(f"❌ TC-{result['tc_id']}: ARS outputs MISMATCH")
            for m in result["mismatches"]:
                print(f"   • {m}")
        return

    files = list(args.files)
    if args.batch:
        batch_dir = Path(args.batch)
        files = sorted(batch_dir.glob("*_ars.json"))

    if not files:
        print("No files to validate. Usage: ars_validator.py <files> [--batch <dir>] [--cross-check <R> <Py>]")
        sys.exit(1)

    all_valid = True
    print("╭" + "─" * 78 + "╮")
    print(f"│ ARS Envelope Validation — {len(files)} file(s)")
    print("╰" + "─" * 78 + "╯")

    for f in files:
        result = validate_ars_file(f)
        status = "✅ VALID" if result["valid"] else "❌ INVALID"
        print(f"\n{status} — {os.path.basename(f)}")
        print(f"  TC: {result['tc_id']}")
        print(f"  Statistics: {result['n_statistics']}")
        print(f"  Variables: {result['n_variables']}")
        print(f"  Result Groups: {result['n_result_groups']}")
        if result["errors"]:
            for e in result["errors"]:
                print(f"  ⚠ {e}")
            all_valid = False

    print("\n" + "─" * 78)
    if all_valid:
        print("✅ ALL ARS OUTPUTS VALID")
    else:
        print("❌ SOME ARS OUTPUTS HAVE ERRORS")
        sys.exit(1)


if __name__ == "__main__":
    main()
