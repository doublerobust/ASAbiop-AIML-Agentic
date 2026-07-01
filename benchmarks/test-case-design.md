# Test Case Design — Agentic AI Benchmark for TFL Programming

**Version:** 0.1 (Day 2 expansion, corrected for WG alignment)
**Date:** 2026-05-26
**Status:** 🟡 Draft — TFL-focused, multilingual (R + SAS + Python)

---

## 1. Design Principles for Test Cases

### TCD-P1. Clinically Realistic, Legally Clean
Every test case must be based on realistic clinical trial scenarios but use **synthetic, non-proprietary data**. No patient data, no confidential protocol information. All datasets must be reproducible from `simstudy` or `random.cdisc.data`.

### TCD-P2. Unambiguous Ground Truth, Multi-Language
Each test case must have a **single correct answer** or a **well-defined equivalence class** of acceptable answers. Ground truth must be computable in **R, SAS, and Python** independently, and results must cross-validate across languages. Discrepancies between languages should be documented and resolved in the scoring criteria.

### TCD-P3. Human-Verifiable
A practicing biostatistician with 3+ years of experience should be able to review and confirm the ground truth within 30 minutes. If they can't, the test case is too complex for a benchmark (save it for the white paper's case studies).

### TCD-P4. Tool-Agnostic Specification
Test cases must be specified in **domain language**, not in any programming language. The agent should be free to solve them in R, SAS, Python, or any other tool. The scoring checks the output, not the implementation path. **Per-language scores** are reported independently, plus an aggregate score.

### TCD-P5. Individually Scoped, Composably Chained
Level 1 and Level 2 tasks should be independently scorable. Level 3 tasks may chain multiple Level 1/2 tasks together, but each sub-step should remain independently verifiable to allow partial credit.

### TCD-P6. Contamination-Resistant
Test case parameters (sample sizes, effect sizes, number of strata) should be **parametrizable** so the same scenario can be generated in multiple variants. This prevents agents from memorizing answers to public benchmark cases.

---

## 2. Test Case Template

Every test case in the library uses the following template:

```yaml
id: TC-<NNN>
title: <Short descriptive name>
level: 1 | 2 | 3
domain: <safety | efficacy | design | reporting | regulatory>
statistical_methods: [<list of methods required>]
data_requirements:
  format: <SDTM | ADaM | raw>
  source: <simstudy | random.cdisc.data | custom>
  n_subjects: <approximate>
n_variants: <number of parametrizations available>
description: |
  <Full natural language description of the task>
inputs:
  - <file or parameter specification>
  - <additional inputs>
expected_output:
  type: <dataset | table | figure | listing | section | code | report>
  format: <specific format requirements>
ground_truth_method: <R | SAS | Python | Manual review | Hybrid>
scoring:
  exact_match_weight: <0-1>
  functional_equiv_weight: <0-1>
  partial_credit: <yes | no>
  tolerance: <numerical tolerance if applicable>
estimated_human_time: <minutes>
estimated_agent_time_reference: <minutes>
contamination_risk: <low | medium | high>
parametrizable_params: [<list of parameters that can vary>]
```

---

## 3. Level 1 Test Cases (Single-Step, Well-Specified)

### TC-001: Kaplan-Meier Median PFS Estimation

```yaml
id: TC-001
title: "Kaplan-Meier estimate of median PFS for a single treatment arm"
level: 1
domain: efficacy
statistical_methods: [Kaplan-Meier estimation]
data_requirements:
  format: ADaM
  source: random.cdisc.data (ADTTE)
  n_subjects: 200
n_variants: 10
description: |
  Given an ADaM ADTTE dataset with a single treatment arm (TRT01PN = 1),
  compute the Kaplan-Meier estimate of the median progression-free survival
  (PFS) with 95% confidence interval using the log-log transformation method.
  
  Population: ITT (ITTFL = "Y")
  Event of interest: PFS event (CNSR = 0)
  Time variable: AVAL (months)
  
  Return: median PFS, 95% CI (lower, upper), and number of events observed.
inputs:
  - dataset: adtte_adam.sas7bdat (or .rds / .parquet)
  - specification: "Single arm PFS analysis per ITT population"
expected_output:
  type: structured result
  format: |
    Median PFS: X.X months
    95% CI: (Y.Y, Z.Z)
    Events: N / N_total (%)
ground_truth_method: |
  Verified R output from survival::survfit() with conf.type="log-log".
  Cross-validated against SAS PROC LIFETEST.
scoring:
  exact_match_weight: 0.8
  functional_equiv_weight: 0.2
  partial_credit: no
  tolerance: 1e-4
estimated_human_time: 5 min
estimated_agent_time_reference: 2 min
contamination_risk: low
parametrizable_params: [censoring_rate, sample_size, median_survival]
```

**Ground Truth — R:**
```r
library(survival)
library(pharmaverseadam)

# Load or generate synthetic ADTTE
data(adtte, package = "pharmaverseadam")
fit <- survfit(Surv(AVAL, 1 - CNSR) ~ 1, data = adtte, conf.type = "log-log")
median_ci <- with(summary(fit), cbind(median, `0.95LCL`, `0.95UCL`))
cat(paste0("Median PFS: ", round(median_ci[1], 1), " months\n"))
cat(paste0("95% CI: (", round(median_ci[2], 1), ", ", round(median_ci[3], 1), ")\n"))
cat(paste0("Events: ", fit$nevent, " / ", fit$n, "\n"))
```

**Ground Truth — SAS:**
```sas
proc lifetest data=adtte plots=(s) outs=outs;
   time aval*cnsr(1);
   strata trt01pn / test=logrank;
run;

proc sql;
   select median, lowerlimit, upperlimit
   from outs
   where trt01pn = 1 and quantile = 0.5;
quit;
```

**Ground Truth — Python:**
```python
import pandas as pd
from lifelines import KaplanMeierFitter

adtte = pd.read_sas('adtte_adam.sas7bdat')
trt_arm = adtte[adtte['TRT01PN'] == 1]
kmf = KaplanMeierFitter()
kmf.fit(durations=trt_arm['AVAL'], event_observed=1 - trt_arm['CNSR'])
median_idx = (kmf.survival_function_ <= 0.5).idxmax()
ci = kmf.confidence_interval_
print(f"Median PFS: {kmf.median_survival_time_:.1f} months")
print(f"95% CI: ({ci.loc[median_idx, 'KM_estimate_lower_0.95']:.1f}, "
      f"{ci.loc[median_idx, 'KM_estimate_upper_0.95']:.1f})")
```

---

### TC-002: Baseline Demographics Table (Safety Population)

```yaml
id: TC-002
title: "Descriptive summary of baseline demographics by treatment arm"
level: 1
domain: reporting
statistical_methods: [descriptive statistics, frequency tables]
data_requirements:
  format: ADaM
  source: random.cdisc.data (ADSL)
  n_subjects: 400
n_variants: 8
description: |
  Given an ADaM ADSL dataset with at least two treatment arms, produce a
  descriptive table of baseline demographics by treatment arm for the
  safety population (SAFFL = "Y").
  
  Required variables:
  - Age (AGE): n, mean, SD, median, min, max
  - Sex (SEX): n and % female/male
  - Race (RACE): n and % per category
  - Region (REGION1): n and % per region
  - Baseline ECOG (ECOG): n and % per score
  
  Format: Table with treatment arms as columns, a total column, and
  p-value column for between-arm comparison (chi-square for categorical,
  ANOVA for continuous).
inputs:
  - dataset: adsl_adam.sas7bdat
  - specification: "Baseline demographics by arm, safety population"
expected_output:
  type: table
  format: |
    ┌────────────────────┬──────────┬──────────┬──────────┬──────────┐
    │                    │ Placebo  │ Active   │ Total    │ p-value  │
    │                    │ (N=XXX)  │ (N=XXX)  │ (N=XXX)  │          │
    ├────────────────────┼──────────┼──────────┼──────────┼──────────┤
    │ Age (years)        │          │          │          │          │
    │  Mean (SD)         │ XX.X     │ XX.X     │ XX.X     │  0.XXX   │
    │  Median            │ XX.X     │ XX.X     │ XX.X     │          │
    │  Min, Max          │ XX, XX   │ XX, XX   │ XX, XX   │          │
    ├────────────────────┼──────────┼──────────┼──────────┼──────────┤
    │ Sex, n (%)         │          │          │          │          │
    │  Female            │ XX (XX%) │ XX (XX%) │ XX (XX%) │  0.XXX   │
    │  Male              │ XX (XX%) │ XX (XX%) │ XX (XX%) │          │
    └────────────────────┴──────────┴──────────┴──────────┴──────────┘
ground_truth_method: |
  R with dplyr + tableone or gtsummary for generation.
  Cross-check via SAS PROC FREQ + PROC MEANS.
scoring:
  exact_match_weight: 0.6
  functional_equiv_weight: 0.3
  partial_credit: yes
  tolerance: N/A (categorical)
estimated_human_time: 10 min
estimated_agent_time_reference: 3 min
contamination_risk: low
parametrizable_params: [n_arms, variables_included, population_filter]
```

**Ground Truth — R (Tplyr):**
```r
library(Tplyr)
library(dplyr)

t <- tplyr_table(adsl, TRT01PN) %>%
  add_layer(
    group_desc(AGE, by = vars("Age (years)"))
  ) %>%
  add_layer(
    group_count(SEX, by = vars("Sex")) %>%
      set_format_strings(f_str("xx (xx%)", n, pct))
  ) %>%
  add_layer(
    group_count(RACE, by = vars("Race")) %>%
      set_format_strings(f_str("xx (xx%)", n, pct))
  ) %>%
  add_total_group() %>%
  build()
```

**Ground Truth — SAS:**
```sas
proc tabulate data=adsl format=8.1;
   where saffl = 'Y';
   class trt01pn sex race;
   var age;
   table age*(n mean std min max)
         sex*(n pctn)
         race*(n pctn),
         trt01pn all / box='Variable';
run;

proc freq data=adsl;
   where saffl = 'Y';
   table (sex race)*trt01pn / chisq;
run;
```

**Ground Truth — Python:**
```python
import pandas as pd
import numpy as np
from gtsummary import tbl_summary

adsl = pd.read_sas('adsl_adam.sas7bdat')
safety = adsl[adsl['SAFFL'] == 'Y']

summary = safety.groupby('TRT01PN').agg({
    'AGE': ['count', 'mean', 'std', 'min', 'max'],
    'SEX': lambda x: x.value_counts().to_dict(),
    'RACE': lambda x: x.value_counts().to_dict()
})
```

---

### TC-003: Stratified Log-Rank Test

```yaml
id: TC-003
title: "Stratified log-rank test for treatment comparison with 2 stratification factors"
level: 1
domain: efficacy
statistical_methods: [log-rank test, stratified analysis]
data_requirements:
  format: ADaM
  source: random.cdisc.data (ADTTE)
  n_subjects: 400
n_variants: 12
description: |
  Given an ADaM ADTTE dataset with two treatment arms (TRT01PN = 0, 1),
  perform a stratified log-rank test comparing PFS between arms.
  
  Stratification factors:
  1. Sex (SEX): Male, Female
  2. Baseline ECOG score (ECOG): 0, 1
  
  Population: ITT (ITTFL = "Y")
  
  Return: chi-square statistic, degrees of freedom, p-value.
inputs:
  - dataset: adtte_adam.sas7bdat
  - specification: "Stratified log-rank test with SEX and ECOG strata"
expected_output:
  type: structured result
  format: |
    Method: Stratified log-rank test
    Stratification factors: SEX, ECOG
    Chi-square: X.XXX
    DF: 1
    p-value: 0.XXXX
ground_truth_method: |
  R survival::survdiff() with strata(SEX, ECOG).
  Cross-validated against SAS PROC LIFETEST STRATA statement.
scoring:
  exact_match_weight: 0.8
  functional_equiv_weight: 0.2
  partial_credit: no
  tolerance: 1e-4
estimated_human_time: 5 min
estimated_agent_time_reference: 2 min
contamination_risk: low
parametrizable_params: [effect_size, stratification_factors, sample_size]
```

**Ground Truth — R:**
```r
library(survival)

survdiff(Surv(AVAL, 1 - CNSR) ~ TRT01PN + strata(SEX, ECOG),
         data = adtte, subset = ITTFL == "Y")
```

**Ground Truth — SAS:**
```sas
proc lifetest data=adtte plots=(s);
   time aval*cnsr(1);
   strata sex ecog / group=trt01pn test=logrank;
run;
```

**Ground Truth — Python:**
```python
from lifelines import multivariate_logrank_test

adtte_itt = adtte[adtte['ITTFL'] == 'Y']
result = multivariate_logrank_test(
    adtte_itt['AVAL'],
    adtte_itt['TRT01PN'],
    adtte_itt['CNSR'],
    strata=adtte_itt[['SEX', 'ECOG']]
)
print(f"Chi-square: {result.test_statistic:.3f}")
print(f"p-value: {result.p_value:.4f}")
```

---

## 4. Level 2 Test Cases (Multi-Step, Moderately Ambiguous)

### TC-004: SAP Section for Primary Efficacy Analysis

```yaml
id: TC-004
title: "Draft the primary efficacy analysis section of an SAP"
level: 2
domain: design
statistical_methods: [sample size calculation, group sequential design, log-rank test, interim analysis]
data_requirements:
  format: none (spec-driven)
  source: N/A (design parameters provided)
  n_subjects: N/A
n_variants: 10
description: |
  Write the "Primary Efficacy Analysis" section of a Statistical Analysis
  Plan for a Phase 3 oncology trial with the following design parameters:
  
  - Indication: First-line metastatic non-small cell lung cancer
  - Endpoint: Overall survival (OS)
  - Design: 1:1 randomization, active control
  - Sample size: 600 patients (300 per arm)
  - Interim analysis: 1 interim at 60% of target events
  - Final analysis: At 331 events (90% power, HR = 0.75, two-sided alpha = 0.05)
  - Group sequential method: O'Brien-Fleming spending function
  - Stratification factors: PD-L1 expression (≥50%, 1-49%, <1%), ECOG (0, 1)
  - Primary analysis method: Stratified log-rank test
  - Sensitivity analyses: Unstratified log-rank, Cox PH with stratification factors, RMST
  
  The section must follow ICH E9 structure and include:
  1. Analysis population definition (ITT)
  2. Primary endpoint definition with estimand (per ICH E9(R1))
  3. Statistical hypothesis
  4. Analysis method specification
  5. Handling of intercurrent events (treatment switching, death without event)
  6. Sensitivity and supplementary analyses
  7. Subgroup analyses (pre-specified)
  
inputs:
  - protocol_summary: "<provided specifications above>"
  - template: "Standard SAP template per company X"
expected_output:
  type: document section (prose)
  format: Structured text following ICH E9 / E9(R1) conventions
ground_truth_method: |
  Expert review by 2+ practicing biostatisticians with oncology SAP
  experience. Ground truth criteria defined as a checklist of required
  elements.
scoring:
  exact_match_weight: 0.0
  functional_equiv_weight: 0.0
  partial_credit: yes
  tolerance: N/A
estimated_human_time: 120 min
estimated_agent_time_reference: 15 min
contamination_risk: medium
parametrizable_params: [indication, endpoint, sample_size, design_parameters]
```

**Scoring Checklist for TC-004:**

| Criteria | Weight | Check |
|---|---|---|
| ITT population clearly defined | 10% | ⬜ |
| Estimand specified with 5 attributes (ICH E9(R1)) | 15% | ⬜ |
| Primary hypothesis stated (H0, H1) with significance level | 10% | ⬜ |
| Stratified log-rank test specified with strata | 10% | ⬜ |
| OBF alpha spending function with IA timing | 10% | ⬜ |
| Intercurrent events strategy described (treatment switching, death) | 10% | ⬜ |
| At least 2 sensitivity analyses proposed | 10% | ⬜ |
| Subgroup analysis plan with pre-specified subgroups | 5% | ⬜ |
| Multiplicity control for secondary endpoints mentioned | 10% | ⬜ |
| E9/E9(R1) terminology used throughout | 5% | ⬜ |
| Sample size re-estimation / futility considerations (if any) | 5% | ⬜ |

---

### TC-005: TFL Package QC Review

```yaml
id: TC-005
title: "Review a TFL package for SAP consistency"
level: 2
domain: reporting
statistical_methods: [QC review, discrepancy detection]
data_requirements:
  format: ADaM + TFLs
  source: random.cdisc.data (ADSL, ADTTE, ADLB, ADAE) + synthetic TFLs
  n_subjects: 400
n_variants: 15
description: |
  A TFL package (5 tables, 2 figures, 1 listing) has been produced from
  an ADaM dataset. The SAP specifies:
  
  - Primary analysis: Stratified log-rank test with SEX and ECOG strata
  - ITT population for efficacy
  - Safety population for safety analyses
  - Per-protocol population as sensitivity
  - Subgroup analysis by age group (≤65, >65) and sex
  - Multiplicity adjustment: Hochberg procedure for secondary endpoints
  
  The provided TFLs contain 3 deliberate errors:
  1. Error in table vs. figure: Population mismatch (PP instead of ITT)
  2. Error in analysis: Unstratified log-rank used instead of stratified
  3. Error in reporting: Wrong p-value (from wrong model)
  
  Identify all discrepancies between the TFL package and the SAP.
  For each discrepancy, assess severity (Critical / Major / Minor) and
  propose a correction.
inputs:
  - sap_excerpt: "<key specifications>"
  - tfl_package: ["table_14-1.rtf", "figure_14-2.png", "listing_16-1.txt", ...]
expected_output:
  type: QC report
  format: |
    ## TFL QC Review Report
    
    ### Discrepancies Found: 3
    
    | # | Type | Location | Issue | Severity | Correction |
    |---|---|---|---|---|---|
    | 1 | Population | Table 14-3 | PP used instead of ITT | Critical | Re-run with ITTFL="Y" |
    | 2 | Method | Figure 14-2 | Unstratified log-rank | Critical | Add STRATA statement |
    | 3 | Value | Table 14-4 | Wrong p-value (0.043 vs 0.052) | Major | Regenerate from Cox model |
ground_truth_method: |
  Preseeded errors with known corrections. Ground truth is the
  discrepancy catalog used to create the test case.
scoring:
  exact_match_weight: 0.0
  functional_equiv_weight: 0.5
  partial_credit: yes
  tolerance: N/A
estimated_human_time: 30 min
estimated_agent_time_reference: 8 min
contamination_risk: medium
parametrizable_params: [error_locations, error_types, dataset_variant]
```

---

### TC-006: Sample Size Re-Estimation at Interim

```yaml
id: TC-006
title: "Sample size re-estimation based on blinded interim data"
level: 2
domain: design
statistical_methods: [sample size re-estimation, conditional power, blinded interim]
data_requirements:
  format: ADaM
  source: custom simstudy data (partial enrollment data)
  n_subjects: 200 (enrolled so far, of planned 600)
n_variants: 10
description: |
  A Phase 3 trial is ongoing with a planned enrollment of 600 patients.
  The DMC has requested a blinded sample size re-estimation at the current
  point (200 patients enrolled, 120 events observed).
  
  Original design assumptions:
  - Median PFS in control: 6 months
  - Target HR: 0.75
  - Power: 90% at two-sided alpha = 0.05
  - Required events: 331
  
  Current blinded data shows:
  - Pooled median PFS: 5.2 months (95% CI: 4.6-5.9)
  - 120 events observed across both arms
  
  Tasks:
  1. Estimate the pooled event rate from blinded data
  2. Re-estimate the required sample size under the original design assumptions,
     adjusting the control median downward if the pooled data suggests lower event rate
  3. Assess conditional power under three scenarios:
     a. Original HR assumption (0.75)
     b. More modest HR (0.80)
     c. Optimistic HR (0.70)
  4. Recommend: Continue as planned, increase sample size, or consider futility
  5. Document assumptions and limitations of the re-estimation
  
inputs:
  - enrollment_data: "enrollment_progress.csv"
  - event_data: "interim_events.csv"
  - design_parameters: "<original assumptions>"
expected_output:
  type: structured report with recommendation
  format: |
    ## Sample Size Re-Estimation Report
    
    ### Current Status
    Enrolled: 200 / 600 (33.3%)
    Events observed: 120
    
    ### Blinded Event Rate Estimation
    Pooled median PFS: 5.2 months
    Estimated control median: X.X months
    Estimated event rate: X events/month
    
    ### Revised Sample Size Estimates
    | Scenario | HR | Events Needed | Total N Needed | Recommendation |
    |---|---|---|---|---|
    | Original | 0.75 | 331 | 600 | Continue |
    | Modest | 0.80 | XXX | XXX | Increase |
    | Optimistic | 0.70 | XXX | XXX | Consider reduction |
    
    ### Conditional Power
    At current info fraction (XX%):
    - Under original assumption: XX%
    - Under modest: XX%
    - Under optimistic: XX%
    
    ### Recommendation
    [Structured recommendation with rationale]
ground_truth_method: |
  R gsDesign::ssrCP() for conditional power, gsDesign::nEvents()
  for event count re-estimation. Cross-validated against SAS PROC SEQDESIGN.
scoring:
  exact_match_weight: 0.4
  functional_equiv_weight: 0.4
  partial_credit: yes
  tolerance: 1e-3
estimated_human_time: 45 min
estimated_agent_time_reference: 10 min
contamination_risk: medium
parametrizable_params: [observed_events, original_assumptions, enrollment_rate]
```

---

## 5. Level 3 Test Cases (Full Workflow, Realistic Ambiguity)

### TC-007: Regulatory Response to Reviewer Query on ITT vs. PP Discrepancy

```yaml
id: TC-007
title: "Regulatory response analyzing ITT vs. PP discrepancy in primary endpoint"
level: 3
domain: regulatory
statistical_methods: [ITT analysis, per-protocol analysis, sensitivity analysis, tipping point analysis]
data_requirements:
  format: ADaM + SDTM
  source: random.cdisc.data + custom synthetic data
  n_subjects: 500
n_variants: 8
description: |
  You are the lead biostatistician responding to a regulatory authority
  review query. The reviewer has noted that the ITT analysis shows
  a significant treatment effect for PFS (HR = 0.72, p = 0.023) while
  the per-protocol analysis does not reach significance (HR = 0.84,
  p = 0.12). The reviewer asks whether this discrepancy undermines
  the primary conclusion.
  
  The study has:
  - 500 patients randomized 1:1
  - 87 patients excluded from PP (43 in arm A, 44 in arm B)
  - Reasons for exclusion: major protocol violations (28), early
    discontinuation before first post-baseline assessment (35),
    prohibited medication use (24)
  - More exclusions in the PP had events (60% vs. 45% in ITT)
  
  Tasks:
  1. Analyze the discrepancy between ITT and PP results
  2. Assess whether the exclusion pattern is imbalanced and could
     explain the discrepancy
  3. Perform a tipping point analysis: how many events in the excluded
     patients would need to be reclassified to change the ITT conclusion?
  4. Propose at least 2 additional sensitivity analyses
  5. Draft a formal response memo to the reviewer addressing their
     concern with appropriate statistical justification
inputs:
  - adsl: "adsl_adam.sas7bdat"
  - adtte: "adtte_adam.sas7bdat"
  - pp_analysis: "pp_results.sas7bdat"
  - reviewer_query_text: "<provided>"
expected_output:
  type: regulatory response memo
  format: |
    ## Response to Reviewer Query: ITT vs. PP Discrepancy in PFS Analysis
    
    ### Reviewer Comment
    [Quoted comment]
    
    ### Background
    [Study description, analysis populations]
    
    ### Analysis of Discrepancy
    [Systematic analysis including exclusion pattern, event distribution]
    
    ### Tipping Point Analysis
    [Results showing how many reclassifications needed to negate ITT result]
    
    ### Sensitivity Analyses
    1. [Sensitivity analysis 1: e.g., multiple imputation for early dropouts]
    2. [Sensitivity analysis 2: e.g., composite outcome including dropout]
    
    ### Conclusion
    [Whether the primary conclusion is robust]
    
    ### Attachments
    [Supporting tables and figures]
ground_truth_method: |
  Expert review by multiple biostatisticians. Ground truth for numerical
  analyses (tipping point) from R/gsDesign. Qualitative judgments
  scored against an expert consensus rubric.
scoring:
  exact_match_weight: 0.0
  functional_equiv_weight: 0.0
  partial_credit: yes
  tolerance: N/A
estimated_human_time: 180 min
estimated_agent_time_reference: 25 min
contamination_risk: high
parametrizable_params: [effect_size_discrepancy, exclusion_pattern, treatment_effect]
```

**Expert Review Rubric for TC-007:**

| Domain | Criterion | Weight | Score (0-5) |
|---|---|---|---|
| **Statistical** | Correct analysis of exclusion pattern and event distribution | 15% | ⬜ |
| **Statistical** | Tipping point analysis correctly performed and interpreted | 15% | ⬜ |
| **Statistical** | Appropriate sensitivity analyses proposed | 10% | ⬜ |
| **Regulatory** | Response structured per regulatory expectation | 10% | ⬜ |
| **Regulatory** | Language appropriate for regulatory submission | 10% | ⬜ |
| **Communication** | Clear explanation accessible to non-statistician reviewer | 10% | ⬜ |
| **Communication** | Appropriate use of tables/figures to support argument | 10% | ⬜ |
| **Judgment** | Appropriate conclusion drawn from evidence | 10% | ⬜ |
| **Completeness** | All required elements present and well-integrated | 10% | ⬜ |

---

### TC-008: End-to-End Dose-Finding Study Design

```yaml
id: TC-008
title: "Design a Phase 2 dose-finding study for a novel immunotherapy"
level: 3
domain: design
statistical_methods: [dose-finding, Bayesian methods, model-assisted designs, sample size, historical control]
data_requirements:
  format: summary data
  source: synthetic historical data from 3 prior trials
  n_subjects: 300 (historical)
n_variants: 6
description: |
  Design a Phase 2 dose-finding study for a novel bispecific T-cell engager
  immunotherapy in relapsed/refractory multiple myeloma.
  
  Available information:
  - Historical control data from 3 prior trials (pooled ORR: 26%, n=124)
  - 2 doses of the experimental agent to evaluate: Dose A (low) and Dose B (high)
  - Primary endpoint: Overall response rate (ORR) per IMWG criteria
  - Key secondary: Duration of response, PFS, safety (CRS, ICANS)
  - Target ORR: ≥45% for Dose A, ≥55% for Dose B (experimental treatment effect)
  
  Constraints:
  - Maximum 80 patients total (40 per dose)
  - Must include at least one interim analysis for futility
  - Historical data may be used via Bayesian borrowing (power prior or MAP prior)
  
  Deliverables:
  1. Recommended study design with sample size justification
  2. Analysis method with null and alternative hypotheses
  3. Stopping rules (futility and, if applicable, early efficacy)
  4. Mock SAP outline for the primary analysis
  5. Operating characteristics (Type I error, power) under at least 3 scenarios
  6. Discussion of historical data borrowing approach and its sensitivity
  7. Simulation code demonstrating operating characteristics
inputs:
  - historical_data_summary.csv
  - trial_design_brief.txt
expected_output:
  type: design protocol + simulation code
  format: |
    ## Phase 2 Dose-Finding Study Design
    
    ### Design Overview
    [Design type: e.g., two-arm, Bayesian optimal phase 2 (BOP2), etc.]
    
    ### Sample Size Justification
    [Power analysis, operating characteristics]
    
    ### Analysis Method
    [Primary analysis, historical borrowing approach]
    
    ### Stopping Rules
    [Futility: ...; Early efficacy: ...]
    
    ### SAP Outline
    [Mock table of contents]
    
    ### Operating Characteristics
    | Scenario | True ORR A | True ORR B | Go Probability A | Go Probability B |
    |---|---|---|---|---|
    | Null | 26% | 26% | X% | X% |
    | Target A | 45% | 55% | X% | X% |
    | Target B | 45% | 45% | X% | X% |
    | Safety concern | 45% | 55% | X% (w/ safety stop) | X% (w/ safety stop) |
ground_truth_method: |
  Simulation-based ground truth using R packages: dosfind, bcrm,
  trialr, gsDesign, and BayesCTDesign. Operating characteristics
  generated from 10,000 simulated trials per scenario.
scoring:
  exact_match_weight: 0.0
  functional_equiv_weight: 0.0
  partial_credit: yes
  tolerance: N/A
estimated_human_time: 240 min
estimated_agent_time_reference: 30 min
contamination_risk: high
parametrizable_params: [historical_control_rate, target_rates, max_sample_size, borrowing_strength]
```

---

### TC-009: Complete Safety Signal Evaluation with DMC Report

```yaml
id: TC-009
title: "Complete safety signal evaluation and DMC report for Phase 3 trial"
level: 3
domain: safety
statistical_methods: [safety monitoring, AE tabulation, MedDRA coding, exposure-adjusted rates, statistical signal detection]
data_requirements:
  format: SDTM + ADaM
  source: random.cdisc.data (ADSL, ADAE, ADLB, ADVS) + custom safety data
  n_subjects: 600
n_variants: 8
description: |
  A Phase 3 oncology trial has completed enrollment and the DMC is
  convening for a scheduled safety review. As the study statistician,
  produce a comprehensive safety evaluation report covering:
  
  Data cut: 6 months after last patient enrolled
  Treatment: 1:1 randomization (300 per arm)
  Median follow-up: 14 months (range 6-24)
  
  Areas to evaluate:
  1. **AE Overview** — Overall AE rates, SAEs, AEs leading to discontinuation,
     deaths on study, by arm
  2. **Exposure-Adjusted AE Rates** — AE rate per 100 patient-years for
     common AEs (≥5% in either arm), by MedDRA preferred term and SOC
  3. **Grade 3+ Events** — Tabulation of severe AEs with risk difference
      and 95% CI vs. control
  4. **Laboratory Abnormalities** — Shift tables for key labs (ALT, AST,
     bilirubin, creatinine, hemoglobin, platelets), CTCAE grade shifts
  5. **Time-to-Event Safety** — Time to first Grade 3+ AE (KM plot)
  6. **AE of Special Interest** — Immune-related AEs (irAEs), infusion
     reactions, with onset timing and outcome
  7. **Signal Detection** — Statistical signal detection using:
     a. Empirical Bayes (MGPS) for disproportionate reporting
     b. Confidence interval for risk difference
  8. **Safety Recommendation** — Based on totality of evidence, provide
     a recommendation on trial continuation

inputs:
  - adsl: "adsl_adam.sas7bdat"
  - adae: "adae_adam.sas7bdat"
  - adlb: "adlb_adam.sas7bdat"
  - advs: "advs_adam.sas7bdat"
  - dmc_charter: <provided>
expected_output:
  type: comprehensive safety report
  format: |
    ## DMC Safety Review Report - Data Cut DD-MMM-YYYY
    
    ### 1. Executive Summary
    [One-page summary for DMC]
    
    ### 2. Patient Disposition and Exposure
    [Exposure summary table, follow-up duration]
    
    ### 3. Adverse Event Overview
    [Table 3-1: Overall AE summary by arm]
    
    ### 4. Common AEs (Exposure-Adjusted)
    [Table 4-1: AEs ≥5% by PT, rates per 100 PY]
    
    ### 5. Severe AEs (Grade 3+)
    [Table 5-1: Grade 3+ with risk differences]
    
    ### 6. Laboratory Safety
    [Shift tables, CTCAE grade migrations]
    
    ### 7. AEs of Special Interest
    [irAE analysis with onset plots]
    
    ### 8. Statistical Signal Detection
    [MGPS results, signals flagged]
    
    ### 9. Recommendation
    [Continue as planned / Modify / Pause]
ground_truth_method: |
  R with safety packages: safetyData, safetyGraphics, tidyCDISC,
  PhV (pharmacovigilance), and custom code for signal detection.
  Cross-validation against SAS Clinical Standards Toolkit.
scoring:
  exact_match_weight: 0.0
  functional_equiv_weight: 0.0
  partial_credit: yes
  tolerance: 1e-3
estimated_human_time: 480 min (full day)
estimated_agent_time_reference: 45 min
contamination_risk: high
parametrizable_params: [event_rates, ae_distribution, follow_up_duration]
```

---

### TC-010: CSR Section — Statistical Methods and Results

```yaml
id: TC-010
title: "Draft the statistical methods and results section of a CSR"
level: 3
domain: reporting
statistical_methods: [full CSR statistical section, ICH E3 compliance, data presentation]
data_requirements:
  format: ADaM + TFLs
  source: random.cdisc.data + pre-computed TFLs
  n_subjects: 400
n_variants: 6
description: |
  Draft the Statistical Methods (Section 9) and Statistical Results
  (Section 11) sections of an ICH E3-compliant Clinical Study Report
  for a Phase 3 randomized trial.
  
  The CSR is for a completed Phase 3 study of Drug X vs. Placebo in
  advanced solid tumors. Primary endpoint is PFS per RECIST 1.1.
  
  Provided:
  - Study protocol summary
  - SAP
  - ADaM datasets (ADSL, ADTTE, ADRS, ADAE, ADLB)
  - TFL package (12 tables, 4 figures, 3 listings)
  - Blinding has been broken; unblinded results available
  
  Requirements:
  1. **Section 9 (Statistical Methods):** Copy the SAP analysis methods
     and add actual handling details (software version, data cutoff,
     population definitions used)
  2. **Section 11.1 (Patient Disposition):** Summary of randomization,
     treatment exposure, study completion, major protocol deviations
  3. **Section 11.2 (Demographics):** Baseline characteristics table
  4. **Section 11.4 (Efficacy Results):** Primary analysis results,
     sensitivity analyses, subgroup analyses, graphical display
  5. **Section 11.5 (Safety Results):** AE summary, deaths, SAEs,
     laboratory findings
  6. Ensure all references to tables and figures are accurate
  7. Ensure all conclusions are supported by the data presented
  8. Flag any inconsistencies between text, tables, and listings

inputs:
  - protocol.pdf
  - sap.pdf
  - adsl: "adsl_adam.sas7bdat"
  - adtte: "adtte_adam.sas7bdat"
  - adrs: "adrs_adam.sas7bdat"
  - adae: "adae_adam.sas7bdat"
  - adlb: "adlb_adam.sas7bdat"
  - tfl_package/
expected_output:
  type: CSR sections
  format: ICH E3-compliant CSR text (Sections 9 and 11)
ground_truth_method: |
  Expert review by 2+ biostatisticians with regulatory submission
  experience. Numerical values cross-checked against verified R output.
  Checklist-based scoring using ICH E3 requirements.
scoring:
  exact_match_weight: 0.0
  functional_equiv_weight: 0.0
  partial_credit: yes
  tolerance: N/A
estimated_human_time: 480 min (full day)
estimated_agent_time_reference: 45 min
contamination_risk: high
parametrizable_params: [study_parameters, treatment_effect, safety_profile]
```

---

## 4. Level 1 Test Cases — Expansion (TC-011 through TC-014)

### TC-011: Adverse Event Summary Table by SOC and PT

```yaml
id: TC-011
level: 1
domain: safety
statistical_methods: [descriptive statistics, AE tabulation]
data_requirements:
  format: ADaM (ADAE)
  source: synthetic (seed-controlled)
  n_subjects: 200 (100 per arm)
n_variants: 10
description: |
  Generate a standard adverse event summary table with:
  - Rows: SOC → PT hierarchy (MedDRA coding)
  - Columns: Treatment arms (Experimental vs Control)
  - Cells: n (%) for each AE term, sorted by descending frequency
  - Summary rows: Any AE, Serious AEs, AEs leading to discontinuation
  
  Population: Safety (SAFFL = "Y")
  Scoring: exact match on n-counts, ±0.5% on percentages
inputs:
  - dataset: adae_adam.sas7bdat (or .rds / .parquet)
  - specification: "AE summary by SOC/PT, safety population"
expected_output:
  type: table
  format: structured JSON with ae_table array
ground_truth_method: Python + R (cross-validated)
scoring:
  exact_match_weight: 0.7
  functional_equiv_weight: 0.3
  partial_credit: yes
  tolerance: n exact, pct ±0.5%
estimated_human_time: 20 min
estimated_agent_time_reference: 5 min
contamination_risk: low
parametrizable_params: [seed, n_subjects, ae_rate_distribution, soc_hierarchy]
```

**Auto-scoring rules:**
- N-counts must match ground truth exactly (subject counts per term are deterministic given seed)
- Percentages within ±0.5% (rounding tolerance)
- SOC/PT hierarchy must be preserved (PT nested within SOC)
- Sorting must be by descending frequency within each SOC
- Summary rows (Any AE, SAE, Discontinuation) must be present

---

### TC-012: Forest Plot — Subgroup Hazard Ratios

```yaml
id: TC-012
level: 1
domain: efficacy
statistical_methods: [Cox proportional hazards, subgroup analysis]
data_requirements:
  format: ADaM (ADTTE + ADSL)
  source: synthetic (seed-controlled exponential survival)
  n_subjects: 300 (150 per arm)
n_variants: 10
description: |
  Compute hazard ratios with 95% CIs for predefined subgroups:
  - Age group (<65, >=65)
  - Sex (Male, Female)
  - ECOG PS (0, 1+)
  - Region (NA, Europe, Asia)
  - Prior therapy (Yes, No)
  
  Use Cox PH model per subgroup. Report overall HR and subgroup-specific
  HRs with 95% CI. Compute interaction p-values.
inputs:
  - dataset: adtte_adam + adsl_adam
  - specification: "Subgroup analysis per SAP, Cox PH model"
expected_output:
  type: structured result (forest plot data)
  format: JSON with overall HR, subgroup HRs, interaction p-values
ground_truth_method: R (survival::coxph) + Python (rate-ratio approximation)
scoring:
  exact_match_weight: 0.5
  functional_equiv_weight: 0.5
  partial_credit: yes
  tolerance: HR ±0.05, CI ±0.1
estimated_human_time: 15 min
estimated_agent_time_reference: 8 min
contamination_risk: low
parametrizable_params: [seed, n_subjects, hazard_ratio, subgroup_distribution]
```

**Auto-scoring rules:**
- HR within ±0.05 of ground truth (R survival::coxph reference)
- CI bounds within ±0.1
- All 11 subgroups must be present
- Interaction p-values within ±0.01
- CI lower < HR < CI upper ordering enforced

---

### TC-013: Waterfall Plot — Best % Change in Tumor Size

```yaml
id: TC-013
level: 1
domain: efficacy (oncology)
statistical_methods: [RECIST 1.1 response categorization]
data_requirements:
  format: ADaM (ADRS or custom)
  source: synthetic (seed-controlled)
  n_subjects: 150 (75 per arm)
n_variants: 10
description: |
  Compute best percentage change from baseline in tumor size (sum of
  longest diameters) for each subject. Categorize per RECIST 1.1:
  - CR: -100%
  - PR: >= -30% decrease
  - PD: >= +20% increase
  - SD: neither PR nor PD
  
  Compute ORR (CR+PR), DCR (CR+PR+SD), median best % change.
  Sort subjects by best % change for waterfall plot.
inputs:
  - dataset: tumor_response_data (ADRS or custom)
  - specification: "Waterfall plot data per RECIST 1.1"
expected_output:
  type: structured result (waterfall plot data)
  format: JSON with subjects array (sorted), summary stats
ground_truth_method: Python + R (cross-validated)
scoring:
  exact_match_weight: 0.6
  functional_equiv_weight: 0.4
  partial_credit: yes
  tolerance: pct ±1.0%, counts exact
estimated_human_time: 10 min
estimated_agent_time_reference: 5 min
contamination_risk: low
parametrizable_params: [seed, n_subjects, response_rate_distribution]
```

**Auto-scoring rules:**
- Response category counts (CR/PR/SD/PD) must match exactly
- ORR and DCR within ±1.0%
- Individual subject BESTPCHG within ±1.0%
- Sorting order must be ascending by BESTPCHG
- RECIST 1.1 thresholds (-30%, +20%) must be correctly applied

---

### TC-014: Listing of Key Protocol Deviations

```yaml
id: TC-014
level: 1
domain: reporting
statistical_methods: [data listing, categorization]
data_requirements:
  format: ADaM (ADPD or custom)
  source: synthetic (seed-controlled)
  n_subjects: 200 (100 per arm)
n_variants: 10
description: |
  Generate a listing of key protocol deviations with:
  - Subject ID, treatment arm, deviation category, description,
    study day, date, severity
  - Categories: Eligibility, Visit Window, Prohibited Medication,
    Dose Modification, Consent, Endpoint Deviation
  - Severity: Critical, Major, Minor
  - Sorted by subject ID
  
  Compute summary statistics: n subjects with PDs, n total PDs,
  breakdown by category and severity.
inputs:
  - dataset: protocol_deviation_data (ADPD or custom)
  - specification: "PD listing sorted by subject, summary by category"
expected_output:
  type: listing
  format: JSON with listing array + summary stats
ground_truth_method: Python + R (cross-validated)
scoring:
  exact_match_weight: 0.8
  functional_equiv_weight: 0.2
  partial_credit: yes
  tolerance: exact match for counts, category names
estimated_human_time: 15 min
estimated_agent_time_reference: 5 min
contamination_risk: low
parametrizable_params: [seed, n_subjects, pd_rate, severity_distribution]
```

**Auto-scoring rules:**
- Listing must be sorted by USUBJID
- PD category codes must match standard taxonomy
- Summary counts must match exactly
- Severity classification must be consistent with data
- All PD subjects must appear in listing

---

## 5. Level 1 Test Cases — Expansion II (TC-015 through TC-018)

> **Added:** 2026-06-21 (Day 21). Four new Level 1 test cases expanding TFL type
> coverage to include KM curve figures, exposure tables, lab shift tables, and
> longitudinal change-from-baseline tables.

### TC-015: Kaplan-Meier Curve with Risk Table

```yaml
id: TC-015
name: KM Curve with Risk Table
level: 1
domain: Efficacy
tfl_type: Figure
description: |
  Generate a Kaplan-Meier survival curve with 95% CI and risk table at
  specified time points. The agent must produce survival probabilities,
  confidence intervals, and numbers at risk at each time point, for each
  treatment arm.
input_data: ADTTE (time-to-event)
output_format: JSON with curve coordinates + risk table
params:
  seed: random seed for data generation
  n_subjects: number of subjects (default 200)
  time_points: [0, 3, 6, 9, 12, 15, 18, 21, 24, 30]
ground_truth_method: Python + R (cross-validated)
scoring:
  survival_prob_tolerance: 0.01 absolute
  n_at_risk_tolerance: ±2 (censoring order)
  logrank_tolerance: 0.05 chi-square
  weight: curve 50%, risk table 20%, log-rank 20%, median 10%
estimated_human_time: 10 min
contamination_risk: low
parametrizable_params: [seed, n_subjects, time_points, event_rate, censoring_rate]
```

### TC-016: Exposure Summary Table

```yaml
id: TC-016
name: Exposure Summary Table
level: 1
domain: Safety
tfl_type: Table
description: |
  Summarize treatment exposure metrics per arm: treatment duration (weeks),
  cumulative dose (mg), dose intensity (%), and dose reduction rates.
  Includes mean, SD, median, Q1, Q3, min, max for continuous; n(%) for
  categorical.
input_data: Custom exposure dataset (ADCM-derived)
output_format: JSON with summary stats per arm per metric
params:
  seed: random seed
  n_subjects: default 200
  duration_mean_exp: 48 weeks
  duration_mean_ctl: 28 weeks
ground_truth_method: Python + R (cross-validated)
scoring:
  continuous_tolerance: ±0.5 for duration, ±50 for cumdose, ±1% for intensity
  categorical_tolerance: ±2 subjects for dose reduction counts
  weight: duration 25%, cumdose 20%, intensity 25%, reduction 25%, N 5%
estimated_human_time: 15 min
contamination_risk: low
parametrizable_params: [seed, n_subjects, duration_means, adherence_range, dose_reduction_rates]
```

### TC-017: Laboratory Shift Table

```yaml
id: TC-017
name: Laboratory Shift Table
level: 1
domain: Safety
tfl_type: Table
description: |
  Generate a 3×3 shift table showing baseline lab category (LOW/NORMAL/HIGH)
  vs worst post-baseline lab category. Includes overall, per-arm, and by-visit
  summaries. Uses Hemoglobin as the reference lab test.
input_data: ADLB (lab data — baseline + 3 post-baseline visits)
output_format: JSON with 3×3 shift counts + percentages per block
params:
  seed: random seed
  n_subjects: default 200
  lab_test: Hemoglobin (g/L)
  thresholds: LOW < 120, HIGH > 160
  n_post_baseline: 3 visits
ground_truth_method: Python + R (cross-validated)
scoring:
  shift_count_tolerance: ±2 per cell (borderline value classification)
  summary_count_tolerance: ±2
  percentage_tolerance: ±1 pp
  weight: shift cells 40%, summary 25%, percentages 20%, N 15%
estimated_human_time: 10 min
contamination_risk: low
parametrizable_params: [seed, n_subjects, lab_test, thresholds, treatment_effect]
```

### TC-018: Change from Baseline Table

```yaml
id: TC-018
name: Change from Baseline Table
level: 1
domain: Efficacy
tfl_type: Table
description: |
  Generate a longitudinal change-from-baseline table at each visit (baseline,
  Week 6, 12, 18, 24). Per arm per visit: n, mean, SD, median change, SE,
  95% CI, and between-arm t-test p-value.
input_data: Longitudinal efficacy (tumor size, mm)
output_format: JSON with visit-wise summaries + p-values
params:
  seed: random seed
  n_subjects: default 200
  visits: [BASELINE, WEEK_6, WEEK_12, WEEK_18, WEEK_24]
  endpoint: Tumor Size (mm)
  treatment_effect: -0.8 mm/week (exp) vs -0.1 mm/week (ctl)
ground_truth_method: Python + R (cross-validated)
scoring:
  mean_chg_tolerance: ±0.5 mm
  sd_chg_tolerance: ±0.5 mm
  ci_tolerance: ±1.0 mm
  p_value_tolerance: ±0.01
  weight: mean 25%, sd 15%, median 10%, CI 15%, p-value 20%, N 15%
estimated_human_time: 15 min
contamination_risk: low
parametrizable_params: [seed, n_subjects, visits, endpoint, treatment_effect_per_week, baseline_mean]
```

---

## 5. Level 2 Test Cases (Detailed)

### TC-004: SAP Section Drafting

```yaml
id: TC-004
title: "Draft SAP section for primary efficacy analysis"
level: 2
domain: design
statistical_methods: [group sequential design, log-rank test, estimands]
data_requirements:
  format: Protocol + SAP template
  source: synthetic protocol
  n_subjects: N/A (design task)
n_variants: 10
description: |
  Given a synthetic Phase III oncology protocol (two-arm, randomized,
  double-blind), draft the "Primary Efficacy Analysis" section of the
  SAP. The section must include:
  - Estimand specification (5 attributes per ICH E9(R1))
  - Primary endpoint definition (PFS per RECIST 1.1)
  - Statistical method (stratified log-rank test)
  - Multiplicity adjustment (O'Brien-Fleming group sequential boundaries)
  - Missing data handling strategy
  - Analysis population definitions (ITT, mITT, PP)
  
  The agent must correctly implement the O'Brien-Fleming spending function
  and specify the information fraction for the interim analysis.
inputs:
  - specification: "Phase III protocol synopsis with treatment arms and endpoints"
expected_output:
  type: section
  format: Structured Markdown with ICH E3-compliant section numbering
ground_truth_method: Manual review (checklist-based scoring)
scoring:
  exact_match_weight: 0.0
  functional_equiv_weight: 1.0
  partial_credit: yes
estimated_human_time: 120 min
estimated_agent_time_reference: 15 min
contamination_risk: high
parametrizable_params: [trial_phase, n_arms, endpoint_type, interim_timing]
```

---

### TC-005: TFL QC Review

```yaml
id: TC-005
title: "QC review of a TFL package (3 tables, 2 figures, 1 listing)"
level: 2
domain: reporting
statistical_methods: [QC methodology, cross-table verification]
data_requirements:
  format: TFL output package (JSON/RTF) + SAP
  source: pre-generated with seeded errors
  n_subjects: 200
n_variants: 15
description: |
  Review a pre-generated TFL package containing:
  - Table 1: Baseline demographics (with 2 seeded errors)
  - Table 2: Efficacy summary (with 1 seeded error)
  - Table 3: Safety summary (with 3 seeded errors)
  - Figure 1: KM curve (with 1 seeded error)
  - Figure 2: Forest plot (no errors)
  - Listing 1: Protocol deviations (with 1 seeded error)
  
  The agent must identify and classify each error using the 3-class
  severity taxonomy (A/B/C). Total: 8 seeded errors across 6 TFLs.
inputs:
  - tfl_package: 6 TFL outputs with seeded errors
  - sap: matching SAP for reference
  - error_catalog: ground truth error locations (hidden from agent)
expected_output:
  type: report
  format: JSON with error_id, location, severity, description
ground_truth_method: Auto (pre-seeded error catalog)
scoring:
  exact_match_weight: 0.6
  functional_equiv_weight: 0.4
  partial_credit: yes
estimated_human_time: 30 min
estimated_agent_time_reference: 8 min
contamination_risk: medium
parametrizable_params: [seed, error_types, error_locations, n_errors]
```

---

### TC-006: Sample Size Re-Estimation at Interim

```yaml
id: TC-006
title: "Sample size re-estimation based on interim data"
level: 2
domain: design
statistical_methods: [conditional power, sample size re-estimation, group sequential]
data_requirements:
  format: ADaM (ADTTE) — interim dataset (50% information)
  source: synthetic
  n_subjects: 200 (interim), re-estimation target
n_variants: 10
description: |
  Given interim data from a Phase III trial at 50% information fraction:
  - Compute observed hazard ratio at interim
  - Compute conditional power for 3 assumed HR scenarios (observed, null, alternative)
  - Recommend sample size re-estimation (increase, maintain, or stop for futility)
  - Implement the pre-planned Cui-Hung-Wang (CHW) method
  
  The agent must correctly implement the CHW sample size re-estimation
  formula and provide a recommendation with justification.
inputs:
  - dataset: interim_adtte (50% events)
  - specification: "CHW method per SAP, alpha-spending O'Brien-Fleming"
expected_output:
  type: code + recommendation
  format: JSON with observed HR, conditional powers, recommended N
ground_truth_method: R (gsDesign) + expert review
scoring:
  exact_match_weight: 0.4
  functional_equiv_weight: 0.6
  partial_credit: yes
estimated_human_time: 45 min
estimated_agent_time_reference: 10 min
contamination_risk: medium
parametrizable_params: [seed, interim_fraction, true_hr, alpha_spending]
```

---

## 6. Level 3 Test Cases (Expert Review)

### TC-007: Regulatory Response — ITT/PP Discrepancy

```yaml
id: TC-007
title: "Draft regulatory response addressing ITT/PP discrepancy"
level: 3
domain: regulatory
statistical_methods: [tipping point analysis, sensitivity analysis, estimands]
data_requirements:
  format: ADaM (ADSL, ADTTE) + regulatory question
  source: synthetic
  n_subjects: 300
n_variants: 8
description: |
  FDA requests explanation for why ITT analysis (HR=0.72, p=0.018)
  shows significant treatment effect but PP analysis (HR=0.81, p=0.089)
  does not. The agent must:
  1. Identify the drivers of the ITT/PP discrepancy
  2. Conduct tipping point analysis
  3. Provide sensitivity analyses (multiple imputation, pattern mixture)
  4. Draft a regulatory response letter (max 3 pages)
  
  The response must be consistent with ICH E9(R1) estimand framework
  and FDA guidance on missing data.
inputs:
  - dataset: adsl + adtte with protocol deviations
  - specification: "FDA information request on ITT/PP discrepancy"
expected_output:
  type: report
  format: regulatory letter (Markdown) + analysis results (JSON)
ground_truth_method: Expert review (3 biostatisticians)
scoring:
  exact_match_weight: 0.0
  functional_equiv_weight: 1.0
  partial_credit: yes
estimated_human_time: 180 min
estimated_agent_time_reference: 20 min
contamination_risk: high
parametrizable_params: [seed, itt_hr, pp_hr, n_protocol_deviations]
```

---

### TC-008: Dose-Finding Study Design

```yaml
id: TC-008
title: "Design a Phase I dose-finding study with expansion cohort"
level: 3
domain: design
statistical_methods: [CRM, BOIN, EWOC, simulation]
data_requirements:
  format: DLT rates per dose level (historical)
  source: synthetic historical data
  n_subjects: N/A (design task)
n_variants: 6
description: |
  Design a Phase I dose-finding study for a novel oncology agent:
  - Select dose-escalation method (CRM, BOIN, or EWOC)
  - Define dose levels (5-7 levels) with DLT rate assumptions
  - Specify stopping rules
  - Design expansion cohort at recommended Phase 2 dose (RP2D)
  - Simulate operating characteristics (1000 trials)
  
  The agent must produce simulation-based operating characteristics:
  - Probability of selecting each dose as RP2D
  - Expected number of DLTs
  - Expected sample size
inputs:
  - specification: "Phase I protocol synopsis, DLT rates from preclinical"
expected_output:
  type: design document + simulation results
  format: Markdown + JSON (simulation OCs)
ground_truth_method: Expert review + simulation verification
scoring:
  exact_match_weight: 0.0
  functional_equiv_weight: 1.0
  partial_credit: yes
estimated_human_time: 240 min
estimated_agent_time_reference: 30 min
contamination_risk: high
parametrizable_params: [dlt_rates, n_doses, target_dlt_rate, method]
```

---

### TC-009: Safety Signal Evaluation / DMC Report

```yaml
id: TC-009
title: "Evaluate safety signals and draft DMC recommendation"
level: 3
domain: safety
statistical_methods: [safety monitoring, Bayesian signal detection, group sequential]
data_requirements:
  format: ADaM (ADAE, ADLB, ADVS, ADSL)
  source: synthetic with planted safety signals
  n_subjects: 500
n_variants: 8
description: |
  Review interim safety data and draft a DMC recommendation:
  - Identify potential safety signals using Bayesian and frequentist methods
  - Evaluate hepatotoxicity signals (Hy's Law cases)
  - Assess cardiovascular risk (QTc prolongation)
  - Compare event rates across treatment arms with Fisher's exact test
  - Draft DMC recommendation (continue, modify, stop)
inputs:
  - dataset: adae + adlb + advs + adsl (interim)
  - specification: "DMC charter, safety monitoring plan"
expected_output:
  type: report
  format: DMC recommendation letter (Markdown) + signal analysis (JSON)
ground_truth_method: Expert review (safety physician + biostatistician)
scoring:
  exact_match_weight: 0.0
  functional_equiv_weight: 1.0
  partial_credit: yes
estimated_human_time: 480 min
estimated_agent_time_reference: 30 min
contamination_risk: high
parametrizable_params: [seed, signal_types, signal_magnitudes, interim_fraction]
```

---

### TC-010: CSR Statistical Sections

```yaml
id: TC-010
title: "Draft CSR statistical sections (Sections 11-16)"
level: 3
domain: reporting
statistical_methods: [CSR authoring, ICH E3, multiple analyses]
data_requirements:
  format: Full ADaM package + SAP + protocol
  source: synthetic (complete trial data)
  n_subjects: 400
n_variants: 6
description: |
  Draft the statistical sections of a Clinical Study Report (ICH E3):
  - Section 11: Study population (disposition, protocol deviations)
  - Section 12: Efficacy evaluation (primary + secondary endpoints)
  - Section 13: Safety evaluation (AEs, labs, vital signs)
  - Section 14: Tables, figures, listings (TFL listing)
  - Section 15: Appendix (individual patient data listings)
  - Section 16: Supplemental (exploratory analyses)
  
  Each section must follow ICH E3 structure, include proper references
  to TFLs, and maintain narrative consistency.
inputs:
  - dataset: full ADaM suite
  - sap: completed SAP
  - protocol: completed protocol
expected_output:
  type: report
  format: CSR sections (Markdown) per ICH E3
ground_truth_method: Expert review (medical writer + biostatistician)
scoring:
  exact_match_weight: 0.0
  functional_equiv_weight: 1.0
  partial_credit: yes
estimated_human_time: 480 min
estimated_agent_time_reference: 45 min
contamination_risk: high
parametrizable_params: [trial_phase, therapeutic_area, n_endpoints]
```

---

## 7. Test Case Distribution Matrix

| Test Case | Level | Domain | Statistical Methods | Scoring Type | Ground Truth | Param. Variants | Est. Human Time |
|---|---|---|---|---|---|---|---|
| TC-001: KM Median PFS | 1 | Efficacy | KM estimation | Auto (numerical) | R+Py ✅ | 10 | 5 min |
| TC-002: Demographics Table | 1 | Reporting | Descriptive stats | Auto (tabular) | R+Py ✅ | 8 | 10 min |
| TC-003: Stratified Log-Rank | 1 | Efficacy | Log-rank, stratification | Auto (numerical) | R+Py ✅ | 12 | 5 min |
| TC-011: AE Summary Table | 1 | Safety | AE tabulation, SOC/PT | Auto (tabular) | R+Py ✅ | 10 | 20 min |
| TC-012: Forest Plot HRs | 1 | Efficacy | Cox PH, subgroup analysis | Auto (numerical) | R+Py ✅ | 10 | 15 min |
| TC-013: Waterfall Plot | 1 | Efficacy (onc.) | RECIST 1.1 categorization | Auto (tabular) | R+Py ✅ | 10 | 10 min |
| TC-014: PD Listing | 1 | Reporting | Data listing, categorization | Auto (listing) | R+Py ✅ | 10 | 15 min |
| TC-015: KM Curve + Risk Table | 1 | Efficacy | KM curve, risk sets, CI | Auto (curve+counts) | R+Py ✅ | 10 | 10 min |
| TC-016: Exposure Summary | 1 | Safety | Descriptive, dose metrics | Auto (tabular) | R+Py ✅ | 8 | 15 min |
| TC-017: Lab Shift Table | 1 | Safety | Categorical shift, 3×3 | Auto (tabular) | R+Py ✅ | 8 | 10 min |
| TC-018: Change from Baseline | 1 | Efficacy | Longitudinal, CFB, t-test | Auto (tabular) | R+Py ✅ | 10 | 15 min |
| TC-004: SAP Section | 2 | Design | GS design, log-rank, estimands | Checklist | — | 10 | 120 min |
| TC-005: TFL QC Review | 2 | Reporting | QC, discrepancy detection | Partial auto | — | 15 | 30 min |
| TC-006: Sample Size Re-Est. | 2 | Design | Conditional power, SSR | Auto + rubric | — | 10 | 45 min |
| TC-007: Reg. Response ITT/PP | 3 | Regulatory | Tipping point, sensitivity | Expert rubric | — | 8 | 180 min |
| TC-008: Dose-Finding Design | 3 | Design | Bayesian, OCs, simulation | Expert rubric | — | 6 | 240 min |
| TC-009: Safety/DMC Report | 3 | Safety | Safety monitoring, signal detection | Expert rubric | — | 8 | 480 min |
| TC-010: CSR Section | 3 | Reporting | CSR writing, ICH E3 | Expert rubric | — | 6 | 480 min |

**Coverage Summary:**
- **Domains:** Efficacy (5), Design (2), Reporting (4), Safety (4), Regulatory (1), Cross-cutting (1)
- **Levels:** Level 1 (11), Level 2 (3), Level 3 (4)
- **Auto-scorable:** 11 (Level 1) + 1 partial (Level 2)
- **Expert-review needed:** 3 (Level 2) + 4 (Level 3)
- **Ground truth implemented:** 11 (TC-001 through TC-003, TC-011 through TC-018)
- **Total parametrizable variants:** 179 across all test cases

---

## 7. Data Generation Strategy

### 7.1 Synthetic Dataset Specifications

Each test case needs reproducible synthetic data. The generation strategy:

| Test Case | Data Required | Generation Method | Random Seed |
|---|---|---|---|
| TC-001 | ADTTE dataset | `random.cdisc.data::radtte()` with custom parameters | Parametrized per variant |
| TC-002 | ADSL dataset | `random.cdisc.data::radsl()` | Parametrized per variant |
| TC-003 | ADTTE dataset | `random.cdisc.data::radtte()` + custom event rates | Parametrized per variant |
| TC-004 | None (design spec) | N/A | N/A |
| TC-005 | ADSL, ADTTE, ADLB, ADAE | `random.cdisc.data::radsl/adtte/adlb/adae()` | Fixed seed per variant |
| TC-006 | Partial enrollment + events | `simstudy::simstudy()` for staggered enrollment | Parametrized per variant |
| TC-007 | ADSL, ADTTE with seeded PP exclusions | Custom simulation w/ `simstudy` | Fixed seed per variant |
| TC-008 | Historical trial summary | Synthetic summary stats | Fixed seed |
| TC-009 | ADSL, ADAE, ADLB, ADVS | `random.cdisc.data` + custom AE rates | Fixed seed per variant |
| TC-010 | Full ADaM suite | `random.cdisc.data` family | Fixed seed per variant |

### 7.2 Reproducibility Rules

1. **Every test case variant** must be fully reproducible by R code in `references/ground-truth/`
2. **Seeds** must be documented in the variant metadata
3. **Variant parameters** must produce meaningfully different scenarios (different censorship rates, effect sizes, etc.)
4. **A no-data-needed label** must be recorded for test cases that are purely specification-based (TC-004)

---

## 8. Contamination Mitigation

| Strategy | Applied To | Mechanism |
|---|---|---|
| **Parametric variants** | All TC except TC-004, TC-008 | Each run samples a different parameter set |
| **Seed randomization** | All data-generating TCs | Seed = function of variant ID + run date |
| **Error injection randomization** | TC-005 | Error types and locations randomly sampled from pool |
| **Variable renaming** | TC-001, TC-002, TC-003 | Column names standardized to ADaM but seed-dependent |
| **Structural perturbation** | TC-009 | AE distribution parameters vary across variants |
| **Held-out variants** | All | 20% of variants reserved for final validation only |

---

## 9. Scoring Automation Feasibility

| Test Case | Auto-Score Feasibility | Method | Tooling Required |
|---|---|---|---|
| TC-001 | ✅ Full | Numerical comparison + JSON output | R `testthat` + Python `pytest` |
| TC-002 | ✅ Full | Tabular comparison (categorical match) | R `testthat` + `arsenal` |
| TC-003 | ✅ Full | Numerical comparison + method check | R `testthat` |
| TC-004 | ⚠️ Partial | Checklist via GPT-as-judge + human verification | PromptFoo / DeepEval |
| TC-005 | ✅ Full | Pre-seeded error catalog matching | Python script |
| TC-006 | ⚠️ Partial | Numerical check for SSR + rubric for recommendation | R + human review |
| TC-007 | ❌ Expert only | Expert review rubric | Human panel |
| TC-008 | ❌ Expert only | Expert review rubric + simulation run check | Human panel + R |
| TC-009 | ⚠️ Partial | Auto-checks for tables + signal detection + expert for narrative | Python + human |
| TC-010 | ❌ Expert only | Expert review + ICH E3 checklist | Human panel |

---

## 10. Next Steps

1. **WG Review:** Present TC-001 through TC-010 to the WG for feedback on:
   - Clinical realism
   - Difficulty calibration (are Level 3 tasks appropriately hard?)
   - Missing domains or methods
   - Scoring preferences

2. **Implement ground truth:** For auto-scorable TCs (TC-001 through TC-003, TC-005, TC-006 partial), create verified R reference implementations in `references/ground-truth/`

3. **Build data generation pipeline:** Create R scripts using `random.cdisc.data` and `simstudy` to generate synthetic datasets for all parametrizable variants

4. **Develop scoring harness:** Start with the 3 auto-scorable Level 1 test cases (TC-001, TC-002, TC-003) as the pilot evaluation

5. **Human baseline study:** Recruit 2-3 WG biostatisticians to complete TC-001 through TC-003 and record time/accuracy as the human performance baseline

---

## Level 1 Extension: TC-019 through TC-021

### TC-019: Concomitant Medications Summary
| Field | Value |
|---|---|
| **Domain** | Safety |
| **TFL Type** | Table |
| **Statistical Method** | Descriptive summary (counts + percentages by ATC class and medication) |
| **Description** | Concomitant medications summary by treatment arm, sorted by ATC class |
| **ADaM Dataset** | ADCM |
| **Output Fields** | summary_rows, detailed_rows (atc_class, medication, n, pct per arm) |
| **Scoring** | Tolerance-based (exact n, ±0.1 pct) |
| **Languages** | R + Python + SAS |
| **Cross-language Score** | 1.0000 (Day 30) |

### TC-020: ORR by Subgroup
| Field | Value |
|---|---|
| **Domain** | Efficacy |
| **TFL Type** | Table |
| **Statistical Method** | Binomial proportion (ORR) by subgroup with CMH interaction test |
| **Description** | Objective Response Rate (CR+PR) by subgroup (SEX, AGEGR1, ECOG) with 95% CI and interaction p-values |
| **ADaM Dataset** | ADVS (tumor response) |
| **Output Fields** | overall ORR, subgroup ORRs, CI bounds, ORR difference, CMH p-values |
| **Scoring** | Tolerance-based (±0.1 pct, exact n) |
| **Languages** | R + Python + SAS |
| **Cross-language Score** | 1.0000 (Day 30) |

### TC-021: Time-to-Progression (TTP) KM Median
| Field | Value |
|---|---|
| **Domain** | Efficacy |
| **TFL Type** | Table |
| **Statistical Method** | Kaplan-Meier TTP estimation with 95% CI (death censored) |
| **Description** | Time from randomization to first documented disease progression; death is censored (unlike PFS which counts death as an event) |
| **ADaM Dataset** | ADTTE (PARAM = "Time to Progression") |
| **Output Fields** | median_ttp, ci_lower, ci_upper, n_events, n_total, estimable |
| **Scoring** | Tolerance-based (same as TC-001) |
| **Languages** | R + Python + SAS |
| **Cross-language Score** | 1.0000 (Day 30) |
| **Compliance Rules** | TCG: death censoring documented; CSR: TTP vs PFS distinction stated |
| **Safety Rules** | TTP events ≤ PFS events (PFS includes death); N-count consistency with TC-001 |
| **Differentiation** | Tests censoring rule knowledge: death is censored for TTP, event for PFS |
| **ARS Envelope** | ✅ Available (--ars-output flag) |

### TC-021 Differentiation from TC-001
TC-021 uses the same KM methodology as TC-001 but with a different event definition:
- **PFS (TC-001):** Event = disease progression OR death (whichever comes first)
- **TTP (TC-021):** Event = disease progression only (death censored)

This tests whether the agent correctly handles censoring rules — a common source of programming errors in oncology trials.

### TC-022: Duration of Response (DOR) KM Median

| Field | Value |
|---|---|
| **Domain** | Efficacy |
| **TFL Type** | Table |
| **Statistical Method** | Kaplan-Meier DOR estimation with 95% CI among responders |
| **Description** | Time from first documented response (CR or PR) to disease progression or death, among subjects who achieved a response |
| **ADaM Dataset** | ADTTE (with PARAM = "Duration of Response", filtered to responders) |
| **Key Variables** | AVAL, CNSR, TRT01PN, TRT01A, BOR, IS_RESPONDER |
| **Output Fields** | median_dor, ci_lower, ci_upper, n_responders, n_events, n_total, estimable |
| **Scoring** | Tolerance-based (same structure as TC-021) |
| **Languages** | R + Python (+ SAS planned) |
| **Variants** | 5 (seed variation, response thresholds, N) |
| **Compliance Rules** | TCG: responder population definition; CSR: DOR population footnote |
| **Safety Rules** | n_responders ≤ n_total (from TC-020), responder subset consistency |
| **ARS Output** | ✅ `--ars-output` flag with ARS v1.0 envelope |
| **Cross-language Score** | 1.0000 (verified Day 31) |

### TC-022 Differentiation from TC-001/021
DOR is calculated only among responders (CR+PR), testing:
1. Correct subsetting to responder population
2. KM estimation on a selected subset (not the full ITT)
3. Handling of left truncation (response occurs after randomization)

- **PFS (TC-001):** All subjects, event = progression OR death
- **TTP (TC-021):** All subjects, event = progression only (death censored)
- **DOR (TC-022):** Responders only, event = progression OR death
