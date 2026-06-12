# Vendor Capabilities Catalog — AI-Powered TFL Review & Automation

**Version:** 0.1
**Date:** 2026-06-11
**Author:** Natasha, on behalf of ASA Biopharm AI/ML WG — Agentic AI Workstream

---

## 1. Purpose

This catalog documents existing commercial AI TFL tools and services to:

1. **Provide competitive benchmarks** — each vendor's claimed capabilities become an evaluation target
2. **Identify gaps** — features vendors don't cover (where our benchmark can differentiate)
3. **Calibrate "human baseline"** — understand what experienced programmers actually do vs. what agents claim to do
4. **Support the WG's "exam" framing** — vendors self-assess using our published benchmark cases
5. **Track market evolution** — the vendor landscape changes rapidly; maintain as a living document

---

## 2. Benchmark Context

Per the framework (Section 1.2), this benchmark is **pharma-led, not vendor-led**. Vendor products are evaluated, not endorsed. This document captures vendor claims objectively for WG analysis.

### 2.1 Mapping to Benchmark Dimensions

Each vendor is evaluated against the benchmark's core dimensions:

| Dimension | Benchmark Definition | Why It Matters |
|---|---|---|
| **Numerical Correctness** (weight: 0.35) | Can the tool produce statistically correct TFLs? | Primary signal — is the output correct? |
| **Schema Compliance** (weight: 0.10) | Does output conform to CDISC/ICH standards? | Regulatory submission requirement |
| **Safety & Consistency** (weight: 0.25) | Does output pass cross-table, N-count, denominator checks? | Industry QC pain point |
| **Regulatory Compliance** (weight: 0.15) | ADaM mapping, FDA TCG, CSR formatting | Submission readiness |
| **Operational Efficiency** (weight: 0.15) | Cost, time, first-pass success rate | Practical deployment |

---

## 3. Vendor Catalog

### 3.1 Saama — TLF Analyzer

| Attribute | Details |
|---|---|
| **Company** | Saama (Campbell, CA) |
| **Product** | TLF Analyzer (part of AI-powered DS/CM platform) |
| **Announced** | October 30, 2025 |
| **Claimed Capabilities** | Multi-modal GenAI for TFL summarization; Protocol/SAP-grounded analysis; "Figures-to-Text" (KM curves, forest plots, waterfall plots, box plots into text summaries); NLP-powered TFL search; interactive refinement (shorten/elaborate/bullet); CSR traceable summaries with citations |
| **Claimed Results** | CSR drafting reduced from 2-3 weeks to 3-4 days; 60-70% reduction in manual analysis time |
| **Error Detected Against Our TCs** | Unknown — not yet benchmarked |
| **Error Categories** | Primarily interpretive (summarization) rather than verification |
| **Key Papers** | PharmaSUG 2026 (Saama presented multiple AI papers) |
| **Relevance to Benchmark** | **HIGH** — first commercial product explicitly branded as "TLF Analyzer"; multi-modal figures-to-text directly tests our safety dimension (cross-TFL consistency, figure interpretation) |
| **Future Roadmap** | PK/PD & exposure-response figures; cross-study insights via Agentic AI; fully automated CSR generation |

**Benchmark Analysis:** Saama is closest to our "exam" framing — a product designed specifically for TFL review. However, their claimed focus is **interpretation/summarization** (turning tables/figures into text narratives) rather than **verification** (checking tables/figures against SAP/data). These are complementary use cases. Our benchmark directly addresses the verification gap.

---

### 3.2 JDIX — TFL Reviewer

| Attribute | Details |
|---|---|
| **Company** | JDIX (Taiwan-based) |
| **Product** | TFL Reviewer (AI-powered TFL QC) |
| **Claimed Capabilities** | Automated TFL quality checking; table-to-table consistency verification; statistical methodology validation |
| **Error Detected Against Our TCs** | Unknown — not yet benchmarked |
| **Relevance to Benchmark** | **HIGH** — explicitly positioned as TFL review; Taiwan-based with growing pharma adoption |

**Benchmark Analysis:** JDIX is a direct candidate for our benchmark evaluation. Their TFL Reviewer is likely to have strong N-count validation (SV-001) and cross-table consistency checks (our safety dimension). Worth prioritizing for early benchmark testing.

---

### 3.3 TrialMind — AI Review

| Attribute | Details |
|---|---|
| **Company** | TrialMind |
| **Product** | AI Review |
| **Claimed Capabilities** | AI-powered TFL review workflow; statistical methodology validation; data-to-output traceability |
| **Relevance to Benchmark** | **MEDIUM-HIGH** — explicitly positioned for TFL QC in pharma |

**Benchmark Analysis:** TrialMind's "AI Review" is positioned as a QC tool that validates TFL outputs against analytical plans. This maps directly to our TC-001 through TC-003 verification use cases.

---

### 3.4 EDETEK — INSIGHT Platform

| Attribute | Details |
|---|---|
| **Company** | EDETEK |
| **Product** | INSIGHT (AI-driven clinical analytics) |
| **Claimed Capabilities** | AI-assisted ADaM generation; statistical programming automation; TFL generation |
| **Relevance to Benchmark** | **MEDIUM** — broader platform covering ADaM-to-TFL pipeline |

**Benchmark Analysis:** EDETEK's INSIGHT covers the full ADaM-to-TFL pipeline. Our benchmark would test the TFL generation output specifically. Also, EDETEK presented "AI-Driven Automation of Statistical Analysis Plans" at PHASESUG 2026 (Qingyuan Zhang, EDETEK) — highly relevant.

---

### 3.5 Veristat — InStat AI Biostatistics

| Attribute | Details |
|---|---|
| **Company** | Veristat (June 2026 launch) |
| **Product** | InStat AI Biostatistics Platform |
| **Claimed Capabilities** | Commercial AI platform for biostatistics services; first client: Clene Nanomedicine (NfL biomarker analyses supporting NDA) |
| **Relevance to Benchmark** | **HIGH** — first commercial "AI biostatistics" service platform |

**Benchmark Analysis:** Veristat's InStat represents a new category: **AI as a biostatistics service provider** (not just a tool). This is the ultimate test case for our benchmark — if an AI agent can serve as a biostatistician on a real NDA submission, it must pass every dimension of our framework.

---

### 3.6 Maxis — Anomaly Detection in Clinical Data Science

| Attribute | Details |
|---|---|
| **Company** | Maxis AI |
| **Product** | AI-powered anomaly detection platform |
| **Claimed Capabilities** | Agentic AI for anomaly detection in clinical data science |
| **Relevance to Benchmark** | **MEDIUM** — focuses on anomaly detection (our safety dimension overlap) |

**Benchmark Analysis:** Maxis focuses on the **anomaly detection** subspace. Our safety dimension (edge cases, N-counts, denominators) is closely related. This product may be a partial match — anomaly detection is one component of full TFL review.

---

### 3.7 Industry Papers (PharmaSUG 2026 AI Section)

These are not commercial products but **practitioner-led implementations** that reveal what pharma companies are building internally:

| Paper ID | Title | Authors | Relevance |
|---|---|---|---|
| **AI-201** | Eliminating QC Programming Duplication Through Claude AI-Assisted Independent Code Generation | Jaime Yan (Kardigan Bio), Jason Zhang | **HIGH** — Independent code generation mirrors our ground truth verification approach |
| **AI-206** | An Agentic AI Framework That Reads SAPs and Generates TFL Table of Contents | Wang/Kimura/Xie/Du (Arcsine/Regeneron/Alnylam) | **HIGH** — Directly relevant: AGENTIC AI + SAP + TFL |
| **AI-116** | ARMed AutoTable Macro Agents: An ARM-Driven Framework for Automated Analysis Table Generation | Chengxin Li (AutoCheng) | **MEDIUM** — ARM-driven; directly targets table generation |
| **AI-201** | Schema-Preserving Generation of Clinical TLF Templates and Executable R Code via Iterative LLM-Guided Debugging | Jaime Yan (Kardigan Bio), Ming Yang (Kura Oncology) | **HIGH** — Schema preservation maps to our schema compliance dimension |
| **AI-362** | Using LLMs to Validate TLF Outputs Against Statistical Review Comments | Kishore Reddy Rollakanti | **HIGH** — Directly maps to our error detection use cases |
| **AI-135** | The Next Frontier of Statistical Programming: Vibe Coding with AI Coding Agents into SAS, R & Python | Kevin Lee & Nathan Lee (Clinvia) | **MEDIUM** — Multi-language AI coding agents; relevant to our multilingual benchmark |
| **AI-201** | Agentic R in Clinical Trials: Empowering Statistical Programmers with Open Source LLM Packages & Positron Tools | Phil Bowsher (RStudio/Posit) | **HIGH** — Agentic R directly targets our primary language; Posit's involvement is significant |
| **AI-259** | AI-Augmented SDTM Review: A Practical Framework Enhanced by a Structured Prompt Library | Vihar Patel (PPD/Thermo Fisher) | **MEDIUM** — SDTM focus (our secondary scope), but framework methodology is transferable |
| **AI-332** | A Human-in-the-Loop AI-Assisted Framework for ADaM Standardization | Xia/Du (Merck) | **HIGH** — Merck internal framework; best paper; directly relevant to our regulatory compliance dimension |

---

## 4. Vendor Positioning Matrix

### 4.1 Capability Coverage Heatmap

| Vendor | TFL Verification | N-count Check | Statistical Method Validation | Cross-TFL Consistency | Schema Compliance | Figure Interpretation | SAP-to-TFL Traceability |
|---|---|---|---|---|---|---|---|
| **Saama** | Partial (interpretation) | Unknown | Unknown | Partial (NLP search) | Unknown | **Primary** | Partial (Protocol/SAP-grounded) |
| **JDIX** | **Primary** | Likely | Likely | Likely | Unknown | Unknown | Unknown |
| **TrialMind** | **Primary** | Likely | Likely | Unknown | Unknown | Unknown | Likely |
| **EDETEK/INSIGHT** | Part of pipeline | Unknown | Likely | Unknown | Likely | Unknown | Likely |
| **Veristat** | Service-level | N/A (as a service) | **Primary** | N/A | Unknown | N/A | N/A |
| **Maxis** | Anomaly detection | Likely | N/A | N/A | N/A | N/A | N/A |

Note: "?" = vendor does not publicly disclose these capabilities.

### 4.2 Benchmark Readiness Assessment

| Tier | Vendors | Why They're Ready | Why They're Not Ready |
|---|---|---|---|
| **T1** | Saama, JDIX, TrialMind | Explicitly positioned for TFL QC/review; multi-modal capabilities | No published benchmark results; claims not externally validated |
| **T2** | Veristat, EDETEK | Strong AI/ML engineering; clinical data expertise | Broader platforms; TFL is one component, not primary focus |
| **T3** | Maxis | Strong in specific sub-domain (anomaly detection) | Does not cover full TFL review scope |

---

## 5. Integration with Benchmark Design

### 5.1 Vendor Benchmark Pipeline

When the WG is ready to benchmark vendors:

```
1. Select test cases (TC-001 through TC-003 from test-case-design.md)
2. Send vendor their choice of R/SAS/Python implementation of TCs
3. Vendor returns TFL outputs (JSON, RTF, etc.)
4. Scoring harness (katsu) computes scores across all dimensions
5. Compare vendor score against:
   - Ground truth (R/SAS/Python verification)
   - Human baseline (WG statisticians review same TCs)
6. Publish benchmark results (vendor-permissioned)
```

### 5.2 What Our Benchmark Tests That Vendors Don't Cover

| Capability | Covered by Our Benchmark | Covered by Any Vendor |
|---|---|---|
| **Cross-language verification** | ✅ R → SAS → Python | ❌ None (single language only) |
| **Standardized error taxonomy** | ✅ 3-class severity (A/B/C) | ❌ Vendors use proprietary error classifications |
| **TPP-style operating curves** | ✅ DR × FPR | ❌ Vendors report single accuracy numbers |
| **Human baseline comparison** | ✅ WG statistician baseline | ❌ No vendor compares against human performance |
| **Contamination mitigation** | ✅ Parametric variants, seed randomization | ❌ Vendors don't account for this |
| **Bootstrap CI for rankings** | ✅ Statistical rigor | ❌ Point estimates only from vendors |
| **Open methodology** | ✅ Fully open | ❌ Vendors' scoring is proprietary |

### 5.3 Research Paper Connections

From PharmaSUG 2026 and recent publications:

1. **Jaime Yan/Kura Oncology (AI-201)** — Independent code generation via Claude for QC. This directly mirrors our T1 test case approach: generate two independent implementations and compare.
2. **Merck's Xia & Du (AI-332, Best Paper)** — Human-in-the-loop ADaM standardization framework. Shows Merck is already working on this problem internally (Yue Shentu's company). Our benchmark could serve as an industry-wide extension of this approach.
3. **Posit/Phil Bowsher (AI-164)** — "Agentic R" with open-source LLM packages. This validates our language weight scheme (R: 0.50, given strong agentic R ecosystem).
4. **Veristat's InStat AI** — First commercial "biostatistics as a service" with AI. Our benchmark directly addresses the need to evaluate these new service offerings.

---

## 6. Future Expansion Plan

### 6.1 Short-Term (Next 3 Months)
- [ ] Contact 2-3 T1 vendors (Saama, JDIX, TrialMind) for benchmark pilot
- [ ] Add internal company frameworks to catalog (Merck's Xia/Du, EDETEK, etc.)
- [ ] Extend to SDTM review vendors (once we add SDTM scope)

### 6.2 Medium-Term (6-12 Months)
- [ ] Annual benchmark update with new vendor additions
- [ ] Expand to preprint/published paper results from WG members
- [ ] Add "AI-generated vs. human-verified" comparison for each vendor

### 6.3 Long-Term (1-2 Years)
- [ ] Industry-wide vendor certification program (WG as "industry AI union")
- [ ] Open-source benchmark runner (everyone can evaluate their agents)
- [ ] Cross-vendor competitive analysis published in stats journal

---

## 7. Known Limitations

1. **Vendor claims are self-reported** — capabilities advertised may not match actual performance
2. **No independent benchmark validation yet** — all vendor claims need our benchmark to validate
3. **Catalog focuses on publicly disclosed information** — internal tools at Merck, BMS, etc. may have capabilities not captured here
4. **Rapidly evolving space** — by next update, new vendors may emerge, existing ones may pivot

---

## 8. Appendix: PharmaSUG 2026 AI Section Summary

PharmaSUG 2026 AI section had **25+ papers** (AI-101 through AI-438 range), indicating AI in pharma is the dominant conference theme. Key takeaways:

- **AI is no longer experimental** — most presentations describe production deployments
- **Agentic AI is the latest term** — replacing "ML" and "GenAI" with "agents" and "AI coding"
- **R ecosystem is growing** — several papers specifically cover R+LLM integration
- **Human-in-the-loop is standard** — no vendor claims full automation; all emphasize human oversight
- **Regulatory compliance is table stakes** — every paper mentions SOP compliance, audit trails, or regulatory requirements
