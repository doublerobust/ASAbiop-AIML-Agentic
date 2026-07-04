# Cross-Language Verification Results — Day 24

**Date:** 2026-06-24
**Environment:** R 4.6.0, Python 3.14.4, lifelines 0.30.3, survival 3.8.6
**Seed:** 42, N=200 (TC-012: N=300)

## Executive Summary

First comprehensive cross-language verification run across all 11 Level 1 test cases.
**8 of 11 TCs achieve perfect 1.0000 R↔Python agreement** on shared data.
3 TCs (TC-011, TC-013, TC-014) show discrepancies due to lack of shared-data
support — they generate domain-specific data (ADAE, ADVS, protocol deviations)
internally, and R/Python RNG streams diverge.

## Results

| Test Case | Domain | Shared Data | Score | Status |
|---|---|---|---|---|
| TC-001 | KM Median PFS | ADTTE (shared) | 1.0000 | ✅ PASS |
| TC-002 | Demographics | ADSL (shared) | 1.0000 | ✅ PASS |
| TC-003 | Stratified Log-Rank | ADTTE (shared) | 1.0000 | ✅ PASS |
| TC-011 | AE Summary Table | Internal (R≠Py) | 0.4814 | ❌ FAIL |
| TC-012 | Forest Plot HR | ADSL (shared) | 1.0000 | ✅ PASS |
| TC-013 | Waterfall Plot | Internal (R≠Py) | 0.7250 | ❌ FAIL |
| TC-014 | PD Listing | Internal (R≠Py) | 0.4944 | ❌ FAIL |
| TC-015 | KM Curve + Risk Table | ADTTE (shared) | 1.0000 | ✅ PASS |
| TC-016 | Exposure Summary | Internal (det.) | 1.0000 | ✅ PASS |
| TC-017 | Lab Shift Table | ADFB (shared) | 1.0000 | ✅ PASS |
| TC-018 | Change from Baseline | Internal (det.) | 1.0000 | ✅ PASS |

## Fixes Applied During Verification

### 1. TC-012 (Forest Plot HR) — Added `--data` support to R script
- **Problem:** R script had no `--data` argument; only Python supported `--data-csv`
- **Fix:** Added `--data` argument parsing and shared-CSV loading to
  `tc-012-forest-hr.R`, wrapping the data generation in an `if/else` block
- **Result:** R and Python now produce identical HR/CI/p-values on shared data

### 2. TC-015 (KM Curve) — Shared ADTTE needed EVNT column
- **Problem:** TC-015 uses `EVNT` (1=event) while shared ADTTE has `CNSR` (0=event)
- **Fix:** Created `adtte_with_evnt.csv` with `EVNT = 1 - CNSR` column added
- **Result:** R and Python produce identical curve coordinates, risk tables, and log-rank test

### 3. TC-017 (Lab Shift) — Generated shared lab data
- **Problem:** TC-017 generates lab data internally; no shared dataset existed
- **Fix:** Generated `adlb_shift.csv` in R with the same `generate_labs()` logic,
  loaded it in both R and Python via `--data`
- **Result:** Perfect 3×3 shift matrix agreement

## Root Cause Analysis for Failures

### TC-011 (AE Summary) — Score: 0.4814
- **Root cause:** R and Python generate different ADAE datasets (different RNG
  streams), so SOC/PT frequencies differ
- **Fix needed:** Add `--data` support for shared ADAE CSV in both R and Python
- **Expected after fix:** 1.0000 (same logic, same data → same results)

### TC-013 (Waterfall) — Score: 0.7250
- **Root cause:** R and Python generate different tumor measurement data
- **Fix needed:** Add `--data` support for shared ADVS/tumor CSV
- **Note:** Response categorization logic is deterministic given same data

### TC-014 (PD Listing) — Score: 0.4944
- **Root cause:** R and Python generate different protocol deviation catalogs
- **Fix needed:** Add `--data` support for shared PD CSV
- **Note:** PD taxonomy is categorical; same data → exact match expected

## Infrastructure Created

### `run-cross-lang-verify.sh`
Driver script that:
1. Generates shared ADTTE and ADSL datasets in R
2. Runs all 11 Level 1 TCs in both R and Python
3. Outputs JSON to `cross-lang-results/{r,python}-output/`

### Shared Datasets (`cross-lang-results/shared/`)
- `adtte.csv` — Shared ADTTE (200 subjects, seed=42)
- `adsl.csv` — Shared ADSL (200 subjects, seed=42)
- `adtte_with_evnt.csv` — ADTTE with EVNT column added (for TC-015)
- `adlb_shift.csv` — Shared lab data (200 subjects, for TC-017)
- `tc012_adsl.csv` — Shared survival data (300 subjects, for TC-012)

## Verification Commands

```bash
# Run all TCs
bash run-cross-lang-verify.sh 42 200

# Verify individual TC
python3 scoring-harness/score.py verify --tc TC-001 \
  --r cross-lang-results/r-output/TC-001.json \
  --python cross-lang-results/python-output/TC-001.json
```

## Next Steps

1. **Add `--data` support to TC-011, TC-013, TC-014** (R and Python) —
   generate shared ADAE/ADVS/PD datasets and achieve 1.0000 on all 11 TCs
2. **Automate verification in CI** — add `run-cross-lang-verify.sh` to
   GitHub Actions so regressions are caught on every PR
3. **Document tolerance bands** — record the empirical cross-language
   differences for edge cases (small strata, boundary p-values)
4. **Extend to SAS** — where SAS license is available, run the 11 SAS
   reference scripts on the same shared CSVs for trilingual verification

---

## Update: Day 31 (2026-07-01) — TC-022 Added

**New test case:** TC-022 (Duration of Response, DOR)

| Test Case | Domain | Shared Data | Score | Status |
|---|---|---|---|---|
| TC-022 | DOR KM Median | tc022_adtte.csv (shared) | 1.0000 | ✅ PASS |

- R: median_dor=5.85, CI=(2.72, 13.11), n_responders=23, n_events=16
- Python: median_dor=5.85, CI=(2.72, 13.11), n_responders=23, n_events=16
- ARS envelopes generated for both R and Python
- **Total Level 1 TCs verified: 15/15 at 1.0000**

---

## Update: Day 34 (2026-07-03) — TC-024 and TC-025 Added

**New test cases:** TC-024 (Overall Survival) and TC-025 (BOR Summary Table)

| Test Case | Domain | Shared Data | Score | Status |
|---|---|---|---|---|
| TC-024 | OS KM Median | tc024_os_adtte.csv (shared) | 1.0000 | ✅ PASS |
| TC-025 | BOR Summary | tc025_bor.csv (shared) | 1.0000 | ✅ PASS |

### TC-024 Details
- R: median_os (ctrl)=16.41, median_os (exp)=24.58, HR=0.6727, log-rank p=0.0158
- Python: median_os (ctrl)=16.41, median_os (exp)=24.58, HR=0.6727, log-rank p=0.0158
- Subgroups: SEX (F/M), AGEGR1 (<65/>=65), ECOG (0/1) — all verified
- ARS envelopes generated for both R and Python
- Fixed R subgroup row-name extraction bug (grep pattern for survfit strata)

### TC-025 Details
- R: BOR distribution by arm, ORR with Clopper-Pearson CI, DCR, Fisher exact test
- Python: matching implementation with scipy
- Cross-TFL consistency with TC-020 (ORR) and TC-023 (DCR) verified

- **Total Level 1 TCs verified: 18/18 at 1.0000**
- **SAS reference scripts created for TC-024 and TC-025** (18/18 SAS coverage)

---

## Update: Day 35 (2026-07-04) — TC-027 Added

**New test case:** TC-027 (Duration of Stable Disease, DOSD)

| Test Case | Domain | Shared Data | Score | Status |
|---|---|---|---|---|
| TC-027 | DOSD KM Median | tc027_dosd_adtte.csv (shared) | 1.0000 | ✅ PASS |

### TC-027 Details
- R: median_dosd (ctrl)=2.33, median_dosd (exp)=5.44, HR=0.5223, log-rank p=0.0214
- Python: median_dosd (ctrl)=2.33, median_dosd (exp)=5.44, HR=0.5223, log-rank p=0.0214
- Subgroups: SEX (F/M), AGEGR1 (<65/>=65), ECOG (0/1) — all verified at 1.0000
- ARS envelopes generated for both R and Python
- BOR distribution: Control (CR 2%, PR 18%, SD 45%, PD 30%, NE 5%), Active (CR 8%, PR 35%, SD 35%, PD 15%, NE 7%)
- 89 SD subjects out of 200 (44.5%), 83 in ITT with valid DOSD times
- Cross-TFL: DOSD N = TC-025 SD count, DOSD N ≤ DCR N (TC-023)

- **Total Level 1 TCs verified: 20/20 at 1.0000**
- **White paper Section 8 (References and Appendices) drafted**
- **Test case design updated with TC-027 specification**
