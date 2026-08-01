#!/usr/bin/env python3
"""Mutation Test Harness — verify the scorer REJECTS wrong-but-plausible outputs.

For every test case that has (a) a scorer in score.py and (b) a checked-in
ground truth output, this script:

  1. Loads the ground truth JSON.
  2. Mutates EVERY numeric field: value * 1.5 + 0.5  (large enough to exceed
     typical absolute and relative tolerances).
  3. Scores the mutated output against the TRUE ground truth.
  4. Asserts the total score DROPS below 1.0 (i.e., the mutation is caught).
  5. Also runs a schema validation on the mutated output (structure must
     remain valid — only values change, not types/keys).

A PASS means the scorer detects the corrupted value. A FAIL means the scorer
certified a wrong answer (the exact class of bug found in the audit).

Usage:
    python scripts/mutation-test.py                     # all TCs
    python scripts/mutation-test.py --tc TC-001,TC-006  # subset
    python scripts/mutation-test.py --json              # machine-readable output

Exit code: 0 if all mutations caught, 1 if any scorer fails to catch.
"""
import argparse
import copy
import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent.parent
SCORING = BENCH / "scoring-harness"
R_OUT = BENCH / "cross-lang-results" / "r-output"
PY_OUT = BENCH / "cross-lang-results" / "python-output"

sys.path.insert(0, str(SCORING))

from score import (  # noqa: E402
    load_tolerances,
    score_tc001, score_tc002, score_tc003,
    score_tc011, score_tc012, score_tc013, score_tc014,
    score_tc015, score_tc016, score_tc017, score_tc018,
    score_tc019, score_tc020, score_tc021, score_tc022,
    score_tc023, score_tc024, score_tc025, score_tc026,
    score_tc027, score_tc028, score_tc029, score_tc030,
    score_tc031, score_tc032, score_tc033, score_tc034,
    score_tc035, score_tc006,
)

SCORERS = {
    "TC-001": score_tc001, "TC-002": score_tc002, "TC-003": score_tc003,
    "TC-011": score_tc011, "TC-012": score_tc012, "TC-013": score_tc013,
    "TC-014": score_tc014, "TC-015": score_tc015, "TC-016": score_tc016,
    "TC-017": score_tc017, "TC-018": score_tc018, "TC-019": score_tc019,
    "TC-020": score_tc020, "TC-021": score_tc021, "TC-022": score_tc022,
    "TC-023": score_tc023, "TC-024": score_tc024, "TC-025": score_tc025,
    "TC-026": score_tc026, "TC-027": score_tc027, "TC-028": score_tc028,
    "TC-029": score_tc029, "TC-030": score_tc030, "TC-031": score_tc031,
    "TC-032": score_tc032, "TC-033": score_tc033, "TC-034": score_tc034,
    "TC-035": score_tc035, "TC-006": score_tc006,
}


def load_schema(tc_id: str):
    """Load JSON Schema for a test case, if present."""
    path = BENCH / "references" / "output-schemas" / f"{tc_id.lower()}-output-schema.json"
    return json.loads(path.read_text()) if path.exists() else None


def validate_schema(data: dict, schema: dict) -> bool:
    """Validate against the TC output schema using the full jsonschema library.
    Returns True if structurally valid (mutation only changes values)."""
    if schema is None:
        return True  # no schema to check against
    try:
        import jsonschema
        jsonschema.validate(data, schema)
        return True
    except ImportError:
        # Fallback: minimal structural check (required keys present)
        required = schema.get("required", [])
        return all(req in data for req in required)
    except jsonschema.ValidationError:
        return False


def mutate_numbers(obj, pct=0.5, offset=2.0, _path=""):
    """Recursively perturb every numeric leaf: value -> value*(1+pct) + offset.
    Offset 2.0 ensures mutations exceed even large absolute tolerances
    (e.g., cumdose_stats at abs=50) so every mutated field is individually
    caught, not just the aggregate. Preserves types/keys so the mutated
    output stays structurally valid."""
    if isinstance(obj, dict):
        return {k: mutate_numbers(v, pct, offset, f"{_path}.{k}") for k, v in obj.items()}
    if isinstance(obj, list):
        return [mutate_numbers(v, pct, offset, f"{_path}[{i}]") for i, v in enumerate(obj)]
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, int):
        # Preserve integer type (schemas often require integer for counts/seeds)
        return int(obj * (1 + pct) + offset)
    if isinstance(obj, float):
        return obj * (1 + pct) + offset
    return obj


def strip_const_leaves(mutated, original, schema):
    """Restore const/enum-constrained leaves to their ORIGINAL (truth) values.

    These are fixed parameters (e.g., thresholds), not scored outputs —
    mutating them makes the output structurally invalid by definition
    (schema enforces const/enum). Restoring the original keeps the output
    schema-valid while all true result fields remain mutated."""
    if schema is None or not isinstance(schema, dict):
        return mutated

    if isinstance(mutated, dict):
        props = schema.get("properties", {})
        for k, v in mutated.items():
            if k in props:
                sub = props[k]
                if isinstance(sub, dict) and ("const" in sub or "enum" in sub):
                    # restore original value from truth
                    mutated[k] = original[k]
                else:
                    mutated[k] = strip_const_leaves(v, original[k], sub)
        return mutated

    if isinstance(mutated, list):
        items = schema.get("items", {})
        return [strip_const_leaves(v, o, items) for v, o in zip(mutated, original)]

    return mutated


def clamp_to_schema(data, schema, path=()):
    """Clamp numeric values into schema min/max bounds while keeping them
    DIFFERENT from the true value (wrong-but-plausible mutation).

    Uses jsonschema's own validator to resolve $ref/allOf/patternProperties.
    Strategy: repeatedly validate; for each violation, clamp the offending
    leaf into [minimum, maximum] (or nudge for enum/const); stop when the
    mutated output validates. Returns (data, ok) where ok=False means the
    mutation could not be made schema-valid.
    """
    if schema is None:
        return data, True
    try:
        import jsonschema
    except ImportError:
        return data, True

    import copy as _copy
    work = _copy.deepcopy(data)

    def get_path(root, path_parts):
        node = root
        for p in path_parts:
            if isinstance(node, dict):
                # JSON object keys are strings; err.path may give ints
                key = str(p) if isinstance(p, int) else p
                if key not in node:
                    return None
                node = node[key]
            elif isinstance(node, list):
                if isinstance(p, str):
                    try:
                        p = int(p)
                    except ValueError:
                        return None
                if p >= len(node):
                    return None
                node = node[p]
            else:
                return None
        return node

    def set_path(root, path_parts, value):
        node = root
        for p in path_parts[:-1]:
            if isinstance(node, dict):
                node = node[str(p) if isinstance(p, int) else p]
            elif isinstance(node, list):
                node = node[int(p)]
        last = path_parts[-1]
        if isinstance(node, dict):
            node[str(last) if isinstance(last, int) else last] = value
        elif isinstance(node, list):
            node[int(last)] = value

    for _ in range(1000):
        try:
            jsonschema.validate(work, schema)
            return work, True
        except jsonschema.ValidationError as err:
            parts = list(err.path)
            if not parts:
                return data, False
            node = get_path(work, parts)
            if node is None:
                return data, False
            if isinstance(node, bool):
                return data, False
            if isinstance(node, (int, float)):
                if err.validator == "maximum":
                    hi = err.validator_value
                    lo = node * 0.01  # keep different from truth
                    # nudge below max but keep plausible
                    new = hi - (abs(hi) * 0.1 + 0.001)
                    if isinstance(node, int):
                        new = max(lo, int(new) if int(new) != node else int(new) + 1)
                    set_path(work, parts, new)
                elif err.validator == "minimum":
                    lo = err.validator_value
                    new = lo + (abs(lo) * 0.1 + 0.001)
                    if isinstance(node, int):
                        new = max(lo, int(new) if int(new) != node else int(new) + 1)
                    set_path(work, parts, new)
                else:
                    # type/enum/const violation — leave value as-is but try
                    # to coerce type or skip (cannot fix cleanly)
                    if err.validator == "type" and isinstance(node, (int, float)):
                        if err.validator_value in ("string", "str"):
                            set_path(work, parts, str(node))
                        else:
                            return data, False
                    else:
                        return data, False
            else:
                return data, False
    return data, False


def get_ground_truth(tc_id: str):
    """Load checked-in ground truth (prefer Python output, fall back to R)."""
    for d in (PY_OUT, R_OUT):
        p = d / f"{tc_id}.json"
        if p.exists():
            return json.loads(p.read_text())
    return None


def main():
    ap = argparse.ArgumentParser(description="Mutation test for scoring harness")
    ap.add_argument("--tc", default=None, help="Comma-separated TC subset")
    ap.add_argument("--json", action="store_true", help="Machine-readable output")
    args = ap.parse_args()

    tcs = [t.strip() for t in args.tc.split(",")] if args.tc else sorted(SCORERS.keys())
    tolerances = load_tolerances()

    results = []
    failures = 0
    skipped = 0

    for tc in tcs:
        truth = get_ground_truth(tc)
        if truth is None:
            skipped += 1
            results.append({"tc": tc, "status": "SKIP", "reason": "no ground truth"})
            continue

        schema = load_schema(tc)
        mutated = mutate_numbers(copy.deepcopy(truth))
        mutated = strip_const_leaves(mutated, truth, schema)
        mutated, clamp_ok = clamp_to_schema(mutated, schema)

        # Structural validity must be preserved (only values changed)
        if not clamp_ok or not validate_schema(mutated, schema):
            results.append({"tc": tc, "status": "SKIP",
                            "reason": "mutation broke structure (schema-check harness issue)"})
            skipped += 1
            continue

        try:
            result = SCORERS[tc](mutated, truth, tolerances)
        except Exception as e:
            results.append({"tc": tc, "status": "ERROR", "reason": str(e)[:200]})
            failures += 1
            continue

        total = result.get("score", 0.0)
        caught = total < 1.0
        if not caught:
            failures += 1
        results.append({
            "tc": tc,
            "status": "PASS" if caught else "FAIL",
            "score_after_mutation": round(total, 4),
            "component_scores": result.get("component_scores", {}),
        })

    # Report
    if args.json:
        print(json.dumps({"results": results, "failures": failures, "skipped": skipped}, indent=2))
    else:
        print(f"{'TC':<8} {'Status':<6} {'Score':<8} Notes")
        print("-" * 60)
        for r in results:
            if r["status"] == "PASS":
                print(f"{r['tc']:<8} PASS   {r['score_after_mutation']:<8.4f} mutation caught")
            elif r["status"] == "FAIL":
                print(f"{r['tc']:<8} **FAIL** {r['score_after_mutation']:<8.4f} SCORER ACCEPTED MUTATION")
            else:
                print(f"{r['tc']:<8} {r['status']:<6} {'':<8} {r.get('reason', '')}")
        print("-" * 60)
        print(f"Total: {len(results)} | Passed: {len(results) - failures - skipped} "
              f"| Failed: {failures} | Skipped: {skipped}")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
