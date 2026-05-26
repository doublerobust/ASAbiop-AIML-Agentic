# Progress Log — Agentic AI Benchmark for Stats Trial Design, Analysis & Reporting

**Project:** Industry-standard benchmark for evaluating agentic AI in clinical trial statistics
**Started:** 2026-05-25
**Repo:** https://github.com/doublerobust/asa-ai-manuscript (workstream root)

---

## 2026-05-25 — Day 1: Foundation

### 🎯 Assignment
Yue asked in #agentic-ai-wg (Discord) to:
1. Start thinking about how to create an industry-standard benchmark for agentic workflow in statistical trial design, analysis, and reporting
2. Survey other relevant pharma/biotech work
3. Identify what the WG needs to build this into a deliverable
4. Create a dedicated folder with incremental daily updates
5. Set up a daily cron job to continue building

### 🗺️ WG Decisions (from Yue's reply)
- **Scope priority:** TFL programming (Tables, Figures, Listings) — most concrete demand
- **Languages:** R + SAS + Python — multilingual by nature in pharma
- **Repo:** Existing ASA WG repo (`asa-ai-manuscript/benchmark/`)

### ✅ What Got Created (v1, corrected)
- **`benchmark/`** directory inside the existing asa-ai-manuscript repo
- **`benchmark-framework-v1.md`** — Updated with TFL specialization and multilingual scoring
- **`relevant-work.md`** — Catalog of existing benchmarks and pharma initiatives
- **`tools-packages.md`** — Multi-language tooling survey (R packages + SAS + Python)
- **`progress-log.md`** — This file
- **`README.md`** — Project overview, TFL-first focus

### 🔍 Key Research Findings

1. **No existing benchmark covers this space.** SWE-bench, GAIA, AgentBench — none test statistical correctness + regulatory compliance + agentic workflow.

2. **Vendors are shipping but can't self-evaluate.** JDIX (TFL Reviewer), TrialMind, Taimei (INSIGHT), EDETEK all claim AI agent capabilities. No standardized benchmarks exist.

3. **TFL programming is the consensus 

## 2026-05-26 — Day 2: Test Case Design

### 🎯 Assignment
Cron job triggered daily benchmark development. Today's rotation: **Test Case Design** — draft 5-10 concrete test cases at all 3 difficulty levels.

### ✅ What Got Created
- **`test-case-design.md`** — Comprehensive test case library document with:
  - 6 design principles for benchmark test cases
  - Standardized YAML template for every test case in the library
  - **3 Level 1 test cases** (auto-scorable): KM median PFS estimation, baseline demographics table, stratified log-rank test
  - **3 Level 2 test cases** (partial auto + rubric): SAP section drafting, TFL package QC review, sample size re-estimation at interim
  - **4 Level 3 test cases** (expert review): Regulatory response to ITT/PP discrepancy, dose-finding study design, safety signal evaluation/DMC report, CSR statistical sections
  - Test case distribution matrix with domain/method/coverage mapping
  - Data generation strategy using `random.cdisc.data` and `simstudy`
  - Contamination mitigation strategies (parametric variants, seed randomization, error injection)
  - Scoring automation feasibility analysis per test case
  - Next steps for WG review and implementation

### 🔍 Key Research Findings
1. **Admiral release schedule confirmed:** pharmaverse admiral has Q2 2026 release mid-June 2026, extension packages include `admiralonco`, `admiralophtha`, `admiralvaccine`, `admiralpeds`, `admiralmetabolic`, `admiralneuro` — perfect for building oncology-focused test cases

2. **Web search unavailable** (DuckDuckGo bot detection); relied on direct web_fetch of pharmaverse GitHub and CDISC standards pages — both are stable references

3. **Contamination is a real concern** for Level 3 tasks — SAP sections, CSR writing, and regulatory responses all involve domain language that frontier models may have seen during training. Mitigation via parametric variants is essential.

4. **93 parametrizable variants** across the 10 test cases means the benchmark can generate thousands of unique evaluations by combining variant parameters with different random seeds.

5. **Auto-scoring is feasible for Level 1**, partially feasible for Level 2 (checklist + numerical), and requires expert human review for Level 3. This stratification is expected and aligns with the benchmark's design.

### 📊 Test Case Library Summary

| Level | Count | Auto-Score | Partial Score | Expert Review | Est. Variants |
|---|---|---|---|---|---|
| 1 | 3 | 3 | 0 | 0 | 30 |
| 2 | 3 | 0 | 2 | 1 | 35 |
| 3 | 4 | 0 | 1 | 3 | 28 |
| **Total** | **10** | **3** | **3** | **4** | **93** |

### ⚡ Decisions to Surface

| Question | Recommendation |
|---|---|
| Should we ground truth in R only, or add SAS cross-validation? | R primary (pharmaverse + survival), SAS cross-validation for regulatory-critical TCs (TC-001, TC-003, TC-007) |
| Auto-scoring for Level 2 — LLM-as-judge or strict checklist? | Checklist-based with GPT-as-judge fallback for free-text; numerical parts auto-scored |
| Human baseline: recruit WG volunteers? | Yes — need 2-3 biostatisticians for TC-001 through TC-003 validation |
| How many test cases for v1? | 20-50 target. Current 10 is a strong start. Next: safety monitoring, multiplicity, estimands |

### 🔮 Plan for Day 3
1. Deep-dive into **Statistical Correctness** — ground truth verification protocol, edge cases, floating-point tolerance
2. Build out the verification protocol from Section 5 of the framework with concrete edge-case test vectors
3. Research numerical tolerance standards in regulatory submissions
4. Draft reference implementation for TC-001 (KM median PFS) as a reference coding example
5. Update this log

---

## 2026-05-25 — Day 1: Foundation (corrected)

### 🎯 Assignment Correction (from Yue's reply)
- **Scope priority:** TFL programming — not all three pillars at once
- **Languages:** R + SAS + Python — multilingual, not R-only
- **Repo:** https://github.com/doublerobust/ASAbiop-AIML-Agentic (`benchmarks/`)

### ✅ What Was Fixed
- Moved benchmark from standalone `agentic-ai-wg-benchmark/` → `asa-ai-manuscript/benchmark/`
- All documents updated for TFL-first focus and multilingual scoring
- Cron job corrected to point to proper path with TFL focus
- Git committed and pushed

---

## 2026-05-26 — Day 2: Test Case Design (TFL-focused, multilingual)

### ✅ What Was Produced
- **`test-case-design.md`** — 10 fully specified test cases across 3 levels:
  - Level 1 (3): KM median PFS, demographics table, stratified log-rank
  - Level 2 (3): SAP section, TFL QC review, sample size re-estimation
  - Level 3 (4): Regulatory response (ITT/PP), dose-finding design, safety/DMC report, CSR section
- Ground truth scripts in **R, SAS, and Python** for auto-scorable cases
- Contamination mitigation (parametrizable params, seed randomization, error injection pools)
- Full YAML template with scoring metadata
- Scoring automation feasibility assessment per test case
- Expert review rubrics for Level 3 human-scored cases

### 🗂️ Final File Structure
```
benchmark/
├── README.md
├── benchmark-framework-v1.md
├── test-case-design.md
├── progress-log.md
├── relevant-work.md
├── tools-packages.md
└── references/
```

### 🔮 Plan for Day 3
1. **Statistical correctness deep-dive** — cross-validate ground truth in R vs SAS vs Python
   - Identify any language-specific numerical differences (floating point, tie handling, censoring conventions)
   - Document tolerance standards for regulatory submissions
2. Build first automated scoring harness for TC-001 (KM median PFS)
3. Research: SAS vs R vs Python cross-validation frameworks in pharma

---
