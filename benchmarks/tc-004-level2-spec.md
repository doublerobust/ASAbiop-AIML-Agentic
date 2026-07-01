# TC-004 Detailed Specification — SAP Section Drafting (Level 2)

**Date:** 2026-07-01 (Day 31)
**Status:** Draft for WG Review
**Level:** 2 (Multi-step, moderately ambiguous, partial auto-scoring)

---

## Overview

TC-004 evaluates an AI agent's ability to draft the "Primary Efficacy Analysis" section of a Statistical Analysis Plan (SAP) for a Phase 3 oncology trial. Unlike Level 1 test cases that produce numerical outputs, TC-004 produces a structured prose document that must adhere to ICH E9 and ICH E9(R1) conventions.

This test case bridges the gap between numerical TFL programming (Level 1) and complex regulatory scenarios (Level 3). It tests the agent's understanding of statistical concepts, regulatory frameworks, and its ability to produce coherent, compliant prose.

---

## Design Parameters

### Trial Design
| Parameter | Value |
|---|---|
| **Indication** | First-line metastatic non-small cell lung cancer (NSCLC) |
| **Endpoint** | Overall survival (OS) |
| **Design** | 1:1 randomization, active control, superiority |
| **Sample size** | 600 patients (300 per arm) |
| **Interim analysis** | 1 interim at 60% of target events (199 events) |
| **Final analysis** | At 331 events |
| **Power** | 90% |
| **Target HR** | 0.75 (25% risk reduction) |
| **Two-sided alpha** | 0.05 |
| **Group sequential method** | O'Brien-Fleming spending function |
| **Stratification factors** | PD-L1 expression (≥50%, 1-49%, <1%), ECOG (0, 1) |
| **Primary analysis method** | Stratified log-rank test |
| **Sensitivity analyses** | Unstratified log-rank, Cox PH with strata, RMST |

### Variant Parameters (10 variants)
| Parameter | Options |
|---|---|
| Indication | NSCLC, melanoma, breast cancer, colorectal cancer |
| Endpoint | OS, PFS |
| Sample size | 400, 600, 800, 1000 |
| HR target | 0.70, 0.75, 0.80 |
| Interim timing | 50%, 60%, 70% of events |
| Stratification | PD-L1+ECOG, ECOG+region, PD-L1+histology |

---

## Required Output Structure

The agent must produce a structured document with the following sections, following ICH E9 conventions:

### Section 1: Analysis Population Definition
- ITT population definition (all randomized subjects)
- Handling of subjects who discontinue treatment
- Exclusion criteria for sensitivity populations (per-protocol, as-treated)

### Section 2: Primary Endpoint Definition
- Endpoint specification (OS: time from randomization to death from any cause)
- Estimand specification per ICH E9(R1) with 5 attributes:
  1. **Population:** ITT
  2. **Variable:** OS (time-to-event)
  3. **Intercurrent events:** Treatment switching, death without prior progression (for PFS), loss to follow-up
  4. **Summary measure:** Hazard ratio (stratified log-rank)
  5. **Treatment:** Experimental vs. Active control

### Section 3: Statistical Hypothesis
- H₀: HR = 1 (no difference in OS between arms)
- H₁: HR ≠ 1 (two-sided)
- Significance level: α = 0.05 (two-sided)
- Group sequential adjustment: O'Brien-Fleming alpha spending function

### Section 4: Analysis Method Specification
- Primary: Stratified log-rank test (strata: PD-L1, ECOG)
- Hazard ratio estimation: Cox proportional hazards model with treatment as covariate, stratified by PD-L1 and ECOG
- Confidence intervals: 95% CI for HR
- Assumptions: Proportional hazards (tested via Schoenfeld residuals)

### Section 5: Handling of Intercurrent Events
- Treatment switching: Intention-to-treat principle (no adjustment for switching in primary analysis)
- Death without prior progression: Counted as event for OS
- Loss to follow-up: Censored at last known alive date
- Sensitivity analyses for departures from ITT

### Section 6: Sensitivity and Supplementary Analyses
- Unstratified log-rank test
- Cox PH model with stratification factors as covariates
- Restricted Mean Survival Time (RMST) at fixed time points
- Tipping point analysis for informative censoring
- Per-protocol analysis

### Section 7: Subgroup Analyses (Pre-specified)
- Subgroups by stratification factors (PD-L1, ECOG)
- Subgroups by demographics (age <65 vs ≥65, sex)
- Forest plot presentation
- Interaction tests (treatment × subgroup)

---

## Scoring Rubric

### Auto-Scorable Elements (40% of total)
These elements can be checked programmatically using structured parsing:

| Criterion | Weight | Check Method |
|---|---|---|
| All 7 required sections present | 8% | Section header detection |
| ICH E9(R1) estimand with 5 attributes | 8% | Keyword/structure extraction |
| Hypothesis test correctly stated (H₀, H₁) | 4% | Pattern matching |
| Alpha and power values match design spec | 4% | Numeric extraction |
| Stratified log-rank specified with correct strata | 4% | Keyword matching |
| At least 2 sensitivity analyses listed | 4% | Count analysis methods |
| OBF alpha spending function mentioned | 4% | Keyword matching |
| Subgroup analysis plan with ≥3 subgroups | 4% | Count subgroups |

### LLM-as-Judge Elements (40% of total)
These elements require semantic evaluation:

| Criterion | Weight | Check Method |
|---|---|---|
| ITT population correctly defined | 4% | LLM judge |
| Intercurrent events strategy described (treatment switching, death) | 6% | LLM judge |
| Estimand attributes correctly mapped to ICH E9(R1) | 6% | LLM judge |
| Statistical reasoning is sound and appropriate | 6% | LLM judge |
| Sensitivity analyses are appropriate and justify primary | 4% | LLM judge |
| Multiplicity control mentioned for secondary endpoints | 4% | LLM judge |
| Sample size / futility considerations addressed | 4% | LLM judge |
| E9/E9(R1) terminology used correctly throughout | 6% | LLM judge |

### Human Review Elements (20% of total)
Require expert biostatistician review:

| Criterion | Weight | Check Method |
|---|---|---|
| Clinical relevance of analysis plan | 5% | Expert review |
| Appropriateness of sensitivity analysis selection | 5% | Expert review |
| Clarity and completeness for regulatory submission | 5% | Expert review |
| Consistency with trial design and objectives | 5% | Expert review |

---

## Input Format

```yaml
# TC-004 Input specification
protocol_summary:
  indication: "First-line metastatic NSCLC"
  endpoint: "Overall survival (OS)"
  design: "1:1 randomization, active control, superiority"
  sample_size: 600
  interim_analysis:
    timing: "60% of target events"
    n_events: 199
  final_analysis:
    n_events: 331
  power: 0.90
  target_hr: 0.75
  alpha: 0.05
  group_sequential: "O'Brien-Fleming"
  stratification_factors:
    - "PD-L1 expression (≥50%, 1-49%, <1%)"
    - "ECOG performance status (0, 1)"
  primary_method: "Stratified log-rank test"
  sensitivity_analyses:
    - "Unstratified log-rank"
    - "Cox PH with stratification factors"
    - "RMST"

template: |
  Standard SAP template following ICH E9 structure:
  1. Analysis Population
  2. Primary Endpoint and Estimand
  3. Statistical Hypothesis
  4. Analysis Method
  5. Intercurrent Events
  6. Sensitivity Analyses
  7. Subgroup Analyses
```

---

## Output Validation

### Schema Validation (auto-scorable)
```json
{
  "type": "object",
  "required": ["sections"],
  "properties": {
    "sections": {
      "type": "array",
      "minItems": 7,
      "items": {
        "type": "object",
        "required": ["title", "content"],
        "properties": {
          "title": {"type": "string"},
          "content": {"type": "string", "minLength": 50}
        }
      }
    },
    "estimand": {
      "type": "object",
      "required": ["population", "variable", "intercurrent_events", "summary_measure", "treatment"]
    }
  }
}
```

### Contamination Mitigation
- **Parametric variants:** Each run uses different indication, endpoint, sample size, and HR combinations
- **Seed randomization:** Variant parameters sampled from a pool of 10 configurations
- **Error injection:** Not applicable for prose generation; replaced by missing-section injection
- **Knowledge cutoff:** Agent should reference ICH E9(R1) (2019), not pre-E9(R1) conventions

---

## Implementation Notes

1. **Ground truth:** Expert review by 2+ practicing biostatisticians with oncology SAP experience. Ground truth = consensus SAP section meeting all rubric criteria.

2. **LLM-as-judge configuration:** Use a frontier model (GPT-4o, Claude 3.5 Sonnet) as judge with a structured prompt evaluating each criterion on a 0-1 scale. Judge sees both the agent output and the rubric criteria.

3. **Human review:** 2 reviewers independently score the 20% human-review portion. Inter-rater agreement (Cohen's κ) tracked across runs. Disagreements resolved by consensus.

4. **Estimated times:**
   - Human from scratch: 120 min
   - Human verifying agent output: 15-20 min
   - Agent reference time: 5-10 min

5. **Contamination risk:** Medium. SAP drafting is well-documented in ICH guidelines, but specific design parameter combinations create unique outputs.

---

## Cross-TC Relationships

| Pair | Rule |
|---|---|
| TC-004 ↔ TC-001 | SAP method (stratified log-rank) should match TC-001 ground truth implementation |
| TC-004 ↔ TC-003 | SAP specifies stratified log-rank; TC-003 implements it |
| TC-004 ↔ TC-005 | SAP defines the QC criteria that TC-005 checks against |
| TC-004 ↔ TC-006 | Sample size re-estimation at interim should be mentioned in SAP |

---

## Next Steps

1. Build LLM-as-judge prompt template for auto-scoring
2. Create 10 parametric variants with different design parameters
3. Recruit 2-3 WG biostatisticians for human baseline collection
4. Pilot test with 2-3 frontier models (GPT-4o, Claude 3.5, Gemini 2.5)
5. Finalize scoring weights based on pilot results
