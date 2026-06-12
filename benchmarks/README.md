# Agentic AI Benchmark — TFL Programming in Clinical Trial Statistics

**Part of:** ASA Biopharm AI/ML Working Group — Agentic AI Workstream
**Lead:** Yue Shentu (Merck)
**Status:** 🟢 Active — daily incremental development
**Started:** 2026-05-25
**Priority scope:** TFL programming (Tables, Figures, Listings generation and review)
**Languages:** R + SAS + Python (multilingual)
**Repo:** https://github.com/doublerobust/ASAbiop-AIML-Agentic (within `benchmarks/`)

---

## Purpose

Establish an **industry-standard benchmark** for evaluating agentic AI systems
in the specific domain of **clinical trial statistics** — covering trial design,
statistical analysis, and regulatory reporting.

This is **not** a general AI benchmark. It targets the exact workflows a
biostatistician performs: SAP generation, TFL programming, sample size
calculation, safety monitoring, CSR authoring, and regulatory submission
readiness.

## Why This Matters Now

- SWE-bench measures general coding — it doesn't test whether an agent
  correctly implements a stratified log-rank test with O'Brien-Fleming
  boundaries
- WebArena measures web navigation — it doesn't test whether an agent
  correctly populates an ADaM ADSL dataset per CDISC standards
- GAIA measures general assistant capability — it doesn't test regulatory
  submission readiness
- **No existing benchmark** covers the intersection of statistical rigor,
  regulatory compliance, and agentic workflow execution that defines our
  domain

## Deliverables

| # | Deliverable | Timeline | Status |
|---|---|---|---|
| 1 | Benchmark taxonomy — 5 dimensions, scoring framework, TPP curves | Ongoing | 🟢 Complete |
| 2 | **TFL test case bank** — 14 test cases (7 Level 1 with ground truth in R+Python) | Phase 1 | 🟡 In progress (14/50) |
| 3 | Evaluation harness — scoring CLI (compliance, safety, efficiency) | Phase 2 | 🟡 In progress |
| 4 | Reference implementations — 7 gold-standard TFL outputs (R+Python, 15 scripts) | Phase 2 | 🟡 In progress |
| 5 | Public leaderboard — vendor and open-source submissions | Phase 3 | 🔴 Not started |
| 6 | White paper — benchmark methodology and industry findings | Phase 3 | 🔴 Not started |

## Folder Structure

```
benchmarks/
├── references/
│   ├── ground-truth/
│   │   ├── R/ (7 scripts + common/)
│   │   ├── SAS/ (3 scripts)
│   │   └── Python/ (7 scripts + common/)
│   ├── output-schemas/ (7 JSON Schema files)
│   ├── edge-cases/ (14 edge case files)
│   ├── safety-vectors/ (10 safety vector files)
│   └── verification/ (cross-language-compare.R)
├── scoring-harness/
│   ├── score.py (CLI: score, verify, validate, compliance, check-safety, evaluate)
│   ├── safety.py, compliance.py
│   ├── tolerances.yaml, safety.yaml, compliance.yaml, efficiency.yaml
│   └── README.md
├── test-case-design.md (14 test cases, 7 with ground truth)
├── scoring-framework.md (multi-language aggregation, TPP curves)
├── vendor-catalog.md (6 vendors + PharmaSUG 2026 papers)
├── safety-robustness.md
├── regulatory-compliance.md
├── operational-efficiency.md
├── cross-language-verification.md
├── benchmark-framework-v1.md
├── relevant-work.md
├── tools-packages.md
├── progress-log.md
└── README.md
```

## Daily Cadence

Each day, a cron job:
1. Reviews the progress log and current state
2. Searches for new relevant work, tools, or standards
3. Incrementally expands one dimension of the benchmark
4. Updates the progress log
5. Commits and pushes to GitHub

Yue receives a digest when there's meaningful progress or a decision needed.
