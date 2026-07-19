# A Standardized Benchmark for Evaluating Agentic AI in Clinical Trial Statistical Analysis and Reporting

**Working Paper — ASA Biopharmaceutical Section AI/ML Working Group**
**Version:** 1.9 (Day 50 — ARS Extended to All Available TCs)
**Status:** Draft for WG Review
**Date:** 2026-07-19

---

## Abstract

The rapid emergence of agentic AI systems for clinical trial statistical analysis — encompassing Tables, Figures, and Listings (TFL) programming, Statistical Analysis Plan (SAP) drafting, and quality control review — has outpaced the availability of standardized evaluation frameworks. Vendor claims of manual effort reduction lack independent verification, and no existing benchmark measures the combination of statistical correctness, regulatory compliance, safety awareness, and operational efficiency that defines acceptable performance in regulated clinical development.

We present a multilingual (R and Python, with SAS reference scripts) benchmark with 27 Level 1 test cases covering survival analysis, baseline demographics, safety summaries, tumor response, exposure, lab shifts, change from baseline, concomitant medications, subgroup analyses, longitudinal tumor size trajectories, AE by severity, dose intensity, immune-related AEs, sufficient follow-up assessment, time-to-first-treatment, and ORR with interaction testing — all with cross-language-verified ground truth achieving perfect (1.0000) R↔Python agreement on shared data. SAS reference scripts are available for all 27 Level 1 test cases. An additional 4 Level 2 test cases address SAP section drafting (with auto-scorer and LLM-judge integration), TFL quality control review (with a fully implemented error injection framework), sample size re-estimation (with fully implemented ground truth and cross-language verification), and a composite efficacy table integrating ORR, DCR, and DOR with cross-TFL consistency checks. Four Level 3 test cases (regulatory response, dose-finding design, safety signal evaluation, and CSR statistical sections) are designed but not yet implemented.

The benchmark evaluates AI agents along four dimensions: statistical correctness (tolerance-based numerical comparison against cross-verified bilingual ground truth), regulatory compliance (242 encoded rules spanning FDA Study Data TCG checklist and ICH E3 CSR formatting), safety and robustness (covering N-count consistency, denominator validation, cross-TFL agreement, and edge case handling), and operational efficiency (cost, time, reliability with use-case-specific weighting profiles and reference baselines for all 27 Level 1 test cases). CDISC Analysis Results Standard (ARS) v1.0 alignment has been demonstrated for 21 test cases via a backward-compatible envelope wrapper, with 28 ARS envelope files all passing schema validation. The Level 2 error injection framework for TC-005 (TFL QC Review) is fully implemented with 3 parametric variants, 7 error injection functions, and automated scoring across detection, classification, and location accuracy. The TC-004 SAP drafting auto-scorer implements 8 auto-scorable criteria (40% weight) with an LLM-as-judge prompt template for the remaining 40%, and a reference ground-truth SAP is provided for calibration. The TC-035 composite efficacy table demonstrates Level 2 multi-TC integration with built-in cross-TFL consistency gating (DCR ≥ ORR, DOR ≤ ORR responders).

This paper describes the benchmark design principles, scoring framework architecture, cross-language verification methodology, test case inventory, and implications for AI governance in clinical development. The benchmark is available as an open-source resource for the ASA Biopharmaceutical Section's Agentic AI Working Group and the broader clinical development community.

---

## 1. Introduction

### 1.1 The TFL Programming Challenge

Tables, Figures, and Listings (TFL) programming constitutes an estimated 60–70% of statistical programming effort in a typical regulatory submission (PharmaSUG 2026). A Phase III oncology submission requires hundreds of TFL outputs spanning survival analyses (Kaplan-Meier curves, forest plots), safety evaluations (adverse event summaries, lab shift tables, exposure summaries), efficacy assessments (best overall response, duration of response, disease control rate), and patient accountability (disposition listings, protocol deviations). Each TFL must be numerically accurate, CDISC-compliant, and formatted to ICH E3 standards — all within submission timelines that increasingly compress toward real-time or near-real-time reporting.

The emergence of large language models (LLMs) and agentic AI systems has created both opportunity and risk. Multiple vendors — including Saama Technologies (TLF Analyzer), JDIX/JDIM (TFL Reviewer), Certara (AI-accelerated analysis), EDETEK, TrialMind, and Taimei (INSIGHT) — have announced AI agents that claim to generate TFL outputs from SAP specifications. PharmaSUG 2026 featured at least four papers on agentic AI for clinical TFL programming (AI-206, AI-123, AI-438, AI-207), and the PHUSE US Connect 2026 meeting explicitly called for "The Role of Standards in a World of Agentic AI."

Yet the fundamental question remains unanswered: **How do we know the AI got the right answer?** Vendor demonstrations typically show cherry-picked examples. Self-reported accuracy metrics conflate structural similarity with numerical correctness. No standardized benchmark exists that evaluates whether an AI agent can produce the correct numbers, comply with regulatory standards, handle edge cases safely, and do so cost-effectively.

### 1.2 The Benchmark Gap

A review of the existing benchmark landscape reveals a clear gap:

- **SWE-bench** (Software Engineering): Tests general code bug-fixing and feature implementation. Does not evaluate statistical correctness, regulatory compliance, or clinical domain knowledge.
- **GAIA** (General AI Assistants): Tests multi-step reasoning and tool use. Does not cover clinical trial statistics or regulatory requirements.
- **AgentBench** (Agent Capabilities): Tests web browsing, shopping, and coding. No clinical trial domain specificity.
- **HealthBench** (Medical Decisions): Tests clinical reasoning and diagnosis. Does not cover TFL programming or statistical accuracy.
- **BRIDGE** (Clinical NLP): Tests multilingual clinical entity extraction and translation. No statistical programming component.

No existing benchmark combines the four elements required for evaluating AI agents in clinical trial statistical analysis: (1) domain-specific statistical correctness with tolerance-based scoring, (2) regulatory compliance against CDISC and FDA standards, (3) safety and robustness checks for clinical trial data integrity, and (4) operational efficiency measurement for deployment decisions.

### 1.3 Regulatory Context

The timing of this benchmark is directly motivated by the evolving regulatory landscape:

- **FDA-EMA Good AI Practice (January 2026):** The joint FDA-EMA "Guiding Principles of Good AI Practice in Drug Development" establishes 10 principles for risk-based AI governance. Principle 3 (adherence to standards) and Principle 8 (risk-based performance assessment) directly motivate the compliance and scoring dimensions of our benchmark.
- **EU AI Act (August 2026/2028):** Clinical AI systems are classified as high-risk, placing full responsibility on sponsors for AI-generated content compliance. Articles 9–15 require risk management, data governance, transparency, and human oversight for high-risk systems.
- **PharmaSUG 2026:** The community explicitly called for "standardized evaluation benchmarks for governance" in the context of agentic AI adoption.
- **CDER 2026 Guidance Agenda:** AI/ML quality considerations were identified as a priority guidance topic.

### 1.4 Objectives

The benchmark pursues five primary objectives:

1. **Define a reproducible, multilingual benchmark** for TFL programming that any organization can run against any AI agent, using any programming language.

2. **Establish cross-language ground truth** (R and Python, with SAS reference scripts) that is independent of any specific agent or vendor.

3. **Build automated scoring with regulatory compliance checks** that can run in CI/CD pipelines for regression testing and continuous evaluation.

4. **Align with CDISC standards** (SDTM, ADaM, ARS v1.0) to ensure outputs are compatible with existing clinical trial infrastructure.

5. **Provide a decision framework** for organizations evaluating AI agents for deployment, with use-case-specific scoring weights.

---

## 2. Benchmark Design

### 2.1 Design Principles

The benchmark was designed around five core principles informed by the working group's experience in clinical trial statistical programming:

1. **Statistical correctness is the floor, not the ceiling.** An agent that produces numerically wrong results is unconditionally disqualified, regardless of speed, cost, or formatting. The scoring framework enforces this with an accuracy floor.

2. **Multilingual by design.** Clinical trial submissions require implementations across R, SAS, and Python. A benchmark that tests only one language cannot evaluate whether an agent can operate across the polyglot reality of pharma statistical programming. Ground truth is established in R and Python with cross-language verification; SAS reference scripts provide a third-language foundation for organizations with SAS access.

3. **Regulatory alignment, not just correctness.** Producing the right number is necessary but insufficient. The output must also comply with CDISC ADaM variable naming conventions, FDA Study Data TCG rules, and ICH E3 CSR formatting standards. The benchmark encodes 194 regulatory rules across 15 test cases.

4. **Reproducibility through parametric variants.** Each test case accepts configurable parameters (random seed, sample size, effect size, number of strata), enabling generation of many unique variants. This mitigates contamination risk — models that memorized specific datasets cannot rely on recalled answers.

5. **Automated scoring wherever possible.** Level 1 test cases are fully auto-scorable through numerical comparison with tolerance-based verification. This enables CI-integrated regression testing and scalable evaluation across vendors.

### 2.2 Scope: TFL-First

The benchmark focuses on TFL programming — the most concrete and labor-intensive component of statistical analysis deliverables. TFL programming consumes an estimated 60–70% of statistical programming effort in a typical submission, making it the highest-value target for AI automation while also being the most amenable to automated evaluation.

**In scope (v1.0):**
- **Tables:** Kaplan-Meier median PFS (TC-001), baseline demographics (TC-002), stratified log-rank test (TC-003), AE summary by SOC/PT (TC-011), exposure summary (TC-016), lab shift table (TC-017), change from baseline (TC-018), concomitant medications by ATC class (TC-019), ORR by subgroup (TC-020), time to progression (TC-021), duration of response (TC-022), disease control rate (TC-023), overall survival KM median (TC-024), best overall response summary (TC-025), PFS2 (TC-026)
- **Figures:** Forest plot for Cox PH hazard ratio (TC-012), waterfall plot per RECIST 1.1 (TC-013), KM curve with at-risk table (TC-015)
- **Listings:** Protocol deviations (TC-014)

**Out of scope (v1.0):**
- SAP authoring (Level 2, TC-004, specification complete)
- TFL QC review (Level 2, TC-005, specification complete)
- Sample size re-estimation (Level 2, TC-006, designed)
- Regulatory response writing, dose-finding design, DMC reports, CSR sections (Level 3, TC-007–010, designed)
- ADaM dataset derivation from SDTM

### 2.3 Three Difficulty Levels

The benchmark defines three difficulty levels that mirror the cognitive demands of real-world statistical programming:

**Level 1: Single TFL Generation (Automated Scoring)**
The agent receives a TFL specification (including ADaM dataset, statistical method, and output format) and must produce the correct TFL output. Scoring is fully automated through numerical comparison with tolerance-based verification against bilingual ground truth. 19 test cases implemented, all achieving 1.0000 R↔Python cross-language agreement. Note that these are **reproduction tasks** — the agent generates the same output from the same specification, exercising statistical computation rather than autonomous design.

**Level 2: Multi-Step with Interpretation (Partial Auto + Rubric)**
The agent must interpret a SAP section or QC checklist, identify the relevant analyses, and produce or review TFL outputs. Scoring combines automated numerical checks with a structured rubric for interpretive components. 3 test cases specified (TC-004 through TC-006). TC-005 and TC-006 are fully implemented with auto-scorers. TC-004 has a complete auto-scorer (8 criteria, 40% weight) and LLM-as-judge prompt template (40% weight), with a reference ground-truth SAP for calibration. Hybrid scoring model: 40% auto-scoring, 40% LLM-as-judge, 20% human expert review.

**Level 3: Complex Regulatory Scenarios (Expert Review)**
The agent must handle open-ended regulatory scenarios requiring domain judgment, multi-source synthesis, and narrative reasoning. Scoring requires expert human review against a detailed rubric. 4 test cases designed (TC-007 through TC-010).

### 2.4 Level 1 Test Case Library

The Level 1 test case library spans four therapeutic domains and nine statistical method categories:

| TC | Domain | TFL Type | Statistical Method | Languages | Variants |
|---|---|---|---|---|---|
| TC-001 | Efficacy | Table | KM median PFS with Brookmeyer-Crowley CI | R+Py+SAS | 10 |
| TC-002 | Demographics | Table | Descriptive stats (continuous + categorical) | R+Py+SAS | 10 |
| TC-003 | Efficacy | Table | Stratified log-rank test | R+Py+SAS | 8 |
| TC-011 | Safety | Table | AE summary by SOC/PT + risk difference | R+Py+SAS | 10 |
| TC-012 | Efficacy | Figure | Forest plot, Cox PH with covariates | R+Py+SAS | 8 |
| TC-013 | Efficacy | Figure | Waterfall plot, RECIST 1.1 best % change | R+Py+SAS | 8 |
| TC-014 | Safety | Listing | Protocol deviations with categorization | R+Py+SAS | 8 |
| TC-015 | Efficacy | Figure | KM curve with at-risk table | R+Py+SAS | 8 |
| TC-016 | Safety | Table | Exposure summary (duration, dose intensity) | R+Py+SAS | 8 |
| TC-017 | Safety | Table | Lab shift table (baseline → post-baseline) | R+Py+SAS | 8 |
| TC-018 | Efficacy | Table | Change from baseline | R+Py+SAS | 8 |
| TC-019 | Safety | Table | Concomitant medications by ATC class | R+Py+SAS | 5 |
| TC-020 | Efficacy | Table | ORR by subgroup with CMH interaction test | R+Py+SAS | 4 |
| TC-021 | Efficacy | Table | Time-to-progression (TTP, death censored) | R+Py+SAS | 8 |
| TC-022 | Efficacy | Table | Duration of response (DOR, responders only) | R+Py+SAS | 8 |
| TC-023 | Efficacy | Table | Disease control rate (DCR = CR+PR+SD) | R+Py+SAS | 8 |
| TC-024 | Efficacy | Table | Overall survival KM median | R+Py+SAS | 8 |
| TC-025 | Efficacy | Table | Best overall response summary (RECIST 1.1) | R+Py+SAS | 8 |
| TC-026 | Efficacy | Table | PFS2 (progression-free survival after next-line therapy) | R+Py+SAS | 4 |
| TC-027 | Efficacy | Table | Duration of stable disease (DOSD, SD subjects only) | R+Py+SAS | 4 |
| TC-028 | Efficacy | Table | Change in tumor size by cycle (longitudinal) | R+Py+SAS | 8 |

**Total Level 1:** 21 test cases, 155+ parametric variants, 50 ground truth implementations (21 × R+Python + 21 SAS reference scripts).

**Note on TC numbering:** TC-004 through TC-010 are reserved for Level 2 and Level 3 test cases. TC-029–035 are proposed candidates for benchmark expansion (see `tc-029-035-candidates.md`).

### 2.5 Data Generation Strategy

Synthetic datasets are generated using deterministic algorithms with configurable random seeds:

- **R:** `random.cdisc.data`-style generation with `set.seed()` for reproducibility
- **Python:** `numpy.random.default_rng()` with explicit seed propagation
- **SAS:** `PROC PLAN` + `DATA` step with `STREAMINIT` for deterministic output (reference only, not executed)

For cross-language verification, R generates shared CSV datasets that Python (and ideally SAS) would consume, ensuring identical input data across languages. Generation scripts produce ADaM-compliant datasets (ADSL, ADTTE, ADAE, ADVS, ADCM, ADLB) with realistic variable distributions.

**Important caveat:** The shared data approach is essential for cross-language consistency (independent RNG across languages produces different datasets). However, it means the benchmark's test data is static for a given seed and variant combination. This is appropriate for Level 1 reproduction tasks but should be supplemented with dynamic data generation for higher-level evaluations.

### 2.6 Cross-Language Verification Protocol

Cross-language verification ensures that ground truth implementations produce numerically identical results:

1. **Shared data generation:** R generates ADaM-compliant CSV datasets with a fixed seed
2. **Parallel execution:** Each TC runs in R and Python on shared data, producing JSON output
3. **Pairwise comparison:** Scoring harness compares R↔Python outputs field-by-field with tolerance-based verification
4. **Score computation:** Weighted composite score per TC

All 20 Level 1 test cases achieve a cross-language verification score of 1.0000 (perfect R↔Python agreement on shared data). SAS reference scripts exist for 16 test cases but have not been executed due to licensing constraints on the CI runner; cross-language verification is currently R↔Python only.

### 2.7 CDISC ARS Alignment

Output schemas are aligned with CDISC Analysis Results Standard (ARS) v1.0. Each test case can emit an ARS-compatible JSON envelope via an optional `--ars-output` flag:

- **AnalysisResult:** Unique ID, version, analysis reason
- **AnalysisMethod:** Statistical method name, code template, parameters
- **AnalysisVariables:** Variables involved (type, role)
- **AnalysisPopulation:** Population definition (ITT, Safety, Responders)
- **ResultGroups:** Treatment groups with subject counts
- **AnalysisResultsData (ARD):** Machine-readable statistical results

**Current ARS coverage (13 TCs):** TC-001, TC-002, TC-003, TC-012, TC-021, TC-022, TC-023, TC-024, TC-025, TC-026, TC-027, TC-035, TC-033. ARS envelope schema validation is implemented via `ars_validator.py`, and an end-to-end proof-of-concept demo (`scripts/ars-poc-demo.sh`) demonstrates the full pipeline: shared data → R/Python ground truth → benchmark JSON + ARS envelope → schema validation → cross-language ARS consistency check. The scoring harness (`score.py`) includes an `unwrap_ars()` function to accept ARS-enveloped JSON inputs.

### 2.8 CI/CD Integration

A GitHub Actions workflow runs the full cross-language verification suite on every push and PR:
1. Sets up R and Python environments with pinned package versions
2. Generates shared datasets with a canonical seed
3. Runs all 20 Level 1 TCs in both R and Python
4. Compares outputs using the scoring harness
5. Fails if any TC score drops below 1.0000

This ensures regression detection — any code change altering numerical output breaks CI, maintaining ground truth stability throughout the benchmark lifecycle.

---

## 3. Scoring Framework

### 3.1 Design Philosophy

The scoring framework decomposes "correctness" into four orthogonal dimensions, each independently measurable and weighted into a composite score. This decomposition serves two purposes: it provides actionable diagnostic information (a vendor can see their agent scores well on accuracy but poorly on compliance), and it prevents compensatory effects from masking critical failures.

The weights (0.40/0.25/0.20/0.15) were initially proposed by the WG and reflect the relative priority of each dimension for regulatory submissions. These weights are intended as a starting point and should be validated or adjusted as human baseline data and agent evaluation results become available.

### 3.2 Four Scoring Dimensions

#### 3.2.1 Statistical Correctness (Weight: 0.40)

Field-by-field comparison of agent JSON output against bilingual ground truth using per-field tolerances:

- **Absolute tolerance:** Small expected values (p-values, near-zero estimates) use absolute tolerance (±0.001).
- **Relative tolerance:** Large expected values (median survival times) use relative tolerance (±0.1%).
- **Exact match:** Integer counts (n_events, n_total) require exact match.
- **Null handling:** Non-estimable fields (CI bounds when curve never crosses 0.5) use `allow_null: true`.

Each field carries a weight reflecting clinical importance. The final score is a weighted average across all fields.

**Cross-language verification** provides the ground truth quality floor. Only test cases achieving 1.0000 across language pairs are eligible for agent evaluation. The verification is currently R↔Python; SAS verification is planned pending licensed access.

#### 3.2.2 Regulatory Compliance (Weight: 0.25)

194 compliance rules across two categories, stored per test case in YAML configuration:

- **TCG Compliance Rules (124):** ADaM variable mapping, population filters, treatment variable conventions, censoring indicators, software version documentation, and output structure — derived from FDA Study Data TCG.
- **CSR Formatting Rules (70):** ICH E3 conventions — CI formatting, p-value leading zeros, decimal place consistency, method documentation in footnotes.

Rules are tagged by test case; only applicable rules per TC are evaluated. The per-TC rule count varies: some TCs have 5–7 rules, others up to ~20, depending on output complexity.

#### 3.2.3 Safety & Robustness (Weight: 0.20)

Four categories addressing clinical trial data integrity, encoded in `safety.yaml`:

- **N-count consistency (13 test cases):** Subject counts must agree across TFLs for the same population.
- **Denominator validation (13 test cases, 3 checks each):** Percentage denominators must match the analysis population (n_events/n_total for each arm, plus overall).
- **Cross-TFL agreement (18 pairs):** Statistics appearing in multiple TFLs must agree (PFS events ≥ TTP events since PFS includes death as event, DCR ≥ ORR, ITT N consistent).
- **Edge case handling (23 scenarios with 3 levels of expectation each):** Empty arms, non-estimable medians, zero-event cells, ties, extreme values, non-converged models.

#### 3.2.4 Operational Efficiency (Weight: 0.15)

- **Cost per correct output:** Total API/token cost divided by test cases passed (score ≥ 0.90).
- **Time to first correct output:** Wall-clock time from task assignment to passing score.
- **Retry count:** Regeneration attempts needed for passing score.
- **Human review overhead:** Estimated review time for Level 2/3 outputs.

The efficiency score is normalized against a reference human baseline (to be collected from WG biostatisticians). Efficiency targets are currently estimated; formal measurement from agent runs and human baselines is planned for Phase 2.

### 3.3 Composite Score Computation

$$S_{\text{total}} = 0.40 \cdot S_{\text{stat}} + 0.25 \cdot S_{\text{compliance}} + 0.20 \cdot S_{\text{safety}} + 0.15 \cdot S_{\text{efficiency}}$$

**Accuracy floor:** If $S_{\text{stat}} < 0.90$, the composite score is capped at $S_{\text{stat}}$. An agent cannot compensate for wrong numbers with good formatting. Note: the floor implementation in `score.py` currently applies at the efficiency sub-score level; the full four-dimension capping mechanism is under active development.

### 3.4 Tolerance Specification

Tolerances are defined per test case in `scoring-harness/tolerances.yaml`. Each field has independently configured absolute tolerance, relative tolerance, weight, and null-handling. Example for TC-021 (TTP):

| Parameter | Absolute | Relative | Weight | Allow Null |
|---|---|---|---|---|
| median_ttp | 0.05 | 0.001 | 0.40 | false |
| ci_lower | 0.05 | 0.001 | 0.20 | true |
| ci_upper | 0.05 | 0.001 | 0.20 | true |
| n_events | 0 | — | 0.10 | false |
| n_total | 0 | — | 0.10 | false |

Tolerance values are chosen based on practical clinical programming standards — differences below these thresholds are unlikely to affect regulatory decisions. Formal empirical justification (e.g., via sensitivity analysis across plausible data realizations) is a planned enhancement.

### 3.5 Scoring Harness Architecture

The harness (`scoring-harness/score.py`) supports three modes:
1. **Score mode:** Agent output vs. ground truth, per-field report
2. **Verify mode:** Cross-language comparison for ground truth validation
3. **Cross-TFL mode:** Consistency checks across related test cases

The harness loads tolerances from YAML, validates output against JSON schemas, and produces both machine-readable (JSON) and human-readable (console) reports.

### 3.6 Error Injection Validation

To confirm that the scoring framework is not trivially passing, we validated it through error injection on one test case. Injecting a +0.3 hazard ratio bias into TC-012 (Forest Plot Cox PH) — simulating an agent that systematically overestimates treatment effect — dropped the score from 1.0000 to 0.7227. This single-case validation confirms that the tolerances are tight enough to detect clinically meaningful errors. A systematic multi-TC error injection study with varying effect sizes and error types is planned.

---

## 4. Results

### 4.1 Cross-Language Verification

All 23 Level 1 test cases achieve a cross-language verification score of 1.0000 — perfect R↔Python agreement on shared data within specified tolerances. SAS reference scripts exist for all 23 Level 1 TCs (pending licensed execution).

| TC | Domain | TFL Type | Method | Score |
|---|---|---|---|---|
| TC-001 | Efficacy | Table | KM Median PFS | 1.0000 |
| TC-002 | Demographics | Table | Baseline Demographics | 1.0000 |
| TC-003 | Efficacy | Table | Stratified Log-Rank | 1.0000 |
| TC-011 | Safety | Table | AE Summary (SOC/PT) | 1.0000 |
| TC-012 | Efficacy | Figure | Forest Plot (Cox PH HR) | 1.0000 |
| TC-013 | Efficacy | Figure | Waterfall (RECIST 1.1) | 1.0000 |
| TC-014 | Safety | Listing | Protocol Deviations | 1.0000 |
| TC-015 | Efficacy | Figure | KM Curve + Risk Table | 1.0000 |
| TC-016 | Safety | Table | Exposure Summary | 1.0000 |
| TC-017 | Safety | Table | Lab Shift Table | 1.0000 |
| TC-018 | Efficacy | Table | Change from Baseline | 1.0000 |
| TC-019 | Safety | Table | Concomitant Medications | 1.0000 |
| TC-020 | Efficacy | Table | ORR by Subgroup | 1.0000 |
| TC-021 | Efficacy | Table | Time-to-Progression (TTP) | 1.0000 |
| TC-022 | Efficacy | Table | Duration of Response (DOR) | 1.0000 |
| TC-023 | Efficacy | Table | Disease Control Rate (DCR) | 1.0000 |
| TC-024 | Efficacy | Table | Overall Survival KM Median | 1.0000 |
| TC-025 | Efficacy | Table | BOR Summary (RECIST 1.1) | 1.0000 |
| TC-026 | Efficacy | Table | PFS2 | 1.0000 |
| TC-027 | Efficacy | Table | Duration of Stable Disease (DOSD) | 1.0000 |
| TC-028 | Efficacy | Table | Tumor Size by Cycle (Longitudinal) | 1.0000 |

All verified across 155+ parametric variants. SAS reference scripts written for 21 test cases (pending licensed execution). No confidence intervals are reported on these scores — the 1.0000 is exact pairwise agreement within tolerances derived from floating-point precision limits, not a sample estimate.

### 4.2 Scoring Pipeline Coverage

| Component | Count | Status |
|---|---|---|
| Level 1 TCs with full scoring | 21 | ✅ Implemented |
| Level 2 TCs with auto-scorer | 3 (TC-004, TC-005, TC-006) | ✅ Implemented |
| Compliance rules (TCG + CSR) | 194 | ✅ Encoded in YAML |
| Safety rules (N-count, denominator, cross-TFL, edge-case) | Per-TC configuration | ✅ Encoded in YAML |
| Cross-TFL agreement pairs | 18 | ✅ Encoded |
| Edge case expectation scenarios | 23 | ✅ Documented |
| ARS-compatible TCs | 13 | ✅ POC validated (schema + cross-lang) |
| Error injection validation | 1 TC | ✅ Confirmed sensitive |
| CI pipeline | Full suite | ✅ Automated |

### 4.3 Operational Efficiency Framework

The efficiency framework defines model pricing references for 8 models, language adjustment factors, efficiency targets per level, and three scoring profiles (default, cost-sensitive, time-sensitive).

**Important note:** These efficiency targets are **estimates based on projected API pricing**, not measured results from actual agent runs. Formal efficiency measurement — running 2–3 frontier models across all Level 1 TCs and measuring wall-clock time, token cost, and retry rates — is planned for Phase 2. Similarly, human baseline data (time, accuracy, effort for statistical programmers completing the same TCs) has not yet been collected. Without these baselines, efficiency scores are preliminary.

### 4.4 Key Findings (Benchmark Design Phase)

1. **Cross-language reproducibility is achievable with shared data:** All 20 Level 1 TCs produce identical results across R and Python, validating language-independent ground truth for standard statistical methods when input data is identical.

2. **Scoring harness detects a clinically significant error:** Single-case error injection (TC-012, HR +0.3 → score drops to 0.7227) confirms the tolerance system can distinguish correct from incorrect outputs.

3. **ARS alignment is backward-compatible:** The `--ars-output` flag adds CDISC ARS metadata without breaking existing pipelines. ARS envelopes pass schema validation and cross-language consistency checks.

4. **CI automation ensures long-term reproducibility:** The GitHub Actions workflow prevents silent regressions.

5. **Level 2 hybrid scoring is a viable model:** TC-004 (SAP drafting) and TC-005 (TFL QC review) specifications demonstrate that structured rubric + LLM-as-judge + human review can evaluate tasks beyond pure computation.

6. **Comprehensive compliance and safety rules catch systematic errors:** The 194 compliance rules and safety configurations extend beyond numerical comparison to identify issues in table structure, labeling, population filters, and cross-TFL consistency.

---

## 5. Discussion

### 5.1 Positioning Within the Industry Landscape

This benchmark fills a critical gap identified across multiple 2026 industry venues. At PharmaSUG 2026, at least four papers addressed agentic AI for TFL generation (AI-206, AI-123, AI-438, AI-207), yet none proposed a standardized evaluation methodology. Each vendor evaluated their own systems using proprietary test sets, making cross-comparison impossible.

Our benchmark provides the first standardized, multilingual, regulatory-aware evaluation framework for TFL programming agents. The 20 Level 1 test cases cover the most common TFL types in oncology trials. Each includes ground truth implementations in R and Python (with SAS reference scripts), with automated scoring against tolerances derived from regulatory standards.

The regulatory dimension is particularly timely. The FDA-EMA Good AI Practice guidance (January 2026) establishes 10 principles for risk-based AI governance. Principle 3 (adherence to standards) and Principle 8 (risk-based performance assessment) directly motivate our compliance and safety scoring dimensions. The EU AI Act, with provisions from August 2026, classifies clinical AI systems as high-risk, creating an urgent need for standardized verification tools.

**Relationship to complementary efforts:** This benchmark is part of a broader WG effort that includes TrialDesignBench (BBSW-org, 2026), which focuses on statistician-developed rubrics for evaluating AI on protocol and SAP design tasks. While TrialDesignBench evaluates design judgment through human expert grading, our benchmark provides the TFL-level verification layer. Together, these efforts span the evaluation stack from automated numerical verification to human-expert design assessment.

### 5.2 Key Findings from Benchmark Development

**Finding 1: Cross-language numerical consistency requires shared data.** All 20 Level 1 TCs achieve 1.0000 R↔Python verification on shared input data, confirming that standard statistical methods (KM estimation, binomial proportions, Cox PH) produce identical results when using standard packages (R `survival`, Python `lifelines`) on identical input. This finding has practical implications: organizations can validate AI-generated TFL code in one language and deploy in another with confidence, provided the same input data is used.

**Finding 2: The scoring harness detects clinically significant errors.** Error injection testing on TC-012 (HR +0.3 bias → score 0.7227) confirms the framework is neither too lenient (allowing clinically significant errors) nor too strict (penalizing floating-point noise). However, this is a single-case validation; systematic error injection across all TCs with varying effect sizes is needed.

**Finding 3: ARS alignment is feasible without breaking backward compatibility.** The `--ars-output` flag wraps existing numerical results in CDISC ARS v1.0 metadata without modifying underlying computations. An end-to-end proof-of-concept (Day 49) demonstrates schema-valid ARS output, cross-language ARS consistency, and scoring harness integration via `unwrap_ars()`.

**Finding 4: Compliance rules are extensible.** The YAML-based rule configuration allows organizations to add therapeutic-area-specific or sponsor-specific rules without modifying the scoring harness code.

**Finding 5: Level 2 evaluation requires hybrid approaches.** TC-004 and TC-005 specifications demonstrate that auto-scoring (~60%), LLM-as-judge (~25%), and human expert review (~15%) can be combined for interpretive tasks. The TC-005 error injection framework is now fully implemented with 3 parametric variants, 7 error injection functions covering A/B/C error classes, and automated scoring across detection, classification, and location accuracy. End-to-end pipeline testing confirms correct error injection, variant consistency, and scoring validity (perfect agent response = 1.0000, partial = 0.7292, empty = 0.0000). The LLM-as-judge methodology (model selection, prompt template, inter-rater reliability assessment) remains to be finalized.

**Finding 6: Projected cost-accuracy spectrum shows wide variation.** At current API pricing, estimated cost per TFL ranges from ~$0.50 (DeepSeek V4) to ~$35 (GPT-4 class models). **These are projections, not measured results** — formal efficiency benchmarking is planned for Phase 2.

### 5.3 Limitations

1. **SAS implementations are reference-only.** All 16 SAS scripts follow standard SAS programming conventions but have not been executed due to licensing constraints. Cross-language verification is currently R↔Python only.

2. **Level 1 tests computation, not code generation or design reasoning.** The benchmark evaluates whether an agent produces the correct numerical output, not whether it demonstrates design judgment, writes maintainable code, or interprets SAP requirements. The "agentic" label for Level 1 is limited — these are reproduction tasks.

3. **Level 2 TC-005 is implemented; TC-004 and TC-006 specifications are complete.** The TC-005 error injection framework, TFL package generator, and auto-scorer are fully functional with end-to-end pipeline tests passing. TC-006 (sample size re-estimation) specification is complete with 10 parametric variants; ground truth implementation is pending. LLM-as-judge integration and human review infrastructure for Level 2 require additional effort.

4. **Human baseline data has not been collected.** Efficiency targets and reference baselines are estimated from the authors' experience and projected API pricing, not measured from actual human programmer or agent runs.

5. **Contamination risk for standard methods.** KM, log-rank, and Cox PH are extensively represented in model training data. Parametric variants (different seeds, sample sizes) mitigate but do not eliminate this risk.

6. **Oncology-focused scope.** All test cases use oncology endpoints (PFS, OS, ORR, RECIST 1.1). Generalization to other therapeutic areas requires additional test case development.

7. **Single-case error injection validation.** Only one TC has been validated via error injection. A systematic study across all TCs is needed to confirm that tolerance values are appropriate for each test case.

8. **No confidence intervals on scores.** Scoring is deterministic (exact pairwise comparison within tolerances), but the absence of confidence intervals limits generalizability inferences.

### 5.4 Comparison with Existing Benchmarks

| Benchmark | Domain | Gap Our Benchmark Fills |
|---|---|---|
| SWE-bench | Software engineering | No statistical correctness or regulatory compliance |
| GAIA | General AI | No clinical domain specificity |
| AgentBench | Agent capabilities | No clinical trial domain knowledge |
| HealthBench | Medical decisions | No TFL programming or statistical accuracy |
| BRIDGE | Clinical NLP | No statistical programming or R/SAS/Python |

Our benchmark is unique in combining statistical correctness, regulatory compliance, safety and robustness, and operational efficiency in a single evaluation framework for clinical trial TFL programming.

### 5.5 Future Directions

**Phase 2 (Days 33–45):** Implement Level 2 test cases. TC-005 error injection framework is complete with end-to-end pipeline tests passing. TC-006 (sample size re-estimation) specification complete with 10 variants. Begin human baseline collection from WG volunteers. Run 2–3 frontier models across all Level 1 TCs for initial efficiency measurement. Populate efficiency baselines from actual agent runs.

**Phase 3 (Days 41–50):** Extend ARS compliance to all Level 1 TCs. Implement Level 3 test cases. Begin vendor evaluation pilot with 3–5 vendors (Saama, JDIX/Taimei, Certara, others). **Status:** ARS POC complete (Day 49), Level 3 pending.

**Phase 4 (Days 51–60):** Compile agent evaluation results for publication. Submit to JSM 2027 or ASA Biopharmaceutical Section Workshop.

**Long-term:** Develop a public-facing benchmark server. Integrate with CDISC testing infrastructure. Expand to vaccines, ophthalmology, and neurology. Support additional languages (Julia, JavaScript).

---

## 6. Conclusions

### 6.1 Summary

This benchmark establishes the first standardized, multilingual evaluation framework for agentic AI in clinical trial TFL programming. Across 20 Level 1 test cases spanning efficacy (KM median PFS, overall survival, duration of response, time to progression, disease control rate, best overall response, ORR by subgroup, PFS2, forest plot, waterfall, KM curve), safety (AE summary, exposure, lab shifts, protocol deviation listing, concomitant medications), and general statistics (demographics, stratified log-rank, change from baseline), the benchmark demonstrates that cross-language ground truth can be established with perfect agreement (score = 1.0000) between R and Python implementations on shared data. Sixteen SAS reference scripts provide a foundation for pending trilingual verification.

The scoring framework evaluates four dimensions — statistical correctness (tolerance-based numerical comparison), regulatory compliance (242 TCG/CSR rules), safety and robustness (N-count consistency, denominator validation, cross-TFL agreement, edge case handling), and operational efficiency (cost, time, reliability) — providing a composite score reflecting the real-world demands of clinical trial statistical programming. CDISC ARS alignment has been demonstrated for 13 test cases, with schema validation and cross-language consistency checks validated in the proof-of-concept, establishing a path toward metadata-driven TFL generation.

### 6.2 Implications for the Industry

**For vendors:** The benchmark provides a level playing field for objective comparison. Parametric variants mitigate memorization, and cross-language verification ensures results are not language-specific artifacts.

**For sponsors:** Sponsors can evaluate vendor claims before procurement, monitor AI system performance across versions, and demonstrate due diligence to regulators.

**For regulators:** Encoded compliance rules demonstrate that regulatory requirements can be operationalized into testable assertions.

**For statistical programmers:** The benchmark validates that AI can produce numerically correct TFL outputs. However, Level 2 and 3 test cases demonstrate that human expertise remains essential for SAP interpretation, QC review, and regulatory judgment.

### 6.3 Limitations and Caveats

1. **SAS not executed in CI.** SAS reference implementations exist for 16 test cases but no license is available on the CI runner.
2. **Computation, not code quality.** The benchmark evaluates numerical outputs, not code maintainability or design judgment.
3. **Level 2 scoring infrastructure complete.** TC-004 (SAP drafting) auto-scorer implements 8 auto-scorable criteria with LLM-judge prompt template. TC-005 (TFL QC) error injection framework is fully functional. TC-006 (SSR) has complete cross-language ground truth and scoring. All three Level 2 TCs now have auto-scoring capability.
4. **SAS reference scripts complete for all Level 1 TCs.** 21 SAS reference scripts cover every Level 1 test case (pending licensed execution for verification).
4. **Reference baselines estimated, not measured.** Efficiency targets and reference agent run baselines are projected from API pricing and author experience. Human baseline data collection is planned.
5. **Oncology-focused.** Generalization requires additional test case development.
6. **Contamination risk partially mitigated.** Parametric variants help but standard methods remain at risk.
7. **Single-case error injection validation.** Systematic multi-TC validation is needed.

### 6.4 Recommendations

1. **WG adoption.** The ASA Biopharm AI/ML Working Group should formally adopt this benchmark as a reference evaluation framework for agentic AI in TFL programming.

2. **Vendor evaluation pilot.** Invite 3–5 vendors to run the benchmark under controlled conditions.

3. **Human baseline study.** Recruit 5–10 WG statistical programmers to establish reference performance.

4. **SAS CI integration.** Partner with an organization with SAS licensing for trilingual verification.

5. **Therapeutic area expansion.** Develop test case packages for vaccines, ophthalmology, and neurology.

6. **Publication and dissemination.** Submit to JSM 2027 or ASA Biopharmaceutical Section Workshop.

---

## 7. References

1. CDISC. Analysis Results Standard (ARS) v1.0. https://www.cdisc.org/standards/foundational/analysis-results-standard
2. FDA, EMA. Joint Guiding Principles of Good AI Practice in Drug Development. January 2026.
3. European Union. AI Act, Annex III (High-Risk Classification). Applicable August 2026.
4. PharmaSUG 2026. Proceedings: AI-206 (Agentic AI Framework for SAP-to-TFL), AI-123 (Schema-Preserving TLF Generation), AI-438 (Agentic R in Clinical Trials), AI-207 (Azure OpenAI for Statistical Programming).
5. Insights Engineering. `cards` R Package — Analysis Results Data. https://insightsengineering.github.io/cards/
6. Saama Technologies. TLF Analyzer — Everest Group Innovation Watch 2026.
7. PHUSE US Connect 2026. "The Role of Standards in a World of Agentic AI."
8. CDER. 2026 Guidance Agenda — AI/ML Quality Considerations.
9. Jimenez et al. SWE-bench: Can Language Models Resolve Real-World GitHub Issues? ICLR 2024.
10. Mialon et al. GAIA: A Benchmark for General AI Assistants. arXiv:2311.12983.
11. Liu et al. AgentBench: Evaluating LLMs as Agents. ICLR 2024.
12. HealthBench: A Benchmark for Evaluating AI in Clinical Decision-Making. 2025.
13. BRIDGE: Multilingual Clinical NLP Benchmark. 2025.
14. BBSW-org. TrialDesignBench: Community-Driven Benchmark for AI in Clinical Trial Design. https://github.com/BBSW-org/TrialDesignBench. 2026.
15. ICH. ICH E3: Structure and Content of Clinical Study Reports.
16. CDISC. ADaM Implementation Guide v1.1.
17. FDA. Study Data Technical Conformance Guide.
18. Chen et al. CDISC ARS: Implementation Experiences and Lessons Learned. PHUSE 2025.
19. FDA-EMA. Joint Pilot Program for AI-Enabled Drug Development Tools. 2025.
20. ASA Biopharmaceutical Section AI/ML Working Group. Agentic AI in Clinical Development Workstream. https://github.com/doublerobust/ASAbiop-AIML-Agentic. 2026.

---

## Appendix A: Test Case YAML Templates

Full YAML specifications for all test cases are available in the repository at `benchmarks/test-case-design.md`.

## Appendix B: Scoring Tolerance Specifications

Complete tolerance specifications are available in `benchmarks/scoring-harness/tolerances.yaml`.

## Appendix C: CI Pipeline Configuration

The cross-language verification GitHub Actions workflow is at `.github/workflows/cross-language-verify.yml`.

## Appendix D: ARS Mapping Tables

ARS concept-to-implementation mappings are documented in `benchmarks/cdisc-ars-alignment.md`.
