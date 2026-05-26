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
| 1 | Benchmark taxonomy — dimensions, metrics, scenarios | Ongoing | 🟡 In progress |
| 2 | **TFL test case bank** — 20-50 TFL generation & review tasks in R, SAS, Python | Phase 1 | 🟡 Started |
| 3 | Evaluation harness — automated scoring pipeline (multi-language) | Phase 2 | 🔴 Not started |
| 4 | Reference implementations — gold-standard TFL outputs | Phase 2 | 🔴 Not started |
| 5 | Public leaderboard — vendor and open-source submissions | Phase 3 | 🔴 Not started |
| 6 | White paper — benchmark methodology and industry findings | Phase 3 | 🔴 Not started |

## Folder Structure

```
benchmark/
├── README.md                        ← This file
├── benchmark-framework-v1.md        ← The benchmark framework proposal
├── progress-log.md                  ← Daily log — what happened, decisions, next steps
├── relevant-work.md                 ← Catalog of related pharma/biotech benchmark efforts
├── tools-packages.md                ← Tools, packages, and infrastructure needed
└── references/                      ← Reference papers and standards
```

## Daily Cadence

Each day, a cron job:
1. Reviews the progress log and current state
2. Searches for new relevant work, tools, or standards
3. Incrementally expands one dimension of the benchmark
4. Updates the progress log
5. Commits and pushes to GitHub

Yue receives a digest when there's meaningful progress or a decision needed.
