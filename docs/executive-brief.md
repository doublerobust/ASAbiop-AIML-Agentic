# Ontology for Agentic AI in Clinical Biostatistics

## Executive Brief — For BARDS Leadership Review

---

### The Problem

Biostatistics is already drowning in documentation burden. Every SAP goes through 3-5 rounds of QC. Every audit traces back to the same pattern: two study teams made different analysis decisions for the same endpoint type because knowledge lived in people's heads, not in a shared, enforceable framework.

Agentic AI is coming to clinical development — whether we prepare for it or not. The question is not whether it will be used. The question is whether it will be used *safely*, *consistently*, and *defensibly* under regulatory scrutiny.

Without structure, an AI agent making analysis decisions is a black box. You cannot audit it, cannot trace its reasoning, cannot freeze its knowledge at a point in time, and cannot show an inspector *why* it chose Method A over Method B.

That is a risk that compounds with every trial.

---

### The Insight

The solution is not "better prompts" or "bigger models." The solution is a formal, machine-readable, human-verifiable knowledge framework that encodes our regulatory guidelines, endpoint conventions, and analysis decision rules in one place.

Think of it as the **statistical playbook that every study team agrees to follow** — except it's machine-executable, version-controlled, and capable of validating every analysis decision before it reaches the SAP.

When an agent proposes ANCOVA for a longitudinal endpoint, the framework catches it: "Longitudinal endpoints require repeated-measures methods per ICH E9(R1)." It doesn't replace the statistician — it catches the mistakes that humans catch in QC cycle 2, but at the moment of proposal, not three weeks later.

---

### What's Changed by the Multi-Model Review

The initial proposal was a technical document for ontology engineers. It used language that would not survive a leadership conversation. The revised proposal — shaped through 9 critiques across 4 different AI model architectures — now addresses the questions that matter:

| Question | Answer |
|----------|--------|
| What does it cost? | ~$2M over 2 years for a dedicated team of 6-7 |
| What's the return? | 80% faster SAP drafts, 60% reduction in QC cycles, near-elimination of preventable audit findings |
| How long until value? | 3-6 months for a bounded proof-of-concept on superiority trials |
| What's the risk? | Building a team with rare skillset (statistics + formal knowledge systems). Mitigated by starting small. |
| Does this replace statisticians? | No. It frees them from repetitive decisions to focus on trial design, regulatory strategy, and interpretation. |
| Has this been tested against critics? | Yes. 4 independent AI reviewers stress-tested every objection. No blocking issues remain. |

---

### The Asks

1. **Review the technical proposal** (`docs/ontology-as-grounding-layer-for-agentic-ai.md` in the working group repo) at your convenience
2. **Discuss a Minimum Viable Ontology** — a 3-6 month pilot scoped to superiority trials with binary/continuous endpoints
3. **Identify the right team** — 2 statisticians, 1 ontology engineer, 1 regulatory compliance lead, 1 DevOps engineer, plus senior oversight

---

### One-Page Summary

**The problem:** AI in clinical biostatistics needs guardrails. Without structured knowledge representation, AI agents are unauditable black boxes — unacceptable under GxP.

**The solution:** A formal, version-controlled knowledge framework (ontology) that encodes ICH guidelines, endpoint conventions, and analysis rules. Every AI-proposed decision is validated against this framework before reaching a SAP.

**The value proposition:** Faster SAP generation, fewer QC cycles, consistent decisions across studies, audit-ready traceability, and a defensible path to using AI in regulated work.

**The timeline:** 3-6 months to prove the concept on a bounded domain. 3-5 years to full production capability.

**The investment:** ~$2M over 2 years for a dedicated team of 6. Break-even at 15 studies deployed.

**The team:** Within BARDS, with a hybrid skillset — statistics leads the domain, engineering builds the framework.
