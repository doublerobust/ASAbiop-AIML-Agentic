# Relevant Work — Agentic AI Benchmarking in Pharma/Biotech and Adjacent Domains

**Last updated:** 2026-05-25

---

## 1. General AI Agent Benchmarks (Reference Architecture)

These benchmarks provide design patterns we can adapt or reference for our domain-specific benchmark.

### SWE-bench / SWE-bench Verified
- **Domain:** Software engineering (Python)
- **Tasks:** Resolve real GitHub issues by producing patches
- **Evaluation:** Pass/Fail on test suite
- **Relevance:** Most mature software engineering agent benchmark. Our benchmark should follow its methodology (ground-truth + automated evaluation) but adapt to statistical/regulatory domain.
- **Limitation for us:** No statistical knowledge required. A patch that passes tests may still be statistically invalid.
- **URL:** https://www.swebench.com/

### GAIA (General AI Assistants)
- **Domain:** General assistant tasks
- **Tasks:** Multi-step reasoning with tool use (web search, calculations, research)
- **Evaluation:** Exact match / numerical tolerance / contains
- **Relevance:** Good reference for task decomposition and multi-step evaluation. Level 1-3 stratification is applicable.
- **Limitation for us:** No domain specialization. No statistical or regulatory knowledge.
- **URL:** https://huggingface.co/gaia-benchmark

### WebArena
- **Domain:** Web navigation and task completion
- **Tasks:** Realistic web tasks across 5 sandboxed apps (GitLab, maps, e-commerce, CMS, forum)
- **Evaluation:** Page state / API endpoint check
- **Relevance:** Reference for browser-based agent evaluation. Our TFL review agents may need browser interaction.
- **URL:** https://webarena.dev/

### AgentBench
- **Domain:** Multi-environment agent evaluation
- **Tasks:** 1,091 tasks across 8 environments (shell, database, web, games, etc.)
- **Evaluation:** Per-environment success criteria
- **Relevance:** Good multi-environment evaluation architecture. We could apply similar methodology to clinical trial workflow phases.
- **URL:** https://github.com/THUDM/AgentBench

### OSWorld
- **Domain:** Desktop computer use
- **Tasks:** Real application workflows (Office, IDE, browsers, media)
- **Evaluation:** Application state checks
- **Relevance:** Reference for evaluating agents that interact with statistical software GUIs (e.g., SAS Studio, RStudio).
- **URL:** https://os-world.github.io/

### Terminal-Bench
- **Domain:** Shell/terminal workflows
- **Tasks:** Filesystem ops, package management, scripting sysadmin
- **Evaluation:** File system state comparison
- **Relevance:** For agents that work via CLI (Rscript, SAS batch, Python scripts) — common in pharma programming.

### Tau-Bench
- **Domain:** Tool-augmented agents
- **Tasks:** Customer service, research, information retrieval
- **Evaluation:** Task completion + tool-use efficiency
- **Relevance:** Reference for evaluating tool-calling patterns and multi-turn interactions.
- **URL:** https://github.com/sierra-research/tau-bench

---

## 2. Pharma-Specific Evaluation Initiatives

### PHUSE Test Data Factory
- **What:** Standardized CDISC test datasets (SDTM, ADaM) for tool validation
- **Relevance:** Source of realistic, non-proprietary clinical trial data for our test cases
- **URL:** https://www.phuse.eu/test-data-factory

### FDA Study Data Technical Conformance Guide (TCG)
- **What:** FDA guidance on electronic study data submission format
- **Relevance:** Ground truth for regulatory compliance dimension. Our benchmark should verify conformance to this guide.
- **URL:** https://www.fda.gov/regulatory-information/search-fda-guidance-documents/study-data-technical-conformance-guide

### CDISC Public Review / Standards
- **What:** SDTM IG, ADaM IG, Define-XML specifications
- **Relevance:** Reference standards for data mapping and metadata evaluation dimensions
- **URL:** https://www.cdisc.org/standards

### Pharmaverse
- **What:** Collection of curated R packages for clinical trial analysis
- **Packages:** `survival`, `gsDesign`, `lme4`, `tidymodels`, `pharmaversesdtm`, `pharmaverseadam`, `random.cdisc.data`, `xportr`, `metacore`, `metatools`
- **Relevance:** Gold-standard reference implementations. Our benchmark ground truth should be generated using these packages.
- **URL:** https://pharmaverse.org/

### BeiGene AI-278 Platform (PharmaSUG 2026)
- **What:** AI-driven ADaM automation platform presented at PharmaSUG 2026
- **Relevance:** Industry case study of agentic AI in stat programming. Their approach to ADaM generation is a testable scenario.
- **Status:** Abstract accepted, paper pending

### Taimei INSIGHT Case Study (Top-10 Pharma)
- **What:** 200 TFLs generated in <2 hours, ~80% first-pass accuracy
- **Relevance:** Provides reference benchmarks for "human vs. agent" performance: human days → agent hours
- **Source:** BBSW AI Summit 2026 / deep read in vendor-landscape-synthesis.md

---

## 3. Standards and Regulatory Bodies

| Body | Relevant Standard | Impact on Benchmark |
|---|---|---|
| **ICH** | E3, E6(R2), E8, E9, E9(R1), E10, E17 | Defines statistical principles and reporting standards |
| **CDISC** | SDTM, ADaM, Define-XML, ODM, CDASH | Defines data standards — traceability and compliance checks |
| **FDA** | Study Data TCG, Bayesian Guidance (Jan 2026), AI Council | Regulatory acceptance criteria for AI in submissions |
| **EMA** | Reflection paper on AI in drug development | European regulatory perspective |
| **PMDA (Japan)** | AI-related guidance | APAC regulatory perspective |
| **ASA Biopharm** | Our WG | The benchmark itself |

---

## 4. AI Evaluation Frameworks (Tooling)

| Tool | Purpose | Relevance |
|---|---|---|
| **LangSmith / LangFuse** | LLM evaluation, tracing, monitoring | Agent evaluation infrastructure |
| **PromptFoo** | LLM output evaluation, regression testing | Could adapt for statistical output evaluation |
| **Braintrust** | AI evaluation, experimentation | Evaluation platform for custom benchmarks |
| **DeepEval** | LLM evaluation framework | Programmatic evaluation of LLM outputs |
| **ragas** | RAG evaluation | If our agents use retrieval (protocols, regulatory docs) |
| **EleutherAI LM Eval** | Standardized LM evaluation | General architecture reference |
| **HuggingFace Open LLM Leaderboard** | Public LLM benchmarks | Community engagement model |

---

## 5. What's Missing (The Gap)

**No benchmark exists that tests:**
1. Statistical method correctness in a clinical trial context
2. Regulatory compliance (CDISC, ICH, FDA guidance)
3. Agentic workflow execution (multi-step, multi-tool, human-in-the-loop)
4. Safety/containment in a regulated environment
5. Audit trail quality and traceability

**All existing benchmarks test at most one of these dimensions.**
The ASA Agentic AI WG is uniquely positioned to fill this gap.

---

## 6. Strategic Positioning

### Why the WG Should Own This

| Reason | Explanation |
|---|---|
| **Domain expertise** | WG members are practicing biostatisticians and regulatory experts |
| **Vendor independence** | Unlike any single vendor, the WG can create an objective standard |
| **Regulatory credibility** | ASA Biopharm has existing relationship with FDA/regulatory bodies |
| **Community** | ASA membership spans pharma, CRO, academia, and regulatory |
| **Timing** | Vendors are shipping but can't evaluate their own products objectively |

### Communication Strategy

| Audience | Message |
|---|---|
| **WG members** | "This benchmark validates what we're proposing in the white paper" |
| **Vendors** | "Here's a transparent, level playing field to demonstrate your product" |
| **Regulators** | "Here's an evidence-based framework for evaluating AI in clinical stats" |
| **Statisticians** | "Here's how to compare and choose AI tools for your work" |
| **Academia** | "Here's a research platform for statistical AI methods" |
