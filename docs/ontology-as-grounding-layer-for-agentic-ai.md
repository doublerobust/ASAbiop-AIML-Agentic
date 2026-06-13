# Institutional Knowledge for Agentic AI in Biostatistics

## Technical Proposal

---

### 1. The Problem

Agentic AI for clinical biostatistics is already happening. Teams are building prototypes — agents that draft SAPs, generate TLFs, automate QC. Benchmarking efforts are quantifying time savings and capability gaps. This is not a debate about whether agents will be used.

But there's a ceiling on how effective these agents can be with current memory architectures.

| Memory Layer | What It Holds | Limits |
|-------------|---------------|--------|
| **Prompt / system message** | Instructions, role, constraints | Fragile; limited context window; no depth |
| **RAG (vector retrieval)** | Documents, PDFs, past outputs | Unstructured retrieval; no reasoning or constraints |
| **Conversation history** | Recent turns | Short-lived; flat; no structured knowledge |
| **Fine-tuning** | Behavioral patterns | Expensive; static; hard to audit |

None of these capture **structured institutional knowledge** — the decision logic, conventions, and rules that senior statisticians carry in their heads and that take years to transfer. This is the knowledge that governs choices like:

- When to use MMRM vs ANCOVA for a given endpoint type and visit structure
- Which missing data strategies are acceptable under ICH E9(R1) vs which are not
- Which stratification factors require pooling and which can be handled directly
- What analysis conventions a given therapeutic area's reviewers expect

An agent without this knowledge is inconsistent. It may answer the same question differently depending on which document it retrieves. It has no audit trail for _why_ it made a decision. And every new study starts from scratch.

### 2. The Proposal

When an agent pilot reaches a natural checkpoint (enough work done to demonstrate value), pause and **codify what the agent learned** into a structured, versioned, machine-readable knowledge base — an **ontology**.

This ontology captures:

- **Declarative knowledge** — the concepts in the domain (endpoint types, analysis methods, estimand components, data structures)
- **Constraints** — what's required, what's allowed, what's forbidden, per ICH guidelines and institutional conventions
- **Relationships** — how concepts connect (Endpoint → HasAnalysisMethod → MMRM)
- **Rules** — conditional logic that can be validated automatically (Longitudinal endpoint → Repeated-measures analysis required)

This is not an additional project. It is a byproduct of the pilot work already underway. Built incrementally, protocol by protocol, it becomes the structured institutional memory for an AI-native biostatistics group.

#### 2.1 The Self-Reinforcing Cycle

```
Better ontology ──→ More effective agents ──→ Faster pilots ──→ Richer ontology
     ↑                                                              │
     └────────────────────── Compounds over time ────────────────────┘
```

The ontology does not require separate funding. It is built at a natural pilot checkpoint. It makes the agent iterate faster for the remainder of the pilot (no re-prompting to remember things already discovered). After the pilot, the ontology is a reusable asset.

#### 2.2 The Copy-Adapt-Extend Workflow

Study teams already build new protocols by copying old ones and adapting. The ontology follows the same pattern:

1. **Copy** — Protocol 12's team loads Protocol 5's ontology
2. **Adapt** — adjust endpoints, comparators, stratification factors, conventions
3. **Extend** — add new rules for anything genuinely novel (rare, per the 80/20 rule)
4. **Validate** — the ontology changes go through the same review process as the SAP

Within the same therapeutic area, protocols are more alike than different. The vast majority of structure — endpoint taxonomies, analysis conventions, CDISC mappings — is shared. Tools like nano-ontoprompt let the LLM suggest the delta for new protocols, which a statistician validates in minutes.

#### 2.3 The Ontology in the Agent Memory Stack

The ontology is **one layer** of the agent's memory, not the whole stack.

| Layer | Technology | What It Holds | Auditable? | Versioned? |
|-------|-----------|---------------|------------|------------|
| **Ontology** | SHACL / RDF triples | Structured concepts, constraints, rules | ✅ Fully traceable | ✅ Git-native |
| **Documents** | RAG vector store | Guideline PDFs, SAP examples, regulatory precedent | Partial | ❌ Not typically |
| **Code** | Skill libraries, | Execution logic, analysis code | ✅ If CI/CD | ✅ Git |
| **Context** | Conversation history | Recent session context | ❌ Ephemeral | ❌ |
| **Judgment** | Human-in-the-loop | Edge cases, novel designs, override decisions | ✅ Per override log | N/A |

Each layer has a role. The ontology is the only one that is simultaneously structured, auditable, version-controlled, and transferable between studies. It does not replace documents (ICH guidelines still need full-text retrieval). It does not replace code (agents need skills to execute analyses). It does not replace human judgment (edge cases require escalation). But it fills a gap that nothing else fills — the structured institutional knowledge that makes an agent consistent, traceable, and effective across studies.

---

### 3. Architecture: The Ontology Layer

The ontology uses **SHACL (Shapes Constraint Language) Core** for deterministic validation of agent-generated analysis decisions against a predefined vocabulary representing ICH guidelines, protocol intent, and institutional conventions. SHACL Core is W3C-standard, vendor-independent, and produces machine-readable validation reports suitable for audit logging.

#### 3.1 The Agent ↔ Ontology Interface

```
[Agent proposes decision]
         │
         ▼ Simple JSON (Pydantic schema)
[Deterministic Middleware]    ← GxP boundary starts here
         │ Maps JSON → JSON-LD
         ▼
[SHACL Core Validator]
         │ Checks against TBox shapes
         ▼
  ┌──────────┬──────────┐
  │          │          │
  ▼          ▼          ▼
PASS      Retry (×3)  Escalation
          (self-correct with error report)
```

Key design decisions:

- **The agent does not output RDF directly.** LLMs are unreliable at generating valid JSON-LD. The agent outputs simple JSON (validated via Pydantic schema), and a deterministic middleware layer translates this into JSON-LD for SHACL validation.

- **The GxP boundary sits at the middleware.** Everything upstream (the LLM agent) is unvalidated space. Everything downstream (middleware, SHACL validator, code generator) is validated once. The LLM can be updated without revalidating the pipeline.

- **SHACL uses strict Core semantics only.** No SHACL-AF extensions (`sh:condition`, `sh:rule`) which have inconsistent validator support.

#### 3.2 Self-Correction Loop

When SHACL validation fails:
1. The validation report is translated into structured natural-language error messages
2. The agent is re-prompted with these errors and original context
3. **Retry cap:** Maximum 3 iterations. Each attempt tracked in audit log.
4. **Degradation guard:** If the agent produces different failing outputs (oscillation), escalation triggers early.
5. **Escalation:** After 3 retries or oscillation, the case is flagged for human review. Full failure trace (original proposal + all iterations + validation reports) is bundled.
6. **Gaming guard:** SHACL conformance does not guarantee clinical appropriateness. The audit log explicitly notes: "SHACL conformance ≠ clinical judgment correctness." Human reviewer retains final authority.

---

### 4. Concrete SHACL Example

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

**Input:** Phase 3 superiority trial, continuous endpoint with weekly visits over 12 weeks, two arms.

**Agent proposal:** ANCOVA at week 12 with LOCF for missing data, no longitudinal structure.

**SHACL validation result:**

| Shape | Check | Result |
|-------|-------|--------|
| `ContinuousEndpointShape` | Has missing data handling? | ✅ PASS |
| `ContinuousEndpointShape` | Has analysis method? | ✅ PASS |
| `LongitudinalContinuousShape` | Method appropriate for longitudinal? | ❌ FAIL — ANCOVA not in allowed methods list |
| `PreferredLongitudinalRecommendation` | MMRM preferred? | ⚠️ Warning only (advisory) |

**Agent self-corrected proposal:** MMRM with unstructured covariance, MAR assumption, Kenward-Roger df.

**Result:** PASS. Audit log records concept traces (LongitudinalEndpoint → LongitudinalContinuousShape → MMRM), ICH E9(R1) reference, and the corrective iteration.

---

### 5. Integration with Existing Standards

| Standard | Coverage | Relationship |
|----------|----------|--------------|
| **OBO Foundry** | Biomedical ontology principles | Adopts OBO design principles (prefers single asserted parent, unique identifiers, orthogonality) |
| **NCI Thesaurus** | Cancer terminology | Imported for indication and comparator mappings |
| **SNOMED CT** | Clinical terminology | Used for adverse event semantic enrichment |
| **CDISC SDTM/ADaM** | Study data standards | Consumed via define.xml parsing; ADaM variable semantics mapped to ontology through deterministic YAML-to-triples layer |
| **CDISC Controlled Terminology** | Codelists | Imported as value-set definitions for study metadata validation |
| **OCRe** | Clinical research design taxonomy | Evaluated for reuse; covers trial design concepts but not statistical analysis rules — this is the gap the ontology fills |

This ontology does not replace existing standards. It fills a gap: none of the above provide machine-executable **analysis decision rules**. CDISC describes what data looks like. This ontology describes how to analyze it correctly given the regulatory framework.

---

### 6. Key Objections and Rebuttals

#### 6.1 "Ontologies are too hard to build and maintain"

**Rebuttal:** The ontology is not built in a single formalization exercise. It grows incrementally alongside the work it supports. After completing a project, the AI copilot drafts the relevant ontology nodes. When new specifications arrive, the LLM proposes how to integrate them into the existing graph — suggesting new nodes, links, rules, and actions — and the human inspects and validates each addition individually. Inspecting one new node in an existing graph is far easier than building from nothing.

This pattern — AI proposes, human validates, graph accumulates — turns knowledge acquisition from a bottleneck into a byproduct of normal workflow. Tools like nano-ontoprompt make the "propose and validate" cycle lightweight. The initial investment is building the graph skeleton and validation pipeline; the ongoing cost is minutes per addition.

Statisticians express domain knowledge through YAML/Markdown templates — no Turtle or SPARQL required. A deterministic parser converts templates to triples. Changes go through a PR workflow with automated regression testing.

#### 6.2 "What happens when the ontology is wrong?"

**Acknowledged risk.** The blast radius of a bad TBox rule is all studies using it. Mitigations:

- **Regression test suite:** Each ontology update runs against a curated set of known-good analysis decision graphs. If a rule change breaks a previously passing test, the PR is blocked.
- **TBox/ABox separation:** Schema (TBox) is version-controlled independently from study instances (ABox). Schema changes require Core Ontology Board approval.
- **Break-glass override:** Study teams can deviate with documented justification:
  1. Statistician files deviation — classified as "rule is wrong" (ontology error) or "rule doesn't apply" (study-specific exception)
  2. Board reviews within 5 business days
  3. Approved deviations create study-level branches with full audit trail
  4. "Rule is wrong" cases automatically create TBox change tickets
  5. Patterns reviewed quarterly for systemic ontology gaps

#### 6.3 "This replaces statisticians"

**Rebuttal:** The ontology handles repetitive execution — SAP boilerplate, constraint checking, routine method selection. It elevates the statistician's role to strategic trial design, regulatory interaction, and interpretation. For junior statisticians, the ontology serves as an interactive validation engine: when they propose an analysis, SHACL explains _why_ a constraint was violated, building domain intuition faster than traditional mentorship alone.

#### 6.4 "What about regulatory acceptance?"

**Acknowledged risk.** No regulator has issued guidance on ontology-based validation of AI-generated analysis decisions. Strategy:
1. **Parallel validation:** First 6-12 months post-MVO, ontology runs alongside traditional processes. All decisions compared against human-generated SAPs.
2. **Historical study validation:** Test ontology against 10-20 completed studies to measure agreement and identify edge cases.
3. **FDA/CDISC engagement:** Submit framework via existing working groups for input.
4. **The ontology has a regulatory path:** It is a deterministic artifact subject to standard Computer System Validation (GAMP 5). Unlike the LLM, it can be validated independently.

#### 6.5 "What about LLM-bootstrapping paradox?"

**Acknowledged.** LLMs assist in drafting ontology axioms. The circularity is closed by a validation gate: every axiom generated by LLM assistance is validated by a human domain expert before merging. This is 100% human validation for TBox changes — not spot-checking, not sampling.

---

### 7. Organizational Structure

#### 7.1 Core Ontology Board

| Role | Count | Responsibility |
|------|-------|---------------|
| Lead Statistical Scientist | 1 | Domain authority; chairs Board; final TBox approval |
| Senior Statisticians | 3 | Domain expertise across TAs; review PRs, break-glass requests |
| Ontology Engineer | 1 | Technical authority on SHACL, middleware, tooling |
| Regulatory Compliance Lead | 1 | CSV (GAMP 5), Part 11 compliance, audit readiness |
| MLOps/DevOps Engineer | 1 | CI/CD pipeline, regression testing, versioning |

Reporting line: Within BARDS, reporting to head of Late Development Statistics. Funding: Central BARDS budget, 2-year committed runway for MVO development.

#### 7.2 Knowledge Acquisition Workflow

Statisticians provide domain knowledge in YAML templates:

```yaml
rule_id: MISSING_DATA_LONGITUDINAL
domain: continuous_endpoint
condition: endpoint_type == "longitudinal" && trial_phase == "Phase3"
constraint:
  type: hard
  path: analysis_method
  allowed: [MMRM, GEE, GrowthCurveModel, BayesianLongitudinal]
  justification: "Longitudinal data requires repeated-measures method (ICH E9(R1) §2.3)"
```

The deterministic parser converts YAML to Turtle triples. The LLM assists in suggesting template fields and flagging inconsistencies. Every axiom is human-validated before merge.

---

### 8. Cost-Benefit

#### 8.1 Investment (24 months)

| Item | FTE | Annual Cost |
|------|-----|-------------|
| Senior Statisticians (3 × 50%) | 1.5 | $375K |
| Ontology Engineer | 1.0 | $200K |
| Regulatory Compliance | 0.5 | $125K |
| MLOps/DevOps | 1.0 | $200K |
| Infrastructure | — | $100K |
| **Total annual** | — | **$1.0M** |
| **2-year total** | — | **$2.0M** |

#### 8.2 Projected Returns

| Metric | Current | Post-Ontology | Savings |
|--------|---------|---------------|---------|
| SAP first draft | 4-6 weeks | 3-5 days | ~80% |
| SAP QC cycles | 2-3 rounds | 0-1 rounds | ~60% |
| Methodology audit findings | Baseline | Near-elimination of preventable findings | ~70% |
| Cross-study consistency | Variable across teams | Enforced | Standardization |

**Break-even estimate:** 15 Phase II/III studies post-MVO deployment. At an estimated ~$100K/study in labor + QC + audit remediation (internal planning benchmark), the ontology pays for itself within 12-18 months of enterprise-wide use.

**Risk-adjusted (50% adoption):** Break-even extends to ~24 months for 30 studies.

---

### 9. Implementation Timeline

| Phase | Scope | Duration | Exit Criteria |
|-------|-------|----------|---------------|
| **MVO** | Superiority, binary/continuous endpoints, two-arm, simple stratification | 3-6 months | SHACL validates 10 historical studies with ≥95% agreement (exact-match of analysis method, missing data strategy, stratification) |
| **Pilot** | 2-3 active studies running ontology-parallel | 6-12 months | No critical disagreements between ontology and human SAPs |
| **Expansion** | TTE endpoints, non-inferiority, multi-arm | 12-18 months | ≥80% of Phase II/III studies covered |
| **Production** | Full coverage, governance mature | 18-24 months | Ontology is default SAP authorship pathway |

**Total: 3-5 years to full production. MVO proof-of-value in 3-6 months.**

---

### 10. Known Unknowns and Failure Modes

| Risk | Impact | Mitigation |
|------|--------|------------|
| Regulators reject ontology-based AI validation | High | Parallel validation generates evidence; ontology has standalone value as documentation/training tool |
| Knowledge acquisition bottleneck | High | Start with MVO; prove the workflow scales before expanding |
| SHACL performance at enterprise scale | Medium | Benchmark during MVO; partition TBox by therapeutic area |
| Agent gaming — passes SHACL but clinically inappropriate | Medium | Audit log caveats; human-in-the-loop during Pilot |
| Governance becomes too slow | Medium | Publish SLAs (5-day break-glass, 2-week TBox changes) |
| Cross-pharma adoption stalls | Low | Single-pharma value is positive; publish framework regardless |

---

### 11. What This Proposal Is and Isn't

**What it is:** An argument that structured institutional knowledge (ontology) fills a critical gap in agent memory — one that prompts, RAG, conversation history, and fine-tuning all miss. The ontology is built incrementally as a byproduct of agent pilot work, follows the copy-adapt-extend pattern that study teams already use, and compounds in value with each additional protocol.

**What it isn't:** A claim that ontology replaces documents, code, or human judgment. A demand for separate upfront funding. An assertion that ontology is the only thing agents need. The ontology is one layer of the agent memory stack — but it is the only layer that is simultaneously structured, auditable, version-controlled, and transferable across studies. That is the gap it fills, and no existing technology fills it better.
