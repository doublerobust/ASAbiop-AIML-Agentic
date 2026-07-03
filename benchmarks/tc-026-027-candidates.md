# TC-026 and TC-027 Candidate Design

## TC-026: Time to Second Progression (PFS2)

### Overview
- **Domain:** Efficacy (time-to-event)
- **TFL Type:** Table (KM median with CI)
- **Difficulty Level:** 1 (auto-scorable)
- **Endpoint:** PFS2 — time from randomization to second disease progression or death, whichever comes first
- **Population:** ITT (ITTFL = "Y")

### Clinical Context
PFS2 is a regulatory-relevant endpoint introduced to capture the total duration of disease control, including post-progression treatment benefit. It is particularly relevant in immuno-oncology and ADC trials where post-progression therapy may confer additional benefit. PFS2 is defined per RECIST 1.1 as the time from randomization to the first documented progression **after the initial progression** (i.e., second progression) or death, whichever occurs first.

Key distinction from PFS (TC-001):
- PFS: Time to **first** progression or death
- PFS2: Time to **second** progression or death (captures post-1st-progression benefit)

### What This Tests
1. Correct understanding of PFS2 endpoint definition (second progression, not first)
2. Handling of competing risks: subjects without first progression cannot have PFS2 event
3. KM estimation with complex censoring (censor at last assessment if no second progression)
4. Log-rank test and Cox PH HR for treatment comparison
5. Cross-TFL consistency: PFS2 ≥ PFS for every subject (PFS2 events ≤ PFS events in count but times ≥ PFS times)

### Data Generation
- ADTTE dataset with: USUBJID, TRT01PN, AVAL (PFS2 time), CNSR, ITTFL, SEX, AGEGR1, ECOG
- PFS2 time ≥ PFS time for all subjects (by construction)
- Event indicator: CNSR=0 (second progression or death), CNSR=1 (censored)
- Base rate: median PFS2 control = 9 months (longer than PFS median of 6 months)
- HR = 0.65 (larger treatment effect than PFS, reflecting post-progression benefit)

### Output Schema
```json
{
  "test_case_id": "TC-026",
  "endpoint": "Progression-Free Survival 2",
  "population": "ITT",
  "arm_control": {
    "median_pfs2": <number>,
    "median_ci_lower": <number>,
    "median_ci_upper": <number>,
    "n_events": <integer>,
    "n_total": <integer>,
    "event_rate": <number>
  },
  "arm_experimental": { ... },
  "logrank_p": <number>,
  "hazard_ratio": <number>,
  "hr_ci_lower": <number>,
  "hr_ci_upper": <number>,
  "subgroups": [ ... ],
  "language": "<R|Python|SAS>",
  "version": "1.0"
}
```

### Tolerances
- median_pfs2: ±0.05 absolute, ±0.001 relative
- CI bounds: ±0.05 absolute
- HR: ±0.005 absolute
- log-rank p: ±0.005
- n_events, n_total: exact match

### Compliance Rules (Planned)
- TCG: PFS2 endpoint definition (second progression or death), ITT filter, KM median with CI, log-rank, Cox PH, subgroup analysis
- CSR: Table numbering, title, CI method footnote, endpoint definition footnote

### Safety Rules (Planned)
- N-count: PFS2 events ≤ ITT N, PFS2 event+censor = ITT N
- Cross-TFL: PFS2 ITT N = PFS ITT N (TC-001), PFS2 median ≥ PFS median
- Edge cases: no second progressions (all censored), all events, small subgroup

### Cross-TFL Relationships
- TC-026 ↔ TC-001 (PFS): Same ITT N, PFS2 median ≥ PFS median
- TC-026 ↔ TC-024 (OS): PFS2 events ≤ OS events (PFS2 censors at 2nd progression, OS at death)

### Implementation Priority: P1 (next TC to implement after Day 34)

---

## TC-027: Duration of Stable Disease (DOSD)

### Overview
- **Domain:** Efficacy (time-to-event, subset analysis)
- **TFL Type:** Table (KM median with CI)
- **Difficulty Level:** 1 (auto-scorable)
- **Endpoint:** Duration of Stable Disease — time from first documentation of SD (stable disease) to disease progression or death, among subjects whose BOR = SD
- **Population:** ITT subjects with BOR = SD (subset analysis)

### Clinical Context
DOSD measures how long subjects with stable disease maintain disease control before progressing. It is a secondary efficacy endpoint that provides insight into the durability of non-response benefit. While ORR captures responder benefit and DCR captures disease control rate, DOSD captures the **duration** of the stable disease component.

Key distinction from DOR (TC-022):
- DOR: Duration among responders (CR+PR) — time from response to progression/death
- DOSD: Duration among SD subjects — time from SD documentation to progression/death

### What This Tests
1. Correct subset identification (BOR = SD only, not CR/PR/PD/NE)
2. Time-to-event analysis on a non-trivial subset (typically 30-45% of ITT)
3. Left truncation potential (SD must be confirmed before clock starts)
4. KM estimation with small-to-moderate sample sizes
5. Cross-TFL consistency: DOSD subjects = ITT N × (SD proportion from TC-025)

### Data Generation
- ADTTE dataset with: USUBJID, TRT01PN, AVAL (DOSD time), CNSR, BOR, ITTFL, SEX, AGEGR1, ECOG
- Only subjects with BOR = "SD" are included in analysis
- Event = progression or death
- Base rate: median DOSD = 4.5 months (shorter than DOR, as SD subjects have less durable benefit)
- HR = 0.80 (modest treatment effect on DOSD, as SD duration may be less treatment-sensitive)

### Output Schema
```json
{
  "test_case_id": "TC-027",
  "endpoint": "Duration of Stable Disease",
  "population": "ITT with BOR=SD",
  "arm_control": {
    "median_dosd": <number>,
    "median_ci_lower": <number>,
    "median_ci_upper": <number>,
    "n_events": <integer>,
    "n_total": <integer>,
    "event_rate": <number>
  },
  "arm_experimental": { ... },
  "logrank_p": <number>,
  "hazard_ratio": <number>,
  "hr_ci_lower": <number>,
  "hr_ci_upper": <number>,
  "subgroups": [ ... ],
  "language": "<R|Python|SAS>",
  "version": "1.0"
}
```

### Tolerances
- median_dosd: ±0.05 absolute, ±0.001 relative
- CI bounds: ±0.05 absolute
- HR: ±0.01 absolute (wider than TC-026 due to smaller sample)
- log-rank p: ±0.01
- n_events, n_total: exact match

### Compliance Rules (Planned)
- TCG: DOSD endpoint definition (SD to PD/death), BOR=SD subset filter, ITT filter, KM median with CI, log-rank, Cox PH
- CSR: Table numbering, title, subset definition footnote, CI method footnote

### Safety Rules (Planned)
- N-count: DOSD subjects = ITT N × SD proportion (cross-TFL with TC-025), DOSD events+censor = SD N
- Cross-TFL: DOSD N = TC-025 SD count, DOSD N ≤ DCR N (TC-023, since SD ⊂ DCR)
- Edge cases: no SD subjects (empty analysis), all SD subjects progress, small subgroup

### Cross-TFL Relationships
- TC-027 ↔ TC-025 (BOR Summary): DOSD N = SD count from BOR distribution
- TC-027 ↔ TC-023 (DCR): DOSD N ≤ DCR N (SD is subset of DCR)
- TC-027 ↔ TC-022 (DOR): DOSD subjects and DOR subjects are disjoint (SD vs CR+PR)

### Implementation Priority: P2 (after TC-026)

---

## Summary

| TC | Endpoint | Population | Key Distinction | Priority |
|---|---|---|---|---|
| TC-026 | PFS2 (2nd progression) | ITT | Second progression, not first | P1 |
| TC-027 | Duration of Stable Disease | ITT ∩ BOR=SD | SD subset, not responder subset | P2 |

These two TCs expand the time-to-event coverage to 6 endpoints (PFS, TTP, DOR, OS, PFS2, DOSD), providing comprehensive assessment of an agent's ability to correctly implement different survival analysis definitions.
