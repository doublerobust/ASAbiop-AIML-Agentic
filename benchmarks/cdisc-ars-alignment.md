# CDISC ARS Alignment — Mapping Benchmark Output Schemas to Analysis Results Standard

**Version:** 0.1 (Day 26)
**Date:** 2026-06-26
**Status:** 🟡 Draft for WG Review
**Depends on:** CDISC ARS v1.0 (April 2024), `cards` R package

---

## 1. Purpose

The CDISC Analysis Results Standard (ARS) provides a machine-readable logical
data model for analysis results and their metadata. By aligning our benchmark
output schemas with ARS, we:

1. **Enable interoperability** — benchmark outputs can be consumed by ARS-compatible
   tools (gtsummary, cards, siera, TFL Designer)
2. **Support metadata-driven TFL generation** — AI agents that produce ARS-compliant
   output can be directly validated against our ground truth
3. **Future-proof** — as CDISC ARS adoption grows, our benchmark stays aligned
4. **Regulatory alignment** — ARS traceability supports FDA Study Data TCG and
   ICH E3 compliance checks already in our scoring harness

---

## 2. CDISC ARS Overview

### 2.1 Core Concepts

| ARS Concept | Description | Our Equivalent |
|---|---|---|
| **Analysis Result (AR)** | A single statistical result with metadata | One TC output JSON file |
| **Analysis Results Data (ARD)** | Machine-readable statistical summaries | JSON output fields (e.g., `median_pfs`, `hr`, `ci_lower`) |
| **Analysis Variable** | Variable involved in the analysis | ADaM variable (e.g., AVAL, CNSR, TRT01PN) |
| **Analysis Population** | Population for the analysis | ITT, SAFETY (via ITTFL/SAFFL) |
| **Analysis Method** | Statistical method applied | e.g., "Kaplan-Meier", "Cox PH", "Chi-square" |
| **Analysis Reason** | Why the analysis was performed | e.g., "Primary endpoint", "Safety summary" |
| **Documentation** | Free-text documentation | `metadata` block in output JSON |
| **Code Template** | Parametrized code for reproduction | Ground truth R/Python/SAS scripts |

### 2.2 ARS Data Model Structure

```
AnalysisResult
├── id (unique identifier)
├── version
├── analysisReason
├── analysisMethod
│   ├── name
│   ├── codeTemplate
│   └── parameters
├── analysisVariables[]
├── analysisPopulation
├── analysisDataset
├── resultGroups[]
├── resultAnalyzers[]
├── documentation
└── analysisResultsData (ARD)
```

---

## 3. Mapping: Benchmark Output Schemas → ARS

### 3.1 TC-001: KM Median PFS — ARS Mapping

| Benchmark JSON Field | ARS Element | XPath |
|---|---|---|
| `metadata.tc_id` | AnalysisResult.id | `/id` |
| `metadata.tc_title` | AnalysisResult.documentation | `/documentation` |
| `metadata.population` | AnalysisPopulation | `/analysisPopulation` |
| `metadata.method` | AnalysisMethod.name | `/analysisMethod/name` |
| `metadata.r_version` | AnalysisMethod.codeTemplate (env) | `/analysisMethod/codeTemplate/env` |
| `results.median_pfs` | ARD statistic | `/analysisResultsData/statistics/statistic[name="median"]/value` |
| `results.ci_lower` | ARD statistic | `/analysisResultsData/statistics/statistic[name="CI_lower"]/value` |
| `results.ci_upper` | ARD statistic | `/analysisResultsData/statistics/statistic[name="CI_upper"]/value` |
| `results.n_experimental` | ResultGroup.n | `/resultGroups[id="Experimental"]/n` |
| `results.n_control` | ResultGroup.n | `/resultGroups[id="Control"]/n` |
| `results.events_experimental` | ResultGroup.events | `/resultGroups[id="Experimental"]/events` |
| `results.events_control` | ResultGroup.events | `/resultGroups[id="Control"]/events` |

### 3.2 TC-002: Demographics Table — ARS Mapping

| Benchmark JSON Field | ARS Element |
|---|---|
| `results.continuous[].variable` | AnalysisVariable.name |
| `results.continuous[].mean` | ARD statistic (type=mean) |
| `results.continuous[].sd` | ARD statistic (type=sd) |
| `results.continuous[].median` | ARD statistic (type=median) |
| `results.categorical[].variable` | AnalysisVariable.name |
| `results.categorical[].categories[].category` | ResultGroup.category |
| `results.categorical[].categories[].n` | ARD statistic (type=count) |
| `results.categorical[].categories[].pct` | ARD statistic (type=percent) |

### 3.3 TC-012: Forest Plot HR — ARS Mapping

| Benchmark JSON Field | ARS Element |
|---|---|
| `results.overall.hr` | ARD statistic (type=hazard_ratio) |
| `results.overall.ci_lower` | ARD statistic (type=CI_lower) |
| `results.overall.ci_upper` | ARD statistic (type=CI_upper) |
| `results.overall.p_value` | ARD statistic (type=p_value) |
| `results.subgroups[].subgroup` | ResultGroup.id |
| `results.subgroups[].hr` | ARD statistic per subgroup |
| `metadata.method` | AnalysisMethod.name = "Cox Proportional Hazards" |
| `metadata.cox_tie_method` | AnalysisMethod.parameter (tie handling) |

### 3.4 General Mapping Pattern

For all 11 Level 1 TCs:

```
benchmark_output = {
  "metadata": {
    "tc_id":       → ARS AnalysisResult.id
    "tc_title":    → ARS AnalysisResult.documentation
    "population":  → ARS AnalysisPopulation
    "method":      → ARS AnalysisMethod.name
    "seed":        → ARS AnalysisMethod.parameter
    "r_version":   → ARS AnalysisMethod.codeTemplate.environment
  },
  "results": {
    <numeric fields>  → ARS AnalysisResultsData.statistics
    <group fields>    → ARS ResultGroups
  }
}
```

---

## 4. ARS-Compatible Output Envelope

### 4.1 Proposed ARS Envelope Wrapper

To make benchmark outputs ARS-compatible, wrap existing JSON in an ARS envelope:

```json
{
  "ars_version": "1.0",
  "analysisResult": {
    "id": "TC-001",
    "version": "1.0",
    "analysisReason": "Primary efficacy endpoint estimation",
    "analysisMethod": {
      "name": "Kaplan-Meier",
      "codeTemplate": "R/survival::survfit(Surv(AVAL, EVNT) ~ TRT01A)",
      "parameters": {
        "tie_method": "efron",
        "conf_type": "log-log"
      }
    },
    "analysisVariables": [
      {"name": "AVAL", "dataset": "ADTTE", "role": "analysis time"},
      {"name": "CNSR", "dataset": "ADTTE", "role": "censoring"},
      {"name": "TRT01A", "dataset": "ADSL", "role": "treatment"}
    ],
    "analysisPopulation": {
      "name": "ITT",
      "filter": "ITTFL = 'Y'"
    },
    "analysisDataset": "ADTTE",
    "resultGroups": [
      {"id": "Experimental", "n": 100, "events": 72},
      {"id": "Control", "n": 100, "events": 85}
    ],
    "documentation": "KM median PFS estimation with 95% CI (Brookmeyer-Crowley)",
    "analysisResultsData": {
      "statistics": [
        {"name": "median_pfs_experimental", "value": 7.2, "unit": "months"},
        {"name": "median_pfs_control", "value": 4.5, "unit": "months"},
        {"name": "ci_lower_experimental", "value": 5.8},
        {"name": "ci_upper_experimental", "value": 9.1},
        {"name": "ci_lower_control", "value": 3.2},
        {"name": "ci_upper_control", "value": 6.0}
      ]
    }
  }
}
```

### 4.2 Backward Compatibility

- Existing `metadata` + `results` JSON format remains the primary benchmark output
- ARS envelope is an **optional wrapper** for agents/tools that produce ARS-native output
- The scoring harness (`katsu score`) unwraps ARS envelope if present, then scores
  the inner statistics using existing tolerance-based comparison
- No breaking changes to ground truth scripts or scoring pipeline

---

## 5. `cards` R Package Integration

### 5.1 What `cards` Provides

The `cards` R package (part of pharmaverse) generates ARD objects compliant with
CDISC ARS v1.0:

```r
library(cards)
library(gtsummary)

# Create ARD from a summary table
tbl <- trial |> tbl_summary(by = trt)
ard <- tbl |> as_ard()

# Export as ARS-compatible JSON
ard |> write_ard_json("tc-002-ard.json")
```

### 5.2 Integration Path

| Step | Action | Priority |
|---|---|---|
| 1 | Add `cards` + `gtsummary` to R ground truth dependencies | P1 |
| 2 | Create ARD export wrappers for TC-001 through TC-018 | P2 |
| 3 | Add `--ars-output` flag to R ground truth scripts | P2 |
| 4 | Extend scoring harness to accept ARS-enveloped JSON | P2 |
| 5 | Validate ARS output against CDISC ARS JSON Schema | P3 |

### 5.3 Python ARD Equivalents

Python doesn't have a direct `cards` equivalent, but the benchmark's JSON output
structure is already compatible with ARS's statistical-summary model. A future
`pyards` library could bridge this gap.

---

## 6. Benefits of ARS Alignment

### 6.1 For AI Agents

- Agents that produce ARS-compliant output get **automatic benchmark scoring**
- ARS metadata provides structured context (method, variables, population)
- Reduces ambiguity in output format expectations

### 6.2 For the Working Group

- Positions the benchmark within the CDISC ecosystem
- Enables integration with pharmaverse tools (`cards`, `gtsummary`, `siera`)
- Supports the metadata-driven TFL automation vision from PharmaSUG 2026

### 6.3 For Regulatory Compliance

- ARS traceability chain: protocol → SAP → analysis specification → ADaM → ARD → TFL
- Our compliance checks (ADaM mapping, TCG, CSR formatting) align with ARS
  requirements for documentation and method specification
- Supports FDA Study Data TCG and ICH E3 CSR appendix requirements

---

## 7. Implementation Plan

| Phase | Scope | Timeline |
|---|---|---|
| **Phase 1** (current) | Document mapping (this file) | ✅ Done |
| **Phase 2** | Add `--ars-output` to TC-001 as proof-of-concept | Day 27-28 |
| **Phase 3** | Extend ARS envelope to TC-002, TC-003, TC-012 | Day 29-31 |
| **Phase 4** | Scoring harness: unwrap ARS envelope in `score.py` | Day 32 |
| **Phase 5** | Full ARS compliance for all 11 Level 1 TCs | Day 33-35 |
| **Phase 6** | CDISC ARS JSON Schema validation in CI | Day 36+ |

---

## 8. References

1. CDISC Analysis Results Standard v1.0 — https://www.cdisc.org/standards/foundational/analysis-results-standard
2. CDISC ARS GitHub — https://github.com/cdisc-org/analysis-results-standard
3. `cards` R package — https://insightsengineering.github.io/cards/
4. `gtsummary` + ARD integration — https://www.danieldsjoberg.com/ARD-onboarding/
5. CDISC ARS implementation guide — https://clymbclinical.com/ars-ard-implementation/
6. PharmaSUG 2025 AI-349: ARS + GenAI for TFL automation
7. Appsilon CDISC standards guide — https://www.appsilon.com/post/guides-cdisc-standards-open-source-pharma
