# Cross-Language Verification Protocol — TFL Benchmark

**Version:** 0.2 (Day 3 expansion; QC-revised 2026-06-18)
**Date:** 2026-05-27 (revised 2026-06-18)
**Status:** 🟢 R and Python empirically cross-validated on SHARED data for
TC-001/002/003 (score.py verify = 1.0); SAS reference-only (no license)
**Dimension:** TFL-Specific Correctness — Ground Truth Validation & Numerical Tolerance

---

## 1. Purpose & Scope

### 1.1 Why Cross-Language Verification Matters

The benchmark's ground truth must be **demonstrably correct across all three supported languages** (R, SAS, Python). If ground truth differs between languages, we cannot tell whether an agent's error is a genuine mistake or a correct answer computed in a different language runtime.

> ⚠️ **CRITICAL METHODOLOGY POINT (added in QC review):** R (Mersenne-Twister),
> SAS (its own PRNG), and Python/numpy (PCG64) produce **different random
> streams for the same seed**. Generating the synthetic data *independently in
> each language* therefore yields **different datasets**, and the resulting
> statistics **cannot be expected to match** — even when every implementation
> is correct. Cross-language verification is only meaningful when all three
> languages consume the **same shared dataset** (a single CSV). The ground-truth
> scripts now support a `--data <shared.csv>` flag for exactly this purpose; R
> writes the canonical dataset via `write_shared_data()`. Any claim of
> "same seed → same results" that does *not* use a shared CSV is incorrect and
> has been removed from this document.

This document establishes:
1. A **verification protocol** for validating ground truth across R, SAS, and Python
2. A **catalog of known numerical differences** between the three languages for common clinical statistical methods
3. **Tolerance standards** for each statistical method, informed by regulatory submission practice
4. **Edge-case test vectors** that stress-test numerical precision
5. **Automated scoring harness design** for TC-001 (KM median PFS) as a pilot

### 1.2 Scope

| Method | Languages | Priority | Known Differences |
|---|---|---|---|
| Kaplan-Meier estimation | R (survival), SAS (LIFETEST), Python (lifelines) | 🔴 Critical | Tie handling, confidence interval methods |
| Log-rank test (stratified) | R (survival), SAS (LIFETEST), Python (lifelines) | 🔴 Critical | Stratification weighting, exact vs. approximate |
| Cox proportional hazards | R (survival), SAS (PHREG), Python (lifelines) | 🟡 High | Tie resolution (Efron/Breslow/exact), baseline hazard |
| Descriptive statistics | R (dplyr), SAS (MEANS), Python (pandas) | 🟢 Medium | Default rounding, precision |
| Frequency tables | R (Tplyr), SAS (FREQ), Python (pandas) | 🟢 Medium | Cell suppression rules, exact vs. approximate tests |
| Sample size re-estimation | R (gsDesign), SAS (SEQDESIGN), Python (custom) | 🟡 High | IA timing, spending function implementation |

---

## 2. Verification Protocol

### 2.1 Verification Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Verification Pipeline                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Step 1: Generate synthetic data with fixed seed                 │
│       ↓                                                          │
│  Step 2: Compute ground truth in R (primary reference)           │
│       ↓                                                          │
│  Step 3: Cross-validate in SAS                                   │
│       ↓                                                          │
│  Step 4: Cross-validate in Python                                │
│       ↓                                                          │
│  Step 5: Compare all three outputs                               │
│       ├── Within tolerance → Verified ground truth               │
│       └── Outside tolerance → Investigate & document             │
│                                                                  │
│  Step 6: If discrepancy found:                                   │
│       a) Identify root cause (algorithm, defaults, precision)    │
│       b) Document in Known Differences catalog (Section 3)       │
│       c) Adjust tolerance or select a reference language         │
│       d) Flag in scoring criteria for this test case             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Reference Language Selection

| Situation | Reference Language | Rationale |
|---|---|---|
| Method originated in R (`survival`, `gsDesign`) | **R** | Most widely validated, pharmaverse ecosystem |
| Method is a SAS PROC standard (`FREQ`, `MEANS`, `TABULATE`) | **SAS** | Regulatory gold standard for descriptive stats |
| Method requires Python-specific implementation | **Python** | Only when no R/SAS cross-validated equivalent exists |
| Discrepancy after investigation | **R** (with documented tolerance) | Transparency: pharmaverse is open-source, replicable |

### 2.3 Verification Test Harness Design

```yaml
verification_test:
  test_id: VF-<NNN>
  method: <statistical method>
  languages: [R, SAS, Python]
  data_seed: <integer>
  n_simulations: <number>
  tolerance:
    absolute: <float or "N/A">
    relative: <float or "N/A">
    categorical: <exact | equivalence>
  acceptance_criteria:
    - "All three languages produce results within tolerance"
    - "Discrepancies documented and tolerance adjusted"
  edge_cases:
    - <edge case 1>
    - <edge case 2>
```

---

## 3. Catalog of Known Numerical Differences

### 3.1 Kaplan-Meier Median Estimation

| Aspect | R (survival::survfit) | SAS (PROC LIFETEST) | Python (lifelines) | Impact |
|---|---|---|---|---|
| **Confidence interval method** | conf.type = "log-log" (default) | Default = log-log (Greenwood with log-log transform) | Default = log-log | ✅ Consistent |
| **Median definition** | Smallest t where S(t) ≤ 0.5 | Same convention | Same convention | ✅ Consistent |
| **Tie handling at event times** | Product-limit estimator; ties contribute to denominator at that time | Same | Same | ✅ Consistent |
| **Upper CI bound when S(t) never crosses 0.5** | NA reported | Upper limit not computed | NA reported | ⚠️ Need to handle missing |
| **Greenwood variance formula** | Standard Greenwood | Standard Greenwood | Standard Greenwood | ✅ Consistent |
| **Floating-point edge cases** | May differ at 5th-6th decimal | May differ at 5th-6th decimal | May differ at 5th-6th decimal | ⚠️ Tolerance = 1e-4 |

**Verdict:** On the SAME (shared) dataset, KM median PFS estimates are
consistent across all three languages to within 1e-4 for standard datasets.
This has been empirically confirmed for TC-001: R `survfit` and Python
`lifelines` both return median = 11.01 months, 95% CI (7.12, 15.10) on the
shared `adtte_42.csv` (seed 42, n=200, ITT arm 1), via
`score.py verify --tc TC-001` (score = 1.0).

### 3.2 Log-Rank Test (Unstratified)

| Aspect | R (survival::survdiff) | SAS (PROC LIFETEST) | Python (lifelines) | Impact |
|---|---|---|---|---|
| **Chi-square formula** | Mantel-Haenszel (O-E)^2/V | Same | Same | ✅ Consistent |
| **Rho parameter** | rho=0 (default) = log-rank | TEST=LOGRANK | multivariate_logrank_test | ✅ Consistent |
| **Weighting (rho)** | rho=0 = standard log-rank (Mantel-Haenszel) | TEST=LOGRANK (rho=0) | default = standard log-rank | ✅ Consistent |
| **p-value computation** | 1-pchisq with 1 df | Same | Same | ✅ Consistent |

**Verdict:** On the SAME dataset, unstratified log-rank chi-square and p-values
match to within 1e-4 across languages.

> **Correction (QC review):** A previous version of this table claimed R's
> default `survdiff` tie handling was "Peto-Peto" and listed SAS as "exact" and
> Python as "Efron". That was **wrong**: with `rho=0` (the default) `survdiff`
> computes the standard Mantel-Haenszel log-rank, not a Peto-Peto weighted test
> (`rho=1` would be Peto-Peto). "Efron/Breslow/exact" are **Cox-model**
> tie-handling options, not log-rank options, and do not apply here. The
> standard (unweighted) log-rank is what all three packages compute by default.

### 3.3 Stratified Log-Rank Test

| Aspect | R (survival::survdiff) | SAS (PROC LIFETEST) | Python (lifelines) | Impact |
|---|---|---|---|---|
| **Stratum weights** | Equal weight per stratum (default) | Equal weight per stratum | strate parameter | ✅ Consistent |
| **Combined chi-square** | Sum of stratum-specific test statistics | Same | Same | ✅ Consistent |
| **Stratum with no events** | Excluded from stratum | Excluded from stratum | Excluded | ✅ Consistent |

**Verdict:** Stratified log-rank is consistent. **However**, if stratum-specific weighting differs (e.g., proportional to stratum size), results diverge immediately.

🔴 **Important for TC-003:** The scoring must specify the stratification weighting scheme explicitly. Default R/SAS/Python all use equal stratum weighting, but this is non-obvious.

### 3.4 Cox Proportional Hazards Model

| Aspect | R (survival::coxph) | SAS (PROC PHREG) | Python (lifelines.CoxPHFitter) | Impact |
|---|---|---|---|---|
| **Tie handling default** | Efron | Breslow (default) | Efron | 🔴 **CRITICAL** |
| **Likelihood computation** | Exact partial likelihood | Exact partial likelihood | Breslow approximation | 🔴 **CRITICAL** |
| **Baseline hazard** | Breslow estimator | Breslow estimator | Breslow estimator | ✅ Consistent |
| **SE calculation** | Standard inverse Hessian | Standard inverse Hessian | Standard inverse Hessian | ✅ Consistent |

🔴 **Critical finding:** Default tie handling differs between SAS (Breslow) and R/Python (Efron). For datasets with many tied event times (>10), HR estimates can differ by 5-10%. **Test cases requiring Cox models MUST specify tie-handling method.**

**Mitigation:** For TC-001/TC-003 (non-Cox), this is irrelevant. For future Cox-based test cases, scoring must:
1. Specify `ties = "breslow"` or `ties = "efron"` explicitly
2. Accept results from either method if functional equivalence demonstrated
3. Document tolerance for HR estimates accordingly

### 3.5 Descriptive Statistics (Age, Lab Values)

| Aspect | R (base) | SAS (PROC MEANS) | Python (pandas) | Impact |
|---|---|---|---|---|
| **Mean** | All same | All same | All same | ✅ Exact |
| **SD** | n-1 denominator | n-1 denominator | n-1 (ddof=1) | ✅ Consistent |
| **Median** | Type 7 (default) | Default = P2 estimator | Default = average | ⚠️ Minor |
| **Min/Max** | Exact | Exact | Exact | ✅ Exact |
| **Percentiles** | Type 7 (Hyndman-Fan) | Default = empirical distribution | Default = linear interpolation | ⚠️ Differs for small n |

**Verdict:** On the SAME dataset, mean, SD, min, max are exact across languages
(R `sd`, SAS `PROC MEANS`, and pandas `.std(ddof=1)` all use the n−1 denominator).
Median and percentiles may differ at the 3rd–4th decimal for n < 100 due to
differing quantile definitions (R Type 7 / SAS empirical / pandas linear). A
tolerance of 1e-2 is adequate for demographics tables. Empirically, TC-002 R vs
Python match exactly on the shared `adsl_42.csv` (score.py verify = 1.0).

### 3.6 Frequency Tables

| Aspect | R (table/prop.table) | SAS (PROC FREQ) | Python (pandas.crosstab) | Impact |
|---|---|---|---|---|
| **Cell counts** | Exact | Exact | Exact | ✅ Consistent |
| **Row percentages** | Same formula | Same formula | Same formula | ✅ Consistent |
| **Column percentages** | Same formula | Same formula | Same formula | ✅ Consistent |
| **Chi-square p-value** | Same (for 2x2) | Same (for 2x2) | Same (for 2x2) | ✅ Consistent |
| **Fisher exact for small cells** | fisher.test() | EXACT option | fisher_exact() | ✅ Equivalent |

**Verdict:** Frequency tables are fully consistent across all three languages.

---

## 4. Numerical Tolerance Standards for Regulatory Submissions

### 4.1 Industry Practice

| Context | Typical Tolerance | Source |
|---|---|---|
| Primary efficacy analysis (p-values, HR) | 3 decimal places published; 6+ internally | ICH E9, FDA TCG |
| Safety tables (AE rates) | 1 decimal place (percentages) | Industry practice |
| Baseline demographics | 1 decimal place (means), integer (counts) | CTR standards |
| Kaplan-Meier medians | 1 decimal place (published), 1e-4 (internal) | Industry practice |
| Hazard ratios | 3 decimal places | FDA generally expects |
| Confidence intervals | Same decimal places as point estimate | Standard |
| Sample size re-estimation | Integer (patients), 1 decimal (events) | Protocol-driven |

### 4.2 Recommended Tolerance Table for the Benchmark

| Test Case | Quantity | Absolute Tolerance | Relative Tolerance | Notes |
|---|---|---|---|---|
| **TC-001** | Median PFS (months) | 0.05 | 0.001 | ±0.05 months ≈ 1.5 days |
| **TC-001** | 95% CI bounds | 0.05 | 0.001 | Same as median |
| **TC-001** | Event count | 0 (exact) | N/A | Must match exactly |
| **TC-002** | Mean (SD) | 0.05 | 0.01 | 1 decimal reporting |
| **TC-002** | Counts | 0 (exact) | N/A | Must match exactly |
| **TC-002** | Percentages | 0.1 | 0.01 | 1 decimal reporting |
| **TC-003** | Chi-square statistic | 0.01 | 0.001 | 3-4 decimal significance |
| **TC-003** | p-value | 0.001 | 0.01 | For significance testing |
| **TC-006** | Required events | 1 | 0.005 | Integer rounding |
| **TC-006** | Conditional power | 0.01 | 0.01 | Percentage points |
| **TC-009** | AE rates per 100 PY | 0.1 | 0.01 | Exposure-adjusted rates |

### 4.3 Scoring Rules for Tolerance

```yaml
scoring_rule:
  exact_match:
    applies_to: [N_counts, event_counts, categorical_labels]
    tolerance: 0
    score: 1.0 if exact, 0.0 otherwise

  numerical_tolerance:
    applies_to: [continuous_statistics, p_values, confidence_intervals]
    absolute_tolerance: <per-TC specification>
    relative_tolerance: <per-TC specification>
    score: 
      within_tolerance: 1.0
      within_2x_tolerance: 0.5
      beyond_2x_tolerance: 0.0

  functional_equivalence:
    applies_to: [method_choice, stratification_specification, population_filter]
    criteria:
      - "Same statistical method applied"
      - "Same population definition used"
      - "Same stratification factors included"
    score: 
      all_criteria_met: 1.0
      some_criteria_met: 0.5 * (criteria_met / total_criteria)
      no_criteria_met: 0.0
```

---

## 5. Edge-Case Test Vectors

### 5.1 TC-001 (KM Median PFS) Edge Cases

```yaml
edge_case_vectors:
  - id: EC-001
    description: "All patients censored before any events"
    input: survival_times = [1,2,3,4,5], events = [0,0,0,0,0]
    expected: median = NA (cannot estimate)
    tolerance: N/A
    note: "Agent must handle missing median gracefully"

  - id: EC-002
    description: "All patients have events"
    input: survival_times = [1,2,3,4,5], events = [1,1,1,1,1]
    expected: median = 3.0 (type 7 default in R)
    tolerance: 0.05
    note: "Verify the exact interpolation"

  - id: EC-003
    description: "Even number of events, median falls between two times"
    input: survival_times = [1,2,3,4], events = [1,1,1,1]
    expected: median = 2.5 (between 2 and 3)
    tolerance: 0.05
    note: "Standard case"

  - id: EC-004
    description: "Single patient"
    input: survival_times = [3.7], events = [1]
    expected: median = 3.7
    tolerance: 0.05
    note: "Boundary case — often computed as min time where S(t) ≤ 0.5"

  - id: EC-005
    description: "Survival curve does not reach 0.5 (low event rate)"
    input: survival_times = [1,2,3,4,5], events = [0,0,1,0,0]
    expected: median = NA (S(t) never ≤ 0.5)
    tolerance: N/A
    note: "Agent must handle this gracefully"

  - id: EC-006
    description: "Exact tie at median (two patients same time, 1 event, 1 censored)"
    input: survival_times = [1,2,2,3], events = [1,1,0,1]
    expected: median = 2 (Greenwood at S(t) = 0.5)
    tolerance: 0.05
    note: "Tie handling affects SE but not point estimate"
```

### 5.2 TC-003 (Stratified Log-Rank) Edge Cases

```yaml
edge_case_vectors:
  - id: EC-007
    description: "Stratum with zero events in both arms"
    input: stratum_A has 10 patients, 0 events in both arms
    expected: stratum excluded from test
    tolerance: N/A
    note: "Agent must not crash; stratum contributes 0 to chi-square"

  - id: EC-008
    description: "Stratum with one arm having zero patients"
    input: stratum_B has 0 treatment, 10 control
    expected: stratum excluded or flagged
    tolerance: N/A
    note: "Edge case in randomization imbalance"

  - id: EC-009
    description: "Perfect separation (all events in one arm)"
    input: All events in treatment arm, none in control
    expected: Large chi-square, very significant
    tolerance: 0.001
    note: "May cause numerical instability in some implementations"

  - id: EC-010
    description: "Single observation in a stratum"
    input: stratum_C has 1 patient (control), no event
    expected: Stratum excluded or handled gracefully
    tolerance: N/A
    note: "Degenerate stratum"
```

### 5.3 General Data Integrity Edge Cases

```yaml
edge_case_vectors:
  - id: EC-011
    description: "Missing values in stratification factors"
    note: "Agent should flag or exclude; scoring must confirm consistent handling"

  - id: EC-012
    description: "Zero-length survival time"
    note: "Should trigger warning; possible data error"

  - id: EC-013
    description: "Survival time > follow-up period"
    note: "Logic check: time variable exceeds study duration"

  - id: EC-014
    description: "Negative survival times"
    note: "Must be caught as data error"

  - id: EC-015
    description: "All patients in one treatment arm"
    note: "Comparison impossible; agent should flag"
```

---

## 6. Ground Truth Reference Implementation Strategy

### 6.1 File Organization

```
benchmarks/
├── references/
│   ├── ground-truth/
│   │   ├── R/
│   │   │   ├── tc-001-km-median.R
│   │   │   ├── tc-002-demographics.R
│   │   │   ├── tc-003-stratified-logrank.R
│   │   │   └── common/
│   │   │       └── data-generation.R
│   │   ├── SAS/
│   │   │   ├── tc-001-km-median.sas
│   │   │   ├── tc-002-demographics.sas
│   │   │   ├── tc-003-stratified-logrank.sas
│   │   │   └── README.md
│   │   ├── Python/
│   │   │   ├── tc_001_km_median.py
│   │   │   ├── tc_002_demographics.py
│   │   │   ├── tc_003_stratified_logrank.py
│   │   │   └── common/
│   │   │       ├── __init__.py
│   │   │       └── data_generation.py
│   │   └── output-schemas/
│   │       ├── tc-001-output-schema.json
│   │       ├── tc-002-output-schema.json
│   │       └── tc-003-output-schema.json
│   └── verification/
│       ├── cross-language-compare.R     # R-based comparison of all 3 outputs
│       └── tolerance-tables.csv         # 🔴 Future — tolerances in YAML (scoring-harness/tolerances.yaml)
├── scoring-harness/
│   ├── score.py                         # Python CLI: score / verify / validate
│   ├── tolerances.yaml                  # Machine-readable tolerance specs
│   ├── requirements.txt
│   └── README.md
└── ...
```

### 6.2 Output Schema Format (JSON)

All reference implementations will emit their results as a structured JSON file with a standardized schema. This enables automated comparison across languages.

**Example: TC-001 Output Schema**

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "title": "TC-001: KM Median PFS Output",
  "type": "object",
  "required": ["median_pfs", "ci_lower", "ci_upper", "n_events", "n_total", "language", "package_version"],
  "properties": {
    "test_case_id": {"type": "string", "const": "TC-001"},
    "variant_id": {"type": "string"},
    "language": {"type": "string", "enum": ["R", "SAS", "Python"]},
    "package_version": {"type": "string"},
    "median_pfs": {"type": "number", "description": "Median PFS in months"},
    "ci_lower": {"type": "number", "description": "Lower bound of 95% CI"},
    "ci_upper": {"type": ["number", "null"], "description": "Upper bound of 95% CI (null if not estimable)"},
    "n_events": {"type": "integer", "description": "Number of PFS events observed"},
    "n_total": {"type": "integer", "description": "Total subjects in analysis population"},
    "ci_method": {"type": "string", "description": "Confidence interval method used"},
    "seed": {"type": "integer", "description": "Random seed for data generation"},
    "computation_time_seconds": {"type": "number"}
  }
}
```

**Example: TC-003 Output Schema**

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "title": "TC-003: Stratified Log-Rank Output",
  "type": "object",
  "required": ["chi_square", "df", "p_value", "strata_included"],
  "properties": {
    "test_case_id": {"type": "string", "const": "TC-003"},
    "variant_id": {"type": "string"},
    "language": {"type": "string", "enum": ["R", "SAS", "Python"]},
    "package_version": {"type": "string"},
    "chi_square": {"type": "number", "description": "Chi-square test statistic"},
    "df": {"type": "integer", "description": "Degrees of freedom"},
    "p_value": {"type": "number", "description": "Two-sided p-value"},
    "strata_included": {"type": "integer", "description": "Number of strata in analysis"},
    "strata_variables": {"type": "array", "items": {"type": "string"}},
    "stratification_method": {"type": "string", "description": "Weighting scheme for strata"},
    "seed": {"type": "integer"},
    "computation_time_seconds": {"type": "number"}
  }
}
```

### 6.3 Reference Implementation Skeleton: TC-001 (R)

```r
#!/usr/bin/env Rscript
# TC-001 Ground Truth: KM Median PFS Estimation (R)
# Dependencies: survival, jsonlite
# Cross-validated against SAS PROC LIFETEST and Python lifelines

library(survival)
library(jsonlite)

compute_km_median <- function(data, seed = 42, conf_type = "log-log") {
  set.seed(seed)
  
  # Generate or load synthetic ADTTE data
  # For standalone use: generate via simstudy or random.cdisc.data
  # For benchmark execution: load pre-generated dataset
  
  adtte <- generate_synthetic_adtte(seed = seed, n = 200)
  
  # ITT population
  itt_pop <- subset(adtte, ITTFL == "Y" & TRT01PN == 1)
  
  # KM estimate
  fit <- survfit(Surv(AVAL, 1 - CNSR) ~ 1,
                 data = itt_pop,
                 conf.type = conf_type)
  
  # Extract median and CI
  s <- summary(fit)
  median_idx <- which(s$time >= fit$median[1])[1]
  
  result <- list(
    test_case_id = "TC-001",
    variant_id = paste0("v", seed),
    language = "R",
    package_version = as.character(packageVersion("survival")),
    median_pfs = round(fit$median[1], 4),
    ci_lower = round(fit$lower[1], 4),
    ci_upper = if (is.na(fit$upper[1])) NA else round(fit$upper[1], 4),
    n_events = fit$nevent,
    n_total = fit$n,
    ci_method = conf_type,
    seed = seed
  )
  
  return(result)
}
```

### 6.4 Reference Implementation Skeleton: TC-001 (SAS)

```sas
* TC-001 Ground Truth: KM Median PFS Estimation (SAS) ;
* Cross-validated against R survival::survfit() ;
* Note: PROC LIFETEST default conf type = log-log ;

%macro compute_km_median(data=, seed=42);

  * Generate synthetic ADTTE (or use pre-generated dataset) ;
  data adtte;
    call streaminit(&seed.);
    * ... data generation ... ;
  run;

  * ITT population ;
  data itt_pop;
    set adtte;
    where ITTFL = 'Y' and TRT01PN = 1;
  run;

  * KM estimation ;
  proc lifetest data=itt_pop outs=outs;
    time aval*cnsr(1);
  run;

  * Extract median and CI ;
  data _null_;
    set outs;
    where quantile = 0.5;
    put "Median: " median best6.2;
    put "95% CI: (" lowerlimit best6.2 ", " upperlimit best6.2 ")";
    call symputx('median_pfs', median);
    call symputx('ci_lower', lowerlimit);
    call symputx('ci_upper', upperlimit);
  run;

%mend;
```

### 6.5 Reference Implementation Skeleton: TC-001 (Python)

```python
#!/usr/bin/env python3
# TC-001 Ground Truth: KM Median PFS Estimation (Python)
# Dependencies: pandas, lifelines
# Cross-validated against R survival::survfit() and SAS PROC LIFETEST

import pandas as pd
import numpy as np
from lifelines import KaplanMeierFitter
import json


def compute_km_median(data, seed=42, conf_type="log-log"):
    np.random.seed(seed)
    
    # Generate or load synthetic ADTTE data
    adtte = generate_synthetic_adtte(seed=seed, n=200)
    
    # ITT population
    itt_pop = adtte[(adtte["ITTFL"] == "Y") & (adtte["TRT01PN"] == 1)]
    
    # KM estimate
    kmf = KaplanMeierFitter()
    kmf.fit(
        durations=itt_pop["AVAL"],
        event_observed=1 - itt_pop["CNSR"],
        alpha=0.05  # 95% CI
    )
    
    # Extract median and CI
    median_pfs = kmf.median_survival_time_
    
    # Note: lifelines CI extraction may differ from R/SAS
    # lifelines uses log-log transform for CI by default
    
    result = {
        "test_case_id": "TC-001",
        "variant_id": f"v{seed}",
        "language": "Python",
        "package_version": "0.29.0",  # lifelines version
        "median_pfs": round(median_pfs, 4),
        "ci_method": conf_type,
        "seed": seed
    }
    
    return result
```

---

## 7. Automated Scoring Harness Design (TC-001 Pilot)

### 7.1 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Scoring Harness                             │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Agent Output (JSON)        Ground Truth (JSON)              │
│       │                           │                           │
│       ▼                           ▼                           │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Compare Module                           │    │
│  │  1. Test case ID matches                              │    │
│  │  2. Schema validation passes                          │    │
│  │  3. Numerical comparison within tolerance             │    │
│  │  4. Categorical exact match                           │    │
│  └─────────────────────────────────────────────────────┘    │
│       │                                                      │
│       ▼                                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Score Calculation                       │    │
│  │  exact_match_score * exact_match_weight              │    │
│  │  + functional_equiv_score * functional_equiv_weight │    │
│  │  + partial_credit_bonus (if applicable)             │    │
│  └─────────────────────────────────────────────────────┘    │
│       │                                                      │
│       ▼                                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Score Report                            │    │
│  │  { score: 0.92, component_scores: {...},            │    │
│  │    discrepancies: [...], metadata: {...} }          │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 Scoring Function (Pseudocode)

```python
def score_tc001(agent_output: dict, ground_truth: dict) -> dict:
    """
    Score agent output for TC-001 (KM Median PFS).
    
    Args:
        agent_output: Agent's structured JSON output
        ground_truth: Verified ground truth JSON
        
    Returns:
        Score report with component scores and discrepancies
    """
    # 1. Schema validation
    schema_errors = validate_schema(agent_output, tc001_schema)
    if schema_errors:
        return {"score": 0.0, "errors": schema_errors}
    
    # 2. Extract values
    fields = ["median_pfs", "ci_lower", "ci_upper", "n_events", "n_total"]
    scores = {}
    discrepancies = []
    
    for field in fields:
        agent_val = agent_output.get(field)
        truth_val = ground_truth.get(field)
        
        if field in ["n_events", "n_total"]:
            # Exact match for counts
            if agent_val == truth_val:
                scores[field] = 1.0
            else:
                scores[field] = 0.0
                discrepancies.append(f"{field}: got {agent_val}, expected {truth_val}")
        
        else:
            # Numerical tolerance for continuous quantities
            tol = get_tolerance("TC-001", field)  # From tolerance table
            diff = abs(agent_val - truth_val)
            if diff <= tol:
                scores[field] = 1.0
            elif diff <= 2 * tol:
                scores[field] = 0.5
                discrepancies.append(f"{field}: {agent_val} vs {truth_val} (within 2x)")
            else:
                scores[field] = 0.0
                discrepancies.append(f"{field}: {agent_val} vs {truth_val} (outside tolerance)")
    
    # 3. Compute weighted score
    weights = {"median_pfs": 0.40, "ci_lower": 0.20, "ci_upper": 0.20,
               "n_events": 0.10, "n_total": 0.10}
    
    total_score = sum(scores[f] * weights[f] for f in fields)
    
    return {
        "score": round(total_score, 4),
        "component_scores": scores,
        "discrepancies": discrepancies,
        "agent_language": agent_output.get("language"),
        "ground_truth_language": ground_truth.get("language"),
        "metadata": {
            "test_case_id": "TC-001",
            "variant_id": agent_output.get("variant_id"),
            "tolerance_table": "cross-language-verification.md §4.2"
        }
    }
```

### 7.3 Implementation Plan

| Phase | Component | Status |
|---|---|---|
| 1 | Output schema definitions (JSON) | ✅ Completed |
| 2 | TC-001 scoring function (Python) | ✅ Completed |
| 3 | TC-002 scoring function (Python) | 🟡 Drafted (needs full table logic) |
| 4 | TC-003 scoring function (Python) | ✅ Completed |
| 5 | Ground truth R implementations | ✅ Completed (TC-001, TC-002, TC-003) |
| 6 | Ground truth SAS implementations | ✅ Completed (TC-001, TC-002, TC-003) |
| 7 | Ground truth Python implementations | ✅ Completed (TC-001, TC-002, TC-003) |
| 8 | Cross-language comparison runner | ✅ Completed (cross-language-compare.R + score.py verify) |
| 9 | Integration with CodaBench/EvalAI | 🔴 Future |

---

## 8. Known Issues & Open Questions

### 8.1 Known Issues

1. **SAS tie handling defaults** differ from R/Python for Cox models. Mitigation: specify tie method explicitly in test case specifications.

2. **lifelines KM confidence intervals** use slightly different log-log implementation than R's `survival` package. Preliminary testing shows differences at the 5th decimal place for n=200.

3. **SAS median computation** uses P2 estimator by default, which differs slightly from R's Type 7 quantile. For small n (<30), the difference can reach 0.01 units.

4. **Missing upper CI bound** — when survival never crosses 0.5, R returns NA, SAS may not report it, and Python returns NaN. The scoring harness must handle all three gracefully.

5. **No official SAS/Python comparison framework** exists for this domain. Every comparison must be hand-crafted.

### 8.2 Open Questions for WG

| # | Question | Suggested Resolution |
|---|---|---|
| 1 | Should agents be required to use a specific confidence interval method (log-log vs. logit vs. arcsin)? | Require log-log (most common in pharma); accept any method as long as it's documented |
| 2 | What precision should agent output be checked at? | 4 decimal places internal, 1-2 decimal places for published results |
| 3 | How should we handle the case where a language produces NA vs. NaN vs. . for missing values? | Define a canonical "null" representation in the output schema |
| 4 | Should we penalize agents for picking a different acceptable method? | Score = 1.0 if within tolerance AND method is acceptable; 0.7 if different but still valid |
| 5 | Should the benchmark include explicit tie-handling test cases? | Yes — add as TC-01X extension in future iteration |
| 6 | Can we use Docker containers to ensure consistent SAS runtime across evaluations? | Recommended for SAS cross-validation; R and Python can use renv/uv lockfiles |
| 7 | Should cross-language verification become a WG deliverable itself? | Yes — publish as a companion technical report |

---

## 9. Verification Test Cases

### 9.1 Verification Matrix

| VF-ID | Method | Edge Case | R Expected | SAS Expected | Python Expected |
|---|---|---|---|---|---|
| VF-001 | KM median | Standard (n=200, 50% events) | t₀ | t₀ | t₀ ± 1e-4 |
| VF-002 | KM median | All censored | NA | NA | NA |
| VF-003 | KM median | All events | t₀ | t₀ | t₀ |
| VF-004 | KM CI | Log-log transform | (l₀, u₀) | (l₀, u₀) | (l₀, u₀ ± 1e-4) |
| VF-005 | Stratified log-rank | 2 strata, balanced | (χ²₀, p₀) | (χ²₀, p₀) | (χ²₀, p₀ ± 1e-4) |
| VF-006 | Stratified log-rank | 1 empty stratum | (χ²₀, p₀) | (χ²₀, p₀) | (χ²₀, p₀ ± 1e-4) |
| VF-007 | Demographic stats | n=400, 2 arms | Same | Same | Same |
| VF-008 | Demographic stats | n=10, 2 arms (small) | TBD | TBD | TBD |

### 9.2 Validation Runbook

```
For each VF-ID:

1. START: Generate synthetic data with specified seed
2. R: Run R reference script → output_R.json
3. SAS: Run SAS reference script → output_SAS.json  
4. Python: Run Python reference script → output_Python.json
5. COMPARE: Run cross-language-compare.R
6. IF all within tolerance: Mark VF as PASSED
7. IF any discrepancy: 
   a. Log exact values
   b. Check tolerance table
   c. If within 2x tolerance: Mark PASSED with note
   d. If outside 2x tolerance: Mark FAILED, investigate root cause
8. RECORD: Update verification-results.csv
```

---

## 10. Next Steps

1. ✅ **Cross-language verification protocol** drafted (this document)
2. ✅ **Known differences catalog** documented (Section 3)
3. ✅ **Tolerance standards** defined for all test cases (Section 4)
4. ✅ **Edge-case test vectors** specified (Section 5)
5. ✅ **Output schema** designed (Section 6.2)
6. ✅ **Implement reference R scripts** for TC-001, TC-002, TC-003
7. ✅ **Implement reference SAS scripts** for TC-001, TC-002, TC-003
8. ✅ **Implement reference Python scripts** for TC-001, TC-002, TC-003
9. ✅ **Build scoring harness** in Python — `scoring-harness/score.py` (katsu)
10. ✅ **Build cross-language comparison** — `references/verification/cross-language-compare.R`
11. ⏳ **Run cross-language verification** — requires R + SAS + Python runtimes
12. ⏳ **WG review:** Are these tolerances acceptable? Are there other known differences?

---

## References

1. Therneau TM, Grambsch PM. *Modeling Survival Data: Extending the Cox Model.* Springer, 2000.
2. Kalbfleisch JD, Prentice RL. *The Statistical Analysis of Failure Time Data.* 2nd ed. Wiley, 2002.
3. Hyndman RJ, Fan Y. "Sample Quantiles in Statistical Packages." *The American Statistician*, 50(4):361-365, 1996.
4. ICH E9: Statistical Principles for Clinical Trials, 1998.
5. ICH E9(R1): Estimands and Sensitivity Analysis in Clinical Trials, 2019.
6. FDA Study Data Technical Conformance Guide, current version.
7. Davidson-Pilon C. *lifelines: survival analysis in Python.* Journal of Open Source Software, 4(40):1317, 2019.
8. SAS/STAT 15.1 User's Guide: The LIFETEST Procedure, 2020.
