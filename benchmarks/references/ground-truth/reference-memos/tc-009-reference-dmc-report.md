# TC-009 Reference DMC Report — Safety Signal Evaluation

**Test Case:** TC-009 — Safety Signal Evaluation and DMC Report (Level 3)
**Study:** BENCHMARK-009, Phase III oncology, Active vs Placebo, 1:1 randomization
**Report Type:** Independent Data Monitoring Committee (DMC) Safety Report
**Population:** Safety Analysis Set (SAFFL = Y), all randomized subjects (ITT)
**Reference Ground Truth:** R `tc-009-safety-signal.R` + Python `tc_009_safety_signal.py` on shared datasets (seed=42, n=200/arm)
**Cross-language verification:** R ↔ Python score = **1.0000** (841/841 fields)

> **Regulatory note (ITT-only):** This is a Phase III oncology superiority trial. The safety
> analysis set comprises all randomized subjects who received any study treatment (SAFFL = Y).
> No per-protocol (PP) analysis is performed for safety; ITT is the sole primary analysis
> population for regulatory decision-making, consistent with FDA/EMA standards for Phase III
> oncology studies.

---

## 1. AE Overview

| Endpoint | Active (N=200) | Placebo (N=200) | Risk Difference (95% CI) | Fisher p |
|---|---|---|---|---|
| Any AE | 200 (100.0%) | 194 (97.0%) | 0.030 (0.006, 0.054) | 0.0301 |
| SAE | 98 (49.0%) | 74 (37.0%) | 0.120 (0.024, 0.216) | 0.0201 |
| Discontinuation due to AE | 55 (27.5%) | 44 (22.0%) | 0.055 (−0.029, 0.139) | 0.2465 |
| Death on study | 17 (8.5%) | 21 (10.5%) | −0.020 (−0.077, 0.037) | 0.6095 |

Total AE reports: Active = 1,037; Placebo = 609. Total patient-years: Active = 207.56; Placebo = 215.57.

**Interpretation:** Overall AE and SAE rates are statistically significantly higher in the Active
arm. Death rates are numerically higher in Placebo (consistent with the efficacy hypothesis — worse
disease outcomes in the control arm). Discontinuation due to AEs is higher in Active but the 95% CI
includes 0 (not formally significant).

---

## 2. Exposure-Adjusted AE Rates (per 100 patient-years)

| Metric | Active | Placebo |
|---|---|---|
| AE reports per 100 PY | 499.62 | 282.51 |
| SAE reports per 100 PY | 65.52 | 39.89 |

Common AEs (≥5% in either arm) with elevated Active-arm rates per 100 PY include Fatigue (50.1 vs
28.8), Rash (39.0 vs 14.8), Nausea (49.1 vs 29.7), Diarrhoea (39.0 vs 20.4), and Pruritus (29.4 vs
9.7). Exposure-adjusted rates confirm the Active arm carries a higher AE burden after accounting
for differential follow-up time.

---

## 3. Grade 3+ Adverse Events

| Metric | Active | Placebo | Risk Difference (95% CI) | Fisher p |
|---|---|---|---|---|
| Subjects with ≥1 Grade 3+ AE | 138 (69.0%) | 97 (48.5%) | 0.205 (0.111, 0.299) | <0.0001 |

The Grade 3+ rate is statistically and clinically significantly higher in the Active arm. The most
imbalanced Grade 3+ events by risk difference include Neutropenia (24 vs 8; RD 0.080, 95% CI
0.027–0.133), Anaemia (21 vs 6; RD 0.075, 95% CI 0.026–0.124), Diarrhoea (16 vs 5; RD 0.055, 95% CI
0.012–0.098), Rash (16 vs 5; RD 0.055, 95% CI 0.012–0.098), and Drug-induced liver injury (12 vs 3;
RD 0.045, 95% CI 0.008–0.082).

---

## 4. Laboratory Abnormalities — Hy's Law & QTc Prolongation

### 4.1 Hy's Law (Hepatotoxicity / DILI risk)

| Metric | Active | Placebo | Risk Difference (95% CI) | Fisher p |
|---|---|---|---|---|
| Hy's Law cases (ALT or AST >3×ULN AND bilirubin >2×ULN) | 10 (5.0%) | 2 (1.0%) | 0.040 (0.007, 0.073) | 0.0358 |

Supporting lab abnormalities: ALT >3×ULN — Active 18, Placebo 2; AST >3×ULN — Active 10, Placebo 2;
Bilirubin >2×ULN — Active 10, Placebo 2.

**Hy's Law interpretation:** ALT or AST >3×ULN combined with total bilirubin >2×ULN indicates high
risk of severe drug-induced liver injury (DILI). The 10 vs 2 imbalance, with the 95% CI for the
risk difference excluding 0 and Fisher p = 0.0358, constitutes a confirmed Hy's Law signal. Per
FDA DILI guidance, confirmed Hy's Law cases warrant enhanced hepatotoxicity monitoring and a
protocol amendment for case management — but do not, in the absence of fatal DILI, mandate
automatic study termination.

### 4.2 QTc Prolongation

| Metric | Active | Placebo | Risk Difference (95% CI) | Fisher p |
|---|---|---|---|---|
| QTc >480 ms or Δ>60 ms from baseline | 9 (4.5%) | 5 (2.5%) | 0.020 (−0.016, 0.056) | 0.4155 |

The QTc signal is numerically higher in Active but the 95% CI includes 0 and does not meet the
pre-specified signal threshold (≥5 cases AND 95% CI excludes 0). QTc does not constitute a formal
signal in this dataset; continued routine ECG monitoring is recommended.

---

## 5. Time-to-First Grade 3+ AE (Kaplan-Meier, Log-Rank, Cox PH)

| Metric | Active | Placebo |
|---|---|---|
| Subjects with ≥1 Grade 3+ AE (events) | 138 | 97 |
| Median time-to-first Grade 3+ AE (days, 95% CI) | 202 (180, 296) | 426 (372, NE) |

- **Log-rank test:** p < 0.0001 — time-to-first Grade 3+ AE is significantly shorter in the Active arm.
- **Cox proportional hazards** (Active vs Placebo, Efron ties): **HR = 1.7711**, 95% CI (1.3647,
  2.2985), p < 0.0001. The Active arm experiences Grade 3+ AEs at ~1.77× the hazard rate of Placebo.

The Placebo upper 95% CI bound is non-estimable (NE) because the upper confidence band of the
survival curve does not cross 0.5 within the observed follow-up (insufficient Grade 3+ events in
the Placebo arm to bound the median from above).

---

## 6. Adverse Events of Special Interest — Immune-Related AEs (irAE)

| Metric | Active | Placebo | Risk Difference (95% CI) | Fisher p |
|---|---|---|---|---|
| Subjects with ≥1 irAE | 156 (78.0%) | 38 (19.0%) | 0.590 (0.511, 0.669) | <0.0001 |
| Median irAE onset (days) | 116.5 | 184.5 | — | — |

The irAE rate is markedly and significantly higher in the Active arm (78% vs 19%), with earlier
median onset in Active. This is consistent with the immunologic mechanism of the investigational
agent and constitutes a confirmed irAE signal.

---

## 7. Statistical Signal Detection

### 7.1 Empirical Bayes / MGPS (EBGM disproportionality)

MGPS-style screening (EBGM with add-one-half shrinkage; signal threshold: EBGM ≥ 2.0 AND observed
≥ 3) did not flag any preferred term at the Active-arm reporting proportion level. The
disproportionality screening is most informative in large spontaneous-reporting databases; in a
controlled trial with high background AE rates, the risk-difference approach (below) is more
sensitive for treatment-attributable signals.

### 7.2 Risk-Difference Signals (95% CI excludes 0)

14 preferred terms showed a statistically significantly higher rate in the Active arm (95% CI for
the risk difference excludes 0). The leading signals:

| Preferred Term | Active | Placebo | Risk Difference (95% CI) | Fisher p |
|---|---|---|---|---|
| Rash | 81 | 32 | 0.245 (0.160, 0.330) | <0.0001 |
| Fatigue | 104 | 62 | 0.210 (0.116, 0.304) | <0.0001 |
| Pruritus | 61 | 21 | 0.200 (0.123, 0.277) | <0.0001 |
| Nausea | 102 | 64 | 0.190 (0.095, 0.285) | 0.0002 |
| Diarrhoea | 81 | 44 | 0.185 (0.096, 0.274) | 0.0001 |
| Neutropenia | 51 | 25 | 0.130 (0.054, 0.206) | 0.0013 |
| ALT increased | 49 | 24 | 0.125 (0.050, 0.200) | 0.0018 |
| AST increased | 46 | 23 | 0.115 (0.042, 0.188) | 0.0034 |
| QT prolongation | 15 | 3 | 0.060 (0.020, 0.100) | 0.0063 |
| Drug-induced liver injury | 12 | 3 | 0.045 (0.008, 0.082) | 0.0319 |

(Plus: Anaemia, Vomiting, Peripheral neuropathy, Hypothyroidism.) The convergence of hepatic
(ALT/AST increased, Drug-induced liver injury) and dermatologic/immune (Rash, Pruritus) signals
corroborates the Hy's Law and irAE findings.

---

## 8. Safety Recommendation — DMC Action

### Signal Summary

| Signal | Flag | Criterion (met) |
|---|---|---|
| Hy's Law (hepatotoxicity) | ✅ TRUE | ≥5 cases AND 95% CI excludes 0 (10 vs 2, p=0.0358) |
| QTc prolongation | ❌ FALSE | Numerically higher but 95% CI includes 0 (9 vs 5, p=0.4155) |
| irAE | ✅ TRUE | ≥10 cases AND 95% CI excludes 0 (156 vs 38, p<0.0001) |
| Grade 3+ AE rate | ✅ TRUE | 95% CI excludes 0 (RD 0.205, 95% CI 0.111–0.299) |
| Discontinuation | ❌ FALSE | 95% CI includes 0 |
| Death | ❌ FALSE | Higher in Placebo (disease-related) |
| **Total confirmed signals** | **3** | |

### Overall Recommendation: **MODIFY** (continue with enhanced monitoring and protocol amendment)

**Rationale:** Three significant safety signals are confirmed — Hy's Law hepatotoxicity, immune-
related AEs, and the Grade 3+ AE rate — without evidence of a fatal DILI case or an overwhelming
signal burden (n_signals = 3 < 4). Per FDA DILI guidance, confirmed Hy's Law cases trigger
intensified laboratory monitoring and a protocol amendment for Hy's Law case management rather than
automatic study termination. The combination of a confirmed Hy's Law signal with co-occurring
irAE/Grade 3+ signals warrants a protocol modification with enhanced monitoring and tighter
stopping rules.

### Recommended Conditions / Mitigation Actions

1. Implement enhanced hepatotoxicity monitoring (weekly LFTs for the first 8 weeks of treatment).
2. Protocol amendment for a Hy's Law case management algorithm (hold drug, investigate, re-challenge
   guidance, hepatology consult for confirmed cases).
3. Consider an independent hepatic safety review board for ongoing adjudication of liver events.
4. Implement irAE management guidelines per ASCO/NCCN immune-related toxicity guidance.
5. Ensure mandatory corticosteroid availability for Grade 2+ irAE management.
6. Continue routine DMC safety reviews at the planned interim and final analysis intervals.
7. Continue ECG/QTc monitoring at scheduled visits (QTc signal not formally confirmed but
   numerically elevated; maintain vigilance).

### Stopping Rules (recommended)

- Pause enrollment and convene an ad-hoc DMC meeting if any fatal DILI case is confirmed.
- Pause enrollment if ≥4 confirmed safety signals develop (including Hy's Law) or if the Grade 3+
  AE excess is accompanied by a confirmed QTc signal and an excess of drug-related deaths.

---

## Appendix: Methods

- **Risk difference:** Active − Placebo, 95% normal-approximation CI; Fisher exact two-sided p-value.
- **Exposure-adjusted rates:** AE/SAE reports per 100 patient-years; common AEs ≥5% in either arm.
- **Hy's Law:** (ALT or AST >3×ULN) AND (total bilirubin >2×ULN), per FDA DILI guidance.
- **QTc prolongation:** max QTc >480 ms OR Δ from baseline >60 ms.
- **Time-to-event:** Kaplan-Meier median with Brookmeyer-Crowley 95% CI (log-transform); log-rank
  test; Cox proportional hazards (Efron ties), Active vs Placebo (Placebo reference).
- **MGPS:** Empirical Bayes geometric mean (EBGM) with add-one-half (Beta(0.5,0.5)) shrinkage;
  signal threshold EBGM ≥ 2.0 AND observed ≥ 3.
- **Recommendation logic:** deterministic, totality-of-evidence (Hy's Law, QTc, irAE, Grade 3+,
  discontinuation, death signals).
- **Cross-language verification:** R and Python ground truth computed on identical shared datasets
  (ADSL/ADAE/ADLB CSVs); 841/841 fields match (score = 1.0000).
