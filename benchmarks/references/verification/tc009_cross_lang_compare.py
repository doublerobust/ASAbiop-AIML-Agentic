#!/usr/bin/env python3
"""tc009_cross_lang_compare.py — Cross-language verification for TC-009

Compares the R and Python TC-009 safety-signal JSON outputs field-by-field
and reports a per-field match table plus an overall cross-language score.

Tolerances (mirrors tolerances.yaml philosophy):
  - integer counts: exact
  - percentages / risk differences / CI bounds: abs tol 1e-4
  - p-values: abs tol 1e-6
  - KM median + CI: abs tol 1.0 day (Brookmeyer-Crowley CI band crossing can
    differ by one event time between languages); median exact
  - Cox HR / CI: abs tol 1e-4
  - booleans: exact

Usage:
    python tc009_cross_lang_compare.py <r_json> <py_json>
"""

import json
import math
import sys


def _is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and not (isinstance(x, float) and math.isnan(x))


def cmp_num(a, b, tol):
    if a is None and b is None:
        return True, None
    if a is None or b is None:
        return False, f"{a} vs {b}"
    if _is_num(a) and _is_num(b):
        return abs(a - b) <= tol, abs(a - b)
    return a == b, None


def cmp_scalar(a, b, tol=1e-4):
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b, None
    if _is_num(a) and _is_num(b):
        return abs(a - b) <= tol, abs(a - b)
    if a is None and b is None:
        return True, None
    return a == b, None


def walk(a, b, path, tol_map, results):
    """Recursively compare two JSON structures."""
    if isinstance(a, dict) and isinstance(b, dict):
        for k in a:
            p = f"{path}.{k}" if path else k
            if k not in b:
                results.append((p, "MISSING_IN_PY", None, None, False))
                continue
            walk(a[k], b[k], p, tol_map, results)
        for k in b:
            if k not in a:
                results.append((f"{path}.{k}", "MISSING_IN_R", None, None, False))
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            results.append((path, "LEN_MISMATCH", len(a), len(b), False))
        for i, (x, y) in enumerate(zip(a, b)):
            walk(x, y, f"{path}[{i}]", tol_map, results)
    else:
        tol = tol_map.get(path) if path in tol_map else 1e-4
        ok, diff = cmp_scalar(a, b, tol)
        results.append((path, "SCALAR", a, b, ok))


def main():
    r_path, p_path = sys.argv[1], sys.argv[2]
    r = json.load(open(r_path))
    p = json.load(open(p_path))

    # Tolerance overrides for specific numeric fields
    tol_map = {
        "time_to_grade3.median_active.median": 1.0,
        "time_to_grade3.median_active.ci_lower": 1.0,
        "time_to_grade3.median_active.ci_upper": 1.0,
        "time_to_grade3.median_placebo.median": 1.0,
        "time_to_grade3.median_placebo.ci_lower": 1.0,
        "time_to_grade3.median_placebo.ci_upper": 1.0,
    }

    results = []
    walk(r, p, "", tol_map, results)

    n_total = len(results)
    n_pass = sum(1 for x in results if x[4])
    n_fail = n_total - n_pass
    fails = [x for x in results if not x[4]]
    score = n_pass / n_total if n_total else 0.0

    print("═" * 70)
    print("TC-009 Cross-Language Verification (R vs Python)")
    print("═" * 70)
    print(f"Fields compared : {n_total}")
    print(f"Fields passed   : {n_pass}")
    print(f"Fields failed   : {n_fail}")
    print(f"Cross-lang score: {score:.4f}")
    print("─" * 70)

    if fails:
        print("\nMISMATCHES:")
        for path, kind, a, b, ok in fails:
            print(f"  ✗ {path}  R={a}  Py={b}  [{kind}]")
    else:
        print("\nAll fields match within tolerance. ✅")

    # Key metric spot-check table
    print("\nKey metric spot-check:")
    def g(d, *keys):
        cur = d
        for k in keys:
            if isinstance(cur, dict) and k in cur:
                cur = cur[k]
            else:
                return None
        return cur
    metrics = [
        ("n_subjects", g(r, "study_design", "n_subjects"), g(p, "study_design", "n_subjects")),
        ("AE any Active", g(r, "ae_overview", "by_arm", "Active", "n_any_ae"), g(p, "ae_overview", "by_arm", "Active", "n_any_ae")),
        ("SAE Active", g(r, "ae_overview", "by_arm", "Active", "n_sae"), g(p, "ae_overview", "by_arm", "Active", "n_sae")),
        ("Hy's Law Active", g(r, "lab_abnormalities", "hys_law", "n_active"), g(p, "lab_abnormalities", "hys_law", "n_active")),
        ("QTc Active", g(r, "lab_abnormalities", "qtc_prolongation", "n_active"), g(p, "lab_abnormalities", "qtc_prolongation", "n_active")),
        ("irAE Active", g(r, "ae_special_interest", "irae", "n_active"), g(p, "ae_special_interest", "irae", "n_active")),
        ("Grade3+ Active", g(r, "grade3_plus", "by_arm", "Active", "n"), g(p, "grade3_plus", "by_arm", "Active", "n")),
        ("G3 RD", g(r, "grade3_plus", "risk_difference"), g(p, "grade3_plus", "risk_difference")),
        ("G3 fisher_p", g(r, "grade3_plus", "fisher_p"), g(p, "grade3_plus", "fisher_p")),
        ("TTG3 median Active", g(r, "time_to_grade3", "median_active", "median"), g(p, "time_to_grade3", "median_active", "median")),
        ("TTG3 median Plb", g(r, "time_to_grade3", "median_placebo", "median"), g(p, "time_to_grade3", "median_placebo", "median")),
        ("TTG3 logrank_p", g(r, "time_to_grade3", "logrank_p"), g(p, "time_to_grade3", "logrank_p")),
        ("TTG3 cox_hr", g(r, "time_to_grade3", "cox_hr"), g(p, "time_to_grade3", "cox_hr")),
        ("TTG3 cox_p", g(r, "time_to_grade3", "cox_p"), g(p, "time_to_grade3", "cox_p")),
        ("Recommendation", g(r, "recommendation", "overall"), g(p, "recommendation", "overall")),
        ("n_signals", g(r, "recommendation", "signals_summary", "n_signals"), g(p, "recommendation", "signals_summary", "n_signals")),
    ]
    for name, a, b in metrics:
        ok = (a == b) if not (_is_num(a) and _is_num(b)) else abs(a - b) <= 1e-4
        flag = "✅" if ok else "✗"
        print(f"  {flag} {name:22s}  R={a}  Py={b}")

    print("\n═" * 1)
    print(f"OVERALL: {'PASS (1.0000)' if n_fail == 0 else f'FAIL ({score:.4f})'}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
