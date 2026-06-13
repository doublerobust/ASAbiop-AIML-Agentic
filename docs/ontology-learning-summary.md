# Ontology for Agentic AI in Biopharm — Learning Summary

> A 4-hour hands-on session learning what ontology is, why it matters for agentic AI, and what it could mean for the clinical biostatistics pipeline. Starting from zero.

---

## What We Built

**Toy project:** A subgroup identification simulation study comparing 7 ITR methods across 10 simulation scenarios, with 5 source papers, 2 data-generating processes, and 5 R code files.

**Platform:** [nano-ontoprompt](https://github.com/jingw2/nano-ontoprompt) — an open-source, Palantir Foundry-inspired ontology builder. Self-hosted, all local, no data leaves the machine. Two build paths: pipeline mapping (structured data → ontology) and LLM extraction (upload a PDF → auto-extract entities).

## Ontology Concepts Learned (from scratch)

| Term | Plain English | What we modeled |
|------|--------------|-----------------|
| **Entity** | A thing that matters | ResearchMethod, SimulationScenario, SourcePaper, ScriptFile, PerformanceMetric |
| **Relation** | How two things connect | `MLMR --HAS_SOURCE--> Zhao2025 paper`, `stratified_cavboost.R --IMPLEMENTS--> StratCox` |
| **Class** | A type of entity | 7 classes: ResearchMethod, SimulationScenario, SourcePaper, PerformanceMetric, ScriptFile, DataGeneratingProcess, PrognosticScoreMethod |
| **Property** | Attributes of an entity | `r_package: ranger`, `eta: 0.05`, `file: owl_impl.R` |
| **Logic Rule** | A constraint or inference the ontology enforces | "Every method must have a source paper" — validation rule |
| **Action** | An executable operation an agent can trigger | "Run M-Learning comparison" — points to `master_comparison.R 100 4` |
| **RDF/Turtle** | The standard format for sharing ontologies | Machine-readable triple export (`subject predicate object`) |

**Key insight:** RDF is the grammar (how to write triples), OWL is the language (what classes, properties, and constraints mean). Most practical ontologies use RDF + RDFS + SHACL; full OWL is rarely needed.

## The "Aha" Moment

The problem ontology solves for agentic AI:

> Every time I hand off a project to a subagent, I have to re-explain everything — methods, code files, papers, scenarios, findings. Context windows compress. Memory searches miss. Agents hallucinate methodology.
>
> With ontology: hand the subagent **one file** (the ontology brief + entity dump). It reads the project structure, code paths, success metrics, and constraints in one shot. No repeat explanations.

We demonstrated this by spawning an agent that read our exported `ONTOLOGY_BRIEF.md` and `entities.json` and could answer questions about the project without any conversation history.

## What We Learned About the Hard Parts

1. **Modeling is harder than tooling.** Deciding what to model and what rules to write requires real thought. You will inevitably forget edge cases. The ontology grows with the project.
2. **LLM extraction is useful but noisy.** Extracting from a PDF catches things you might miss, but creates "Concept" and "Process" entities that are noun phrases, not actionable objects. Requires curation.
3. **Rule-writing requires introspection.** Rules like "every method must have a source paper" seem obvious in hindsight but are easy to forget. They're the institutional knowledge that rarely gets written down.
4. **Code paths make ontology actionable.** Linking methods to their `.R` files turns ontology from a description into an operations manual. An agent can go from "tell me about OWL" to "run the OWL implementation" in one hop.

## The Potential for the Biostatistics Pipeline

Session participants identified the clinical trial analysis pipeline as the natural target:

| Current State | With Ontology |
|--------------|---------------|
| Protocol → SAP → SDTM → ADaM → TLFs → CSR stored across Word, PDF, SAS programs | All stages modeled as entities, relations linking them |
| "Which SDTM domain does this ADaM variable come from?" requires searching 5 documents | One SPARQL query |
| Change primary endpoint → manually trace impact across SAP, TLF shells, CSR | Graph shows all downstream dependencies immediately |
| Agent asked to generate a TLF picks variable names that *almost* match | Agent navigates the ontology and finds exact variable names |
| Cross-program consistency depends on institutional memory | Ontology catches drift when the same endpoint uses different methods across trials |

**Proposed entry point:** Model a single trial (protocol → SAP → key TLFs). Prove an agent can answer analysis questions without reading 50 pages. Scale from there.

## The Hardest Question

> "Why do we need this when things have been working fine?"

Answer: Things work fine because specific people know the pipeline. Agentic AI makes the *lack* of codified knowledge impossible to ignore. An agent without ontology is fancy autocomplete. An agent with ontology can trace a requirement from protocol all the way to the R function that implements it.

The framing that resonates: **Don't pitch ontology as a replacement. Pitch it as the map agents need to be useful.** If we're adopting agentic AI — and the ASA Biopharm working group is exploring exactly this — then ontology is the infrastructure layer that makes it work.

---

*Built by someone who started the day not knowing what ontology meant. Tools used: nano-ontoprompt, Python, R, Cloudflare tunnel. All code and data are local. The full ontology export is available for review.*
