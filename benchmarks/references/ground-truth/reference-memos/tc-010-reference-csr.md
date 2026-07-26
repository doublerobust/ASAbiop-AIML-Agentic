# Reference CSR — Statistical Methods and Results Sections (ICH E3)

## TC-010: Draft CSR Statistical Sections (Sections 9 and 11)

**Study:** BENCHMARK-010 — Phase III, Drug X (Active) vs Placebo in Advanced Solid Tumors
**Primary Endpoint:** Progression-Free Survival (PFS) per RECIST 1.1
**Analysis Population:** Intent-to-Treat (ITT) — all randomized subjects
**Document:** Sections 9 and 11 of the ICH E3-compliant Clinical Study Report (CSR)

> **Regulatory Note:** This is a Phase III oncology superiority trial. ITT is the
> SOLE primary analysis population. No per-protocol analysis is performed, per
> FDA/EMA regulatory standards. The safety analysis set is all randomized subjects
> who received any study treatment (SAFFL = Y).

This document covers Section 9 (Statistical Methods) and Section 11 (Statistical
Results) of the ICH E3-compliant Clinical Study Report. Section 11 is further
subdivided into Section 11.1 (Patient Disposition), Section 11.2 (Demographics),
Section 11.4 (Efficacy Results), and Section 11.5 (Safety Results).

---

## 9. Statistical Methods

### 9.1 Analysis Populations

| Population | Definition | Criteria |
|---|---|---|
| Intent-to-Treat (ITT) | All randomized subjects | ITTFL = "Y" (primary analysis population) |
| Safety | All subjects who received any study treatment | SAFFL = "Y" |

### 9.2 Primary Efficacy Analysis

The primary efficacy endpoint is Progression-Free Survival (PFS), defined as the
time from randomization to the first documented disease progression per RECIST 1.1
or death from any cause, whichever occurs first. Subjects without an event were
censored at the last known tumor assessment date.

- **Estimation:** Kaplan-Meier product-limit method, with median PFS and 95%
  confidence intervals (Brookmeyer-Crowley log-transform) reported by treatment arm.
- **Comparison:** Two-sided log-rank test (alpha = 0.05).
- **Hazard Ratio:** Cox proportional hazards model with treatment as the sole
  covariate, using Efron's method for tie handling. Hazard ratio (Active vs Placebo)
  with 95% CI and Wald p-value reported.
- **No multiplicity adjustment** was applied to the primary endpoint (single
  primary endpoint). Secondary endpoints were reported descriptively.

### 9.3 Secondary Efficacy Analyses

- **Overall Survival (OS):** Time from randomization to death from any cause.
  Kaplan-Meier estimation, log-rank test, and Cox PH hazard ratio (same method as PFS).
- **Objective Response Rate (ORR):** Proportion of subjects with best overall
  response (BOR) of CR or PR per RECIST 1.1. Reported with 95% exact CI; treatment
  comparison via Fisher's exact test and risk difference with Wald 95% CI.
- **Disease Control Rate (DCR):** Proportion of subjects with BOR of CR, PR, or SD.
  Same statistical approach as ORR.

### 9.4 Subgroup Analyses

Forest plot of PFS hazard ratios by pre-specified subgroups: sex (M/F), age group
(<65 / ≥65), ECOG performance status (0/1), and disease stage (IIIB/IV). Each
subgroup analyzed with a Cox PH model within the subgroup stratum. No formal
interaction testing; subgroups are exploratory.

### 9.5 Sensitivity Analysis

A sensitivity analysis for PFS was performed to assess the robustness of the
primary result to informative censoring. Subjects who discontinued for reasons
other than disease progression or death (i.e., "Withdrawal by subject" or
"Physician decision") and who had a PFS event were re-censored at their last
follow-up date.

### 9.6 Safety Analyses

Adverse events were coded using MedDRA (current version) by System Organ Class
(SOC) and Preferred Term (PT). Summary statistics include: number (%) of subjects
with any AE, serious AEs (SAE), Grade ≥3 AEs, AEs leading to treatment
discontinuation, and deaths. Laboratory abnormalities summarized as the proportion
of subjects with maximum post-baseline values exceeding pre-specified thresholds
(ALT >3×ULN, AST >3×ULN, bilirubin >2×ULN).

### 9.7 Software and Data Handling

- **Software:** R 4.6.1 with survival package 3.8.6 (reference implementation);
  Python 3.9 with lifelines 0.30.0 (cross-validation implementation).
- **Data cutoff:** Database lock after last patient last visit.
- **Missing data:** Subjects with missing PFS event dates were censored at the
  last known tumor assessment date. No imputation was performed for the primary
  analysis.

---

## 11. Statistical Results

### 11.1 Patient Disposition

A total of **400 subjects** were randomized 1:1 to Active (n=200) or Placebo
(n=200). All randomized subjects were included in the ITT population and received
study treatment (safety population).

**Table 11.1.1: Subject Disposition (ITT Population)**

| Disposition | Active (N=200) | Placebo (N=200) | Total (N=400) |
|---|---|---|---|
| Completed study | 169 (84.5%) | 155 (77.5%) | 324 (81.0%) |
| Discontinued | 31 (15.5%) | 45 (22.5%) | 76 (19.0%) |
| — Disease progression | 14 | 23 | 37 |
| — Adverse event | 7 | 9 | 16 |
| — Withdrawal by subject | 8 | 10 | 18 |
| — Physician decision | 2 | 3 | 5 |
| Died on study | 48 (24.0%) | 73 (36.5%) | 121 (30.3%) |
| Major protocol deviations | 34 (17.0%) | 32 (16.0%) | 66 (16.5%) |
| Total deviations | 44 | 43 | 87 |

The discontinuation rate was higher in the Placebo arm (22.5%) compared to the
Active arm (15.5%), primarily driven by disease progression (23 vs 14 subjects).
The death rate was higher in Placebo (36.5%) than Active (24.0%), consistent with
the efficacy benefit of Active. Major protocol deviations were balanced between
arms (17.0% vs 16.0%).

### 11.2 Demographics and Baseline Characteristics

**Table 11.2.1: Baseline Demographics (ITT Population)**

| Characteristic | Active (N=200) | Placebo (N=200) |
|---|---|---|
| Age (years), mean ± SD | 61.3 ± 10.2 | 62.1 ± 9.4 |
| Age <65, n (%) | 130 (65.0%) | 126 (63.0%) |
| Age ≥65, n (%) | 70 (35.0%) | 74 (37.0%) |
| Sex: Male, n (%) | 126 (63.0%) | 99 (49.5%) |
| Sex: Female, n (%) | 74 (37.0%) | 101 (50.5%) |
| Race: White, n (%) | 148 (74.0%) | 141 (70.5%) |
| Race: Asian, n (%) | 26 (13.0%) | 35 (17.5%) |
| Race: Black, n (%) | 13 (6.5%) | 19 (9.5%) |
| Race: Other, n (%) | 13 (6.5%) | 5 (2.5%) |
| ECOG 0, n (%) | 103 (51.5%) | 125 (62.5%) |
| ECOG 1, n (%) | 97 (48.5%) | 75 (37.5%) |
| Disease stage IIIB, n (%) | 69 (34.5%) | 56 (28.0%) |
| Disease stage IV, n (%) | 131 (65.5%) | 144 (72.0%) |
| Treatment duration (mo), mean | 9.4 | 9.0 |

**Baseline balance tests:**
- Age: t-test p = 0.4546 (no significant difference)
- Sex: chi-square p = 0.0088 (significant imbalance — more males in Active arm)

> **Note:** A statistically significant sex imbalance was observed between
> treatment arms (p = 0.0088). The Active arm had a higher proportion of male
> subjects (63.0% vs 49.5%). This imbalance should be considered when interpreting
> subgroup analyses by sex. Age and other baseline characteristics were balanced.

### 11.4 Efficacy Results

#### 11.4.1 Primary Endpoint: Progression-Free Survival (PFS)

**Table 11.4.1: PFS Summary (ITT Population)**

| Parameter | Active (N=200) | Placebo (N=200) |
|---|---|---|
| Number of events, n (%) | 115 (57.5%) | 150 (75.0%) |
| Number censored, n (%) | 85 (42.5%) | 50 (25.0%) |
| Median PFS (days) | 282.4 | 158.7 |
| 95% CI for median | (248.4, 377.1) | (140.6, 184.9) |

| Comparison | Value | 95% CI | p-value |
|---|---|---|---|
| Hazard Ratio (Active vs Placebo) | 0.5607 | (0.4390, 0.7161) | <0.0001 |
| Log-rank test | — | — | <0.0001 |

**Interpretation:** The primary endpoint of PFS demonstrated a statistically
significant and clinically meaningful benefit for Active compared to Placebo.
The hazard ratio of 0.5607 (95% CI: 0.439–0.716, p < 0.0001) represents a **44%
reduction in the risk of progression or death** for Active-treated subjects. The
median PFS was nearly doubled in the Active arm (282.4 days vs 158.7 days).

**Figure 11.4.1: Kaplan-Meier Curve of PFS by Treatment Arm**
*(Reference: TFL Package, Figure 14.2.1.1)*

#### 11.4.1.1 Sensitivity Analysis: PFS

A sensitivity analysis re-censoring subjects who discontinued for non-progression
reasons (withdrawal by subject, physician decision) confirmed the robustness of
the primary PFS result:

| Parameter | Value | 95% CI | p-value |
|---|---|---|---|
| Hazard Ratio (sensitivity) | 0.5679 | (0.4411, 0.7313) | <0.0001 |

The sensitivity analysis hazard ratio (0.5679) is consistent with the primary
analysis (0.5607), confirming that the treatment effect is robust to the handling
of informative censoring.

#### 11.4.1.2 Subgroup Analysis: PFS Forest Plot

**Table 11.4.1.2: PFS Hazard Ratios by Subgroup (ITT Population)**

| Subgroup | Level | N | Events | HR | 95% CI | p-value |
|---|---|---|---|---|---|---|
| Sex | Male | 225 | — | 0.5361 | — | 0.0003 |
| Sex | Female | 175 | — | 0.6132 | — | 0.0087 |
| Age group | <65 | 256 | — | 0.6030 | — | 0.0014 |
| Age group | ≥65 | 144 | — | 0.4794 | — | 0.0003 |
| ECOG | 0 | 228 | — | 0.5034 | — | 0.0001 |
| ECOG | 1 | 172 | — | 0.6538 | — | 0.0241 |
| Disease stage | IIIB | 125 | — | 0.5335 | — | 0.0069 |
| Disease stage | IV | 275 | — | 0.5719 | — | 0.0002 |

**Interpretation:** The PFS benefit was consistent across all pre-specified
subgroups. All hazard ratios were below 1.0 with p-values < 0.05, indicating a
uniform treatment effect regardless of sex, age, ECOG performance status, or
disease stage. The strongest effect was observed in subjects aged ≥65 (HR=0.4794)
and ECOG 0 subjects (HR=0.5034).

#### 11.4.2 Secondary Endpoint: Overall Survival (OS)

**Table 11.4.2: OS Summary (ITT Population)**

| Parameter | Active (N=200) | Placebo (N=200) |
|---|---|---|
| Number of events, n (%) | — | — |
| Median OS (days) | 776.4 | 553.0 |

| Comparison | Value | 95% CI | p-value |
|---|---|---|---|
| Hazard Ratio (Active vs Placebo) | 0.6591 | (0.5074, 0.8561) | 0.0018 |
| Log-rank test | — | — | 0.0022 |

**Interpretation:** Overall survival demonstrated a statistically significant
benefit for Active (HR = 0.6591, 95% CI: 0.507–0.856, p = 0.0018), representing a
**34% reduction in the risk of death**. The median OS was 776.4 days in the Active
arm compared to 553.0 days in the Placebo arm.

#### 11.4.3 Secondary Endpoints: ORR and DCR

**Table 11.4.3: Tumor Response Summary (ITT Population)**

| Parameter | Active (N=200) | Placebo (N=200) |
|---|---|---|
| ORR (CR+PR), n (%) | 69 (34.5%) | 12 (6.0%) |
| DCR (CR+PR+SD), n (%) | 132 (66.0%) | 90 (45.0%) |

| Endpoint | Risk Difference | 95% CI | Fisher p-value |
|---|---|---|---|
| ORR | 0.2850 | (0.2114, 0.3586) | <0.0001 |
| DCR | 0.2100 | — | — |

**Interpretation:** The objective response rate was significantly higher in the
Active arm (34.5%) compared to Placebo (6.0%), with a risk difference of 28.5%
(95% CI: 21.1%–35.9%, p < 0.0001). The disease control rate was also significantly
higher (66.0% vs 45.0%), demonstrating that Active provides both tumor shrinkage
and disease stabilization benefits.

### 11.5 Safety Results

#### 11.5.1 Adverse Event Overview

**Table 11.5.1: AE Summary (Safety Population)**

| AE Category | Active (N=200) | Placebo (N=200) |
|---|---|---|
| Any AE, n (%) | 180 (90.0%) | 127 (63.5%) |
| Serious AE, n (%) | 47 (23.5%) | 39 (19.5%) |
| Grade ≥3 AE, n (%) | 77 (38.5%) | 60 (30.0%) |
| AE leading to discontinuation, n (%) | 29 (14.5%) | 27 (13.5%) |
| Deaths, n (%) | 48 (24.0%) | 73 (36.5%) |
| Total AE reports | 501 | 311 |

The overall AE rate was higher in the Active arm (90.0% vs 63.5%), consistent with
the known safety profile of the investigational agent. Grade ≥3 AEs were more
frequent in the Active arm (38.5% vs 30.0%), as were serious AEs (23.5% vs 19.5%).
However, the death rate was higher in the Placebo arm (36.5% vs 24.0%), reflecting
the efficacy benefit of Active in reducing disease-related mortality.

#### 11.5.2 Adverse Events by System Organ Class (Active Arm)

**Table 11.5.2: Top 5 SOCs by Subject Frequency (Active Arm)**

| SOC | Subjects n (%) | Reports n | Top Preferred Terms |
|---|---|---|---|
| Respiratory, thoracic and mediastinal disorders | 58 (29.0%) | 71 | Cough (40), Dyspnoea (31) |
| Metabolism and nutrition disorders | 57 (28.5%) | 67 | Hypokalaemia (39), Decreased appetite (28) |
| Blood and lymphatic system disorders | 55 (27.5%) | 64 | Neutropenia (24), Thrombocytopenia (24), Anaemia (16) |
| General disorders | 54 (27.0%) | 64 | Fatigue (25), Pyrexia (21), Oedema peripheral (18) |
| Skin and subcutaneous tissue disorders | 53 (26.5%) | 64 | Rash (28), Alopecia (19), Pruritus (17) |

#### 11.5.5 Deaths

**Table 11.5.5: Death Summary**

| Category | Active | Placebo | Total |
|---|---|---|---|
| Deaths (any cause), n | 48 | 73 | 121 |
| Grade 5 AE reports, n | — | — | 18 |

The higher death rate in the Placebo arm (73 vs 48) is consistent with the observed
efficacy benefit of Active on overall survival. Grade 5 adverse event reports (n=18)
represent fatal events potentially related to study treatment or underlying disease.

#### 11.5.6 Laboratory Abnormalities

**Table 11.5.6: Laboratory Abnormalities (Safety Population)**

| Lab Abnormality | Active (N=200) | Placebo (N=200) |
|---|---|---|
| ALT >3×ULN, n (%) | 0 (0.0%) | 0 (0.0%) |
| AST >3×ULN, n (%) | 0 (0.0%) | 0 (0.0%) |
| Bilirubin >2×ULN, n (%) | 0 (0.0%) | 0 (0.0%) |
| ALT (mean max), U/L | — | — |
| AST (mean max), U/L | — | — |
| Bilirubin (mean max), mg/dL | — | — |

No subjects in either treatment arm met the laboratory abnormality thresholds for
ALT >3×ULN, AST >3×ULN, or bilirubin >2×ULN, indicating no hepatotoxicity signal
in this study.

---

## Conclusions

The study met its primary endpoint. Drug X (Active) demonstrated a statistically
significant and clinically meaningful improvement in PFS compared to Placebo
(HR = 0.5607, 95% CI: 0.439–0.716, p < 0.0001), with a consistent benefit across
all pre-specified subgroups. The secondary endpoints of OS (HR = 0.6591, p = 0.0018)
and ORR (34.5% vs 6.0%, p < 0.0001) also demonstrated significant benefit. The
safety profile was manageable, with higher rates of AEs in the Active arm but a
lower death rate, consistent with the efficacy benefit. The totality of evidence
supports the efficacy and acceptable safety of Drug X in this patient population.

---

*This reference CSR document was generated from the TC-010 ground truth analysis
(Study BENCHMARK-010, seed=42, N=400). All numerical values are verified by
R↔Python cross-language verification (score = 1.0000, 341/341 fields match).*
