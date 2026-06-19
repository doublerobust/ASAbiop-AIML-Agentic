#!/usr/bin/env bash
# run-comparison.sh: Step-by-step TC-012 cross-language verification.
# Run from the glm-comparison-demo/ directory.

set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"

echo "=== Step 1: Generate common data + R analysis ==="
Rscript "$HERE/compare-tc012.R" "$HERE"

echo ""
echo "=== Step 2: Python analysis on same data ==="
python3 "$HERE/compare-tc012.py"

echo ""
echo "=== Step 3: Check agreement ==="
python3 "$HERE/check-comparison.py"

echo ""
echo "=== Cross-language comparison complete ==="
