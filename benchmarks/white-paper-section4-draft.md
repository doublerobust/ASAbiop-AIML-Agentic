# Section 4: Scoring Framework — Prose Draft

**Working Document — ASA Biopharm AI/ML Working Group**
**Date:** 2026-06-30 (Day 30)
**Status:** Draft for WG Review

---

## 4.1 Design Philosophy

The scoring framework was designed to answer a question that vendor marketing materials consistently sidestep: *How do we know the AI got the right answer?* In clinical trial statistics, "right" is not a single number — it is a composite of numerical accuracy, regulatory compliance, safety awareness, and operational practicality. A model that produces the correct median PFS but uses non-compliant ADaM variable names, or that takes 47 retries and $200 of API costs to get there, is not a viable replacement for a human statistical programmer.

The framework therefore decomposes "correctness" into four orthogonal dimensions, each independently measurable and weighted into a composite score. This decomposition serves two purposes: (1) it provides actionable diagnostic information — a vendor can see that their agent scores well on accuracy but poorly on compliance, and know exactly where to invest improvement effort; and (2) it prevents compensatory effects from masking critical failures — an agent cannot compensate for wrong hazard ratios with good formatting.

## 4.2 Four Scoring Dimensions

### 4.2.1 Statistical Correctness (Weight: 0.40)

**Definition:** Does the agent's output numerically agree with independently verified ground truth, within pre-specified tolerances?

The statistical correctness dimension is the foundation of the scoring framework. It operates through a field-by-field comparison of the agent's JSON output against ground truth produced in R, Python, and (where available) SAS. Each output field has an independently configured tolerance:

- **Absolute tolerance:** Fields with small expected values (e.g., p-values near 0) use absolute tolerance (±0.001). A p-value of 0.0432 vs. 0.0438 passes; 0.0432 vs. 0.0462 fails.
- **Relative tolerance:** Fields with large expected values (e.g., median survival times) use relative tolerance (±0.1%). A median of 10.54 vs. 10.55 passes; 10.54 vs. 10.63 fails.
- **Exact match:** Integer counts (n_events, n_total) require exact match. An agent reporting 49 events when the ground truth has 50 receives zero credit for that field.
- **Null handling:** Fields that may be non-estimable (e.g., CI bounds when the survival curve never crosses 0.5) use `allow_null: true` — both outputs being null is a match, not a failure.

Each field carries a weight reflecting its clinical importance. The median survival time carries more weight than the CI bounds, which carry more weight than the n_total count. The final statistical correctness score is a weighted average across all fields:

$$S_{\text{stat}} = \frac{\sum_{i} w_i \cdot s_i}{\sum_{i} w_i}$$

where $s_i \in [0, 1]$ is the per-field score (1.0 if within tolerance, 0.0 if not) and $w_i$ is the field weight.

**Cross-language verification** provides a floor on ground truth reliability. Before any agent is scored, the R and Python (and SAS, where available) ground truth implementations are compared against each other on identical shared data. Only test cases where all language pairs achieve a cross-language verification score of 1.0000 are eligible for agent evaluation. As of Day 30, all 14 Level 1 test cases (TC-001 through TC-021) meet this standard.

### 4.2.2 Regulatory Compliance (Weight: 0.25)

**Definition:** Does the agent's code and output conform to CDISC ADaM variable naming conventions, FDA Study Data TCG rules, and ICH E3 CSR formatting standards?

Regulatory compliance is scored through three rule sets totaling 244 individual rules:

- **ADaM Variable Mapping (86 TCG rules):** Verifies that the agent uses correct CDISC variable names (e.g., `TRT01PN` not `treatment_arm`, `AVAL` not `value`, `CNSR` not `censor`). The rules are derived from the FDA Study Data Technical Conformance Guide and CDISC ADaMIG v1.1.
- **TCG Checklist Adherence (128 rules):** Checks output structure, metadata completeness, and format conventions required for FDA submission (e.g., treatment arm ordering, missing value representation, decimal place consistency).
- **CSR Formatting (42 rules):** Verifies that table/figure outputs follow ICH E3 conventions (e.g., confidence intervals formatted as "(lower, upper)", p-values with leading zero, no trailing zeros in percentages).

Each rule is evaluated as pass/fail. The compliance score is the fraction of applicable rules that pass. Rules are tagged by test case, and only rules applicable to a given TC's output type (table vs. figure vs. listing) are evaluated.

### 4.2.3 Safety & Robustness (Weight: 0.20)

**Definition:** Does the agent demonstrate awareness of clinical trial data integrity rules and handle edge cases without producing misleading results?

The safety dimension addresses a critical gap in pure numerical scoring: an agent could produce the right numbers while violating fundamental clinical trial logic. The safety dimension enforces four categories of checks:

- **N-count consistency (42 rules):** Subject counts must be consistent across TFLs within the same submission. If the demographics table reports N=200 for the ITT population, the KM table for the same population must also report N=200. Inconsistencies trigger a safety flag.
- **Denominator validation (11 TCs):** Percentage denominators must match the analysis population. An agent computing "50/107 = 46.7%" for the experimental arm ITT must use 107 (the ITT N for that arm) as the denominator, not 200 (total subjects) or 100 (a rounding artifact).
- **Cross-TFL agreement (14 pairs):** Statistics that appear in multiple TFLs must agree. The KM median in TC-001 should be consistent with the KM curve in TC-015. The hazard ratio in TC-012 should be consistent with the log-rank p-value in TC-003.
- **Edge case handling (16 scenarios):** The agent must correctly handle: empty treatment arms, non-estimable medians (survival never crosses 0.5), zero-event cells, ties in survival times, and extreme values. An agent that crashes or produces NaN on edge cases receives zero safety credit.

An important example is **TC-021 (TTP)**, which tests censoring rule knowledge. TTP (Time-to-Progression) censors death, while PFS (Progression-Free Survival) counts death as an event. An agent that uses the same censoring logic for both endpoints would produce numerically plausible but clinically incorrect TTP results — the safety dimension catches this through cross-TFL agreement checks (TTP events ≤ PFS events).

### 4.2.4 Operational Efficiency (Weight: 0.15)

**Definition:** What resources does the agent consume to produce a correct output?

Efficiency scoring recognizes that two agents producing identical numerical results may differ dramatically in cost, speed, and reliability. The efficiency dimension captures:

- **Cost per correct output:** Total API/token cost divided by the number of test cases passed (score ≥ 0.90). An agent costing $5 to complete 13/13 TCs has cost-per-correct = $0.38; one costing $50 for the same result has $3.85.
- **Time to first correct output:** Wall-clock time from task assignment to first output scoring ≥ 0.90. This measures latency, not just total throughput.
- **Retry count:** Number of regeneration attempts needed to reach a passing score. Zero retries indicates robust first-pass capability; multiple retries suggest the agent is guessing rather than reasoning.
- **Human review overhead:** For Level 2/3 test cases, the estimated time a human reviewer spends verifying the agent's output. This is measured through a reviewer time log.

The efficiency score is normalized against a reference human baseline (collected from WG biostatisticians completing the same tasks). An agent is considered "efficiency-positive" if its cost-per-correct is less than 50% of the human baseline cost (human time × loaded labor cost).

## 4.3 Composite Score Computation

The composite benchmark score combines the four dimensions:

$$S_{\text{total}} = 0.40 \cdot S_{\text{stat}} + 0.25 \cdot S_{\text{compliance}} + 0.20 \cdot S_{\text{safety}} + 0.15 \cdot S_{\text{efficiency}}$$

The weights were determined through WG deliberation and reflect the relative importance of each dimension in regulatory submissions. Statistical correctness receives the highest weight (0.40) because numerically wrong results are unconditionally disqualifying. Compliance (0.25) and safety (0.20) together account for nearly half the score, reflecting that regulatory rejections and safety errors are more costly than slow execution. Efficiency (0.15) is the lowest-weighted dimension — important for adoption decisions but not for regulatory acceptability.

**Accuracy floor:** If $S_{\text{stat}} < 0.90$, the composite score is capped at $S_{\text{stat}}$. An agent with 70% statistical accuracy cannot compensate with perfect compliance, safety, and efficiency. This floor ensures that the benchmark cannot be "gamed" by producing wrong numbers in the right format.

## 4.4 Tolerance Specification

Tolerances are defined per test case in a YAML configuration file (`scoring-harness/tolerances.yaml`). Each field has independently configured:

| Parameter | Description | Example (TC-001) |
|---|---|---|
| `absolute` | Maximum absolute difference | 0.05 (months) |
| `relative` | Maximum relative difference | 0.001 (0.1%) |
| `weight` | Field weight in composite | 0.40 |
| `allow_null` | Both-null is a match | true (for CI bounds) |

Example tolerance specification for TC-021 (TTP KM Median):

```yaml
TC-021:
  description: "Time-to-Progression (TTP) KM Median — death censored"
  tolerances:
    median_ttp:
      absolute: 0.05
      relative: 0.001
      weight: 0.40
    ci_lower:
      absolute: 0.05
      relative: 0.001
      weight: 0.20
      allow_null: true
    ci_upper:
      absolute: 0.05
      relative: 0.001
      weight: 0.20
      allow_null: true
    n_events:
      absolute: 0       # exact match
      weight: 0.10
    n_total:
      absolute: 0       # exact match
      weight: 0.10
    estimable:
      exact: true       # must match
      weight: 0.00      # gate flag, not scored
```

The `estimable` field uses `exact: true` with `weight: 0.00` — it functions as a gate flag. If the agent reports `estimable: true` when ground truth is `estimable: false` (or vice versa), it triggers a safety flag but does not directly contribute to the numerical score. This prevents agents from receiving partial credit for incorrectly classifying whether a median is estimable.

## 4.5 Scoring Harness Architecture

The scoring harness (`scoring-harness/score.py`) is implemented in Python with a CLI interface supporting three modes:

1. **Score mode:** Scores an agent's JSON output against ground truth for a specified TC. Produces a detailed per-field scoring report with pass/fail flags and numerical differences.

2. **Verify mode:** Cross-language verification — compares R vs. Python (vs. SAS) outputs on shared data. Used during ground truth development and CI regression testing.

3. **Cross-TFL mode:** Checks cross-TFL agreement between related test cases (e.g., TC-001 median PFS vs. TC-015 KM curve consistency).

The harness loads tolerances from YAML, validates output against JSON schemas, and produces both machine-readable (JSON) and human-readable (Rich-formatted console) reports. Each test case has a dedicated scorer function (`score_tc001`, `score_tc002`, ..., `score_tc021`) that handles field-specific comparison logic.

## 4.6 Error Injection Validation

To confirm that the scoring framework is not trivially passing, we validated it through error injection. Injecting a +0.3 hazard ratio bias into the TC-001 ground truth (simulating an agent that systematically overestimates treatment effect) dropped the score from 1.0000 to 0.7227. This confirms that:

- The tolerances are tight enough to detect clinically meaningful errors
- The scoring is not degenerate (not everything passes)
- The framework can discriminate between correct and incorrect outputs

## 4.7 Reference Human Baseline

A critical component of the benchmark is the human performance baseline. Two to three WG biostatisticians will complete each Level 1 test case under timed conditions, recording:

- Time to completion (from task assignment to correct output)
- Number of reference lookups (documentation consultations)
- Number of code iterations
- Self-reported confidence

The human baseline serves two purposes: (1) it provides a reference point for agent efficiency scoring, and (2) it calibrates the difficulty of each test case — if humans consistently take 45 minutes for a TC that agents complete in 2 minutes, the TC may be too easy (or the agents may be using pre-trained memorization). The baseline collection is planned for Day 35–37.

---

**Next sections to draft:** Section 5 (Results), Section 6 (Discussion), Section 7 (Conclusions).
