# Institutional Knowledge for Agentic AI in Biostatistics

## Executive Brief — For BARDS Leadership Review

---

### Where We Are

Agentic AI for clinical biostatistics is no longer hypothetical. Teams are building prototypes — agents that draft SAPs, generate TLFs, automate QC checks. The early evidence shows real time savings. Benchmarking work on agent skills and workflows is underway.

This is not a debate about _whether_ agents will be used in biostatistics. They already are. The question is how to make them effective enough for production work.

### Where the Ceiling Is

Today's agents rely on a shallow memory stack: prompts, RAG over documents, recent conversation history. This works for demos. But it hits a ceiling when the agent needs to make consistent, auditable, domain-grounded decisions across multiple studies.

The missing layer is **structured institutional knowledge** — the decision logic that senior statisticians carry in their heads and that currently takes years to transfer. Things like:

- When to use MMRM vs ANCOVA for a given endpoint type
- What missing data strategies are acceptable per ICH E9(R1)
- Which stratification factors require pooling rules
- The analysis conventions that reviewers expect for a given therapeutic area

Without this layer, every agent pilot starts from scratch. Without this layer, the same question gets answered differently depending on which document the agent happens to retrieve. Without this layer, there's no audit trail for _why_ a decision was made.

### What We Propose

When an agent pilot reaches a natural checkpoint (enough work done to show value), pause and **codify what the agent learned** — the endpoint types it encountered, the methods it selected, the rules it followed, the conventions it discovered. This becomes the first draft of an **ontology**: a structured, versioned, machine-readable knowledge base of analysis decisions.

This is not an additional project. It's a byproduct of the pilot work you're already doing. Tools like nano-ontoprompt let the LLM propose the ontology structure, which a statistician validates — minutes per addition, not weeks.

Here's what happens next:

1. **During the pilot** — the ontology makes the agent iterate faster. No more re-prompting it to remember things it already figured out. The ontology *is* its institutional memory, carried forward.

2. **After the pilot** — the ontology becomes a reusable asset. When Protocol 12 starts, the team doesn't learn from scratch. They copy Protocol 5's ontology, adapt what's different (new endpoints, new comparators, maybe a new convention), and extend. This is exactly how study teams already work — nobody writes a protocol from a blank page.

3. **Over time** — the ontology compounds. Within the same therapeutic area, protocols are more alike than different. The 80/20 rule applies: the ontology captures the 80% once, each new study formalizes the 20% delta. Better ontology → more effective agents → richer ontology.

### What the Ontology Is and Isn't

An ontology captures **structured decision knowledge**: what concepts exist, what rules apply, what's required or forbidden. It gives the agent a shared vocabulary and a rulebook.

It does **not** capture everything. Full guideline documents still need RAG. Code still needs skill libraries. Recent session context still needs conversation history. Human judgment still decides the edge cases.

The ontology is one layer of the agent memory stack — but it's the layer that nothing else fills. Prompts are fragile. RAG is unstructured. Conversation history is short-lived. The ontology is the only layer that is simultaneously structured, auditable, version-controlled, and transferable between studies.

### The Asks

1. **Review this framing.** We're not asking for ontology funding upfront. We're asking to build it as a byproduct of agent pilot work that's already budgeted.

2. **At the next pilot checkpoint**, try codifying what the agent has learned into structured memory. The tools exist. The process is lightweight. The output is reusable.

3. **Discuss how this fits the team's existing workflow** — the copy-adapt-extend pattern is already how study teams work. The ontology just makes that pattern explicit and machine-readable.
