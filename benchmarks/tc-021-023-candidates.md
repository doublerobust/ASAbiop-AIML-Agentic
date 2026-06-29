# TC-021/022/023 Candidate Design — Time-to-Event Progression, Duration of Response, Disease Control Rate

**Date:** 2026-06-29 (Day 29)
**Status:** Draft for WG Review

---

## TC-021: Time-to-Progression (TTP)

| Field | Value |
|---|---|
| **Domain** | Efficacy |
| **TFL Type** | Table |
| **Statistical Method** | Kaplan-Meier TTP estimation with 95% CI |
| **Description** | Time from randomization to first documented disease progression (death is censored, unlike PFS which includes death as an event) |
| **ADaM Dataset** | ADTTE (with PARAM = "Time to Progression") |
| **Key Variables** | AVAL, CNSR, TRT01PN, TRT01A |
| **Output Fields** | median_ttp, ci_lower, ci_upper, n_events, n_total, estimable |
| **Scoring** | Tolerance-based (same as TC-001) |
| **Languages** | R + Python + SAS |
| **Variants** | 6 (seed variation, N=100/200/400, censoring patterns) |
| **Compliance Rules** | TCG: death censoring documented; CSR: TTP vs PFS distinction stated |
| **Safety Rules** | N-count consistency with TC-001 (same study population), event count ≤ enrollment |

### Differentiation from TC-001
TC-021 uses the same KM methodology as TC-001 but with a different event definition:
- **PFS (TC-001):** Event = disease progression OR death (whichever comes first)
- **TTP (TC-021):** Event = disease progression only (death censored)

This tests whether the agent correctly handles censoring rules — a common source of programming errors in oncology trials.

---

## TC-022: Duration of Response (DOR)

| Field | Value |
|---|---|
| **Domain** | Efficacy |
| **TFL Type** | Table |
| **Statistical Method** | Kaplan-Meier DOR estimation among responders only |
| **Description** | Time from first documented response (CR or PR) to disease progression or death, among subjects who achieved a response |
| **ADaM Dataset** | ADTTE (with PARAM = "Duration of Response", filtered to responders) |
| **Key Variables** | AVAL, CNSR, TRT01PN, TRT01A, RESPONSE (CR/PR/SD/PD) |
| **Output Fields** | median_dor, ci_lower, ci_upper, n_responders, n_events, estimable |
| **Scoring** | Tolerance-based |
| **Languages** | R + Python + SAS |
| **Variants** | 5 (seed variation, response thresholds, N) |
| **Compliance Rules** | TCG: responder population definition; CSR: DOR population footnote |
| **Safety Rules** | n_responders ≤ n_total (from TC-020), responder subset consistency |

### Differentiation from TC-001/021
DOR is calculated only among responders (CR+PR), testing:
1. Correct subsetting to responder population
2. KM estimation on a selected subset (not the full ITT)
3. Handling of left truncation (response occurs after randomization)

---

## TC-023: Disease Control Rate (DCR)

| Field | Value |
|---|---|
| **Domain** | Efficacy |
| **TFL Type** | Table |
| **Statistical Method** | DCR (CR+PR+SD) rate with 95% CI by arm, difference test |
| **Description** | Proportion of subjects with disease control (CR + PR + SD) as best overall response, by treatment arm |
| **ADaM Dataset** | ADVS or ADRS (tumor response) |
| **Key Variables** | BOR (CR/PR/SD/PD), TRT01PN, TRT01A |
| **Output Fields** | dcr_experimental, dcr_control, ci_lower_exp, ci_upper_exp, ci_lower_ctrl, ci_upper_ctrl, dcr_difference, diff_ci_lower, diff_ci_upper |
| **Scoring** | Tolerance-based |
| **Languages** | R + Python + SAS |
| **Variants** | 5 (seed variation, SD duration threshold, N) |
| **Compliance Rules** | TCG: DCR definition (CR+PR+SD ≥X weeks); CSR: DCR vs ORR distinction |
| **Safety Rules** | DCR ≥ ORR (disease control includes response), n consistency with TC-020 |

### Differentiation from TC-020
DCR complements ORR (TC-020):
- **ORR (TC-020):** CR + PR rate
- **DCR (TC-023):** CR + PR + SD rate (broader benefit measure)

This tests whether the agent correctly categorizes additional response categories beyond ORR, and whether it maintains consistency between related endpoints.

---

## Implementation Priority

| TC | Priority | Rationale |
|---|---|---|
| TC-021 (TTP) | P1 | Direct extension of TC-001, tests censoring rule knowledge |
| TC-022 (DOR) | P2 | Tests subset analysis and left truncation handling |
| TC-023 (DCR) | P2 | Tests response categorization and cross-TFL consistency with TC-020 |

All three candidates use existing ADaM datasets (ADTTE/ADVS) and established statistical methods (KM, binomial proportion), making them straightforward to implement as Level 1 test cases.

---

## Cross-TFL Safety Rules (New)

Adding these TCs creates new cross-TFL agreement pairs:

| Pair | Rule |
|---|---|
| TC-001 ↔ TC-021 | PFS events ≥ TTP events (PFS includes death) |
| TC-020 ↔ TC-022 | n_responders in DOR = ORR responders from TC-020 |
| TC-020 ↔ TC-023 | DCR ≥ ORR (every responder also has disease control) |
| TC-021 ↔ TC-022 | TTP can be computed for all subjects; DOR only for responders |
