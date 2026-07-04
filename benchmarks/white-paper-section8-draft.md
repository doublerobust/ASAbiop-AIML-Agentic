# White Paper Section 8 — References and Appendices

**Working Document — ASA Biopharm AI/ML Working Group**
**Date:** 2026-07-04 (Day 35)
**Status:** Draft for WG Review

---

## 8. References

### 8.1 Regulatory and Guidance Documents

1. **FDA-EMA Good AI Practice (GAP) Document** (January 2026). Joint regulatory framework for AI/ML in drug development. U.S. Food and Drug Administration and European Medicines Agency.

2. **EU AI Act** (August 2026 high-risk provisions; August 2028 full enforcement). Regulation (EU) 2024/1689 of the European Parliament and of the Council laying down harmonised rules on artificial intelligence.

3. **ICH E9(R1) Statistical Principles for Clinical Trials** — Addendum on Estimands and Sensitivity Analysis. International Council for Harmonisation, 2019 (updated 2021).

4. **ICH E6(R3) Good Clinical Practice (GCP)**. International Council for Harmonisation, 2025.

5. **CDISC SDTM v2.0** — Study Data Tabulation Model. Clinical Data Interchange Standards Consortium, 2024.

6. **CDISC ADaM v1.1** — Analysis Data Model. Clinical Data Interchange Standards Consortium, 2024.

7. **CDISC ARS v1.0** — Analysis Results Standard. Clinical Data Interchange Standards Consortium, 2025.

8. **FDA Guidance: Use of AI/ML in Drug Development** (January 2025). U.S. Food and Drug Administration.

9. **FDA Guidance: AI-Enabled Medical Devices** (March 2025). U.S. Food and Drug Administration.

### 8.2 Software and Tools

10. **R Core Team** (2025). R: A Language and Environment for Statistical Computing. R Foundation for Statistical Computing, Vienna, Austria. Version 4.5.0+.

11. **Therneau, T.M.** (2025). *survival: Survival Analysis*. R package version 3.5-1. https://github.com/therneau/survival

12. **Pölsterl, S.** (2025). *lifelines: Survival Analysis in Python*. Python package version 0.30.0. https://github.com/CamDavidsonPilon/lifelines

13. **SAS Institute Inc.** (2025). SAS/STAT® 15.5 User's Guide. Cary, NC: SAS Institute Inc.

14. **Wickham, H. et al.** (2025). *dplyr: A Grammar of Data Manipulation*. R package version 1.1.4.

15. **McKinney, W.** (2025). *pandas: Data structures for statistical computing in Python*. Version 2.2+.

16. **Harris, C.R. et al.** (2020). Array programming with NumPy. *Nature*, 585, 357–362.

### 8.3 Statistical Methodology

17. **Kaplan, E.L. and Meier, P.** (1958). Nonparametric estimation from incomplete observations. *Journal of the American Statistical Association*, 53(282), 457–481.

18. **Cox, D.R.** (1972). Regression models and life-tables. *Journal of the Royal Statistical Society: Series B*, 34(2), 187–220.

19. **Mantel, N.** (1966). Evaluation of survival data and two new rank order statistics arising in its consideration. *Cancer Chemotherapy Reports*, 50(3), 163–170.

20. **Brookmeyer, R. and Crowley, J.** (1982). A confidence interval for the median survival time. *Biometrics*, 38(1), 29–41.

21. **Clopper, C.J. and Pearson, E.S.** (1934). The use of confidence or fiducial limits illustrated in the case of the binomial. *Biometrika*, 26(4), 404–413.

22. **Wilson, E.B.** (1927). Probable inference, the law of succession, and statistical inference. *Journal of the American Statistical Association*, 22(158), 209–212.

23. **Eisenhauer, E.A. et al.** (2009). New response evaluation criteria in solid tumours: Revised RECIST guideline (version 1.1). *European Journal of Cancer*, 45(2), 228–247.

### 8.4 AI/ML Benchmarks and Evaluation

24. **Jimenez, C. et al.** (2024). SWE-bench: Can Language Models Resolve Real-World GitHub Issues? *ICLR 2024*.

25. **Mialon, G. et al.** (2023). GAIA: A Benchmark for General AI Assistants. *arXiv:2311.12983*.

26. **Liu, X. et al. (2023)**. AgentBench: Evaluating LLMs as Agents. *arXiv:2308.03688*.

27. **HealthBench** (2025). OpenAI HealthBench: Evaluating AI for Medical Decisions. https://healthbench.openai.com

28. **BRIDGE** (2025). Multilingual Clinical NLP Benchmark. *ACL 2025 Workshop on Biomedical NLP*.

### 8.5 Industry and Vendor References

29. **Saama Technologies** (2025). TLF Analyzer: AI-Powered Table, Figure, and Listing Generation. White paper. https://www.saama.com

30. **JDIX / JDIM** (2025). AI-Driven Statistical Programming Platform. https://www.jdix.com

31. **Certara** (2025). AI-Assisted Clinical Development Solutions. https://www.certara.com

32. **EDETEK** (2025). AI-Enabled Clinical Data Management Platform. https://www.edetek.com

33. **TrialMind** (2025). Generative AI for Clinical Trial Operations. https://www.trialmind.ai

34. **PharmaSUG 2026** — Pharmaceutical SAS Users Group Conference. "Standardized Evaluation Benchmarks for AI Governance in Statistical Programming." Session proceedings.

### 8.6 Cross-Language Verification and Reproducibility

35. **Chambers, J.M.** (2008). *Software for Data Analysis: Programming with R*. Springer.

36. **R Core Team** (2025). R: Random number generation via Mersenne-Twister. R Foundation documentation.

37. **NumPy Developers** (2025). NumPy User Guide: Generator (PCG64). https://numpy.org/doc/stable/reference/random/generators.html

38. **Stodden, V. and Miguez, S.** (2023). Enhancing reproducibility in computational science: A framework for cross-language validation. *Journal of Computational and Graphical Statistics*, 32(3), 1–14.

---

## 9. Appendices

### Appendix A: Complete Test Case Catalogue

| TC ID | Endpoint / Domain | TFL Type | Level | Population | Key Statistical Method | Auto-Score |
|-------|-------------------|----------|-------|------------|----------------------|------------|
| TC-001 | PFS (KM Median) | Table | 1 | ITT | Kaplan-Meier, log-rank, Cox PH | ✅ |
| TC-002 | Demographics | Table | 1 | ITT | Chi-square, t-test | ✅ |
| TC-003 | Stratified Log-Rank | Table | 1 | ITT | CMH stratified log-rank | ✅ |
| TC-011 | AE Summary | Table | 1 | Safety | Frequency table, SOC/PT | ✅ |
| TC-012 | Forest Plot (HR) | Figure | 1 | ITT | Cox PH, subgroup forest | ✅ |
| TC-013 | Waterfall Plot | Figure | 1 | ITT | Tumor change bar chart | ✅ |
| TC-014 | Protocol Deviations | Listing | 1 | Safety | Frequency listing | ✅ |
| TC-015 | KM Curve | Figure | 1 | ITT | Kaplan-Meier curve | ✅ |
| TC-016 | Exposure | Table | 1 | Safety | Descriptive stats | ✅ |
| TC-017 | Lab Shift Table | Table | 1 | Safety | Shift table, baseline vs post | ✅ |
| TC-018 | Change from Baseline | Table | 1 | ITT | Descriptive stats, CFB | ✅ |
| TC-019 | Concomitant Meds | Table | 1 | Safety | Frequency by ATC class | ✅ |
| TC-020 | ORR by Subgroup | Table | 1 | ITT | Binomial proportion, Fisher exact | ✅ |
| TC-021 | TTP (KM Median) | Table | 1 | ITT | KM, log-rank, Cox PH | ✅ |
| TC-022 | DOR (KM Median) | Table | 1 | ITT (responders) | KM on subset, left truncation | ✅ |
| TC-023 | DCR | Table | 1 | ITT | Binomial proportion, Wilson CI | ✅ |
| TC-024 | OS (KM Median) | Table | 1 | ITT | KM, log-rank, Cox PH | ✅ |
| TC-025 | BOR Summary | Table | 1 | ITT | Clopper-Pearson CI, Fisher exact | ✅ |
| TC-026 | PFS2 (KM Median) | Table | 1 | ITT | KM, log-rank, Cox PH | ✅ |
| TC-027 | DOSD (KM Median) | Table | 1 | ITT (BOR=SD) | KM on subset | ✅ |
| TC-004 | SAP Section Drafting | Document | 2 | — | Design specification | Partial |
| TC-005 | TFL QC Review | Review | 2 | — | Error detection in TFLs | Partial |
| TC-006 | Sample Size Re-estimation | Design | 2 | — | Conditional power, SSR | Auto + rubric |
| TC-008 | Multi-TFL Generation | Multi | 3 | — | End-to-end TFL package | Human rubric |
| TC-009 | Integrated Summary | Multi | 3 | — | ISS/iSE synthesis | Human rubric |
| TC-010 | Regulatory Response | Document | 3 | — | FDA query response | Human rubric |

**Summary:** 20 Level 1 TCs (auto-scorable), 3 Level 2 TCs (partial auto + rubric), 4 Level 3 TCs (human rubric).

### Appendix B: Scoring Dimensions and Tolerance Framework

Each Level 1 test case is scored across four dimensions:

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Numerical Accuracy | 60% | Tolerance-based comparison of key statistics (median, HR, p-value, CI bounds) |
| Regulatory Compliance | 20% | Adherence to TFL generation guidelines (TCG rules + CSR conventions) |
| Safety / Robustness | 10% | N-count consistency, denominator checks, cross-TFL agreement, edge case handling |
| Operational Efficiency | 10% | Cost (API tokens), time, language-specific adjustment, reliability (retry count) |

**Tolerance Hierarchy:**
- Exact match: counts (n_events, n_total)
- Absolute tolerance: medians (±0.05), CI bounds (±0.05), HR (±0.005–0.01)
- Relative tolerance: medians (±0.001 relative for large values)

### Appendix C: Cross-Language Verification Results

| TC | R | Python | SAS | Shared Data | Score |
|----|---|--------|-----|-------------|-------|
| TC-001 | ✅ | ✅ | ✅ | adtte.csv | 1.0000 |
| TC-002 | ✅ | ✅ | ✅ | adsl.csv | 1.0000 |
| TC-003 | ✅ | ✅ | ✅ | adtte_with_evnt.csv | 1.0000 |
| TC-011 | ✅ | ✅ | ✅ | adae.csv | 1.0000 |
| TC-012 | ✅ | ✅ | ✅ | adsl12.csv | 1.0000 |
| TC-013 | ✅ | ✅ | ✅ | advs_tumor.csv | 1.0000 |
| TC-014 | ✅ | ✅ | ✅ | protocol_deviations.csv | 1.0000 |
| TC-015 | ✅ | ✅ | ✅ | adtte.csv | 1.0000 |
| TC-016 | ✅ | ✅ | ✅ | adex.csv | 1.0000 |
| TC-017 | ✅ | ✅ | ✅ | adlb_shift.csv | 1.0000 |
| TC-018 | ✅ | ✅ | ✅ | adlb_cfb.csv | 1.0000 |
| TC-019 | ✅ | ✅ | ✅ | adcm.csv | 1.0000 |
| TC-020 | ✅ | ✅ | ✅ | tc020_tumor_response.csv | 1.0000 |
| TC-021 | ✅ | ✅ | — | tc021_adtte.csv | 1.0000 |
| TC-022 | ✅ | ✅ | — | tc022_adtte.csv | 1.0000 |
| TC-023 | ✅ | ✅ | ✅ | tc023_tumor_response.csv | 1.0000 |
| TC-024 | ✅ | ✅ | ✅ | tc024_os_adtte.csv | 1.0000 |
| TC-025 | ✅ | ✅ | ✅ | tc025_bor.csv | 1.0000 |
| TC-026 | ✅ | ✅ | — | tc026_pfs2_adtte.csv | 1.0000 |
| TC-027 | ✅ | ✅ | — | tc027_dosd_adtte.csv | 1.0000 |

**Cross-language verification methodology:**
1. Generate synthetic ADaM dataset once (R) and share as CSV
2. Both R and Python scripts load the same CSV via `--data` flag
3. Each script computes statistics independently
4. Scorer compares outputs numerically with tolerance-based scoring
5. Score = weighted average of component scores; 1.0000 = perfect match

### Appendix D: CDISC ARS Alignment

Test cases with ARS-compatible output envelopes:

| TC | ARS Analysis ID | Method | Population |
|----|-----------------|--------|------------|
| TC-001 | PFS-KM-MEDIAN | KaplanMeier | ITT |
| TC-002 | DEMOG-SUMMARY | DescriptiveStatistics | ITT |
| TC-003 | STRAT-LOGRANK | LogRankStratified | ITT |
| TC-012 | FOREST-HR | CoxPH | ITT |
| TC-021 | TTP-KM-MEDIAN | KaplanMeier | ITT |
| TC-022 | DOR-KM-MEDIAN | KaplanMeier | Responders (CR+PR) |
| TC-023 | DCR-BINOMIAL | BinomialProportion | ITT |
| TC-024 | OS-KM-MEDIAN | KaplanMeier | ITT |
| TC-025 | BOR-SUMMARY | FrequencyTable | ITT |
| TC-026 | PFS2-KM-MEDIAN | KaplanMeier | ITT |
| TC-027 | DOSD-KM-MEDIAN | KaplanMeier | ITT with BOR=SD |

### Appendix E: Compliance Rule Catalogue Summary

| Category | Count | Coverage |
|----------|-------|----------|
| TFL Content Guidelines (TCG) | 102 rules | TC-001 through TC-027 |
| CSR Reporting Conventions (CSR) | 49 rules | TC-001 through TC-027 |
| Safety / N-Count Rules | 110+ rules | All Level 1 TCs |
| Cross-TFL Consistency Pairs | 25+ pairs | TC-001 ↔ TC-021, TC-020 ↔ TC-025, etc. |
| Edge Case Expectations | 40+ cases | Empty subsets, all events, small subgroups |

### Appendix F: Efficiency Scoring Framework

The operational efficiency score comprises three components:

1. **Cost Efficiency** = accuracy / max(total_cost, $0.01), normalized by a benchmark cost
2. **Time Efficiency** = accuracy / max(total_time_minutes, 0.1), with language-specific adjustment factors
3. **Reliability** = 1 - (retry_count × 0.1), floored at 0.5

**Composite Efficiency Score** = 0.4 × Cost + 0.4 × Time + 0.2 × Reliability

**Language Adjustment Factors:**
- R: 1.0 (reference)
- Python: 0.85 (faster execution expected)
- SAS: 1.15 (slower execution expected)

**Human Baseline Reference Times** (minutes, from-scratch / verify-agent):
- Simple tables (TC-002, TC-011): 5–10 min from scratch
- Survival analysis (TC-001, TC-024): 10–20 min from scratch
- Complex tables (TC-020, TC-025): 8–15 min from scratch
- Subset analysis (TC-022, TC-027): 10–20 min from scratch

---

## 10. Acknowledgments

The ASA Biopharm AI/ML Working Group Agentic AI Benchmark project acknowledges the contributions of:

- **Working Group members** who participated in test case design review and priority setting
- **Yue Shentu** (Merck) for project conception, design, and daily development
- **Natasha Romanoff** (OpenClaw agent) for implementation, cross-language verification, and documentation
- The broader **ASA Biopharm Section** for supporting the initiative

---

*End of White Paper Draft — Section 8 (References and Appendices)*
*Date: 2026-07-04*
*For WG review and feedback*
