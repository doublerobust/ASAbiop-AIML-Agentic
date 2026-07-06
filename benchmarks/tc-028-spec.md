# TC-028: Change in Tumor Size by Cycle (Longitudinal)

**Level:** 1  
**Domain:** Oncology / Tumor Response  
**RECIST Version:** 1.1  
**Date Added:** 2026-07-06 (Day 37)  
**Status:** Active — R↔Python cross-language verified at 1.0000

---

## 1. Objective

Compute the percentage change from baseline in tumor size (sum of longest
diameters, SLD) at each treatment cycle (C1D1 through C6D1) for each subject.
Summarize by visit and arm with descriptive statistics. Identify best/worst
response and time-to-best response per subject.

This tests the agent's ability to:
1. Compute longitudinal % change from baseline across multiple visits
2. Handle missing visits (not all subjects have all assessments due to dropout/PD)
3. Summarize by visit and arm (mean, median, SE, n assessed, n missing)
4. Identify best/worst response timing per subject
5. Produce overall arm-level summaries (mean/median best % change, mean n assessments)

## 2. Data Input

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--seed` | 42 | Random seed for reproducible data generation |
| `--n` | 150 | Number of subjects (75 per arm) |
| `--data-csv` | None | Optional shared CSV for cross-language verification |
| `--output` | Required | Output JSON path |
| `--ars-output` | None | Optional CDISC ARS v1.0 envelope output |

## 3. Expected Output Structure

```json
{
  "test_case_id": "TC-028",
  "title": "Change in Tumor Size by Cycle (Longitudinal)",
  "cycles": ["C1D1", "C2D1", "C3D1", "C4D1", "C5D1", "C6D1"],
  "baseline_cycle": "C1D1",
  "visit_summaries": {
    "C2D1": {
      "all": { "n_total": 150, "n_assessed": 141, "mean_pct_change": -17.66, ... },
      "experimental": { "n_total": 75, "n_assessed": 69, "mean_pct_change": -24.32, ... },
      "control": { "n_total": 75, "n_assessed": 72, "mean_pct_change": -10.99, ... }
    },
    ...
  },
  "overall_summary": {
    "experimental": { "n_subjects": 75, "mean_best_pct_change": -52.24, ... },
    "control": { "n_subjects": 75, "mean_best_pct_change": -21.38, ... }
  },
  "subject_summaries": [
    { "USUBJID": "SUBJ-0001", "TRT01A": "Experimental", "best_pct_change": -188.5, ... },
    ...
  ],
  "n_subjects": 150
}
```

## 4. Scoring

| Component | Tolerance | Weight |
|-----------|-----------|--------|
| Visit-wise mean % change (exp) | abs=0.5, rel=0.02 | 0.15 |
| Visit-wise mean % change (ctrl) | abs=0.5, rel=0.02 | 0.15 |
| Visit-wise median % change (exp) | abs=0.5, rel=0.02 | 0.10 |
| Visit-wise median % change (ctrl) | abs=0.5, rel=0.02 | 0.10 |
| Visit-wise SE | abs=0.1, rel=0.05 | 0.08 |
| N assessed per visit | exact match | 0.10 |
| Overall mean best % change (exp) | abs=0.5, rel=0.02 | 0.10 |
| Overall mean best % change (ctrl) | abs=0.5, rel=0.02 | 0.10 |
| Overall median best % change (exp) | abs=0.5, rel=0.02 | 0.05 |
| Overall median best % change (ctrl) | abs=0.5, rel=0.02 | 0.05 |
| N per arm | exact match | 0.02 |

## 5. Ground Truth Scripts

| Language | Script |
|----------|--------|
| Python | `references/ground-truth/Python/tc_028_tumor_size_by_cycle.py` |
| R | `references/ground-truth/R/tc-028-tumor-size-by-cycle.R` |

## 6. Cross-Language Verification

**Score: 1.0000** ✅ (verified on shared CSV data, 2026-07-06)

Both implementations produce identical results when run on the same shared
CSV dataset (`--data-csv`).

## 7. Clinical Relevance

Longitudinal tumor size tracking is a standard exploratory analysis in
oncology trials, complementing the waterfall plot (TC-013) by showing the
**trajectory** of response over time rather than just the best response.
This is particularly important for:
- Assessing durability of response
- Identifying patterns of initial response followed by progression
- Comparing treatment arms for time-to-response differences
- Supporting regulatory submissions with comprehensive tumor response data

## 8. Related Test Cases

- **TC-013**: Waterfall Plot — Best % Change (single timepoint)
- **TC-018**: Change from Baseline Table (general biomarker, not tumor-specific)
- **TC-025**: Best Overall Response (BOR) Summary
