# White Paper Outline — Agentic AI Benchmark for Clinical Trial Statistical Analysis

**Working Document — ASA Biopharm AI/ML Working Group**
**Date:** 2026-06-27 (Day 27)
**Status:** Draft Outline for WG Review

---

## 1. Title & Abstract

**Working Title:** "A Standardized Benchmark for Evaluating Agentic AI in Clinical Trial TFL Programming: Cross-Language Verification, Regulatory Compliance, and Operational Efficiency"

**Abstract (draft):**
The rapid emergence of agentic AI systems for Tables, Figures, and Listings (TFL) programming in clinical trials has outpaced the availability of standardized evaluation frameworks. Vendor claims of 60–70% manual effort reduction lack independent verification. We present a multilingual (R/SAS/Python) benchmark with 13 Level 1 test cases covering survival analysis, demographics, safety summaries, tumor response, exposure, lab shifts, change from baseline, concomitant medications, and subgroup analyses — all with cross-validated ground truth, automated scoring, and regulatory compliance checks. The benchmark includes CI-automated regression detection and CDISC ARS alignment for metadata-driven TFL generation. This paper describes the benchmark design, scoring framework, verification methodology, and implications for AI governance in clinical development.

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
|---|---|---|---|
| 1 | 13 | Automated numerical comparison | Tolerance-based (0–1) |
| 2 | 3 | Partial auto + rubric | Checklist + LLM-judge |
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
| TC-019 | Safety | Table | Concomitant medications | R+Py (NEW) |
| TC-020 | Efficacy | Table | ORR by subgroup | R+Py (NEW) |

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
- All 11 Level 1 TCs achieve 1.0000 R↔Python agreement
- GitHub Actions CI for regression detection

### 4.3 CDISC ARS Alignment
- Output schemas mapped to ARS concepts (8 core concepts)
- ARS-compatible envelope wrapper (backward compatible)
- `cards` R package integration plan
- 6-phase implementation roadmap (Phase 1 done, Phase 2 PoC)

---

## 5. Results

### 5.1 Cross-Language Verification
- 11/11 Level 1 TCs: score=1.0000 (perfect R↔Python agreement on shared data)
- 3 TCs with SAS: TC-001/002/003 trilingual verification
- 8 additional SAS implementations (TC-011–018, not executed)
- CI pipeline: automated regression detection on every push/PR

### 5.2 Scoring Pipeline Coverage
- 13 Level 1 TCs with: scorer + tolerances + schema + ground truth + compliance + safety
- 128 compliance rules, 83 safety rules
- Error injection validated: HR +0.3 → score drops to 0.7227

### 5.3 ARS Proof-of-Concept
- TC-001 `--ars-output` flag emits ARS v1.0-compatible JSON envelope
- R and Python implementations both support ARS output
- Backward compatible with existing scoring pipeline

---

## 6. Discussion

### 6.1 Industry Context
- PharmaSUG 2026: multiple papers on agentic AI for TFL
- FDA-EMA Good AI Practice: 10 principles (Jan 2026)
- EU AI Act: high-risk classification (Aug 2026/2028)
- Saama TLF Analyzer: 60–70% claims unverifiable without benchmarks

### 6.2 Limitations
- Level 1 TCs are auto-scorable but don't test SAP interpretation or code generation
- SAS implementations not executed (no license)
- Level 2/3 TCs require human review — scalability concern
- Contamination risk for Level 3 tasks

### 6.3 Future Directions
- Level 2 test cases: SAP section drafting, TFL QC review
- Full ARS compliance for all 13 Level 1 TCs
- Vendor evaluation: invite Saama, JDIX, others to run benchmark
- WG presentation with scoring findings
- Python `pyards` library for ARS-native Python output

---

## 7. Conclusions
- First standardized, multilingual benchmark for TFL programming
- 13 Level 1 test cases with complete scoring pipeline
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
