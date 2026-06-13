# Ontology as the Grounding Layer for Agentic AI in Clinical Biostatistics

## Final Proposal — Approved (Post-Swarm Iteration 3 + Claude Opus Quality Gate)

> **Review verdict:** APPROVED WITH MINOR CHANGES
> **Reviewer:** Claude Opus 4.7 (quality gate pass)
> **Swarm models:** Gemini 2.5 Pro, MiMo V2.5 Pro, DeepSeek V4 Flash, Natasha
> **Iterations:** 3 (2 full swarm + 1 direct) — 9 critiques across 4 models
> **Date:** 2026-06-13
>
> *Summary assessment: The proposal has evolved from a position paper (v1) to a technically grounded implementation brief (vFinal). The core thesis — ontology as the accountability layer for agentic AI in clinical biostatistics — is robust and defensible. SHACL Core validation with deterministic middleware provides a credible GxP boundary. The MVO path (3-6 months) offers concrete de-risking. Minor issues identified in the quality pass (OBO single inheritance characterization, regulatory framework references, cost-benefit source labels) have been corrected in this final version. No blocking issues remain.*

---

### 1. Core Thesis

Ontology is the essential grounding layer for deploying agentic AI in clinical biostatistics and drug development. It is not an optional add-on. It is the structural prerequisite that transforms a stochastic language model into an auditable, traceable, regulatorily defensible reasoning system.

Automation bias is not an objection to ontology. It is an objection to *ungrounded* AI — agents operating without explicit, reviewable, version-controlled domain knowledge. The counterfactual is not "with or without ontology." The counterfactual is: **in a world where agentic AI will be used in clinical trial design, implementation, analysis, and reporting, ontology is the tool that makes it safe to do so.**

---

### 2. Positioning: Why Ontology, Not "Better Prompts" or "Bigger Models"

| Concern | Pure LLM Approach | Ontology-Grounded Approach |
|---------|-------------------|---------------------------|
| Hallucination | Mitigated by prompt engineering, RAG, fine-tuning; no guarantee | Constrained by formal SHACL shapes; invalid paths fail deterministic validation |
| Audit trail | Logged prompts + outputs; reasoning internal to model weights | Every decision traceable to explicit concept and rule nodes |
| Regulatory defense | "The model determined this" | "Rule R3.2 (ICH E9 §5.3) + Concept C12 (Non-inferiority margin) → Decision D7" |
| Version control | Model version != knowledge version | Ontology versions are diff-able, reviewable, frozen in Git |
| Cross-study consistency | Depends on prompt quality per study | Centralized ontology enforced across all studies |
| Benchmarking | Needs external test sets; subject to leakage | Ontology serves as normative reference — trace decisions to validated knowledge artifacts |

The ontology is not a supplement to the LLM. It is the **accountability layer** that wraps LLM reasoning in a formally reviewable structure, moving validation from stochastic evaluation to deterministic compliance. The ontology does not replace empirical benchmarks (e.g., historical study validation) — it complements them by providing the normative reference against which agent decision traces are evaluated.

---

### 3. Architecture: The LLM↔Ontology Execution Loop

The system uses **SHACL (Shapes Constraint Language) Core** for deterministic validation of LLM-generated analysis decisions against a predefined TBox (schema) representing ICH guidelines, protocol intent, and CDISC conventions. SHACL Core is W3C-standard, vendor-independent, and produces machine-readable validation reports well-suited for audit logging.

#### 3.1 Component Architecture

```
[Protocol & CDISC Metadata]
        │
        ▼
┌───────────────────────────────┐
│  LLM Agent                    │   ← Unvalidated space (non-GxP)
│  - Ingests protocol + study   │
│  - Proposes analysis path     │
│  - Outputs structured JSON    │
└───────────┬───────────────────┘
            │ Simple JSON (Pydantic schema)
            ▼
┌───────────────────────────────┐
│  Deterministic Middleware     │   ← Validated space (GxP boundary)
│  - Maps JSON → JSON-LD        │
│  - Applies URI resolution     │
│  - Fills default graph props  │
└───────────┬───────────────────┘
            │ JSON-LD graph
            ▼
┌───────────────────────────────┐
│  SHACL Core Validator Engine  │   ← Validated boundary
│  - Executes TBox shapes       │
│  - Produces Validation Report │
│  - Logs every check to audit  │
└───────────┬───────────────────┘
            │ PASS / FAIL with report
            ▼
    ┌───────────┬──────────┐
    │           │          │
    ▼           ▼          ▼
Validated   Retry (max 3)  Human Escalation
Code Gen    (self-correct) (after cap exhausted)
```

**Key architectural decisions:**

- **The LLM does not output RDF directly.** LLMs are unreliable at generating valid, deeply nested JSON-LD without hallucinating URIs or violating schema constraints. Instead, the LLM outputs simple JSON (via structured function calling or a Pydantic-validated schema), and a deterministic middleware layer translates this into standard JSON-LD. This eliminates the highest-risk failure mode in the pipeline.

- **The GxP boundary sits before the middleware, not after.** The LLM operates in unvalidated space. Everything downstream — the middleware, the SHACL validator, the code generator — lives in validated space. This means the LLM can be updated without revalidating the pipeline, and the pipeline can be validated independently of the model.

- **SHACL uses strict Core semantics only.** No SHACL-AF extensions (`sh:condition`, `sh:rule`), which have inconsistent validator support. All constraints use core SHACL constructs (`sh:node`, `sh:property`, `sh:in`, `sh:or`, `sh:xone`, `sh:severity`).

#### 3.2 The Self-Correction Loop (with Guardrails)

When SHACL validation fails:

1. The SHACL Validation Report is parsed by a deterministic translator that converts the raw RDF report into structured natural-language error messages (e.g., "Continuous endpoint #2 is longitudinal but has missing data handling strategy undefined — required per ICH E9(R1) §2.3").
2. The LLM is re-prompted with these structured errors and the original context.
3. **Retry budget:** Maximum 3 re-prompt attempts. Each attempt increments a counter tracked in the audit log.
4. **Degradation guard:** If the LLM produces a *different* failing output on each attempt (oscillation rather than convergence), escalation triggers early.
5. **Escalation:** After 3 failed retries, the system halts and flags the case for human statistical review. The full failure trace (original proposal, all 3 failing iterations, SHACL validation reports) is bundled for the reviewer.
6. **Gaming guard:** A passing SHACL validation does not mean the output is clinically appropriate — only that it satisfies formal constraints. The system explicitly logs a caveat: "SHACL conformance does not guarantee clinical judgment correctness." The human reviewer retains final authority.

---

### 4. Concrete SHACL Example: Endpoint Analysis Decision

The following uses **SHACL Core only** — no SHACL-AF extensions. It demonstrates the distinction between hard constraints and advisory recommendations using `sh:severity`.

#### 4.1 TBox Snippet (Turtle)

```turtle
@prefix stat: <http://example.org/biostat#> .
@prefix sh:  <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

# ── Concept Hierarchy ──────────────────────────────────────
stat:Endpoint a sh:NodeShape ;
    sh:targetClass stat:Endpoint .

stat:ContinuousEndpoint
    rdfs:subClassOf stat:Endpoint .

stat:LongitudinalEndpoint
    rdfs:subClassOf stat:ContinuousEndpoint .

# ── Hard Constraint: Missing Data Strategy ──────────────────
# Every continuous endpoint MUST have an explicit missing data
# handling strategy per ICH E9(R1). Violation → BLOCKING.
stat:ContinuousEndpointShape
    a sh:NodeShape ;
    sh:targetClass stat:ContinuousEndpoint ;
    sh:property [
        sh:path stat:hasMissingDataHandling ;
        sh:minCount 1 ;
        sh:severity sh:Violation ;
        sh:message "Continuous endpoints require explicit missing data handling strategy per ICH E9(R1)."^^xsd:string ;
    ] ;
    sh:property [
        sh:path stat:hasAnalysisMethod ;
        sh:minCount 1 ;
        sh:severity sh:Violation ;
        sh:message "At least one primary analysis method must be specified."^^xsd:string ;
    ] .

# ── Hard Constraint: Method ∝ Endpoint Type ─────────────────
# Longitudinal continuous endpoints MUST use a method that
# accounts for repeated measures. Allowed methods enumerated.
stat:LongitudinalContinuousShape
    a sh:NodeShape ;
    sh:targetClass stat:LongitudinalEndpoint ;
    sh:property [
        sh:path stat:hasAnalysisMethod ;
        sh:in ( stat:MMRM stat:GEE stat:GrowthCurveModel stat:BayesianLongitudinal ) ;
        sh:severity sh:Violation ;
        sh:message "Longitudinal endpoints require a repeated-measures-capable analysis method."^^xsd:string ;
    ] .

# ── Advisory Recommendation: Preferred Method ───────────────
# MMRM is recommended as the default for longitudinal continuous
# in superiority trials. This is advisory, not blocking.
stat:PreferredLongitudinalRecommendation
    a sh:NodeShape ;
    sh:targetClass stat:LongitudinalSuperiorityTrial ;
    sh:property [
        sh:path stat:hasAnalysisMethod ;
        sh:hasValue stat:MMRM ;
        sh:severity sh:Warning ;
        sh:message "MMRM is the recommended default for longitudinal superiority trials. Deviation requires documented justification."^^xsd:string ;
    ] .
```

#### 4.2 Decision Trace Example

**Input:** Phase 3 superiority trial, continuous endpoint with weekly visits over 12 weeks, two treatment arms, stratified by site.

**LLM proposal:** ANCOVA at week 12 with LOCF for missing data, no longitudinal structure.

**SHACL validation result:**

| Shape | Check | Result |
|-------|-------|--------|
| `ContinuousEndpointShape` | Has missing data handling? | ✅ PASS (LOCF satisfies `sh:minCount 1`) |
| `ContinuousEndpointShape` | Has analysis method? | ✅ PASS (ANCOVA satisfies `sh:minCount 1`) |
| `LongitudinalContinuousShape` | Method appropriate for longitudinal? | ❌ FAIL — ANCOVA not in `sh:in (...)` for longitudinal endpoints |
| `PreferredLongitudinalRecommendation` | MMRM preferred? | ⚠️ WARNING only — not blocking, but flagged for documentation |

**System action:** Output blocked. Error message returned: "Longitudinal endpoints require a repeated-measures-capable analysis method. Proposed (ANCOVA). Allowed: MMRM, GEE, GrowthCurveModel, BayesianLongitudinal."

**LLM self-corrected proposal:** MMRM with unstructured covariance, MAR assumption, Kenward-Roger df.

**Result:** PASS. Audit log records: concept traces (LongitudinalEndpoint → LongitudinalContinuousShape → MMRM), ICH E9(R1) reference, and the corrective iteration.

---

### 5. Integration with the Existing Ontology Landscape

| Standard | Coverage | This Proposal's Relationship |
|----------|----------|------------------------------|
| **OBO Foundry** | Upper-level biomedical ontology principles | Adopts OBO design principles (prefers single inheritance, unique identifiers, orthogonality) while accommodating OBO's allowance for multiple inheritance where clinically necessary |
| **NCI Thesaurus** | Cancer terminology, disease codes, drug names | Imported as reference terminology for indication and comparator mappings |
| **SNOMED CT** | Clinical findings, procedures, body structures | Used for adverse event and comorbidity semantic enrichment |
| **CDISC SDTM/ADaM** | Study data tabulation and analysis datasets | Consumed via define.xml parsing; ADaM variable semantics (e.g., `AVAL`, `CHG`, `PARAM`) mapped to ontology concepts through a deterministic YAML-to-triples translation layer |
| **CDISC Controlled Terminology** | Codelists for SDTM/ADaM variables | Imported as value-set definitions for study metadata validation |
| **OCRe (Ontology of Clinical Research)** | Clinical trial design concepts | Evaluated for reuse; OCRe provides trial design taxonomy but does not extend to statistical analysis rules — this is the gap the proposal fills |

This proposal does not replace existing standards. It fills a specific gap: **none of the above ontologies or standards formalize statistical analysis decision rules in a machine-executable format.** CDISC describes *what data looks like*; this ontology describes *how to analyze it correctly given the regulatory framework.*

---

### 6. Key Objections and Rebuttals

#### 6.1 "It adds documentation and maintenance burden"

**Rebuttal:** The ontology is not built from scratch in a single formalization exercise — it grows incrementally alongside the work it supports. After completing a project (a simulation study, a SAP, a protocol review), the statistician's AI copilot produces a first draft of the relevant ontology nodes. When new specifications or documents arrive, the LLM proposes how to integrate them into the existing graph — suggesting new nodes, links, rules, and actions — and the human inspects, validates, or rejects each addition individually. Inspecting one new node and its connections in an existing graph is far easier than building the full structure from nothing.

This pattern — AI proposes, human validates, ontology grows — turns knowledge acquisition from a bottleneck into a byproduct of normal workflow. The initial investment is building the graph skeleton and the validation pipeline; the ongoing cost is minutes per document review, not weeks per formalization cycle.

Statisticians express domain knowledge through YAML/Markdown templates — no Turtle or SPARQL required. A deterministic parser converts templates to triples. Changes go through a PR workflow: automated regression tests run all historical SHACL shapes against the updated ontology to detect regressions, then human domain experts (from the Core Ontology Board) review and approve. Semantic versioning applied to the TBox for downstream impact assessment.

#### 6.2 "What happens when the ontology is wrong?"

**Risk acknowledged.** The blast radius of a wrong TBox rule is all studies using it. Mitigations:

- **Regression test suite:** Each ontology update runs against a curated set of "known good" analysis decision graphs. If a rule change breaks a previously passing test, the PR is blocked.
- **TBox/ABox separation:** The TBox (schema + rules) is version-controlled and validated independently from the ABox (study instances). TBox changes are gated by the Core Ontology Board.
- **Break-glass override workflow:** If a study team needs to deviate from a TBox rule (novel design, regulatory agreement, special case):
  1. Study statistician files a deviation request — one of: "rule is wrong" (ontology error) or "rule doesn't apply" (study-specific exception).
  2. Core Ontology Board reviews within 5 business days.
  3. If approved: study-level ABox branch is created with the override annotated. Audit trail records: what was overridden, by whom, why, for how long (single analysis vs. full study vs. indefinite).
  4. If "rule is wrong": a TBox change ticket is created automatically. The ontology fix goes through the standard PR + regression + approval workflow.
  5. Override decisions are reviewed quarterly for patterns that indicate systemic ontology gaps.

#### 6.3 "This replaces statisticians"

**Rebuttal:** The ontology enables the **Bionic Statistician** — handling repetitive execution (SAP boilerplate, constraint checking, routine method selection) while elevating the statistician's role to strategic trial design, regulatory interaction, and interpretation of surprising results. For junior statisticians, the ontology serves as an interactive validation engine: when they propose an analysis, the SHACL engine explains *why* a constraint was violated, building domain intuition faster than traditional mentorship alone. This directly addresses the downstream talent-gap concern: juniors learn through guided constraint interaction rather than rote repetition.

#### 6.4 "What about regulatory acceptance?"

**Acknowledged risk.** No regulator (FDA, EMA, PMDA) has issued guidance on ontology-based validation of AI-generated statistical analysis decisions. Strategy:
1. **Parallel validation:** For the first 6-12 months post-MVO, the ontology runs alongside traditional processes. All SHACL-validated decisions are compared against human-generated SAPs for agreement.
2. **FDA/CDISC engagement:** Submit the ontology framework as a discussion starter via existing CDISC collaboration channels and FDA biomarker/statistics working groups.
3. **Historical study validation:** Run the ontology against 10-20 completed studies with known analysis decisions to measure agreement rate and identify edge cases.
4. **The ontology itself has a regulatory path:** Unlike the LLM, the ontology is a deterministic artifact subject to standard Computer System Validation (GAMP 5) and 21 CFR Part 11 electronic records compliance. The SHACL engine, middleware, and code generator are validated once; the LLM is treated as an unvalidated input source.

#### 6.5 "LLMs will get good enough that ontology becomes unnecessary"

**Rebuttal:** This confuses accuracy with auditability. Even a perfect LLM cannot produce diff-based review, version-controlled knowledge, or traceability to specific ICH guideline paragraphs. Regulators do not accept "the model knew it" — they require documented, reviewable, signed-off rule artifacts. The ontology is not an accuracy enhancer; it is an **audit artifact**. Even if LLMs achieved perfect accuracy, clinical trial reporting would still require the ontology for inspection readiness.

#### 6.6 "LLMs help build the ontology — isn't that circular?"

**Acknowledged.** LLMs assist in extracting axioms from YAML templates during ontology construction. The circularity is closed by a validation gate: **every axiom generated by LLM assistance is validated by a human domain expert before merging into the TBox.** Spot-checking is insufficient; the validation rate is 100% for TBox changes. This eliminates the bootstrapping paradox because the ontology's correctness rests on human expert certification, not on the LLM that helped draft it.

#### 6.7 "Only works for cookie-cutter studies"

The 80/20 split is an argument *for* ontology, not against. Standardizing the 80% (superiority trials, standard endpoints, common designs) frees bandwidth for the complex 20% (adaptive designs, novel endpoints, special regulatory agreements). The ontology is a living artifact: repeating edge cases get formalized and absorbed over successive releases. Break-glass overrides handle the genuinely novel cases while the ontology evolves.

---

### 7. Organizational Structure

#### 7.1 Core Ontology Board

| Role | Count | Responsibility |
|------|-------|---------------|
| Lead Statistical Scientist | 1 | Domain authority; chairs the Board; final decision on TBox changes |
| Senior Statisticians | 3 | Domain expertise across therapeutic areas; review PRs, break-glass requests |
| Ontology Engineer | 1 | Technical authority on SHACL/OWL, middleware, tooling |
| Regulatory Compliance Lead | 1 | Computer System Validation (GAMP 5), Part 11 compliance, audit-readiness |
| MLOps/DevOps Engineer | 1 | CI/CD pipeline, regression testing, versioning infrastructure |

Reporting line: Within BARDS (Biostatistics and Research Decision Sciences), reporting to the head of Late Development Statistics.

Decision authority: The Board has binding authority on TBox content. Study teams can request deviations via break-glass (section 6.2). Escalation of Board-team disagreement goes to the BARDS VP.

Funding: Central BARDS budget allocation (not study-level), with a 2-year committed runway for MVO development.

#### 7.2 Knowledge Acquisition Workflow

Statisticians provide domain knowledge in YAML/Markdown templates:

```yaml
rule_id: MISSING_DATA_LONGITUDINAL
domain: continuous_endpoint
condition: endpoint_type == "longitudinal" && trial_phase == "Phase3"
constraint:
  type: hard  # hard | advisory
  path: analysis_method
  allowed: [MMRM, GEE, GrowthCurveModel, BayesianLongitudinal]
  justification: "Longitudinal data requires repeated-measures-capable method (ICH E9(R1) §2.3)"
```

The deterministic parser converts this YAML into Turtle/RDF triples incrementally. The LLM assists in suggesting template fields and flagging inconsistencies (e.g., "this rule references endpoint_type but no endpoint_type class exists in the TBox") — but every axiom is human-validated before merge.

---

### 8. Cost-Benefit Analysis

#### 8.1 Investment (24 months)

| Item | FTE | Annual Cost |
|------|-----|-------------|
| Senior Statisticians (3 × 50%) | 1.5 | $375K |
| Ontology Engineer | 1.0 | $200K |
| Regulatory Compliance | 0.5 | $125K |
| MLOps/DevOps | 1.0 | $200K |
| Infrastructure (graph store, CI/CD, compute) | — | $100K |
| **Total annual** | — | **$1.0M** |
| **2-year total** | — | **$2.0M** |

#### 8.2 Projected Returns

| Metric | Current State | Post-Ontology | Savings |
|--------|--------------|---------------|---------|
| SAP first draft time | 4-6 weeks | 3-5 days | ~80% reduction |
| SAP QC cycle time | 2-3 rounds | 0-1 rounds (constraint pre-validation catches most issues) | ~60% reduction |
| Statistical methodology audit findings | Baseline | Near-elimination of preventable findings (wrong method, missing estimand component) | Estimated 70% reduction |
| Cross-study method inconsistency | Common for rare endpoints | Enforced consistency | Standardization benefit |

**Break-even estimate:** 15 Phase II/III studies post-MVO deployment. At an estimated ~$100K/study in statistical labor + QC + audit remediation (based on internal planning benchmarks), the ontology pays for itself within 12-18 months of enterprise-wide use.

**Risk-adjusted (50% adoption):** Break-even extends to ~24 months for 30 active studies. Still positive within the 3-year ROI window.

---

### 9. Implementation Stack & Timeline

| Phase | Scope | Duration | Dependencies | Exit Criteria |
|-------|-------|----------|--------------|---------------|
| **MVO** | Superiority trials, binary/continuous endpoints, two-arm, simple stratification | 3-6 months | Core team hired, YAML template format frozen | SHACL validates 10 historical studies with ≥95% agreement on primary analysis decisions (exact-match of analysis method, missing data strategy, and stratification approach between ontology-generated SAP and human-generated SAP) |
| **Pilot** | 2-3 active studies running ontology-parallel with traditional SAP | 6-12 months | MVO complete, SHACL engine validated, FDA/CDISC engagement initiated | No critical disagreements between ontology and human SAPs |
| **Expansion** | Time-to-event endpoints, non-inferiority, multi-arm, complex stratification | 12-18 months | Pilot feedback incorporated, regulatory guidance emerging | ≥80% of Phase II/III studies covered by ontology rules |
| **Production** | Full coverage, break-glass governance mature, regulatory positions known | 18-24 months | Expansion validated, regulatory path clear | Ontology is default SAP authorship pathway |

**Total: 3-5 years to full production readiness. MVO proof-of-value in 3-6 months.**

---

### 10. Known Unknowns and Failure Modes

| Risk | Impact | Mitigation |
|------|--------|------------|
| Regulators explicitly reject ontology-based AI validation | High — could invalidate core premise | Parallel validation generates evidence for discussion; if rejected, ontology still has standalone value as a documentation and training tool |
| Knowledge acquisition bottleneck proves unbreakable | High — ontology cannot scale without domain expert input | Start with MVO (small domain); prove the workflow scales before expanding |
| SHACL engine performance degrades at enterprise scale (hundreds of concurrent studies) | Medium — may require infrastructure investment | Benchmark during MVO phase; scale with partitionable TBox per therapeutic area |
| LLM gaming passes SHACL but produces clinically inappropriate outputs | Medium — false sense of security | Caveats in audit log; human-in-the-loop for all production outputs during Pilot phase |
| Ontology governance becomes a bottleneck (Board too slow to approve changes) | Medium — delays adoption | Publish SLAs (5-day break-glass review, 2-week TBox change review); adjust staffing if needed |
| Cross-pharma adoption stalls (no industry standard emerges) | Low — single-pharma value is already positive per cost-benefit analysis | Publish framework; engage CDISC working groups; lead by example rather than waiting for consensus |

---

### 11. Summary

The debate is not "ontology vs no ontology." The debate is: **if agentic AI will be used in clinical biostatistics, what makes it safe, auditable, and regulatorily defensible?** The answer is formal domain knowledge represented as an ontology grounded in SHACL Core constraints, with a deterministic middleware layer, a capped self-correction loop, Git-based governance, and an explicit break-glass pathway for genuine edge cases.

Every alternative — better prompts, bigger models, RAG, fine-tuning — fails on at least one non-negotiable dimension: traceability, version control, independent validation, and inspection readiness. Ontology is the right tool for this problem. The MVO path (3-6 months) provides a concrete, de-risked starting point.
