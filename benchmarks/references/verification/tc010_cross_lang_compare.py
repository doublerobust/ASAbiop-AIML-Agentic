#!/usr/bin/env python3
"""tc010_cross_lang_compare.py — TC-010 R↔Python Cross-Language Verifier

Recursively compares every leaf value in the R and Python TC-010 JSON outputs.
Reports per-field match/mismatch and an overall cross-language score.

Usage:
    python3 tc010_cross_lang_compare.py <r_output.json> <py_output.json> [--tolerance TOL]
"""

import argparse
import json
import math
import sys
from pathlib import Path


def flatten(obj, prefix=""):
    """Recursively flatten a nested dict/list into {path: leaf_value}."""
    leaves = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            leaves.update(flatten(v, key))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            key = f"{prefix}[{i}]"
            leaves.update(flatten(v, key))
    else:
        leaves[prefix] = obj
    return leaves


def values_match(r_val, py_val, tol):
    """Check if R and Python values match within tolerance."""
    # Both None
    if r_val is None and py_val is None:
        return True, "both None"
    # One None
    if r_val is None or py_val is None:
        return False, f"None mismatch: R={r_val}, Py={py_val}"
    # Booleans
    if isinstance(r_val, bool) or isinstance(py_val, bool):
        return r_val == py_val, f"bool: R={r_val}, Py={py_val}"
    # Numeric
    try:
        r_f = float(r_val)
        py_f = float(py_val)
        if math.isnan(r_f) and math.isnan(py_f):
            return True, "both NaN"
        diff = abs(r_f - py_f)
        ok = diff <= tol
        return ok, f"num: R={r_f}, Py={py_f}, diff={diff:.6f}, tol={tol}"
    except (ValueError, TypeError):
        pass
    # String
    r_s = str(r_val)
    py_s = str(py_val)
    ok = r_s == py_s
    return ok, f"str: R='{r_s}', Py='{py_s}'"


def main():
    parser = argparse.ArgumentParser(description="TC-010 R↔Python cross-language comparator")
    parser.add_argument("r_file", help="R output JSON")
    parser.add_argument("py_file", help="Python output JSON")
    parser.add_argument("--tolerance", type=float, default=1e-4,
                        help="Numeric tolerance (default: 1e-4)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show mismatches")
    args = parser.parse_args()

    # Fields excluded from comparison: language-specific software metadata
    # (R reports R/survival, Python reports python/lifelines — intentionally different)
    EXCLUDE_PREFIXES = ["section_9_methods.software"]

    r_data = json.loads(Path(args.r_file).read_text())
    py_data = json.loads(Path(args.py_file).read_text())

    r_flat = flatten(r_data)
    py_flat = flatten(py_data)

    all_keys = set(r_flat.keys()) | set(py_flat.keys())
    # Remove excluded keys
    all_keys = {k for k in all_keys
                if not any(k.startswith(p) for p in EXCLUDE_PREFIXES)}
    r_flat = {k: v for k, v in r_flat.items() if k in all_keys}
    py_flat = {k: v for k, v in py_flat.items() if k in all_keys}

    matches = 0
    mismatches = 0
    mismatch_details = []

    for key in sorted(all_keys):
        r_val = r_flat.get(key, "<MISSING>")
        py_val = py_flat.get(key, "<MISSING>")
        ok, detail = values_match(r_val, py_val, args.tolerance)
        if ok:
            matches += 1
        else:
            mismatches += 1
            mismatch_details.append((key, detail))

    total = matches + mismatches
    score = matches / total if total > 0 else 0.0

    print(f"TC-010 Cross-Language Verification Results")
    print(f"=" * 60)
    print(f"R file:     {args.r_file}")
    print(f"Python file: {args.py_file}")
    print(f"Tolerance:  {args.tolerance}")
    print(f"-" * 60)
    print(f"Total fields:  {total}")
    print(f"Matches:       {matches}")
    print(f"Mismatches:    {mismatches}")
    print(f"Score:         {score:.4f}")
    print(f"-" * 60)

    if mismatches > 0:
        print(f"\nMismatch details ({mismatches}):")
        for key, detail in mismatch_details[:50]:
            print(f"  {key}: {detail}")
        if len(mismatch_details) > 50:
            print(f"  ... and {len(mismatch_details) - 50} more")
    else:
        print("\n✅ All fields match — cross-language score = 1.0000")

    # Exit code
    sys.exit(0 if score == 1.0 else 1)


if __name__ == "__main__":
    main()
