# An Evaluation Framework for AI-Assisted Clinical Trial Output Review: A Benchmark Blueprint

**Working title** (per WG discussion)
**Version:** 0.2 — incorporating WG design principles & error taxonomy
**Date:** 2026-05-25
**Author:** Yue Shentu, with contributions from WG members (anonymized)
**Editorial:** Natasha (on behalf of ASA Biopharm AI/ML Working Group — Agentic AI Workstream)

---

## Priority Scope: TFL Review

Per WG direction, the benchmark **starts with TFL review** (Tables, Figures,
Listings) — evaluating AI agents that check clinical trial output for
correctness, consistency, and regulatory compliance. SDTM/ADaM review is
secondary scope for later phases.

**Languages:** R + SAS + Python (multilingual)

---

## Table of Contents

1. [Introduction & Motivation](#1-introduction--motivation)
2. [Guiding Principles](#2-guiding-principles)
3. [Three Deliverables](#3-three-deliverables)
4. [Deliverable 1: Error Taxonomy](#4-deliverable-1-error-taxonomy)
5. [Deliverable 2: Example Cases](#5-deliverable-2-example-cases)
6. [Deliverable 3: Scoring Methodology](#6-deliverable-3-scoring-methodology)
7. [The "Exam" Framing](#7-the-exam-framing)
8. [Implementation Guide](#8-implementation-guide)
9. [Open Questions](#9-open-questions-wg-discussion)
10. [Relationship to Prior Work](#10-relationship-to-prior-work)
11. [Context: WG Discussions That Shaped This](#11-context-wg-discussions-that-shaped-this)
12. [Dimension Reference (Previous v0.1)](#12-dimension-reference-previous-v01)

---

## 1. Introduction & Motivation

### 1.1 The Problem

AI tools for SDTM/ADaM/TLF review are proliferating rapidly, but there is
no standard way to evaluate them. Vendors make claims about accuracy;
sponsors cannot compare across tools; and current evaluations focus on
accuracy metrics that fail to reflect real-world review workflows.

### 1.2 Why the ASA WG Owns This

This working group is uniquely positioned:
- **Pharma-led, not vendor-led** — evaluation standards must come from pharma, not vendors
- Built on domain expertise — practicing biostatisticians who understand
  what errors matter and why
- Credible to regulators — ASA Biopharm has existing relationships
- Cross-industry — spans pharma, CRO, academia, and vendors

### 1.3 Scope: What This Is and Isn't

| This IS | This IS NOT |
|---|---|
| An evaluation framework — methodology + examples | A certification body |
| A benchmark ("exam") for AI agents that review clinical trial output | A one-size-fits-all pass/fail test |
| Public methodology; internal data stays private | A replacement for company-specific validation |
| A shared vocabulary across companies and vendors | A guarantee of real-world performance |

---

## 2. Guiding Principles

### P1. Human Validation is the Gold Standard

As Rodman et al. (2025, *NEJM AI*) argue, synthetic-only benchmarks risk
becoming "machine simulacra" — measuring performance on artificial tasks
that don't reflect real-world complexity. Every component of this benchmark
requires human adjudication:

- **Error planting:** Human statisticians define realistic errors based on
  actual QC experience
- **Scoring:** Human experts validate automated scoring, especially for
  context-dependent errors
- **Threshold setting:** Based on real review practice, not arbitrary cutoffs

### P2. Context-Dependent Performance Thresholds

As Parsa et al. (2026, *NEJM AI* — Health AI TPP framework) establish,
"good enough" depends on context:
- Reviewer time available
- False positive burden the team can absorb
- Study phase (Phase 1 vs. submission)
- Criticality of the endpoint

The benchmark should show **where the tool lands on a (detection rate ×
false positive rate) curve**. Each company calibrates their own threshold.

### P3. Methodology Open, Test Data Private

- Methodology is fully open and specified
- Example cases are public and synthetic
- Company-specific test instances built from internal data remain private
- Prevents gaming while enabling informed evaluation

### P4. Define the Exam, Not the Curriculum

This framing emerged from WG discussion: the benchmark specifies what
agents need to demonstrate, not how they should achieve it. Vendors and
internal teams are free to implement however they choose. The market
separates those who can deliver from those who just benchmark well.

### P5. Pharma-Led Independence

The benchmark must not favor any specific vendor, LLM, agent framework, or
programming language. Independence is the core value proposition.

---

## 3. Three Deliverables

Per WG consensus, the
benchmark produces three deliverables:

| # | Deliverable | Description | Visibility |
|---|---|---|---|
| **1** | **Error Taxonomy** | Catalog of realistic TFL errors by severity class (A/B/C) | 📄 Published paper |
| **2** | **Example Cases** | 2-3 full synthetic TFL packages with planted errors | 📦 Public dataset |
| **3** | **Scoring Methodology** | How to measure and interpret agent performance | 📄 Published paper |

---

## 4. Deliverable 1: Error Taxonomy

A hierarchical catalog of errors that an AI agent might encounter when
reviewing TFL packages in a clinical trial context.

### 4.1 Severity Classification

#### Class A — Critical
*Would change the analysis conclusion or regulatory interpretation.*

| ID | Error Type | Example |
|---|---|---|
| A-01 | Wrong statistical method | Cox PH instead of log-rank for primary analysis |
| A-02 | Incorrect denominator | PP population used instead of ITT |
| A-03 | Mis-specified covariate | Unstratified analysis when SAP specifies stratification |
| A-04 | Wrong comparison / reference arm | Active vs. placebo comparison reversed |
| A-05 | Missing multiplicity adjustment | No alpha correction when multiple endpoints tested |

#### Class B — Major
*Requires correction but is unlikely to change the analysis conclusion.*

| ID | Error Type | Example |
|---|---|---|
| B-01 | Wrong population label | "Safety population" header on ITT-only analysis |
| B-02 | Missing subgroup | SAP-specified subgroup analysis absent from TFL |
| B-03 | Wrong reference arm label | "Active" instead of "Placebo" in figure legend |
| B-04 | Incorrect visit window | Day 28 window labelled as Day 14 |
| B-05 | Wrong confidence interval type | CI computed but not clearly labelled as 95% |
| B-06 | N-count mismatch | Subject count differs between demographics and analysis tables |
| B-07 | Missing category | "Unknown" race category dropped without footnote |

#### Class C — Minor
*Cosmetic/formatting issues with no analytical impact.*

| ID | Error Type | Example |
|---|---|---|
| C-01 | Decimal places inconsistent | Mean reported as 5.2 in one table, 5.23 in another |
| C-02 | Alignment error | Decimal alignment off in columns |
| C-03 | Table title typo | "Demographics" misspelled |
| C-04 | Missing footnote | Abbreviation not defined in footnotes |
| C-05 | Font/size inconsistency | Header font differs from body |
| C-06 | Missing page number | Multi-page table pages unnumbered |

### 4.2 Calibration Approach

The severity classification must be validated by the WG through:
1. Survey of member companies — "Would this error change your analysis
   conclusion? Require a re-run? Be caught in QC?"
2. Calibration meeting — resolve edge cases (e.g., is a wrong footnote
   that references a deleted table a B or a C?)
3. Living document — updated as new error types emerge from practice

---

## 5. Deliverable 2: Example Cases

### 5.1 Case Structure

Each example case is a full TFL package representing a realistic analysis
scope (typical interim analysis or final analysis for a Phase 2/3 study):

```
case-NNN/
├── specs/
│   ├── SAP-excerpt.md            # Relevant SAP sections
│   ├── TFL-shells/               # Shell specifications for each TFL
│   └── data-spec.md              # ADaM dataset descriptions
├── data/
│   ├── adsl.csv                  # Subject-level dataset (synthetic)
│   ├── adtte.csv                 # Time-to-event (synthetic)
│   ├── adlb.csv                  # Lab data (synthetic)
│   └── adae.csv                  # AE data (synthetic)
├── outputs/                      # TFL package to be reviewed
│   ├── table-14-1-1-1.rtf
│   ├── table-14-3-1-1.rtf
│   ├── figure-14-3-1-1.rtf
│   └── listing-16-2-1-1.rtf
├── errors/                       # Ground truth
│   ├── error-manifest.yaml       # List of all planted errors
│   └── error-sources/            # Individual error specifications
└── README.md                     # Case overview
```

### 5.2 Error Planting Methodology

1. **Start with correct outputs:** Generate gold-standard TFLs from
   verified R/SAS/Python code
2. **Plant errors deliberately:** WG statisticians introduce errors
   based on real QC experience, documented in error manifests
3. **Blinded validation:** A second statistician reviews the planted
   errors — any disputed plantings are removed
4. **Difficulty gradient:**
   - **Easy:** Obvious errors (wrong header, missing data, label typos)
   - **Medium:** Subtle logic errors (wrong denominator in a subgroup,
     missing adjustment for stratification factor)
   - **Hard:** Context-dependent errors (wrong reference set for a
     comparison that depends on SAP interpretation, inconsistent
     handling of intercurrent events)

### 5.3 Difficulty Levels (for Score Reporting)

| Level | Description | Example |
|---|---|---|
| **Easy** | Surface-level, detectable by format checks | C-02 (alignment), C-04 (missing footnote) |
| **Medium** | Needs statistical domain knowledge | B-04 (wrong visit window), A-02 (wrong population) |
| **Hard** | Needs deep SAP interpretation + clinical context | A-04 (wrong comparison), B-07 (missing category with clinical relevance) |

### 5.4 Data Strategy

- All datasets generated via `random.cdisc.data` + custom `simstudy` scripts
- Parameterized seed system enables multiple variants with same error
  structure
- 20% of variants reserved as held-out validation set
- Forward-looking: member companies may contribute additional cases
  derived from (anonymized) internal data

---

## 6. Deliverable 3: Scoring Methodology

### 6.1 Primary Metrics

| Metric | Definition | Range |
|---|---|---|
| **Detection Rate (DR)** | Errors flagged / total planted errors | 0-100% |
| **DR-by-Severity** | Detection rate for Class A, B, C separately | 0-100% |
| **False Positive Rate (FPR)** | Non-errors flagged / total non-error elements | 0-100% |
| **F1 Score** | Harmonic mean of precision and recall | 0-1 |
| **Review Time** | Wall clock time to complete review | Minutes |

### 6.2 TPP-Style Interpretation (Parsa 2026)

Instead of a single pass/fail score, the benchmark plots agent performance
on a **detection rate × false positive rate** curve:

```
Detection Rate (y-axis, aim high)
    ↑
100% ┼──────────────────────────────────
    │  🟢 Elite (DR≥95%, FPR≤5%)
    │  🟡 Acceptable (DR≥85%, FPR≤15%)
    │  🟠 Marginal (DR≥70%)
    │  🔴 Below threshold
    └──────────────────────────────────→ False Positive Rate (x-axis, aim low)
    0%                               100%
```

Each company calibrates their own operating point:
- **Small team, high workload:** May tolerate higher FPR in exchange for
  higher DR (catch every error, accept some false alarms)
- **Regulatory submission team:** May optimize for low FPR (cannot afford
  wasted reviewer time on false flags)

### 6.3 Class-Specific Reporting

Critical for regulatory use cases:
- Class A DR must meet a minimum floor (e.g., ≥ 95%) regardless of FPR
- Class C errors may have lower DR requirements
- Overall score is reported with breakouts

### 6.4 Multi-Language Scoring

Agents can execute in R, SAS, or Python. Scores are reported:

```
┌──────────────────────┬──────┬──────┬──────┬──────┐
│ Metric               │ R    │ SAS  │ Py   │ Any  │
├──────────────────────┼──────┼──────┼──────┼──────┤
│ DR (Class A)         │ 95%  │ 100% │ 80%  │ 100% │
│ DR (Class B)         │ 88%  │ 92%  │ 75%  │ 92%  │
│ DR (Class C)         │ 70%  │ 65%  │ 60%  │ 70%  │
│ FPR                  │ 8%   │ 5%   │ 12%  │ 8%   │
└──────────────────────┴──────┴──────┴──────┴──────┘
```

"The "Any" column = error caught in at least one language."

### 6.5 Scoring Automation

| Dimension | Auto-score feasible? | Method |
|---|---|---|
| Detection rate (obvious errors) | ✅ Full | YAML manifest comparison |
| Detection rate (subtle errors) | ⚠️ Partial | LLM-as-judge + human verification |
| FPR | ⚠️ Partial | Automated count + human review of flagged-but-incorrect items |
| Detection rate (context-dependent) | ❌ Expert | Human panel review |
| Review time | ✅ Full | Wall clock measurement |

---

## 7. The "Exam" Framing

### 7.1 Like LLM Benchmarks, But for TFL Review

The mental model is how the LLM community benchmarks models:
- **MMLU** measures knowledge across 57 subjects
- **GSM8K** measures math reasoning
- **SWE-bench** measures coding capability

This benchmark is the equivalent for clinical TFL review — a standardized
set of challenges that agents must pass before being qualified for
production use.

### 7.2 Certification Model

The WG can serve an "industry AI union" function:
- Vendors submit their agents for benchmark evaluation
- Passing = certified for TFL review in a clinical trial context
- WG members use certification to inform vendor selection
- Vendors who pass attract more pharma partnerships

### 7.3 Calibration Against Human Baseline

A human baseline must be established:
- Recruit 2-3 WG statisticians to review the example cases
- Record their DR, FPR, and review time
- Agent performance is relative to human baseline, not absolute

---

## 8. Implementation Guide

### 8.1 For Member Companies

- Build internal test instances using your own TFL packages and QC history
- Calibrate the severity taxonomy to your team's standards
- Use the public example cases for initial vendor screening
- Run internal benchmark against vendors' agents before procurement

### 8.2 For Vendors

- Self-assess using the published example cases
- Report: DR by class (A/B/C), FPR, scope of testing, language tested
- Vendors are free to use the published examples for product development

### 8.3 For the WG

- Maintain and refresh example cases annually
- Community contribution model for new error types
- Publication path: methodology paper → ASA Biopharm proceedings /
  stats journal

---

## 9. Open Questions (WG Discussion)

| # | Question | Status |
|---|---|---|
| 1 | **Error taxonomy scope:** SDTM only? ADaM only? Full TLF? Start small? | 🔴 Open |
| 2 | **Who builds the first example cases?** yilong/Keiji's team? Volunteers? | 🔴 Open |
| 3 | **Severity calibration:** How do we reach consensus on A vs B vs C? Survey? | 🔴 Open |
| 4 | **False positive tolerance:** What range is acceptable? Team-size dependent? | 🔴 Open |
| 5 | **Publication:** ASA Biopharm proceedings? Stats journal? | 🔴 Open |
| 6 | **Test dataset tension:** Synthetic public + private internal — what's the right balance? | 🔴 Open |
| 7 | **Language coverage:** Should agents be tested in all 3 languages or just their primary? | 🔴 Open |
| 8 | **Human baseline design:** What constitutes expert-level performance? 5+ years experience? | 🔴 Open |
| 9 | **Case refresh cycle:** How often should example cases be updated? | 🔴 Open |
| 10 | **Regulatory alignment:** FDA endorsement? CDER engagement level? | 🔴 Open |

---

## 10. Relationship to Prior Work

### Prior Benchmark Framework (v0.1 — 6 Dimensions)

The initial v0.1 framework proposed six scoring dimensions (Task Fidelity,
Workflow Completeness, Statistical Correctness, Regulatory Compliance,
Operational Efficiency, Safety & Robustness). The v0.2 framework in this
document **builds on but supersedes** that architecture with:

- **Error taxonomy** (Deliverable 1) replaces the generic multi-dimension
  scoring with clinically meaningful error classification
- **TPP curves** replace the composite CBS formula with context-dependent
  interpretation
- **"Exam" framing** replaces the academic evaluation model with a
  production-qualification model

The v0.1 statistical method coverage matrix remains useful reference and
is preserved in `test-case-design.md`.

### Existing General-Agent Benchmarks

| Benchmark | Domain | Relationship |
|---|---|---|
| **SWE-bench** | General coding | Foundation for coding agent eval; domain-inadequate for clinical stats |
| **GAIA** | General assistants | Useful tool-use patterns; no domain specialization |
| **MMLU / GSM8K** | LLM knowledge/reasoning | Reference for the "exam" framing |
| **PHUSE Test Data Factory** | CDISC test data | Data source, not agent eval |
| **Pharmaverse** | R packages | Reference implementations for ground truth |

### WG Source Documents

- `notes/benchmark-blueprint-outline.md` — Yue's original outline
- `notes/benchmark-notes-private.md` — WG discussion notes (WeChat/Telegram)

---

## 11. Context: WG Discussions That Shaped This

This framework draws directly from WG member input:
| *WG contributions internally documented for privacy.*

---

## 12. Dimension Reference (Previous v0.1)

For reference, the v0.1 scoring dimensions can be mapped onto the
error-taxonomy framework:

| v0.1 Dimension | Maps to v0.2 |
|---|---|
| Task Fidelity | Error planting methodology + instruction parsing |
| Workflow Completeness | End-to-end TFL review workflow |
| Statistical Correctness | Class A errors (would change conclusion) |
| Regulatory Compliance | CDISC/ICH/FDA standard adherence — future extension |
| Operational Efficiency | Review time metric |
| Safety & Robustness | FPR + stress tests — future extension |
