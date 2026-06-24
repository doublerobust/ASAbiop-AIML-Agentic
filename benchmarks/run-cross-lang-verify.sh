#!/usr/bin/env bash
# cross-language-verify.sh
# Run cross-language verification for all 11 Level 1 test cases.
#
# Strategy:
#   1. Generate shared datasets in R (ADTTE, ADSL)
#   2. Run each TC in R on the shared data → R JSON output
#   3. Run each TC in Python on the shared data → Python JSON output
#   4. Compare with score.py verify
#
# Usage: bash run-cross-lang-verify.sh [SEED] [N]
# Defaults: SEED=42, N=200

set -euo pipefail

SEED="${1:-42}"
N="${2:-200}"
BENCH="$(cd "$(dirname "$0")" && pwd)"
GT="$BENCH/references/ground-truth"
RDIR="$GT/R"
PYDIR="$GT/Python"
WORK="$BENCH/cross-lang-results"
SHARED="$WORK/shared"
R_OUT="$WORK/r-output"
PY_OUT="$WORK/python-output"

mkdir -p "$SHARED" "$R_OUT" "$PY_OUT"

echo "════════════════════════════════════════════════════════════════"
echo "  Cross-Language Verification Run"
echo "  Seed=$SEED  N=$N"
echo "  $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "════════════════════════════════════════════════════════════════"

# ───────────────────────────────────────────────────────────────────
# Step 1: Generate shared datasets in R
# ───────────────────────────────────────────────────────────────────
echo ""
echo "▶ Step 1: Generating shared datasets in R..."

(cd "$RDIR" && Rscript -e "
source('common/data-generation.R')
adtte <- generate_adtte(seed=$SEED, n_subjects=$N)
adsl  <- generate_adsl(seed=$SEED, n_subjects=$N)
write_shared_data(adtte, '$SHARED/adtte.csv')
write_shared_data(adsl,  '$SHARED/adsl.csv')
cat('ADTTE:', nrow(adtte), 'rows  ADSL:', nrow(adsl), 'rows\n')
") 2>&1

echo ""
echo "Shared datasets:"
ls -la "$SHARED/"

# ───────────────────────────────────────────────────────────────────
# Step 2: Run each TC in R and Python
# ───────────────────────────────────────────────────────────────────

PASS_COUNT=0
FAIL_COUNT=0

# Function: run one TC with shared ADTTE data
run_tc_adtte() {
  local tc_id="$1"
  local r_script="$2"
  local py_script="$3"
  local extra_args="$4"

  echo ""
  echo "── $tc_id ──────────────────────────────────────────────"

  # Run R (from R directory so source('common/...') works)
  echo "  R:   $r_script"
  if (cd "$RDIR" && Rscript "$r_script" --seed $SEED --n $N --data "$SHARED/adtte.csv" $extra_args --output "$R_OUT/${tc_id}.json") 2>&1; then
    echo "  ✓ R completed"
  else
    echo "  ✗ R FAILED"
    FAIL_COUNT=$((FAIL_COUNT + 1))
    return 1
  fi

  # Run Python (from Python directory so 'from common...' works)
  echo "  Py:  $py_script"
  if (cd "$PYDIR" && python3 "$py_script" --seed $SEED --n $N --data "$SHARED/adtte.csv" $extra_args --output "$PY_OUT/${tc_id}.json") 2>&1; then
    echo "  ✓ Python completed"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ✗ Python FAILED"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
}

# Function: run one TC with internal data generation (no shared CSV)
run_tc_internal() {
  local tc_id="$1"
  local r_script="$2"
  local py_script="$3"

  echo ""
  echo "── $tc_id ──────────────────────────────────────────────"

  echo "  R:   $r_script"
  if (cd "$RDIR" && Rscript "$r_script" --seed $SEED --n $N --output "$R_OUT/${tc_id}.json") 2>&1; then
    echo "  ✓ R completed"
  else
    echo "  ✗ R FAILED"
    FAIL_COUNT=$((FAIL_COUNT + 1))
    return 1
  fi

  echo "  Py:  $py_script"
  if (cd "$PYDIR" && python3 "$py_script" --seed $SEED --n $N --output "$PY_OUT/${tc_id}.json") 2>&1; then
    echo "  ✓ Python completed"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  ✗ Python FAILED"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
}

# TC-001: KM Median PFS (uses ADTTE shared)
run_tc_adtte "TC-001" "tc-001-km-median.R" "tc_001_km_median.py" "--arm 1"

# TC-002: Demographics (uses ADSL shared)
echo ""
echo "── TC-002 ──────────────────────────────────────────────"
echo "  R:   tc-002-demographics.R"
if (cd "$RDIR" && Rscript "tc-002-demographics.R" --seed $SEED --n $N --data "$SHARED/adsl.csv" --output "$R_OUT/TC-002.json") 2>&1; then
  echo "  ✓ R completed"
else
  echo "  ✗ R FAILED"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi
echo "  Py:  tc_002_demographics.py"
if (cd "$PYDIR" && python3 "tc_002_demographics.py" --seed $SEED --n $N --data "$SHARED/adsl.csv" --output "$PY_OUT/TC-002.json") 2>&1; then
  echo "  ✓ Python completed"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ Python FAILED"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# TC-003: Stratified Log-Rank (uses ADTTE shared)
run_tc_adtte "TC-003" "tc-003-stratified-logrank.R" "tc_003_stratified_logrank.py" ""

# TC-011 through TC-018: internal data generation
run_tc_internal "TC-011" "tc-011-ae-summary.R"   "tc_011_ae_summary.py"
run_tc_internal "TC-012" "tc-012-forest-hr.R"     "tc_012_forest_hr.py"
run_tc_internal "TC-013" "tc-013-waterfall.R"    "tc_013_waterfall.py"
run_tc_internal "TC-014" "tc-014-pd-listing.R"     "tc_014_pd_listing.py"
run_tc_internal "TC-015" "tc-015-km-curve.R"      "tc_015_km_curve.py"
run_tc_internal "TC-016" "tc-016-exposure.R"      "tc_016_exposure.py"
run_tc_internal "TC-017" "tc-017-shift-table.R"   "tc_017_shift_table.py"
run_tc_internal "TC-018" "tc-018-cfb-table.R"     "tc_018_cfb_table.py"

# ───────────────────────────────────────────────────────────────────
# Step 3: Summary
# ───────────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  Verification Summary"
echo "  Passed: $PASS_COUNT   Failed: $FAIL_COUNT"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "R outputs:"
ls -1 "$R_OUT/" 2>/dev/null | sed 's/^/  /' || echo "  (none)"
echo ""
echo "Python outputs:"
ls -1 "$PY_OUT/" 2>/dev/null | sed 's/^/  /' || echo "  (none)"
echo ""
echo "Done."
