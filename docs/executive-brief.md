# Institutional Knowledge for Agentic AI in Biostatistics

## Executive Brief — For BARDS Leadership Review

---

### Where We Are

Agentic AI for clinical biostatistics is no longer hypothetical. Teams at Merck and across the industry are building prototypes — agents that draft SAPs, generate TLFs, automate QC. The early evidence shows real capability. Benchmarking work on agent skills and workflows is underway through the ASA Biopharm AIML working group.

This is not a debate about *whether* agents will be used. The question is how to make them effective enough for production work — consistent, traceable, and able to carry institutional knowledge across studies.

### Where the Ceiling Is

Today's agents rely on a shallow memory stack: prompts, document retrieval, recent conversation history. This works for demos. It hits a ceiling when the agent needs to make consistent, grounded decisions across multiple studies.

The missing layer is **structured institutional knowledge** — the decision logic and conventions that senior statisticians carry in their heads and that currently take years to transfer. What analysis method fits this endpoint type? What missing data strategy is appropriate? What do oncology reviewers expect for stratification? These are not answerable by document retrieval alone.

Without this layer, every agent pilot starts from scratch. The same question gets answered differently depending on which document happens to be retrieved. And when a senior statistician leaves, their decision logic leaves with them.

### What We Propose

When an agent pilot reaches a natural checkpoint — after the first end-to-end dry run of a TLF package, typically ~2 months before database lock — pause for 2 days and **codify what the agent learned**. The endpoint types it encountered, the methods it selected, the rules it followed, the conventions it discovered. This becomes the first draft of an **ontology**: a structured, versioned, machine-readable knowledge base of analysis decisions.

This is not an additional project. It is a workflow discipline layered onto pilot work already underway. Tools like nano-ontoprompt let the agent propose the ontology structure, which a statistician validates in minutes — not weeks. It doesn't need to be perfect on the first pass. Edge cases surface when they matter.

Here's what happens next:

1. **During the pilot** — the ontology makes the agent iterate faster. No more re-prompting it to remember things it already figured out. The ontology *is* its institutional memory.

2. **After the pilot** — the ontology becomes a reusable asset. When the next study starts, the team doesn't learn from scratch. They copy the previous study's ontology, adapt what's different (new endpoints, new comparators), and extend. This is exactly how study teams already work — nobody writes a protocol or builds SDTM domains from a blank page.

3. **Over time** — the ontology compounds. Within the same therapeutic area, protocols are more alike than different. The 80/20 rule applies: capture the 80% once, formalize the 20% delta per study.

### What the Ontology Is and Isn't

The ontology is **one layer** of the agent memory stack. It captures structured decision knowledge: what concepts exist, what rules apply, what's required or forbidden. It gives the agent a shared vocabulary and a rulebook.

It does not replace full guideline documents (they still need retrieval), or code libraries (agents still need to execute), or human judgment (edge cases still need escalation). But it fills a gap that no other layer fills — structured, auditable, version-controlled, transferable knowledge. That gap is why agents today are inconsistent across studies.

### Why Now, Why Us

No peer organization has published a working ontology-driven agent validation pipeline for biostatistics. Academic groups have explored SHACL for clinical data quality, but none for AI decision auditing in the analysis and reporting workflow. The feedback from the ASA Biopharm AIML working group confirms that most companies are still in the early stages of understanding what agentic AI needs to work in this space.

BARDS has an opportunity to shape this capability before it becomes table stakes. Regulatory interest in AI validation is accelerating. Building the structured knowledge layer now positions us to define how agents should be governed in biostatistics work, rather than reacting to standards set elsewhere.

### The Ask

**Greenlight a 2-day exercise at the next pilot checkpoint:** have the pilot team spend 2 days codifying what the agent learned into structured form. We report back with a concrete artifact and a validated time estimate for future checkpoints. No additional budget needed — this is time reallocated within the existing pilot scope.
