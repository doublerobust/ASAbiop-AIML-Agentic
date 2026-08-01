#!/usr/bin/env python3
"""Validate ALL checked-in ground truth outputs against their own schemas.

Fails if any checked-in output (R or Python) violates its output schema.
This is the regression guard for the audit finding:
"Checked-in ground truth does not always satisfy its own schemas
(3 R outputs + 1 Python output failed validation)."

Usage:
    python3 scripts/validate-checked-in-outputs.py

Exit code: 0 if all valid, 1 if any fails.
"""
import json
import os
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent.parent
R_OUT = BENCH / "cross-lang-results" / "r-output"
PY_OUT = BENCH / "cross-lang-results" / "python-output"
SCHEMA_DIR = BENCH / "references" / "output-schemas"


def load_schema(tc_id: str):
    p = SCHEMA_DIR / f"{tc_id.lower()}-output-schema.json"
    return json.loads(p.read_text()) if p.exists() else None


def main():
    import jsonschema

    failures = []
    checked = 0

    for out_dir in (R_OUT, PY_OUT):
        for f in sorted(out_dir.glob("TC-*.json")):
            tc_id = f.stem  # e.g. TC-001
            # handle shared-data variants (TC-028_shared.json)
            if "_" in tc_id:
                tc_id = tc_id.split("_")[0]
            schema = load_schema(tc_id)
            if schema is None:
                print(f"  SKIP {f.name}: no schema for {tc_id}")
                continue
            try:
                data = json.loads(f.read_text())
                jsonschema.validate(data, schema)
                checked += 1
            except jsonschema.ValidationError as e:
                path = ".".join(str(x) for x in e.path) or "(root)"
                failures.append((f.name, str(e.message)[:120], path))
            except Exception as e:
                failures.append((f.name, f"EXC: {e}", ""))

    print(f"Checked {checked} outputs against schemas.")
    if failures:
        print(f"\nFAILURES ({len(failures)}):")
        for name, msg, path in failures:
            print(f"  {name}: {msg}  @ {path}")
        sys.exit(1)
    print("ALL CHECKED-IN OUTPUTS PASS THEIR SCHEMAS")
    sys.exit(0)


if __name__ == "__main__":
    main()
