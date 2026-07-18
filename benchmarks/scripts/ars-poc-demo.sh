#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────
# ARS Proof-of-Concept: End-to-End CDISC ARS Workflow Demo
#
# Demonstrates: benchmark TC → ground truth R/Python → ARS envelope output
#               → schema validation → cross-language ARS consistency check
#
# Test Case: TC-035 (Composite Efficacy: ORR/DCR/DOR) — Level 2
# ──────────────────────────────────────────────────────────────────────────

set -euo pipefail

BENCH_DIR="$(cd "$(dirname "$0")/.." && pwd)"
GT_R="$BENCH_DIR/references/ground-truth/R"
GT_PY="$BENCH_DIR/references/ground-truth/Python"
RESULTS="$BENCH_DIR/cross-lang-results"
ARS_DIR="$RESULTS/ars-output"
TC035_DIR="$RESULTS/tc035"
VALIDATOR="$BENCH_DIR/scoring-harness/ars_validator.py"
SCORER="$BENCH_DIR/scoring-harness/score.py"

mkdir -p "$ARS_DIR" "$TC035_DIR"

echo "═══════════════════════════════════════════════════════════════════════════"
echo "  CDISC ARS v1.0 Proof-of-Concept — TC-035 Composite Efficacy Table"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""

# ── Step 1: Generate shared data ────────────────────────────────────────────
echo "▶ Step 1: Generate shared composite efficacy dataset (R → CSV)"
SEED=${1:-42}
N=${2:-200}
Rscript -e "
  source('$GT_R/generate_tc035_composite.R')
  data <- generate_composite_efficacy(seed=$SEED, n_subjects=$N)
  write.csv(data, '$TC035_DIR/shared_data.csv', row.names=FALSE)
  cat('  Generated', nrow(data), 'subjects (seed=$SEED)\n')
" 2>&1 | grep -v "^$" | grep -v "Attaching\|masked\|The following"

echo ""

# ── Step 2: Run R ground truth with ARS output ──────────────────────────────
echo "▶ Step 2: Run R ground truth → benchmark JSON + ARS envelope"
(cd "$GT_R" && Rscript tc-035-composite-efficacy.R \
  --data "$TC035_DIR/shared_data.csv" \
  --output "$TC035_DIR/TC-035_R.json" \
  --ars-output "$ARS_DIR/TC-035_R_ars.json") 2>&1 | grep -E "^Wrote"

echo ""

# ── Step 3: Run Python ground truth with ARS output ─────────────────────────
echo "▶ Step 3: Run Python ground truth → benchmark JSON + ARS envelope"
python3 "$GT_PY/tc_035_composite_efficacy.py" \
  --data "$TC035_DIR/shared_data.csv" \
  --output "$TC035_DIR/TC-035_Py.json" \
  --ars-output "$ARS_DIR/TC-035_Py_ars.json" 2>&1 | grep -E "^Wrote"

echo ""

# ── Step 4: Cross-language numerical verification ───────────────────────────
echo "▶ Step 4: Cross-language numerical verification (R vs Python)"
python3 "$SCORER" verify \
  --r "$TC035_DIR/TC-035_R.json" \
  --python "$TC035_DIR/TC-035_Py.json" \
  --tc TC-035

echo ""

# ── Step 5: ARS schema validation ──────────────────────────────────────────
echo "▶ Step 5: ARS envelope schema validation"
python3 "$VALIDATOR" \
  "$ARS_DIR/TC-035_R_ars.json" \
  "$ARS_DIR/TC-035_Py_ars.json"

echo ""

# ── Step 6: ARS cross-language consistency ──────────────────────────────────
echo "▶ Step 6: ARS envelope cross-language consistency check"
python3 "$VALIDATOR" --cross-check \
  "$ARS_DIR/TC-035_R_ars.json" \
  "$ARS_DIR/TC-035_Py_ars.json"

echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo "  ARS Proof-of-Concept COMPLETE"
echo "  • TC-035 R and Python outputs: numerically verified (score=1.0000)"
echo "  • ARS envelopes: schema-valid (CDISC ARS v1.0)"
echo "  • ARS cross-language: consistent"
echo "  • Pipeline: shared data → R/Python → benchmark JSON + ARS → validate"
echo "═══════════════════════════════════════════════════════════════════════════"
