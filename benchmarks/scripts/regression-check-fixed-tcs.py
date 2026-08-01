#!/usr/bin/env python3
"""Regression check: compare R vs Python ground truth for the 4 fixed TCs."""
import json

def flatten(d, prefix=""):
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            p = f"{prefix}.{k}" if prefix else k
            out.update(flatten(v, p))
    elif isinstance(d, list):
        for i, v in enumerate(d):
            p = f"{prefix}[{i}]"
            out.update(flatten(v, p))
    else:
        out[prefix] = d
    return out

pairs = [
    ("TC-013", "cross-lang-results/r-output/TC-013.json", "cross-lang-results/python-output/TC-013.json"),
    ("TC-014", "cross-lang-results/r-output/TC-014.json", "cross-lang-results/python-output/TC-014.json"),
    ("TC-017", "cross-lang-results/r-output/TC-017.json", "cross-lang-results/python-output/TC-017.json"),
    ("TC-023", "cross-lang-results/r-output/TC-023.json", "cross-lang-results/python-output/TC-023.json"),
]
ok = True
for tc, rf, pyf in pairs:
    try:
        r = json.load(open(rf))
        py = json.load(open(pyf))
    except FileNotFoundError as e:
        print(f"{tc}: MISSING {e.filename.split('/')[-1]}")
        ok = False
        continue
    fr, fp = flatten(r), flatten(py)
    keys = set(fr) & set(fp)
    # Exclude provenance metadata — R and Python intentionally report
    # different language/package names. Only statistical values matter.
    EXCLUDE_SUBSTR = ("metadata.language", "metadata.packages", "metadata.sorting",
                      ".language", ".package", ".package_version", ".packages")
    EXCLUDE_EXACT = {"language", "package", "package_version", "packages"}
    mismatches = []
    for k in sorted(keys):
        if k in EXCLUDE_EXACT or any(s in k for s in EXCLUDE_SUBSTR):
            continue
        a, b = fr[k], fp[k]
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            if abs(a - b) > 1e-6:
                mismatches.append(f"{k}: R={a} Py={b}")
        elif a != b:
            mismatches.append(f"{k}: R={a!r} Py={b!r}")
    status = "OK" if not mismatches else "MISMATCH"
    if mismatches:
        ok = False
    print(f"{tc}: {status} ({len(keys)} shared fields, {len(mismatches)} mismatches)")
    for m in mismatches[:8]:
        print("   ", m)

print()
print("REGRESSION:", "PASS" if ok else "FAIL")
raise SystemExit(0 if ok else 1)
