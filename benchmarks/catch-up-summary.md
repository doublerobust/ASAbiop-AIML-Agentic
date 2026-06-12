# ASA Agentic AI WG — Benchmark Build Catch-Up (Days 4–9)

**Status:** 9 days of daily cron-job builds since kickoff (May 25). Here's what's been shipped.

---

## Day 4: Regulatory Compliance Module

**What was built:**
- `scoring-harness/compliance.py` — Three automated checkers:
  - **ADaM variable mapping** — validates required variables, population flags (ITTFL/SAFFL=Y), treatment variable (TRT01PN), censoring coding (CNSR 0/1), strata
  - **FDA TCG checklist** — validates population filter, treatment var, event/censor handling, analysis time, method doc, software version
  - **ICH E3 CSR formatting** — validates table numbering, title population/endpoint, footnotes, p-value type (1/2-sided), CI method
- `scoring-harness/compliance.yaml` — Per-TC rule definitions for TC-001 through TC-003
- Updated `score.py` — new `--compliance`, `--tcg-check`, `--csr-format` flags + standalone `compliance` subcommand + unified `evaluate` subcommand
- Weighted composite score: ADaM 40% / TCG 35% / CSR 25%

**Key research findings:**
- FDA/EMA Joint Principles on AI in Medicine (Jan 2026) — 10 principles covering accuracy, consistency, human oversight
- FDA draft guidance on AI for regulatory decision-making
- CDISC CORE (Conformance Rules Engine) initiative gaining traction
- PHUSE US Connect 2026 confirmed AI/ML + agent-based systems as the dominant conference theme

**Decisions made:**
- Compliance scoring is a separate dimension (15% of total benchmark weight), not folded into correctness
- ARM metadata generation = bonus criterion (+10%), not a standalone test case

---

## Day 5–6: Safety & Robustness + Operational Efficiency

### Safety & Robustness (Day 5)

**What was built:**
- `safety-robustness.md` — Full TFL safety dimension covering 6 failure mode categories
- `scoring-harness/safety.py` — Safety checker module with 4 core checks:
  - N-count consistency across TFLs (R-COUNT-01 through R-COUNT-06)
  - Denominator consistency (population filter verification)
  - Cross-TFL data agreement (endpoint results match across outputs)
  - Edge case handling (missing data, empty strata)
- `scoring-harness/safety.yaml` — Per-TC safety rules and severity thresholds
- Composite safety score: critical violations weighted 5×, major 3×, minor 1×; penalty structure (−20 pts per critical, max −100)

**Key research findings:**
- Most common TFL errors in practice: wrong N-count (~15% of packages), missing category (~12%), wrong denominator (~5%)
- Cross-table N-count verification is already production-ready elsewhere (BeaconCure, TLFQC R Shiny)
- Error detection difficulty varies widely — N-count/logic checks are straightforward; p-value boundary rounding and chi-square weighting are hard even for humans

### Operational Efficiency (Day 6)

**What was built:**
- `operational-efficiency.md` — Full efficiency dimension with 21 metrics across direct, derived, and language-adjusted categories
- `scoring-harness/efficiency.yaml` — Machine-readable config: model pricing, language adjustment factors, efficiency targets per level
- Efficiency scoring formula: cost_efficiency (40%) + time_efficiency (35%) + reliability (25%)
- Human vs. agent cost comparison framework

**Key research findings:**
- API cost spans 2 orders of magnitude: DeepSeek V4 ≈ $0.50–1.50/TFL-package vs. Claude Sonnet ≈ $12–18
- AI agents are 50–100× faster than humans for single-step TFL generation
- The bottleneck is **verification**, not generation — a 95%-accurate fast agent may beat a 99%-accurate slow agent if the 4% gap takes 10 min of human review
- SAS licensing ($15K–50K/yr) makes it impractical for open CI/CD; R/Python are zero marginal cost
- Efficiency sweet spot in pilot: DeepSeek V4 + Python execution

**Decisions made:**
- Efficiency weight = 15% of total benchmark score
- Separate "Cloud API" and "Local Inference" leaderboards
- Only compute efficiency for runs with accuracy ≥ 0.50 (don't reward fast wrong answers)

---

## Day 7–8: Safety Implementation + Scoring Framework

### Scoring Framework (Day 7)

**What was built:**
- `scoring-framework.md` — Multi-dimensional aggregation methodology:
  - Score hierarchy: Aggregate Benchmark Score → per-TC → per-language → per-dimension
  - Dimension weights: Correctness 0.35 / Safety 0.25 / Compliance 0.15 / Efficiency 0.15 / Schema 0.10
  - Language weights: R 0.50 / Python 0.35 / SAS 0.15
  - TPP-style curves (detection rate × false positive rate) — 3 operating points: Conservative (QC), Balanced (Review), Efficient (Scout)
  - Bootstrap CIs for rankings (1000 replicates)
  - Min test cases for statistical power: 8 for Δ=10pts, 25 for Δ=5pts

### Safety Implementation (Day 8)

**What was built:**
- `score.py` fully integrated with safety — `--safety`, `check-safety` subcommand, `evaluate --safety`
- **14 edge case test data files** in `references/edge-cases/`:
  - Non-estimable median, all-censored data, single subject per arm, zero-event stratum, missing covariate, negative survival time, empty treatment arm, perfect separation, duplicate subject IDs, visit window overlap, degenerate stratum, event at time zero, inconsistent population flag, censoring inconsistency
  - 5 Critical severity, 9 Major severity
- **10 safety test vectors** in `references/safety-vectors/`:
  - Planted-error TFL outputs: N-count mismatch, wrong denominator, event count > N, arm label swap, missing race category, missing stratum, p-value boundary rounding, CI bounds swapped, wrong percentage denominator, chi-square weighting error
  - Each vector = full TFL JSON with planted error + expected detection behavior + rule violated

**Key research findings:**
- PharmaSUG 2026 AI section had 25+ papers — AI is no longer experimental in pharma
- Merck's Xia & Du won Best Paper (AI-332) for human-in-the-loop ADaM standardization — directly relevant to our benchmark
- Posit/Phil Bowsher presented "Agentic R" — validates our R-heavy language weight scheme
- FDA/EMA Joint AI Principles (Jan 2026) explicitly cover accuracy, consistency, human oversight — our safety dimension operationalizes these

---

## Day 9: Vendor Landscape Assessment

**What was built (uncommitted):**
- `vendor-catalog.md` — Commercial AI TFL tools and services catalog covering 6 vendors + 9 PharmaSUG 2026 papers

**Vendors assessed:**
- **Saama — TLF Analyzer** (T1) — First commercial "TLF Analyzer"; focuses on interpretation/summarization (figures-to-text), not verification. Gap = our benchmark's sweet spot
- **JDIX — TFL Reviewer** (T1) — Taiwan-based, explicitly positioned for TFL QC; direct benchmark candidate
- **TrialMind — AI Review** (T1) — AI-powered TFL review workflow; maps to our TC-001 through TC-003
- **EDETEK — INSIGHT** (T2) — Full ADaM-to-TFL pipeline; presented at PharmaSUG 2026
- **Veristat — InStat AI** (T2) — First "AI biostatistics as a service"; first client is Clene Nanomedicine for NDA-supporting NfL analyses
- **Maxis AI** (T3) — Agentic AI for anomaly detection in clinical data science

**Key research findings:**
- No vendor has published independent benchmark results — all claims are self-reported
- PharmaSUG 2026 had 25+ AI papers; "Agentic AI" is the new dominant term replacing "ML" and "GenAI"
- Human-in-the-loop is standard across all vendors — no one claims full automation
- Our benchmark covers capabilities no vendor addresses: cross-language verification (R→SAS→Python), standardized error taxonomy, TPP-style operating curves, human baseline comparison, contamination mitigation, bootstrap CIs

**Decisions made:**
- T1 vendors (Saama, JDIX, TrialMind) prioritized for benchmark pilot
- Vendor benchmark pipeline defined: select TCs → send to vendor → vendor returns outputs → katsu scores → compare vs. ground truth + human baseline
- Living document — annual update cadence

---

## What's Uncommitted

```
?? benchmarks/vendor-catalog.md          ← Day 9 work, ready to commit
?? benchmarks/scoring-harness/__pycache__/
?? benchmarks/scoring_harness/__pycache__/
```

## Current File Structure

```
benchmarks/
├── references/
│   ├── ground-truth/R/ SAS/ Python/ (11 scripts, 1,530 lines)
│   ├── output-schemas/ (3 JSON Schema files)
│   ├── verification/ (cross-language-compare.R)
│   ├── edge-cases/ (14 EC files)
│   └── safety-vectors/ (10 SV files)
├── scoring-harness/
│   ├── score.py (main CLI — katsu)
│   ├── compliance.py + compliance.yaml
│   ├── safety.py + safety.yaml
│   ├── efficiency.yaml
│   ├── tolerances.yaml
│   └── requirements.txt
├── benchmark-framework-v1.md (core framework — "exam" framing)
├── test-case-design.md (10 test cases, 93 parametrizable variants)
├── regulatory-compliance.md
├── safety-robustness.md
├── operational-efficiency.md
├── scoring-framework.md
├── vendor-catalog.md (UNCOMMITTED)
├── progress-log.md
└── README.md
```

## What's Next

1. **Commit vendor-catalog.md** and clean up __pycache__
2. **Cross-validate TPP curves** with error injection runs using SV-001 through SV-010
3. **Run safety checks on ground truth** — verify reference implementations pass all safety checks
4. **Integrate safety score into aggregate scoring** in score.py (per scoring-framework.md)
5. **Contact T1 vendors** (Saama, JDIX, TrialMind) for benchmark pilot
6. **WG presentation prep** — Safety dimension + vendor landscape for next meeting
