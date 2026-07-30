# White Paper Outline — Agentic AI Benchmark for Clinical Trial Statistical Analysis

**Working Document — ASA Biopharm AI/ML Working Group**
**Date:** 2026-07-30 (Day 58 — refreshed after project audit)
**Status:** Draft Outline for WG Review — TC counts updated to current (27 L1, 4 L2, 4 L3)

---

## 1. Title & Abstract

**Working Title:** "A Standardized Benchmark for Evaluating Agentic AI in Clinical Trial TFL Programming: Cross-Language Verification, Regulatory Compliance, and Operational Efficiency"

**Abstract (draft):**
The rapid emergence of agentic AI systems for Tables, Figures, and Listings (TFL) programming in clinical trials has outpaced the availability of standardized evaluation frameworks. Vendor claims of 60–70% manual effort reduction lack independent verification. We present a multilingual (R and Python, with SAS reference scripts) benchmark with 27 Level 1 test cases covering survival analysis, baseline demographics, safety summaries, tumor response, exposure, lab shifts, change from baseline, concomitant medications, subgroup analyses, longitudinal tumor size trajectories, AE by severity, dose intensity, immune-related AEs, sufficient follow-up assessment, time-to-first-treatment, and ORR with interaction testing — all with cross-language-verified ground truth achieving perfect (1.0000) R↔Python agreement on shared data. SAS reference scripts are available for all Level 1 test cases. An additional 4 Level 2 test cases address SAP section drafting (TC-004), TFL quality control review (TC-005), sample size re-estimation (TC-006), and composite efficacy table (TC-035). Four Level 3 test cases (regulatory response, dose-finding design with BOIN, safety signal evaluation/DMC report, and CSR statistical sections) are implemented with R+Python ground truth, expert rubric scorers, and reference documents. CDISC ARS v1.0 alignment is demonstrated for 33 test cases (68 ARS envelope files). This paper describes the benchmark design, scoring framework, verification methodology, and implications for AI governance in clinical development.

---

## 2. Introduction & Motivation

### 2.1 The TFL Programming Challenge
- TFL programming: 60–70% of statistical programming effort
- Industry shift from manual coding to AI-assisted generation
- Regulatory pressure: FDA-EMA Good AI Practice (Jan 2026), EU AI Act (Aug 2026/2028)
- Vendor landscape: Saama TLF Analyzer, JDIX JDIM, Certara, EDETEK, TrialMind

### 2.2 The Benchmark Gap
- No existing benchmark covers TFL programming correctness
- SWE-bench, GAIA, AgentBench: general coding, not clinical statistics
- HealthBench: medical decisions, not statistical programming
- BRIDGE: multilingual clinical NLP, not TFL generation
- PharmaSUG 2026: industry explicitly called for "standardized evaluation benchmarks for governance"

### 2.3 Objectives
1. Define a reproducible, multilingual benchmark for TFL programming
2. Establish cross-language ground truth (R + Python + SAS)
3. Build automated scoring with regulatory compliance checks
4. Align with CDISC standards (SDTM, ADaM, ARS)
5. Provide a framework for AI agent evaluation in clinical development

---

## 3. Benchmark Design

### 3.1 Scope: TFL-First
- Tables: demographics, AE summary, exposure, shift, CFB, concomitant meds, PD listing
- Figures: KM curve, waterfall plot, forest plot
- Listings: protocol deviations
- Statistical methods: KM estimation, Cox PH, log-rank, chi-square, t-test, CMH

### 3.2 Test Case Library

| Level | Count | Description | Scoring |
|---|---|---|---|---|
| 1 | 27 | Automated numerical comparison | Tolerance-based (0–1) |
| 2 | 4 | Partial auto + rubric | Checklist + LLM-judge |
| 3 | 4 | Expert review | Human rubric |

### 3.3 Three Difficulty Levels
- **Level 1:** Single TFL, auto-scorable, exact numerical comparison
- **Level 2:** Multi-step with SAP/QC interpretation, partial auto-scoring
- **Level 3:** Complex regulatory scenarios requiring expert judgment

### 3.4 Test Case Inventory (Level 1)

| TC | Domain | TFL Type | Method | Languages |
|---|---|---|---|---|
| TC-001 | Efficacy | Table | KM Median PFS | R+Py+SAS |
| TC-002 | Demographics | Table | Summary stats | R+Py+SAS |
| TC-003 | Efficacy | Table | Stratified log-rank | R+Py+SAS |
| TC-011 | Safety | Table | AE summary by SOC/PT | R+Py+SAS |
| TC-012 | Efficacy | Figure | Forest plot HR (Cox PH) | R+Py+SAS |
| TC-013 | Efficacy | Figure | Waterfall (RECIST 1.1) | R+Py+SAS |
| TC-014 | Safety | Listing | Protocol deviations | R+Py+SAS |
| TC-015 | Efficacy | Figure | KM curve + risk table | R+Py+SAS |
| TC-016 | Safety | Table | Exposure summary | R+Py+SAS |
| TC-017 | Safety | Table | Lab shift table | R+Py+SAS |
| TC-018 | Efficacy | Table | Change from baseline | R+Py+SAS |
| TC-019 | Safety | Table | Concomitant medications | R+Py+SAS |
| TC-020 | Efficacy | Table | ORR by subgroup | R+Py+SAS |
| TC-021 | Efficacy | Table | TTP (death censored) | R+Py+SAS |
| TC-022 | Efficacy | Table | DOR (responders only) | R+Py+SAS |
| TC-023 | Efficacy | Table | DCR (CR+PR+SD) | R+Py+SAS |
| TC-024 | Efficacy | Table | OS KM Median | R+Py+SAS |
| TC-025 | Efficacy | Table | BOR Summary (RECIST 1.1) | R+Py+SAS |
| TC-026 | Efficacy | Table | PFS2 (sequential) | R+Py+SAS |
| TC-027 | Safety | Table | Duration of study drug | R+Py+SAS |
| TC-028 | Efficacy | Figure | Tumor size by cycle (spaghetti) | R+Py+SAS |
| TC-029 | Safety | Table | AE by severity (Grade 3+) | R+Py+SAS |
| TC-030 | Efficacy | Table | ORR with interaction test | R+Py+SAS |
| TC-031 | Safety | Table | Time-to-first-treatment | R+Py+SAS |
| TC-032 | Safety | Table | Immune-related AE summary | R+Py+SAS |
| TC-033 | Safety | Table | Dose intensity summary | R+Py+SAS |
| TC-034 | Safety | Table | Sufficient follow-up assessment | R+Py+SAS |

---

## 4. Scoring Framework

### 4.1 Four Scoring Dimensions

1. **Statistical Correctness** (weight: 0.40)
   - Numerical tolerance-based comparison
   - Per-field weights (key statistics weighted higher)
   - Cross-language verification (R↔Python↔SAS)

2. **Regulatory Compliance** (weight: 0.25)
   - ADaM variable mapping (86 TCG rules)
   - TCG checklist adherence (128 rules total)
   - CSR formatting (42 CSR rules)

3. **Safety & Robustness** (weight: 0.20)
   - N-count consistency (42 rules)
   - Denominator validation (11 TCs)
   - Cross-TFL agreement (14 pairs)
   - Edge case handling (16 scenarios)

4. **Operational Efficiency** (weight: 0.15)
   - Cost per correct output
   - Time to first correct output
   - Retry count / reliability
   - Human review overhead

### 4.2 Cross-Language Verification Protocol
- Shared CSV datasets (R-generated, Python-loaded)
- Per-TC pairwise comparison with scoring harness
- All 27 Level 1 TCs achieve 1.0000 R↔Python agreement on shared data
- GitHub Actions CI for regression detection

### 4.3 CDISC ARS Alignment
- 33 TCs with ARS envelope wrappers (68 files: R + Python per TC)
- Standalone generator scripts for Level 1, Level 2, and Level 3 TCs
- All 68 ARS files pass schema validation
- ARS coverage: 94% of numerical TCs (TC-004/005 are qualitative — N/A)

---

## 5. Results

### 5.1 Cross-Language Verification
- 27/27 Level 1 TCs: score=1.0000 (perfect R↔Python agreement on shared data)
- 27 SAS reference scripts written (not executed — no SAS license on Mac Studio)
- CI pipeline: automated regression detection on every push/PR

### 5.2 Scoring Pipeline Coverage
- 27 Level 1 TCs with: scorer + tolerances + schema + ground truth + compliance + safety
- 242 compliance rules, 96 safety rules
- Error injection validated: HR +0.3 → score drops to 0.7227

### 5.3 ARS Coverage
- 33 TCs with generated ARS envelope files (68 total: R + Python per TC)
- Standalone ARS envelope generators for Level 1, Level 2, and Level 3 TCs
- All 68 ARS files pass schema validation
- R↔Python cross-language ARS consistency verified for all 33 TCs

---

## 6. Discussion

### 6.1 Industry Context
- PharmaSUG 2026: multiple papers on agentic AI for TFL
- FDA-EMA Good AI Practice: 10 principles (Jan 2026)
- EU AI Act: high-risk classification (Aug 2026/2028)
- Saama TLF Analyzer: 60–70% claims unverifiable without benchmarks

### 6.2 Limitations
- Level 1 TCs are auto-scorable but don't test SAP interpretation or code generation
- SAS implementations not executed (no license; reference-only)
- Level 2/3 TCs require human review — scalability concern
- Contamination risk for all levels (mitigated via parametrizable variants)
- Frontier model evaluation not yet run — all scores are infrastructure verification, not empirical results

### 6.3 Future Directions
- Level 3 expert rubric scoring: run frontier models and collect LLM-judge + human scores
- Full ARS compliance via native `--ars-output` flag in ground truth scripts (vs. standalone generators)
- Vendor evaluation: invite Saama, JDIX, others to run benchmark
- WG presentation with frontier model results
- TPP-style DR×FPR curves for interpretable scoring visualizations

---

## 7. Conclusions
- First standardized, multilingual benchmark for TFL programming
- 27 Level 1 test cases with complete scoring pipeline
- Cross-language verification at 1.0000 accuracy
- CI automation for regression detection
- CDISC ARS alignment for interoperability
- Ready for WG pilot evaluations

---

## 8. References
1. CDISC Analysis Results Standard v1.0 — https://www.cdisc.org/standards/foundational/analysis-results-standard
2. FDA-EMA Good AI Practice Principles (Jan 2026)
3. EU AI Act, Annex III (Dec 2027) and Annex I (Aug 2028)
4. PharmaSUG 2026 Proceedings (AI-206, AI-123, AI-438)
5. `cards` R package — https://insightsengineering.github.io/cards/
6. Saama TLF Analyzer — Everest Group Innovation Watch 2026
7. PHUSE US Connect 2026 — "The Role of Standards in a World of Agentic AI"
8. CDER 2026 Guidance Agenda — AI/ML Quality Considerations

---

## Appendix A: Test Case YAML Templates
## Appendix B: Scoring Tolerance Specifications
## Appendix C: CI Pipeline Configuration
## Appendix D: ARS Mapping Tables

---

**Timeline:** Draft by Day 30, WG review by Day 35, submit to ASA by Day 40
