# TC-006 Detailed Specification — Sample Size Re-Estimation at Interim (Level 2)

**Date:** 2026-07-07 (Day 38)
**Status:** Draft for WG Review
**Level:** 2 (Multi-step, moderately ambiguous, partial auto-scoring)

---

## Overview

TC-006 evaluates an AI agent's ability to perform a blinded sample size re-estimation (SSR) at an interim analysis point. This is a common DMC request during ongoing Phase 3 trials when the observed event rate differs from design assumptions. The agent must:

1. Estimate the pooled event rate from blinded interim data
2. Re-estimate required sample size under multiple HR scenarios
3. Assess conditional power at the current information fraction
4. Produce a structured recommendation (continue / increase / futility)
5. Document all assumptions and limitations

This test case bridges Level 1 (numerical computation) and Level 3 (regulatory judgment). The statistical methods are well-defined (gsDesign, PROC SEQDESIGN), but the recommendation requires interpretation and context.

---

## Design Parameters

### Trial Design
| Parameter | Value |
|---|---|
| **Indication** | First-line metastatic NSCLC |
| **Primary endpoint** | Progression-Free Survival (PFS) |
| **Design** | 1:1 randomization, active control, superiority |
| **Planned enrollment** | 600 patients (300 per arm) |
| **Original assumptions** | Median PFS control = 6 months, HR = 0.75, 90% power, 2-sided α = 0.05 |
| **Required events (original)** | 127 (using Schoenfeld formula, 90% power, 2-sided α=0.05) |
| **Interim analysis** | Blinded SSR at 200 enrolled, 120 events observed |

### Interim Data
| Metric | Value |
|---|---|
| **Enrolled** | 200 / 600 (33.3%) |
| **Events observed** | 120 (both arms pooled) |
| **Pooled median PFS** | 5.2 months (95% CI: 4.6–5.9) |
| **Information fraction** | 120/127 = 94.5% |
| **Accrual rate** | ~20 patients/month |
| **Event rate (observed)** | ~12 events/month (pooled) |

### Variant Parameters (10 variants)

| Variant | Pooled median PFS | Events observed | Enrolled | Accrual rate | Original HR |
|---|---|---|---|---|---|
| v1 (base) | 5.2 | 120 | 200 | 20/mo | 0.75 |
| v2 | 4.8 | 135 | 220 | 22/mo | 0.75 |
| v3 | 5.5 | 110 | 180 | 18/mo | 0.75 |
| v4 | 5.0 | 125 | 200 | 20/mo | 0.80 |
| v5 | 5.2 | 120 | 200 | 20/mo | 0.70 |
| v6 | 4.5 | 140 | 230 | 25/mo | 0.75 |
| v7 | 6.0 | 100 | 170 | 15/mo | 0.75 |
| v8 | 5.2 | 150 | 250 | 20/mo | 0.75 |
| v9 | 4.9 | 130 | 210 | 21/mo | 0.80 |
| v10 | 5.3 | 115 | 195 | 19/mo | 0.75 |

---

## Agent Task

The agent receives:
1. `interim_data.csv` — blinded enrollment and event data (pooled, no arm breakdown)
2. `design_parameters.json` — original trial design assumptions
3. `dmc_request.md` — DMC request letter asking for blinded SSR

The agent must produce a structured report (markdown) containing:

### Required Output Sections

1. **Current Status Summary** — enrollment %, events observed, information fraction
2. **Blinded Event Rate Estimation** — pooled median PFS, estimated control median (deconvolution), event rate
3. **Revised Sample Size Estimates** — table with 3 HR scenarios (0.70, 0.75, 0.80)
4. **Conditional Power Assessment** — at current info fraction under 3 scenarios
5. **Recommendation** — continue / increase N / consider futility, with rationale
6. **Assumptions and Limitations** — blinded analysis assumptions, limitations

### Output Format

```markdown
## Sample Size Re-Estimation Report

### Current Status
- Enrolled: XXX / 600 (XX.X%)
- Events observed: XXX
- Information fraction: XX.X%

### Blinded Event Rate Estimation
- Pooled median PFS: X.X months
- Estimated control median: X.X months
- Estimated event rate: XX.X events/month

### Revised Sample Size Estimates
| Scenario | HR | Events Needed | Total N Needed | Incremental N | Recommendation |
|---|---|---|---|---|---|
| Pessimistic | 0.80 | XXX | XXX | +XX | Increase |
| Original | 0.75 | 331 | 600 | 0 | Continue |
| Optimistic | 0.70 | XXX | XXX | -XX | Consider reduction |

### Conditional Power
At current info fraction (XX.X%):
- Under HR=0.80: XX%
- Under HR=0.75: XX%
- Under HR=0.70: XX%

### Recommendation
[Structured recommendation with rationale]

### Assumptions and Limitations
- Blinded analysis assumes equal allocation and similar event rates across arms
- Deconvolution uses pooled median and design HR to estimate control median
- Conditional power uses current observed effect (not unblinded)
- [...]
```

---

## Ground Truth

### Statistical Methods

1. **Event rate estimation:** Pooled median PFS via Kaplan-Meier (all subjects, blinded)
2. **Control median deconvolution:** Under HR assumption, if pooled median = M_p and HR = h, then:
   - Assuming exponential: 1/M_p = (1/M_control + 1/M_treatment) / 2
   - M_treatment = h × M_control
   - Solve: M_control = M_p × (1 + h) / 2
3. **Sample size re-estimation:** Schoenfeld formula:
   - d = (z_{α/2} + z_{β})² / (ln(h))²
   - N = d / [(1 - exp(-λt)) × (proportion observed)]
4. **Conditional power:** Using gsDesign `ssrCP()` or equivalent:
   - CP = Φ(z_{1-α} √(1-f) - z_{observed} √f) where f = info fraction

### Reference Implementation

**R:** `gsDesign::ssrCP()` for conditional power, `gsDesign::nEvents()` for event re-estimation
**SAS:** `PROC SEQDESIGN` with `DESIGNMETHOD=OBrienFleming` and conditional power
**Python:** Custom implementation using `scipy.stats.norm` for conditional power, Schoenfeld formula for events

### Ground Truth Script

File: `references/ground-truth/R/tc-006-ssr-interim.R`

Computes:
- Pooled KM median from blinded interim data
- Control median deconvolution under 3 HR scenarios
- Revised event counts and sample sizes
- Conditional power at current info fraction
- Structured recommendation logic

---

## Scoring

### Auto-Scored Components (50%)

| Component | Weight | Method | Tolerance |
|---|---|---|---|
| Pooled median PFS | 5% | Exact match | ±0.1 months |
| Estimated control median (3 scenarios) | 10% | Exact match | ±0.2 months |
| Events needed (3 scenarios) | 10% | Exact match | ±5 events |
| Total N needed (3 scenarios) | 10% | Exact match | ±15 subjects |
| Conditional power (3 scenarios) | 10% | Exact match | ±3% |
| Information fraction | 5% | Exact match | ±0.5% |

### LLM-as-Judge Components (30%)

| Component | Weight | Criteria |
|---|---|---|
| Recommendation appropriateness | 10% | Correct recommendation for given scenario |
| Rationale quality | 10% | Statistical reasoning is sound, references specific numbers |
| Assumptions documentation | 5% | Lists key assumptions (blinding, exponential, equal allocation) |
| Limitations discussion | 5% | Acknowledges blinded analysis constraints, deconvolution uncertainty |

### Human Review Components (20%)

| Component | Weight | Criteria |
|---|---|---|
| Regulatory appropriateness | 10% | Follows ICH E9, DMC charter conventions |
| Communication clarity | 5% | Report is clear, actionable for DMC |
| Completeness | 5% | All required sections present, no missing scenarios |

### Scoring Formula

```
total_score = 0.50 × auto_score + 0.30 × llm_judge_score + 0.20 × human_review_score
```

### Tolerances (YAML)

```yaml
TC-006:
  pooled_median_pfs:
    tolerance: 0.1
    unit: months
  control_median:
    tolerance: 0.2
    unit: months
    scenarios: [0.70, 0.75, 0.80]
  events_needed:
    tolerance: 5
    unit: count
    scenarios: [0.70, 0.75, 0.80]
  total_n_needed:
    tolerance: 15
    unit: count
    scenarios: [0.70, 0.75, 0.80]
  conditional_power:
    tolerance: 0.03
    unit: proportion
    scenarios: [0.70, 0.75, 0.80]
  information_fraction:
    tolerance: 0.005
    unit: proportion
```

---

## Contamination Mitigation

- **Parametric variants:** 10 variants with different pooled medians, event counts, and HR assumptions
- **Seed randomization:** Interim data generated with different random seeds per variant
- **Noise injection:** Event times jittered ±10% to prevent exact memorization
- **Scenario shuffling:** HR scenarios presented in different orders across variants

---

## Cross-References

| Related TC | Relationship |
|---|---|
| TC-001 | PFS KM estimation (Level 1 foundation) |
| TC-003 | Stratified log-rank (primary analysis method) |
| TC-004 | SAP drafting (Level 2, same trial context) |
| TC-005 | TFL QC review (Level 2, same TFL ecosystem) |
| TC-007 | Regulatory response (Level 3, could reference SSR results) |

---

## Implementation Status

| Component | Status |
|---|---|
| Spec document | ✅ This file |
| Variant parameters | ✅ 10 variants defined |
| Ground truth R script | ⏳ Pending |
| Ground truth Python script | ⏳ Pending |
| Ground truth SAS script | ⏳ Pending |
| Data generator | ⏳ Pending |
| Auto-scorer | ⏳ Pending |
| End-to-end test | ⏳ Pending |

---

## Next Steps

1. Implement `references/ground-truth/R/tc-006-ssr-interim.R`
2. Implement `references/ground-truth/Python/tc_006_ssr_interim.py`
3. Create interim data generator (blinded enrollment + event data)
4. Add TC-006 scorer to `score.py`
5. Add TC-006 tolerances to `tolerances.yaml`
6. Cross-language verification
