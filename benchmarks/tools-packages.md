# Tools & Packages — Infrastructure Needed for the TFL Benchmark

**Last updated:** 2026-05-25
**Priority focus:** TFL programming — R + SAS + Python
**Status:** 🟡 Survey phase — not yet installed/configured

---

## 1. Evaluation Harness (Core Infrastructure)

| Tool | Purpose | URL | Status |
|---|---|---|---|
| **CodaBench** | Open-source platform for running and scoring benchmark tasks | https://github.com/Decalogue-WG/codabench | 🔴 To investigate |
| **EvalAI** | Platform for evaluating AI agents (used by GAIA) | https://eval.ai/ | 🔴 To investigate |
| **LangSmith** | LLM agent tracing and evaluation | https://smith.langchain.com/ | 🔴 To investigate |
| **PromptFoo** | LLM output evaluation, regression testing, statistical output comparison | https://www.promptfoo.dev/ | 🔴 To investigate |
| **DeepEval** | LLM evaluation framework with programmatic eval | https://github.com/confident-ai/deepeval | 🔴 To investigate |
| **R-testthat** | R package for unit testing — could wrap reference implementations | CRAN | 🔴 To investigate |
| **pytest + hypothesis** | Python property-based testing for statistical correctness | PyPI | 🔴 To investigate |

**Decision needed:** Build custom harness in R/Python (maximum control) vs. use existing platform like CodaBench or EvalAI (faster setup).

---

## 2. Statistical Reference Implementations (Ground Truth Sources)

### R Packages (Primary — recommended as ground truth)

### TFL-Specific

| Package | Purpose | CRAN | TFL Role |
|---|---|---|---|
| **Tplyr** | Clinical tables (TFLs) | 🟢 Yes | Table generation — pharmaverse gold standard |
| **rtables** | Clinical tables (Roche) | 🟢 Yes | Table generation — alternative to Tplyr |
| **tern** | Clinical trial analysis + rtables wrappers | 🟢 Yes | Analysis + table pipeline (Roche) |
| **gt** | General-purpose table formatting | 🟢 Yes | Final RTF/HTML rendering |
| **survminer** | KM curve visualization | 🟢 Yes | Figure generation |
| **ggplot2** | General graphics | 🟢 Yes | Custom figures (forest plots, swimmer plots) |
| **ggforest** | Forest plots for Cox models | 🟢 Yes | Subgroup forest plots |
| **ggswim** | Swimmer plots | 🟡 Available | Individual patient response visualization |

### Statistical (General)

| Package | Purpose | CRAN | Comment |
|---|---|---|---|
| **survival** | KM, log-rank, Cox PH, competing risks | 🟢 Yes | Gold standard for time-to-event |
| **gsDesign** | Group sequential design, alpha spending | 🟢 Yes | O'Brien-Fleming, Pocock, etc. |
| **lme4 / nlme** | Mixed models, MMRM | 🟢 Yes | Longitudinal data analysis |
| **emmeans** | Estimated marginal means, LS means | 🟢 Yes | Treatment effect estimation |
| **multcomp** | Multiple comparison procedures | 🟢 Yes | Closed testing, graphical approaches |
| **boot** | Bootstrap confidence intervals | 🟢 Yes | Resampling |
| **simstudy** | Simulate synthetic clinical trial data | 🟢 Yes | Test data generation |
| **tidycmprsk** | Competing risks analysis | 🟢 Yes | Fine-Gray model |
| **mice** | Multiple imputation | 🟢 Yes | Missing data handling |
| **mmrm** | MMRM (by Roche) | 🟢 Yes | Modern MMRM, regulatory friendly |
| **brms** | Bayesian regression (Stan backend) | 🟢 Yes | Bayesian methods |
| **rpact** | Adaptive clinical trial design | 🟢 Yes | Adaptive designs |

### Pharmaverse Packages (Pharma-Specific)

| Package | Purpose | URL |
|---|---|---|
| **random.cdisc.data** | Generate random CDISC-compliant SDTM/ADaM datasets | https://github.com/insightsengineering/random.cdisc.data |
| **pharmaversesdtm** | CDISC SDTM reference datasets | https://pharmaverse.org/ |
| **pharmaverseadam** | CDISC ADaM reference datasets | https://pharmaverse.org/ |
| **xportr** | Write ADaM datasets to SAS transport format | https://github.com/atorus-research/xportr |
| **metacore** | Import/validate metadata specs from Excel | https://github.com/atorus-research/metacore |
| **metatools** | Metaprogramming of CDISC datasets | https://github.com/atorus-research/metatools |
| **tidyCDISC** | Interactive analysis of CDISC datasets | https://github.com/Biogen-Inc/tidyCDISC |
| **admiral** | ADaM dataset derivation toolkit | https://github.com/pharmaverse/admiral |

### SAS (Required — for TFL ground truth)

| Tool | Purpose |
|---|---|
| **SAS/STAT** | Gold standard for regulatory TFL output |
| **PROC TABULATE** | Summary tables — the SAS workhorse for TLFs |
| **PROC REPORT** | Customizable clinical tables |
| **PROC SGPLOT / SGPANEL** | Clinical figures (KM curves, forest plots, swimmer plots) |
| **PROC FREQ / MEANS / UNIVARIATE** | Descriptive statistics |
| **SAS Clinical Standards Toolkit** | CDISC validation |
| **SAS University Edition** | Free option for ground truth generation |
| **SAS Viya** | Cloud option, Python integration (SWAT package) |

### Python (Required — for TFL ground truth + agent interface)

| Package | Purpose |
|---|---|
| **gt / great-tables** | Clinical tables (emerging alternative to Tplyr) |
| **matplotlib / seaborn** | Clinical figures |
| **plotnine** | Grammar of graphics (ggplot2-like) for clinical figures |
| **lifelines** | Survival analysis |
| **statsmodels** | General statistical models |
| **scikit-survival** | Survival analysis ML |
| **pandas** | Data manipulation (ADaM handling) |
| **numpy / scipy** | Numerical computation |

---

## 3. CDISC Validation & Compliance Tooling

| Tool | Purpose | URL |
|---|---|---|
| **Pinnacle 21** | Industry standard for SDTM/ADaM validation | https://pinnacle21.com/ |
| **CDISC Library API** | Programmatic access to CDISC standards | https://library.cdisc.org/api |
| **Define-XML validator** | Check Define-XML conformance | Multiple tools |
| **pharmaverseadam checker** | Validate ADaM dataset structure | R package |

---

## 4. Agent Frameworks (for Running Benchmark Tasks)

| Framework | Purpose | Notes |
|---|---|---|
| **LangChain/LangGraph** | General agent framework | Popular, multi-provider |
| **CrewAI** | Multi-agent orchestration | Good for replicating WG's multi-agent vision |
| **AutoGen** | Microsoft multi-agent framework | Strong research backing |
| **Semantic Kernel** | Microsoft enterprise agent framework | Enterprise governance focus |
| **Claude Code / Cline** | Code agent frameworks | Directly relevant to TFL programming tasks |
| **OpenAI Agents SDK** | OpenAI agent development | Growing ecosystem |
| **smolagents** | HuggingFace agent framework | Fast, research-oriented |
| **SQLAgent / DAX Agent** | Analytics-specific agents | Narrow but relevant |

---

## 5. Synthetic Data Generation

| Tool | Purpose | Notes |
|---|---|---|
| **simstudy** (R) | Generate realistic clinical trial data | Flexible, well-maintained |
| **random.cdisc.data** (R) | Generate CDISC-compliant datasets | Most realistic for our needs |
| **Synthea** | Synthetic patient data (general) | Not trial-specific but rich |
| **SAS DATAGEN** | SAS data generation | Used by some pharma teams |
| **MDClone** | Synthetic data platform | Commercial, privacy-preserving |
| **Gretel.ai** | Synthetic data API | ML-based generation |

---

## 6. Deployment & Scoring Infrastructure

| Component | Options | Recommendation |
|---|---|---|
| **Task runner** | Docker + Python/R scripts | Docker for isolation, reproducibility |
| **LLM access** | OpenRouter, direct API | Need API budgets / rate limits |
| **SAS runtime** | SAS University Edition (free), SAS Viya (cloud) | Required for SAS cross-validation |
| **R runtime** | Base R + renv (lockfile) | Critical for ground truth generation |
| **Python runtime** | Conda/uv environment | For Python-based agents |
| **CI/CD** | GitHub Actions, Jenkins | For automated benchmark runs |
| **Results database** | SQLite, PostgreSQL | Store benchmark results over time |
| **Leaderboard** | Streamlit, Shiny, or static HTML | For public-facing results |

---

## 7. Priority Installation Order

1. **R + core stat packages** (survival, gsDesign, lme4, boot, simstudy) — immediate
2. **Pharmaverse packages** (random.cdisc.data, admiral, Tplyr, pharmaversesdtm, pharmaverseadam) — immediate
3. **Python + agent frameworks** (LangChain, CrewAI, pytest) — Phase 1
4. **Pinnacle 21 Community Edition** — Phase 1
5. **Evaluation harness** (custom or LangSmith/PromptFoo) — Phase 1
6. **SAS University Edition** — Phase 2
7. **Leaderboard infrastructure** — Phase 3

---

## 8. Open Questions

1. **R-only or multi-language?** Pharmaverse is R-centric. SAS is required by many pharma IT. Python is growing. Recommendation: R baseline, optional SAS/Python cross-validation.

2. **Docker vs. local execution?** Docker ensures reproducibility but adds overhead. For initial development, local R/Python environment is faster.

3. **API cost management?** Running benchmarks against frontier LLMs costs money. Need a tiered system:
   - Tier 1 (daily): Free/open models (Qwen, DeepSeek, Llama)
   - Tier 2 (weekly): Mid-cost models (DeepSeek V4 Flash)
   - Tier 3 (monthly): Frontier models (Claude, GPT-5, Gemini)
   - Quarterly: Full benchmark run on all models

4. **License compatibility?** Pharmaverse is open source. Our benchmark should be Apache 2.0 (matching the parent repo). Vendor tools (Pinnacle 21) have licensing constraints.
