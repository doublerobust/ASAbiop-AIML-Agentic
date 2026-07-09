# TC-029 through TC-035: Candidate Test Cases for Benchmark Expansion

**Date:** 2026-07-09 (Day 40)
**Status:** Proposed — pending WG review
**Rationale:** Expand Level 1/2 coverage to address gaps identified in WG feedback

---

## TC-029: Adverse Event by Severity (Level 1)

**Domain:** Safety
**Priority:** High — standard safety TFL, often requested by reviewers

| Parameter | Default |
|---|---|
| **Description** | AE summary table grouped by severity (CTCAE Grade 1-5) and by arm |
| **Data** | ADSL + ADAE with AESEV, AEBODSYS, AEDECOD |
| **Output** | By SOC → PT → Severity grade: N (%), sorted by descending frequency in any arm |
| **Key checks** | Correct N (%), denominators from SAFETY population, sorting order, total row consistency |
| **Scoring** | N (%) per cell, total N per arm, sorting rank |
| **Cross-TC** | TC-011 (AE Summary) — but TC-029 adds severity dimension; TC-016 (Exposure) — denominators must match |

---

## TC-030: ORR by Subgroup with Interaction Test (Level 1)

**Domain:** Efficacy / Tumor Response
**Priority:** Medium — extends TC-020 with formal interaction testing

| Parameter | Default |
|---|---|
| **Description** | ORR (CR+PR) by subgroup with treatment×subgroup interaction p-value |
| **Data** | ADSL + ADRS with subgroup variables |
| **Output** | Subgroup-level ORR (N, %, CI) per arm + interaction p-value from logistic regression |
| **Key checks** | ORR per subgroup, CI via Clopper-Pearson, interaction p-value from logistic model |
| **Scoring** | ORR %, CI bounds, interaction p-value (tolerance ±0.01) |
| **Cross-TC** | TC-020 (ORR by Subgroup) — TC-030 adds interaction test; TC-025 (BOR Summary) |

---

## TC-031: Time-to-First-Treatment (Level 1)

**Domain:** Oncology / Time-to-Event
**Priority:** Low — niche endpoint, but tests date handling

| Parameter | Default |
|---|---|
| **Description** | Time from randomization to first dose of study treatment |
| **Data** | ADSL with randomization date and first treatment date |
| **Output** | KM median time-to-first-treatment by arm, log-rank p, HR |
| **Key checks** | Date computation, handling of subjects who never receive treatment (censored at 0) |
| **Scoring** | Median, CI, HR, log-rank p |
| **Cross-TC** | TC-001 (KM Median PFS) — similar computation; TC-014 (PD Listing) — similar date logic |

---

## TC-032: Immune-Related AE Summary (Level 1)

**Domain:** Safety / Immuno-oncology
**Priority:** Medium — I-O specific, relevant for checkpoint inhibitors

| Parameter | Default |
|---|---|
| **Description** | Immune-related adverse events (irAEs) summary by category and severity |
| **Data** | ADAE with AEFLAG = "IMMUNE" or pre-specified immune-related SOC list |
| **Output** | irAE by category (endocrine, dermatologic, hepatic, GI, pulmonary) × severity |
| **Key checks** | Correct filtering of irAEs, grouping by category, severity distribution |
| **Scoring** | N (%) per category/severity, total irAE N |
| **Cross-TC** | TC-011 (AE Summary); TC-029 (AE by Severity) |

---

## TC-033: Dose Intensity Summary (Level 1)

**Domain:** Exposure / Treatment Compliance
**Priority:** Medium — standard exposure TFL, required for safety submissions

| Parameter | Default |
|---|---|
| **Description** | Relative dose intensity (RDI) summary by arm — planned vs actual dose |
| **Data** | ADSL + ADEX with dose records |
| **Output** | Per-subject RDI = (actual dose / planned dose) × 100, summarized by arm (N, mean, median, range) |
| **Key checks** | Correct dose computation, handling of dose reductions/discontinuations |
| **Scoring** | Mean/median RDI per arm, % subjects with RDI ≥80%, % with dose reduction |
| **Cross-TC** | TC-016 (Exposure Table); TC-018 (CFB Table) |

---

## TC-034: Sufficient Follow-up Assessment (Level 1)

**Domain:** Safety / Study Conduct
**Priority:** Low — but commonly requested by FDA reviewers

| Parameter | Default |
|---|---|
| **Description** | Assess whether subjects have sufficient safety follow-up per protocol (e.g., 90 days post-last-dose) |
| **Data** | ADSL with last dose date, last follow-up date, treatment status |
| **Output** | N (%) with adequate follow-up by arm, median follow-up duration |
| **Key checks** | Date computation, adequate follow-up definition, handling of ongoing subjects |
| **Scoring** | N adequate, % adequate, median follow-up |
| **Cross-TC** | TC-014 (PD Listing); TC-031 (Time-to-First-Treatment) |

---

## TC-035: Overall Response Rate with DCR and ORR Composite (Level 2)

**Domain:** Efficacy / Tumor Response
**Priority:** Medium — Level 2 multi-TC integration

| Parameter | Default |
|---|---|
| **Description** | Generate a composite efficacy table integrating ORR, DCR, and response duration in a single integrated output |
| **Data** | ADSL + ADRS + ADTTE |
| **Output** | Integrated table: ORR (N, %, CI), DCR (N, %, CI), median DOR with CI, all by arm |
| **Key checks** | Cross-TFL consistency: ORR from TC-025, DCR from TC-023, DOR from TC-022 must all agree |
| **Scoring** | Composite score — all three components must match within tolerance |
| **Cross-TC** | TC-022 (DOR), TC-023 (DCR), TC-025 (BOR Summary) — Level 2 integration |

---

## Summary

| TC | Domain | Level | Priority | Key Addition |
|---|---|---|---|---|
| TC-029 | AE by Severity | 1 | High | Severity dimension to AE summary |
| TC-030 | ORR + Interaction | 1 | Medium | Formal interaction test |
| TC-031 | Time-to-First-Treatment | 1 | Low | Date handling, niche endpoint |
| TC-032 | Immune-Related AE | 1 | Medium | I-O specific safety |
| TC-033 | Dose Intensity | 1 | Medium | Exposure compliance |
| TC-034 | Sufficient Follow-up | 1 | Low | Study conduct quality metric |
| TC-035 | ORR/DCR/DOR Composite | 2 | Medium | Multi-TC integration (Level 2) |

### Recommended Next Steps
1. **TC-029** — implement immediately (high priority, straightforward)
2. **TC-033** — implement next (standard exposure TFL)
3. **TC-030** — implement after (extends existing TC-020)
4. **TC-032, TC-034** — implement as time permits
5. **TC-035** — implement after TC-029/033 are verified (Level 2 integration)
6. **TC-031** — lowest priority, implement only if WG requests
