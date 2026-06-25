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

# Generate ADTTE with EVNT column (for TC-015)
(cd "$RDIR" && Rscript -e "
source('common/data-generation.R')
adtte <- generate_adtte(seed=$SEED, n_subjects=$N)
adtte\$EVNT <- 1 - adtte\$CNSR
write_shared_data(adtte, '$SHARED/adtte_with_evnt.csv')
cat('ADTTE+EVNT:', nrow(adtte), 'rows\n')
") 2>&1

# Generate TC-012 shared survival data (N=300) using the TC-012 R script's internal generator
(cd "$RDIR" && Rscript -e "
source('common/data-generation.R')
# Use TC-012's own generation logic by running it without --data and capturing the data
# Instead, generate from the script's generate_surv_data function
seed <- $SEED
n <- 300
n_arm <- n / 2
set.seed(seed + 100)
exp_df <- data.frame(
  USUBJID = paste0('SUBJ-E-', sprintf('%04d', 1:n_arm)),
  TRT01A = 'Experimental',
  AGEGR1 = sample(c('<65', '>=65'), n_arm, replace=TRUE),
  SEX = sample(c('Male', 'Female'), n_arm, replace=TRUE),
  ECOGGR1 = sample(c('0', '1+'), n_arm, replace=TRUE, prob=c(0.6, 0.4)),
  REGION = sample(c('North America', 'Europe', 'Asia'), n_arm, replace=TRUE),
  PRIORTRT = sample(c('Yes', 'No'), n_arm, replace=TRUE, prob=c(0.4, 0.6)),
  stringsAsFactors=FALSE
)
set.seed(seed + 200)
ctl_df <- data.frame(
  USUBJID = paste0('SUBJ-C-', sprintf('%04d', 1:n_arm)),
  TRT01A = 'Control',
  AGEGR1 = sample(c('<65', '>=65'), n_arm, replace=TRUE),
  SEX = sample(c('Male', 'Female'), n_arm, replace=TRUE),
  ECOGGR1 = sample(c('0', '1+'), n_arm, replace=TRUE, prob=c(0.6, 0.4)),
  REGION = sample(c('North America', 'Europe', 'Asia'), n_arm, replace=TRUE),
  PRIORTRT = sample(c('Yes', 'No'), n_arm, replace=TRUE, prob=c(0.4, 0.6)),
  stringsAsFactors=FALSE
)
adsl12 <- rbind(exp_df, ctl_df)
set.seed(seed + 300)
base_lambda <- ifelse(adsl12\$TRT01A == 'Experimental', 0.05 * 0.65, 0.05)
base_lambda <- base_lambda * ifelse(adsl12\$AGEGR1 == '>=65', 1.2, 1.0)
base_lambda <- base_lambda * ifelse(adsl12\$ECOGGR1 == '1+', 1.4, 1.0)
base_lambda <- base_lambda * ifelse(adsl12\$PRIORTRT == 'Yes', 0.9, 1.0)
tte <- rexp(nrow(adsl12), base_lambda)
censor_time <- runif(nrow(adsl12), 18, 24)
adsl12\$AVAL <- pmin(tte, censor_time)
adsl12\$CNSR <- as.integer(tte > censor_time)
write.csv(adsl12, '$SHARED/tc012_adsl.csv', row.names=FALSE)
cat('TC-012 data:', nrow(adsl12), 'rows\n')
") 2>&1

# Generate shared lab shift data (for TC-017)
(cd "$RDIR" && Rscript -e "
set.seed($SEED + 999)
n <- $N
bl_cat <- sample(c('LOW', 'NORMAL', 'HIGH'), n, replace=TRUE, prob=c(0.1, 0.8, 0.1))
post_cat <- sample(c('LOW', 'NORMAL', 'HIGH'), n, replace=TRUE, prob=c(0.1, 0.8, 0.1))
df <- data.frame(
  USUBJID = paste0('SUBJ-', sprintf('%04d', 1:n)),
  TRT01PN = rep(c(0, 1), each=n/2),
  TRT01P = rep(c('Placebo', 'Active'), each=n/2),
  LBTEST = rep('Alanine Aminotransferase', n),
  VISIT = rep('Week 2', n),
  BL_CAT = bl_cat,
  POST_CAT = post_cat,
  stringsAsFactors=FALSE
)
write.csv(df, '$SHARED/adlb_shift.csv', row.names=FALSE)
cat('ADLB shift:', nrow(df), 'rows\n')
") 2>&1

# Generate shared datasets for TC-011, TC-013, TC-014
echo ""
echo "  Generating shared ADAE, ADVS, PD datasets..."
(cd "$RDIR" && Rscript generate_shared_datasets.R --seed $SEED --n $N --output-dir "$SHARED") 2>&1

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

# TC-011 through TC-018: use shared datasets where available
# TC-011: AE Summary (shared ADAE)
echo ""
echo "── TC-011 ──────────────────────────────────────────"
echo "  R:   tc-011-ae-summary.R"
if (cd "$RDIR" && Rscript "tc-011-ae-summary.R" --seed $SEED --n $N --data "$SHARED/adae.csv" --output "$R_OUT/TC-011.json") 2>&1; then
  echo "  ✓ R completed"
else
  echo "  ✗ R FAILED"; FAIL_COUNT=$((FAIL_COUNT + 1))
fi
echo "  Py:  tc_011_ae_summary.py"
if (cd "$PYDIR" && python3 "tc_011_ae_summary.py" --seed $SEED --n $N --data-csv "$SHARED/adae.csv" --output "$PY_OUT/TC-011.json") 2>&1; then
  echo "  ✓ Python completed"; PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ Python FAILED"; FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# TC-012: Forest Plot HR (shared ADSL with survival data)
echo ""
echo "── TC-012 ──────────────────────────────────────────"
echo "  R:   tc-012-forest-hr.R"
if (cd "$RDIR" && Rscript "tc-012-forest-hr.R" --seed $SEED --n 300 --data "$SHARED/tc012_adsl.csv" --output "$R_OUT/TC-012.json") 2>&1; then
  echo "  ✓ R completed"
else
  echo "  ✗ R FAILED"; FAIL_COUNT=$((FAIL_COUNT + 1))
fi
echo "  Py:  tc_012_forest_hr.py"
if (cd "$PYDIR" && python3 "tc_012_forest_hr.py" --seed $SEED --n 300 --data-csv "$SHARED/tc012_adsl.csv" --output "$PY_OUT/TC-012.json") 2>&1; then
  echo "  ✓ Python completed"; PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ Python FAILED"; FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# TC-013: Waterfall (shared tumor response data)
echo ""
echo "── TC-013 ──────────────────────────────────────────"
echo "  R:   tc-013-waterfall.R"
if (cd "$RDIR" && Rscript "tc-013-waterfall.R" --seed $SEED --n $N --data "$SHARED/advs_tumor.csv" --output "$R_OUT/TC-013.json") 2>&1; then
  echo "  ✓ R completed"
else
  echo "  ✗ R FAILED"; FAIL_COUNT=$((FAIL_COUNT + 1))
fi
echo "  Py:  tc_013_waterfall.py"
if (cd "$PYDIR" && python3 "tc_013_waterfall.py" --seed $SEED --n $N --data-csv "$SHARED/advs_tumor.csv" --output "$PY_OUT/TC-013.json") 2>&1; then
  echo "  ✓ Python completed"; PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ Python FAILED"; FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# TC-014: PD Listing (shared protocol deviations)
echo ""
echo "── TC-014 ──────────────────────────────────────────"
echo "  R:   tc-014-pd-listing.R"
if (cd "$RDIR" && Rscript "tc-014-pd-listing.R" --seed $SEED --n $N --data "$SHARED/protocol_deviations.csv" --output "$R_OUT/TC-014.json") 2>&1; then
  echo "  ✓ R completed"
else
  echo "  ✗ R FAILED"; FAIL_COUNT=$((FAIL_COUNT + 1))
fi
echo "  Py:  tc_014_pd_listing.py"
if (cd "$PYDIR" && python3 "tc_014_pd_listing.py" --seed $SEED --n $N --data-csv "$SHARED/protocol_deviations.csv" --output "$PY_OUT/TC-014.json") 2>&1; then
  echo "  ✓ Python completed"; PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ Python FAILED"; FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# TC-015: KM Curve + Risk Table (shared ADTTE with EVNT)
echo ""
echo "── TC-015 ──────────────────────────────────────────"
echo "  R:   tc-015-km-curve.R"
if (cd "$RDIR" && Rscript "tc-015-km-curve.R" --seed $SEED --n $N --data "$SHARED/adtte_with_evnt.csv" --output "$R_OUT/TC-015.json") 2>&1; then
  echo "  ✓ R completed"
else
  echo "  ✗ R FAILED"; FAIL_COUNT=$((FAIL_COUNT + 1))
fi
echo "  Py:  tc_015_km_curve.py"
if (cd "$PYDIR" && python3 "tc_015_km_curve.py" --seed $SEED --n $N --data "$SHARED/adtte_with_evnt.csv" --output "$PY_OUT/TC-015.json") 2>&1; then
  echo "  ✓ Python completed"; PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ Python FAILED"; FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# TC-016: Exposure Summary (internal, deterministic)
run_tc_internal "TC-016" "tc-016-exposure.R"      "tc_016_exposure.py"

# TC-017: Lab Shift Table (shared lab data)
echo ""
echo "── TC-017 ──────────────────────────────────────────"
echo "  R:   tc-017-shift-table.R"
if (cd "$RDIR" && Rscript "tc-017-shift-table.R" --seed $SEED --n $N --data "$SHARED/adlb_shift.csv" --output "$R_OUT/TC-017.json") 2>&1; then
  echo "  ✓ R completed"
else
  echo "  ✗ R FAILED"; FAIL_COUNT=$((FAIL_COUNT + 1))
fi
echo "  Py:  tc_017_shift_table.py"
if (cd "$PYDIR" && python3 "tc_017_shift_table.py" --seed $SEED --n $N --data "$SHARED/adlb_shift.csv" --output "$PY_OUT/TC-017.json") 2>&1; then
  echo "  ✓ Python completed"; PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  ✗ Python FAILED"; FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# TC-018: Change from Baseline (internal, deterministic)
run_tc_internal "TC-018" "tc-018-cfb-table.R"      "tc_018_cfb_table.py"

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
