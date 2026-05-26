# Benchmark Framework v1 — Agentic AI for TFL Programming

**Version:** 0.1 (initial draft, corrected per WG feedback)
**Date:** 2026-05-25
**Author:** Natasha (on behalf of Yue Shentu / ASA Biopharm Agentic AI WG)

## Priority Scope: TFL Programming

Per WG direction, the benchmark **starts with TFL generation and review**
as the initial test suite — the most concrete, most in-demand use case
across pharma biostatistics. Trial design and CSR writing come later.

## Language Support

**R + SAS + Python** — all three. TFL production is multilingual by nature:
- **R** (pharmaverse: Tplyr, rtables, tern) — growing adoption
- **SAS** (PROC TABULATE, PROC REPORT, PROC SGPLOT) — regulatory gold standard
- **Python** (matplotlib, plotnine, statsmodels) — emerging

The benchmark evaluates agents in all three and scores them independently.

---

## Table of Contents

1. [Design Principles](#1-design-principles)
2. [Benchmark Architecture](#2-benchmark-architecture)
3. [Dimension 1: Task Fidelity](#3-dimension-1-task-fidelity)
4. [Dimension 2: Workflow Completeness](#4-dimension-2-workflow-completeness)
5. [Dimension 3: Statistical Correctness](#5-dimension-3-statistical-correctness)
6. [Dimension 4: Regulatory Compliance](#6-dimension-4-regulatory-compliance)
7. [Dimension 5: Operational Efficiency](#7-dimension-5-operational-efficiency)
8. [Dimension 6: Safety & Robustness](#8-dimension-6-safety--robustness)
9. [Scoring Framework](#9-scoring-framework)
10. [Open Questions](#10-open-questions)

---

## 1. Design Principles

### P1. Domain-Specific, Not General
The benchmark must test capabilities unique to clinical trial statistics.
General coding or QA benchmarks (SWE-bench, HumanEval) are necessary but not
sufficient.

### P2. Regulatory-Grade Ground Truth
Every test case must have a known-correct reference solution that would pass
regulatory review. "Close enough" is not acceptable.

### P3. Multi-Dimensional Scoring
An agent that produces perfect statistical output but costs $50/run is
different from one that does the same for $0.50. Both correctness AND
efficiency matter.

### P4. Progressive Difficulty
Tasks should be stratified by complexity:
- **Level 1 (Basic):** Single-step, well-specified tasks
- **Level 2 (Intermediate):** Multi-step, moderately ambiguous
- **Level 3 (Advanced):** Full workflow, realistic ambiguity requiring judgment

### P5. Auditability Built In
The benchmark must evaluate not just output quality but also the
audit trail — can a reviewer reconstruct what the agent did and why?

### P6. Vendor-Neutral
The benchmark must not favor any specific LLM, agent framework, or
programming language.

---

## 2. Benchmark Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SCORING ENGINE                           │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │Task     │ │Stat.     │ │Regulatory│ │Efficiency     │  │
│  │Fidelity │ │Correct-  │ │Compliance│ │& Safety       │  │
│  │Score    │ │ness Score│ │  Score   │ │   Score       │  │
│  └────┬────┘ └────┬─────┘ └────┬─────┘ └───────┬───────┘  │
│       └───────────┴────────────┴───────────────┘           │
│                            │                                │
│                    ┌───────┴────────┐                       │
│                    │  COMPOSITE     │                       │
│                    │  BENCHMARK     │                       │
│                    │  SCORE (CBS)   │                       │
│                    └────────────────┘                       │
└─────────────────────────────────────────────────────────────┘
         ▲                                       ▲
         │                                       │
┌────────┴──────────┐              ┌─────────────┴──────────┐
│  TASK EXECUTOR    │              │  TEST CASE LIBRARY     │
│  (Agent runs      │              │  ├─ SAP generation     │
│   against test    │              │  ├─ TFL programming    │
│   harness)        │              │  ├─ Sample size calc   │
└───────────────────┘              │  ├─ Safety monitoring  │
                                   │  ├─ CSR writing        │
                                   │  └─ Regulatory mapping │
                                   └────────────────────────┘
```

The benchmark evaluates agents along **six independent dimensions**,
each scored 0-100. The Composite Benchmark Score (CBS) is a weighted
average, with weights adjustable depending on the use case
(e.g., regulatory submissions might weight compliance at 40%,
while internal QC tools might weight efficiency at 35%).

---

## 3. Dimension 1: Task Fidelity

*Does the agent correctly understand and execute the requested task?*

### Sub-Dimensions

| Sub-Dimension | Description | Evaluation Method |
|---|---|---|
| **Instruction Parsing** | Can the agent correctly interpret a clinical task described in natural language? | Compare agent's task decomposition against gold-standard plan |
| **Scope Adherence** | Does the agent stay within the specified scope without adding unsolicited modifications? | Diff analysis — flag additions outside spec |
| **Edge Case Handling** | Does the agent correctly handle missing data, boundary conditions, known pathological cases? | Pre-seeded edge cases in test data |

### Example Test Cases — TFL Focus (Level 1 — Basic)

1. *"Generate a baseline demographics table (Table 14.1.1.1) by treatment arm for the safety population. Include age, sex, race, ethnicity, ECOG score, and disease stage. Use R (Tplyr) / SAS (PROC TABULATE) / Python (gt package)."*
2. *"Produce the primary efficacy analysis TLF: Kaplan-Meier curves for PFS by treatment arm, with number-at-risk table below. Use R (survminer) / SAS (PROC SGPLOT) / Python (matplotlib)."*
3. *"Create an adverse events summary table by SOC and PT, sorted by decreasing frequency in the active arm. SAS: PROC FREQ / R: Tplyr + gt / Python: pandas pivot."*

### Example Test Cases — TFL Focus (Level 2 — Intermediate)

4. *"Generate the complete Table 14 series (14.1.1.1 demographics, 14.2.1.1 disposition, 14.3.1.1 primary efficacy) for a phase 3 oncology trial. Input: ADaM datasets (ADSL, ADTTE, ADLB). Output: formatted RTF files ready for the CSR appendix."*
5. *"Review this 5-table TFL package for consistency with the SAP shells. Flag any discrepancy in: (a) population flags used, (b) visit window labels, (c) baseline definition, (d) p-value formatting, (e) missing categories. Generate a review report."*
6. *"Translate this TFL specification from SAS to R. Input: SAS program for Table 14.1.1.1 using PROC TABULATE. Output: equivalent R program using Tplyr, producing identical output."*

### Example Test Cases — TFL Focus (Level 3 — Advanced)

7. *"A regulatory reviewer has flagged inconsistencies between Table 14.1.1.1 and Listing 16.2.1.1 in your submission package. The count of randomized subjects differs by 2. Diagnose the root cause, fix both outputs, and document the discrepancy. Provide outputs in R and SAS for cross-validation."*
8. *"Generate a complete TFL shell package for a phase 2 basket trial with 5 tumor types. Each tumor type has its own analysis population. Include: adverse events by tumor type, efficacy waterfall plot per tumor type, swimmer plot, and biomarker subgroup forest plot. Input: multi-tumor ADaM datasets. Output: RTF files."*
9. *"Given the TFL package from a previous study, generate a submission-ready clinical study report section (Section 11 — Efficacy Evaluation) integrating the key tables and figures with narrative text. The output must match the ICH E3 CSR standard."*

---

## 4. Dimension 2: Workflow Completeness

*Does the agent execute the end-to-end workflow, not just isolated steps?*

### Standard Workflow Model

```
Trial Design Phase:
  Protocol review → SAP outline → Sample size calc → Randomization spec

Analysis Phase:
  Data ingest → SDTM mapping → ADaM programming → TFL generation

Reporting Phase:
  TFL QC/Review → CSR drafting → Submission package assembly

Cross-cutting:
  Safety monitoring → DMC reporting → Data cleaning flags
```

### Evaluation Criteria

| Criterion | What to Check |
|---|---|
| **Sequencing** | Are steps executed in the correct order? |
| **Artifact Handoff** | Does the output of step N feed correctly into step N+1? |
| **Error Propagation** | If step 3 fails, does the agent recover or propagate the error gracefully? |
| **Human-in-the-Loop** | Does the agent correctly identify decision points requiring human review? |

---

## 5. Dimension 3: Statistical Correctness

*This is the core dimension — does the agent produce statistically valid output?*

### Methodological Test Coverage

| Statistical Method | Test Cases | Ground Truth Source |
|---|---|---|
| **Kaplan-Meier estimation** | Single arm, two arms, competing risks | Verified R `survfit()` output |
| **Log-rank test** | Stratified, unstratified, trend test | Verified R `survdiff()` output |
| **Cox proportional hazards** | Univariable, multivariable, stratified, time-varying covariates | Verified R `coxph()` output |
| **Logistic regression** | Univariable, multivariable, with/without interaction terms | Verified R `glm()` output |
| **Sample size calculation** | Continuous, binary, time-to-event, non-inferiority, group sequential | Verified `gsDesign` / `lme4` output |
| **Multiple comparisons** | Bonferroni, Holm, Hochberg, FDR, graphical approaches | Verified R `multcomp` / `p.adjust()` |
| **Subgroup analysis** | Pre-specified, post-hoc, interaction tests | Verified with multiplicity adjustment |
| **Missing data handling** | LOCF, MMRM, multiple imputation, pattern-mixture models | Verified SAS/R output |
| **Non-inferiority / equivalence** | Margin specification, CI methods, switching non-inf ↔ superiority | Regulatory guidance alignment |
| **Interim analysis** | Alpha spending, conditional power, futility boundaries | Verified `gsDesign` output |

### Verification Protocol

For each test case:
1. Define the statistical problem with clear inputs
2. Generate the gold-standard answer using verified R/SAS code
3. Present the problem to the agent (in natural language or structured spec)
4. Compare agent output to gold standard
5. Score: exact match (100%), functionally equivalent with minor differences (80%), conceptually correct but different implementation (60%), partially correct (40%), incorrect (0%)

**Tolerance:** For numerical methods, allow floating-point differences < 1e-6.
For methodological choices, require the same method (not just same result).

---

## 6. Dimension 4: Regulatory Compliance

*Does the agent produce output that meets regulatory submission standards?*

### Standards Coverage

| Standard | Specific Requirements |
|---|---|
| **ICH E3** (CSR structure) | Correct section ordering, required content elements |
| **ICH E9** (statistical principles) | ITT vs PP, missing data handling, sensitivity analyses |
| **ICH E9(R1)** (estimands) | Estimand specification, intercurrent events handling |
| **ICH E6(R2)** (GCP) | Audit trail, data integrity, version control |
| **CDISC SDTM** | Domain naming, variable mapping, required metadata |
| **CDISC ADaM** | ADSL, ADTTE, ADRS, ADLB structures, timing variables |
| **Define-XML** | Metadata formatting, version compatibility |
| **FDA Study Data Technical Conformance Guide** | Submission package structure |

### Evaluation Criteria

| Criterion | How to Test |
|---|---|
| **Standard Adherence** | Does the output comply with CDISC controlled terminology? |
| **Document Completeness** | Are all required sections present? |
| **Traceability** | Can each output element be traced back to its source data/specification? |
| **Audit Trail Quality** | Is there a clear, human-readable log of all decisions and transformations? |
| **Submission Readiness** | Would this pass a typical FDA technical review? |

---

## 7. Dimension 5: Operational Efficiency

*How fast, cheap, and scalable is the agent?*

### Metrics

| Metric | Definition | Target |
|---|---|---|
| **Wall Clock Time** | End-to-end execution time for standard task | ≤ human time for same task |
| **Token Cost** | Total tokens consumed (input + output) | Benchmark reference (per task) |
| **API Call Count** | Number of LLM calls per task | Minimize — fewer calls = better planning |
| **Tool Call Efficiency** | Tool calls vs optimal calls | Ratio > 0.7 = good |
| **Reproducibility** | Same task → same result? | 90%+ agreement across 5 runs |

---

## 8. Dimension 6: Safety & Robustness

*Does the agent fail safely?*

### Stress Tests

| Test | Description |
|---|---|
| **Missing Data** | Drop 10%, 25%, 50% of key variables |
| **Label Corruption** | Reverse treatment labels, swap control/active |
| **Adversarial Prompts** | Injection attempts, contradictory instructions |
| **Out-of-Distribution Input** | Disease/endpoint combination not in training data |
| **Resource Limits** | Timeout at 50%, 75%, 90% of expected runtime |

### Safety Requirements

| Requirement | Standard |
|---|---|
| **Refuse harmful actions** | Must not execute data deletion, unauthorized access |
| **Confidence calibration** | Must flag low-confidence outputs |
| **Escalation protocol** | Must identify when human review is needed |
| **Containment** | Must not write outside designated directories/databases |

---

## 9. Scoring Framework

### Composite Benchmark Score (CBS)

```
CBS = w₁·S_task + w₂·S_workflow + w₃·S_stat + w₄·S_reg + w₅·S_eff + w₆·S_safety

Default weights (regulatory use case):
  w₁=0.15, w₂=0.15, w₃=0.25, w₄=0.25, w₅=0.10, w₆=0.10

Efficiency-focused weights (internal QC use case):
  w₁=0.10, w₂=0.10, w₃=0.20, w₄=0.10, w₅=0.35, w₆=0.15
```

### Minimum Passing Thresholds

| Use Case | Min CBS | Per-Dimension Floor |
|---|---|---|
| Internal exploratory | 60 | None |
| Internal production QC | 75 | S_stat ≥ 70, S_safety ≥ 60 |
| Regulatory submission | 85 | S_stat ≥ 80, S_reg ≥ 80, S_safety ≥ 70 |

---

## 10. Open Questions (for WG discussion)

1. **Weight calibration:** Are the default weights right for a regulatory submission benchmark? Should different use cases have different weight profiles?

2. **Language bias:** Should we require R, SAS, or Python? All three? The benchmark should be language-agnostic, but scoring needs a reference implementation. What's the ground truth language?

3. **Data sourcing:** Where do we get realistic, non-proprietary clinical trial datasets? Synthetic data generation (e.g., `simstudy`, `random.cdisc.data`)? FDA公开 datasets? Pharmaverse synthetic data?

4. **Task decomposition:** Should we build tasks around individual statistical methods (narrow, testable) or full workflow scenarios (realistic, harder to score)? Answer: both, with clear level stratification.

5. **Human baseline:** What constitutes "expert-level" performance? Need to establish a human benchmark (e.g., "a statistician with 5+ years of oncology experience would score 90 on this task").

6. **Contamination risk:** If we use public datasets and common statistical problems, how do we prevent benchmark contamination in frontier models?

7. **Maintenance:** Who curates the test cases? How often are they updated (new methods, new regulatory guidance)?

8. **Regulatory alignment:** Are we aiming for FDA endorsement? If so, what level of engagement do we need with CDER/ODE?

9. **Zero-shot vs. tool-augmented:** Should the benchmark assume the agent has access to standard R packages, or should it test the agent's ability to write code from scratch?

10. **Scoring automation:** How much of the scoring can be automated (test harness) vs. requiring expert human review?

---

## Appendix A: Relationship to Existing Benchmarks

| Benchmark | Domain | Gap Analyzed | Relevance to Our Benchmark |
|---|---|---|---|
| **SWE-bench** | General Python coding | No statistical domain knowledge | Foundation for coding agent evaluation, but domain-inadequate |
| **GAIA** | General AI assistants | No domain specialization | Useful for general tool-use patterns, not our domain |
| **WebArena** | Web navigation | No statistical/mathematical reasoning | Complements but does not overlap |
| **AgentBench** | Multi-environment | General-purpose, shallow in any domain | Reference architecture for multi-env evaluation |
| **Terminal-Bench** | Shell/DevOps | Infrastructure tasks only | Useful for terminal interaction patterns |
| **PHUSE Test Data Factory** | CDISC test data | Data generation, not agent evaluation | Source of realistic test datasets |
| **Pharmaverse** | R packages for pharma | Tooling, not benchmarks | Reference implementation packages |

## Appendix B: Glossary

| Term | Definition |
|---|---|
| **CBS** | Composite Benchmark Score — weighted average of 6 dimensions |
| **Task Fidelity** | Correctness of task interpretation and execution |
| **Workflow Completeness** | End-to-end coverage of the clinical workflow |
| **Statistical Correctness** | Methodological and numerical accuracy |
| **Regulatory Compliance** | Adherence to ICH, CDISC, FDA standards |
| **Operational Efficiency** | Speed, cost, and scalability |
| **Safety & Robustness** | Failure mode handling and containment |
| **TFL** | Tables, Figures, Listings |
| **SAP** | Statistical Analysis Plan |
| **CSR** | Clinical Study Report |
| **ADaM / SDTM** | CDISC analysis/submission data standards |
