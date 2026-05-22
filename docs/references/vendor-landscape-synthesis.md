# BBSW AI Summit 2026 — Vendor Landscape Synthesis
## Relevance to ASA Biopharm Agentic AI Workstream

---

## The 8 Vendors at a Glance

| Company | Founded | Stage | Core Product | Key Differentiator |
|---|---|---|---|---|
| **EDETEK** | 2009 | Mature (150+ clients) | R&D Cloud + Agentic layer | Enterprise governance, audit-ready |
| **PhaseV** | ~2021 | Growth (45+ clients, $65M) | AI Conductor pipeline | End-to-end ClinDev automation |
| **Atropos Health** | ~2019 | Growth (8/10 top pharma) | ChatRWD + Evidence Agent | RWE network (300M patients) |
| **JDIX** | 2024 | Early (12 clients) | JDIM multi-agent + TFL Reviewer | Built for statisticians specifically |
| **Taimei** | ~2018 | Growth | FORGE/PULSE/INSIGHT modules | APAC expertise, transformation services |
| **TrialMind (Keiji.AI)** | ~2024 | Early-adopter | Full lifecycle AI agents | Academic credibility (UIUC, Nature pubs) |
| **HopeAI** | ~2024 | Early | PURE Evidence + AI Teammates | Clinical-statistical bridge |
| **Bayesoft** | ~2025 | Seed/Early | AIVOLUTION + BAIVOLUTION | Bayesian-native, regulatory-aligned |

---

## Assessment by WG Relevance

### 🟢 Highly Relevant — Directly overlaps with WG scope

**1. JDIX — TFL Reviewer (Pillar 2: Analysis & Reporting)**
- *What they do:* AI agent that reviews TFL packages against SAP, specs, shells, and SAS programs
- *Why relevant:* This is the most concrete "agent doing a statistician's job" example in the set. Not aspirational — they have 12 clients in year one
- *Takeaway for WG:* Use as a case study of what a narrow, well-scoped agentic tool looks like. It solves one problem (TFL review) instead of promising everything
- *Risk:* They're a 2024 startup — depth beyond the demo is unknown

**2. TrialMind / Keiji.AI — Full Lifecycle Agents (All 3 Pillars)**
- *What they do:* Multi-agent system covering planning, execution, analysis, reporting. Deployed at Guardant Health (20+ users), Regeneron, MGB
- *Why relevant:* Most substantive of all 8 — real deployments, published methods in Nature/Nature Comms, academically grounded
- *Takeaway for WG:* Their "decompose clinical tasks into agent-suitable steps" approach validates our white paper methodology. The CEO (Jimeng Sun, ex-IQVIA AI head) bridges academic rigor and industry pragmatism
- *Risk:* Still early in enterprise adoption. Guardant's 20 users is a pilot, not scaled

**3. EDETEK — Enterprise Agentic Governance**
- *What they do:* R&D Cloud with agentic action layer — detect → explain → route → record, with audit trails
- *Why relevant:* They're the only vendor addressing the *governance* question directly. Their "clinical-grade" framing (role permissions, human approval gates, audit logging) is what every pharma company actually needs before deploying agents
- *Takeaway for WG:* Their governance framework (Sense → Reason → Decide → Act) is a reference architecture we should cite. It solves the "how do you audit an AI agent?" question that the workstream will need to answer
- *Risk:* They're a platform play first, AI second. The agentic layer is new

### 🟡 Moderately Relevant — Some overlap, useful validation

**4. HopeAI — Clinical-Stat Bridge**
- *What they do:* PURE Evidence (agentic literature review), SynthIPD (KM curve → IPD), AI Clinician + AI Statistician
- *Why relevant:* Their core thesis — trial design takes 6-12 months of clinical-stat back-and-forth — is exactly the integration problem the workstream identified. "80% of trials designed without systematic review due to timeline pressure" is a striking stat
- *Takeaway for WG:* Their "AI Teammates" framing (specialized agents for specific roles) matches our multi-agent verification pipeline. The AI Clinician + AI Statistician pairing is a concrete reference model
- *Risk:* Claims 2x accuracy over LLMs — would need independent verification. SynthIPD is neat but narrow

**5. Taimei — Prototype-Production Gap**
- *What they do:* FORGE (study setup), PULSE (medical intel), INSIGHT (stat programming)
- *Why relevant:* Their tagline — "The pilot works. The transformation doesn't" — is *exactly* the WG meeting #3 conclusion (#5 and #9 in your notes). Their INSIGHT module (60-80% efficiency in stat programming with human-in-the-loop) validates our Analysis & Reporting direction
- *Takeaway for WG:* Use their "pilot vs production" framing as evidence that this isn't just your WG's opinion — the industry is saying the same thing. Their APAC footprint connects to the China coordination item (#7 in May 8 actions)
- *Risk:* They're a services company masquerading as a product company. Scale claims are hard to verify

**6. PhaseV — Pipeline Automation Validation**
- *What they do:* End-to-end ClinDev pipeline (Synopsis → CSR)
- *Why relevant:* Their pipeline map is a useful reference architecture. 45+ customers and $65M raised suggests there's real demand
- *Takeaway for WG:* Use their pipeline diagram as one model of "what a fully automated analysis pipeline could look like" — then contrast with the critical assessment that makes your white paper valuable
- *Risk:* Pure vendor pitch. No technical depth in the deck

### 🔴 Lower Relevance — Interesting but tangential

**7. Atropos Health — RWE Evidence Agent**
- *What they do:* ChatRWD, Atropos Evidence Agent for RWE generation
- *Why relevant:* RWE is part of the broader AI/ML landscape, and their agentic approach to evidence generation is interesting
- *Takeaway for WG:* Mostly useful as a reference point for the "evidence generation" angle — not directly tied to our three pillars
- *Risk:* RWE-focused, not agentic-biostatistics-focused. The name has "agent" but it's really a chatbot on a federated data network

**8. Bayesoft — Bayesian + Agentic**
- *What they do:* AIVOLUTION (4-layer agentic platform) + BAIVOLUTION (Bayesian methods)
- *Why relevant:* The Bayesian angle is differentiated. FDA's Jan 2026 Bayesian guidance is a real tailwind
- *Takeaway for WG:* Their "decision engine, not copilot" framing is a good slogan-level distinction. The regulatory-aligned Bayesian pitch is worth watching
- *Risk:* Seed-stage. $600K in MSAs is not proof of product. Most aspirational deck of the 8

---

## What These Tell Us Collectively (Patterns)

### Pattern 1: Everyone Claims Human-in-the-Loop
Every single deck mentions human oversight. This isn't differentiator — it's table stakes. The WG white paper needs to go deeper: *what kind* of human oversight? At which decision points? With what escalation path?

### Pattern 2: The Analysis & Reporting Pipeline is the Most Crowded
PhaseV, JDIX, Taimei (INSIGHT), and TrialMind all target some version of "automate the stat programming workflow." This validates demand but means we need clear differentiation in the white paper.

### Pattern 3: Governance is Underserved
Only EDETEK addresses the "how do you audit an AI agent?" question. This is a gap the white paper can fill — and it's directly relevant to the regulatory pillar.

### Pattern 4: No One Is Doing Critical Assessment
All 8 decks are selling. None of them say "here's where this doesn't work" or "here are the failure modes." That's your WG's lane.

### Pattern 5: The Clinical-Stat Gap is Recognized but Unresolved
HopeAI and TrialMind both highlight the communication gap between clinical and statistical teams. The WG can address this as an organizational challenge, not just a technical one.

---

## What to Watch

| Trend | Signal | Timeframe |
|---|---|---|
| FDA Bayesian guidance adoption | Bayesoft + regulators | 1-2 years |
| Enterprise agent governance | EDETEK's approach | 6-12 months |
| TFL review as the "killer app" | JDIX + stat programmer demand | Now - 6 months |
| Multi-agent clinical-stat teams | HopeAI + TrialMind | 1-2 years |
| Vendor consolidation | PhaseV scale + EDETEK maturity | 2-3 years |
| China APAC AI platforms | Taimei + BeiGene | 6-12 months |

---

## Recommended White Paper Positioning

Based on this landscape:

**Don't be:** A survey of vendor products (dated on arrival)
**Don't be:** An exhaustive catalog of methods (others are doing this)
**Do be:** A principled framework for *evaluating* agentic AI in biostatistics — what to look for, what to avoid, how to audit, how to govern

The vendors sell solutions. The WG sells *standards*. That's the distinction worth keeping.
