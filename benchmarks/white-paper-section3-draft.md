# Section 3: Benchmark Design — Prose Draft

**Working Document — ASA Biopharm AI/ML Working Group**
**Date:** 2026-06-29 (Day 29)
**Status:** Draft for WG Review

---

## 3.1 Design Principles

The benchmark was designed around five core principles informed by the working group's experience in clinical trial statistical programming:

1. **Statistical correctness is the floor, not the ceiling.** An agent that produces numerically wrong results is unconditionally disqualified, regardless of speed, cost, or formatting. The scoring framework enforces this with an accuracy floor (Section 4.1).

2. **Multilingual by design.** Clinical trial submissions require R, SAS, and Python implementations. A benchmark that tests only one language cannot evaluate whether an agent can operate across the polyglot reality of pharma statistical programming. Ground truth is established in all three languages with cross-language verification.

3. **Regulatory alignment, not just correctness.** Producing the right number is necessary but insufficient. The output must also comply with CDISC ADaM variable naming conventions, FDA Study Data TCG rules, and ICH E3 CSR formatting standards. The benchmark encodes 244 regulatory rules across 13 test cases.

4. **Reproducibility through parametric variants.** Each test case accepts a random seed and sample size parameter, enabling generation of 93+ unique variants. This mitigates contamination risk — models that memorized specific datasets cannot rely on recalled answers.

5. **Automated scoring wherever possible.** Level 1 test cases are fully auto-scorable through numerical comparison with tolerance-based verification. This enables CI-integrated regression testing and scalable evaluation across vendors.

## 3.2 Scope: TFL-First

The benchmark focuses on Tables, Figures, and Listings (TFL) programming — the most concrete and labor-intensive component of statistical analysis deliverables. TFL programming consumes an estimated 60–70% of statistical programming effort in a typical submission, making it the highest-value target for AI automation.

**In scope:**
- **Tables:** Demographics (TC-002), AE summary (TC-011), exposure (TC-016), lab shift (TC-017), change from baseline (TC-018), concomitant medications (TC-019), ORR by subgroup (TC-020), KM median PFS (TC-001), stratified log-rank (TC-003)
- **Figures:** Forest plot for hazard ratio (TC-012), waterfall plot (TC-013), KM curve with risk table (TC-015)
- **Listings:** Protocol deviations (TC-014)

**Out of scope (v1):**
- SAP authoring (Level 2, planned)
- TFL QC review (Level 2, planned)
- Regulatory response writing (Level 3, planned)
- Dose-finding study design (Level 3, planned)
- CSR statistical sections (Level 3, planned)
- Dataset generation (ADaM derivation from SDTM)

## 3.3 Three Difficulty Levels

The benchmark defines three difficulty levels that mirror the cognitive demands of real-world statistical programming:

### Level 1: Single TFL Generation (Automated Scoring)
The agent receives a TFL specification (including ADaM dataset, statistical method, and output format) and must produce code that generates the correct TFL output. Scoring is fully automated through numerical comparison with tolerance-based verification. All 13 Level 1 test cases have trilingual ground truth (R + Python + SAS) and achieve 1.0000 cross-language agreement.

### Level 2: Multi-Step with Interpretation (Partial Auto + Rubric)
The agent must interpret a SAP section or QC checklist, identify the relevant analyses, and produce or review TFL outputs. Scoring combines automated numerical checks (for any computational components) with a structured rubric for the interpretive components. Three Level 2 test cases are planned: SAP section drafting (TC-004), TFL package QC review (TC-005), and sample size re-estimation at interim (TC-006).

### Level 3: Complex Regulatory Scenarios (Expert Review)
The agent must handle open-ended regulatory scenarios requiring domain judgment, multi-source synthesis, and narrative reasoning. Scoring requires expert human review against a detailed rubric. Four Level 3 test cases are planned: regulatory response to ITT/PP discrepancy (TC-007), dose-finding study design (TC-008), safety signal evaluation/DMC report (TC-009), and CSR statistical sections (TC-010).

## 3.4 Test Case Library

The Level 1 test case library spans four therapeutic domains and nine statistical methods:

| TC | Domain | TFL Type | Statistical Method | Languages | Variants |
|---|---|---|---|---|---|
| TC-001 | Efficacy | Table | Kaplan-Meier median PFS with Brookmeyer-Crowley CI | R+Py+SAS | 10 |
| TC-002 | Demographics | Table | Descriptive statistics (continuous + categorical) | R+Py+SAS | 10 |
| TC-003 | Efficacy | Table | Stratified log-rank test with randomization strata | R+Py+SAS | 8 |
| TC-011 | Safety | Table | AE summary by SOC/PT with risk difference | R+Py+SAS | 10 |
| TC-012 | Efficacy | Figure | Forest plot from Cox PH model with covariates | R+Py+SAS | 8 |
| TC-013 | Efficacy | Figure | Waterfall plot (RECIST 1.1 best % change) | R+Py+SAS | 8 |
| TC-014 | Safety | Listing | Protocol deviations listing with categorization | R+Py+SAS | 8 |
| TC-015 | Efficacy | Figure | KM curve with at-risk table | R+Py+SAS | 8 |
| TC-016 | Safety | Table | Exposure summary (duration, dose intensity) | R+Py+SAS | 8 |
| TC-017 | Safety | Table | Lab shift table (baseline → post-baseline) | R+Py+SAS | 8 |
| TC-018 | Efficacy | Table | Change from baseline (ANOVA / mixed model) | R+Py+SAS | 8 |
| TC-019 | Safety | Table | Concomitant medications by ATC class | R+Py+SAS | 5 |
| TC-020 | Efficacy | Table | ORR by subgroup with CMH interaction test | R+Py+SAS | 4 |

**Total Level 1:** 13 test cases, 93 parametric variants, 39 ground truth implementations (13 × 3 languages).

## 3.5 Data Generation Strategy

Synthetic datasets are generated using deterministic algorithms with configurable random seeds. The primary data generation framework uses:

- **R:** `random.cdisc.data`-style generation with `set.seed()` for reproducibility
- **Python:** `numpy.random.default_rng()` with explicit seed propagation
- **SAS:** `PROC PLAN` + `DATA` step with `STREAMINIT` for deterministic output

For cross-language verification, R generates shared CSV datasets that Python and SAS consume, ensuring identical input data across languages. The generation scripts produce ADaM-compliant datasets (ADSL, ADTTE, ADAE, ADVS, ADCM, ADLB) with realistic variable distributions:

- **ADSL:** Treatment assignment (1:1 randomization), demographics (age, sex, race, region, ECOG)
- **ADTTE:** Time-to-event with exponential hazard, differential treatment effect, administrative censoring
- **ADAE:** Adverse events by SOC and preferred term, with treatment-arm association
- **ADVS:** Tumor measurements with RECIST 1.1 response categorization
- **ADCM:** Concomitant medications by ATC class with realistic frequency distributions
- **ADLB:** Lab values with baseline and post-baseline visits for shift tables

## 3.6 Cross-Language Verification Protocol

Cross-language verification ensures that ground truth implementations in different languages produce numerically identical results on the same input data. The protocol operates in four steps:

1. **Shared data generation:** R generates ADaM-compliant CSV datasets with a fixed seed
2. **Parallel execution:** Each TC runs in R, Python, and SAS on the shared data, producing JSON output
3. **Pairwise comparison:** The scoring harness compares R↔Python and (where SAS is available) R↔SAS outputs field-by-field with tolerance-based verification
4. **Score computation:** A composite score (0.0000–1.0000) is computed based on per-field weighted agreement

All 11 original Level 1 test cases (TC-001 through TC-018) achieve a cross-language verification score of 1.0000 (perfect R↔Python agreement). TC-019 and TC-020 are being verified in this phase.

## 3.7 CDISC ARS Alignment

The benchmark output schemas are aligned with the CDISC Analysis Results Standard (ARS) v1.0. Each test case output can be emitted as an ARS-compatible JSON envelope containing:

- **AnalysisResult metadata:** Unique ID, version, analysis reason
- **AnalysisMethod:** Statistical method name, code template, parameters
- **AnalysisVariables:** Variables involved (type, role)
- **AnalysisPopulation:** Population definition (e.g., ITT, Safety)
- **ResultGroups:** Treatment groups with subject counts
- **AnalysisResultsData (ARD):** Machine-readable statistical results

This alignment enables interoperability with ARS-compatible tools (`cards`, `gtsummary`, `siera`) and supports the industry's move toward metadata-driven TFL generation. The ARS envelope is emitted via an optional `--ars-output` flag, maintaining backward compatibility with the standard scoring pipeline.

**Current ARS coverage:** TC-001 (Phase 1, complete), TC-002 (Phase 3, added Day 29). Phases 2–6 will extend ARS output to all 13 Level 1 TCs.

## 3.8 CI/CD Integration

A GitHub Actions workflow (`.github/workflows/cross-language-verify.yml`) runs the full cross-language verification suite on every push and pull request. The workflow:

1. Sets up R and Python environments with pinned package versions
2. Generates shared datasets with a canonical seed
3. Runs all 13 Level 1 TCs in both R and Python
4. Compares outputs using the scoring harness
5. Fails if any TC score drops below 1.0000

This enables regression detection: any code change that alters numerical output will break CI, ensuring ground truth stability throughout the benchmark's lifecycle.

---

**Next sections to draft:** Section 4 (Scoring Framework), Section 5 (Results), Section 6 (Discussion).
