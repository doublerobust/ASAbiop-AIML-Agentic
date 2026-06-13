# LLM-Driven Ontology Construction — Video Summary

**Source:** Douyin video by Jingwei (nano-ontoprompt developer)
**Title:** 12分钟学习LLM驱动Ontology构建 (12 min learning LLM-driven ontology construction)
**Date:** ~June 2026
**Summarized by:** 豆包 (by Yue)

---

## What Ontology Is & Its Core Value

- Without ontology, LLMs pattern-match when processing data. Repeated queries on the same data produce inconsistent results because the model can't recognize logical connections between data points.
- Ontology acts as a structured knowledge map — entities, attributes, relationships. Enables accurate retrieval and multi-step chained reasoning.
- Traditional ontology building: professional engineers + business experts, extremely time-consuming, costly, hard to maintain.

## Four Major Challenges of LLM-Built Ontology

1. **Unknown entity categories** — hard to know how many entity types exist in a new field
2. **LLM hallucinations** — model invents non-existent concepts
3. **Granularity control** — too broad = useless, too detailed = maintenance burden
4. **No evaluation standards** — no unified rule to judge quality

## Five Technical Approaches

### 1. Decomposition Approach (最可靠)
Split into: entity extraction → deduplication → standardization → verification → graph storage. Double verification before adding to knowledge base. Unverified → logs only.

- **Pros:** Highest reliability, for production
- **Cons:** Heavy workload; early errors cascade
- **Use:** Nuclear power docs, large-scale public KGs

### 2. Clustering Approach
Extract nouns → density-based clustering (AP, not K-Means) → LLM names clusters → extract relational triples.

- **Pros:** Data-driven, low hallucination for subtasks
- **Cons:** Quality depends on clustering; overly detailed in open domains
- **Use:** Exploring unknown fields

### 3. Two-Step Construction Approach
LLM extracts concept list → organizes into hierarchy → generates standard ontology. Human review mid-step.

- **Pros:** Fast iteration, convenient for early validation
- **Use:** Quickly creating first ontology version for testing

### 4. Framework-Based Approach
Adopt existing standard frameworks (e.g., Wikidata) with predefined entity types and rules. LLM extracts within the framework.

- **Pros:** Reduces hallucinations; outputs comply with industry norms
- **Use:** Healthcare, law, power — domains with mature standards

### 5. End-to-End Prompt Approach
Single prompt, LLM generates complete ontology from text in one step.

- **Pros:** Fastest to implement
- **Cons:** Unstable, highest hallucination risk
- **Use:** Quick POC and learning only — not for production

## Selection Guide

| Scenario | Choose |
|----------|--------|
| Rapid POC / idea testing | End-to-end prompt |
| Exploring new fields, no clear classification | Clustering |
| Industry with existing standards | Framework-based |
| Formal production, high accuracy | Decomposition + double verification |

## Key Tips

- Errors in early extraction cascade through the whole process — spend time on early data governance
- Use structured prompt templates, not casual natural language
- High quality + reasonable constraints > massive data

## Tool: Ontoprompt

Jingwei's tool based on the prompt method with extra extraction and verification rules.

- Parameter configuration: confidence thresholds, verification rules
- Prompt management: dedicated prompts per business domain (supply chain, finance, marketing)
- Ontology management: upload Word/Markdown/CSV, select LLM, extract entities & relationships, visualize graph
- Manual editing: add/modify entities, check business logic rules
- Open source on GitHub
