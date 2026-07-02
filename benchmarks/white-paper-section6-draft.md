# White Paper Section 6 — Discussion

**Draft Date:** 2026-07-02 (Day 32)
**Status:** First draft for WG review
**Word Count:** ~2,800

---

## 6. Discussion

### 6.1 Positioning Within the Industry Landscape

The benchmark presented in this work addresses a critical gap identified across multiple 2026 industry venues. At PharmaSUG 2026, at least four papers directly addressed agentic AI for TFL generation: "An Agentic AI Framework That Reads SAPs and Generates TFL Table of Contents" (AI-206), "Schema-Preserving Generation of Clinical TLF Templates and Executable R Code via Iterative LLM-Guided Debugging" (AI-123), "Agentic R in Clinical Trials" (AI-438), and "Evaluation of Azure OpenAI ChatGPT API as Code Assistance Tools for Statistical Programming in SAS, R and Python" (AI-207). Despite this convergence of interest, none of these papers proposed a standardized evaluation methodology. Each vendor and research group evaluated their own systems using proprietary test sets, making cross-comparison impossible.

Our benchmark fills this gap by providing the first standardized, multilingual, regulatory-aware evaluation framework for TFL programming agents. The 16 Level 1 test cases (TC-001 through TC-023) cover the most common TFL types in oncology trials: survival analysis (KM median, TTP, DOR), response analysis (ORR, DCR), safety summaries (AE, exposure, lab shifts, concomitant medications), efficacy summaries (change from baseline), and visual outputs (KM curves, forest plots, waterfall plots). Each test case includes ground truth implementations in R, Python, and SAS, with automated scoring against tolerances derived from regulatory standards.

The regulatory dimension of our benchmark is particularly timely. The FDA-EMA Joint Guiding Principles of Good AI Practice in Drug Development, released in January 2026, establish 10 principles for risk-based AI governance in pharmaceutical development. Principle 3 (adherence to standards) and Principle 8 (risk-based performance assessment) directly motivate the compliance and safety scoring dimensions of our benchmark. Our 148 compliance rules (spanning ADaM variable mapping, FDA TCG checklist, and ICH E3 CSR formatting) and 96 safety rules (N-count consistency, denominator correctness, cross-TFL agreement, edge case resilience) provide a concrete implementation of these principles for TFL outputs.

The EU AI Act, with provisions applicable from August 2026, classifies clinical AI systems as high-risk and places full responsibility on sponsors for AI-generated content. This creates an urgent need for standardized verification tools. Our benchmark's compliance scoring module directly addresses this requirement by checking ADaM variable mapping, population filter correctness, and statistical method documentation against regulatory standards.

### 6.2 Key Findings

**Finding 1: Cross-language numerical consistency is achievable for standard statistical methods.** All 16 Level 1 test cases achieve 1.0000 R↔Python cross-language verification score on shared input data. This confirms that for the most common TFL computations (KM estimation, binomial proportions, descriptive statistics, Cox PH), the choice of programming language does not introduce meaningful numerical differences when standard packages are used (R `survival`, Python `lifelines`, R `stats`, Python `scipy`). This finding has practical implications: organizations can validate AI-generated TFL code in one language and deploy in another with confidence, provided the same input data is used.

**Finding 2: The scoring harness successfully detects clinically meaningful errors.** Error injection testing demonstrates that the scoring framework correctly identifies and penalizes errors. For example, injecting an HR bias of +0.3 into TC-012 (Forest Plot HR) reduces the score from 1.0000 to 0.7227, with the `overall_hr` component correctly flagged as failing. This confirms that the tolerance-based scoring approach is neither too lenient (allowing clinically significant errors) nor too strict (penalizing floating-point noise).

**Finding 3: CDISC ARS alignment is feasible without breaking backward compatibility.** The ARS proof-of-concept (6 test cases with `--ars-output` flag) demonstrates that CDISC ARS v1.0-compatible envelopes can be generated alongside existing JSON output. The ARS envelope wraps the same numerical results in a standardized metadata structure (analysisMethod, analysisVariables, analysisPopulation, resultGroups) without modifying the underlying computation. This backward-compatible approach allows gradual adoption: existing workflows continue to use the flat JSON output, while ARS-aware systems can consume the enriched envelope.

**Finding 4: The compliance and safety rule sets are comprehensive but not exhaustive.** Our current 148 compliance rules and 96 safety rules cover the most common TFL error types identified in PHUSE and FDA guidance documents. However, therapeutic-area-specific rules (e.g., RECIST 1.1 response criteria for oncology, MMRM for CNS trials) and sponsor-specific conventions (e.g., custom footnotes, table shells) are not yet covered. The YAML-based rule configuration allows organizations to extend the rule sets without modifying the scoring harness code.

**Finding 5: Level 2 test cases require fundamentally different evaluation approaches.** The TC-004 (SAP section drafting) and TC-005 (TFL QC review) specifications reveal that Level 2 tasks cannot be evaluated with tolerance-based numerical scoring alone. SAP drafting requires natural language evaluation (coherence, completeness, regulatory compliance), while QC review requires error detection and classification. Our proposed scoring rubric for TC-005 combines auto-scoring (60% — error detection and classification), LLM-as-judge (25% — description quality, SAP reference accuracy), and human expert review (15% — completeness, clinical judgment). This hybrid approach acknowledges that some aspects of TFL quality are inherently subjective and require human assessment.

**Finding 6: Operational efficiency metrics reveal a wide cost-accuracy spectrum.** At current API pricing, the cost per TFL ranges from $0.50 (DeepSeek V4) to $35 (GPT-4o), spanning two orders of magnitude. Our efficiency scoring framework normalizes accuracy against cost and time, enabling organizations to identify the optimal model for their use case. The preliminary finding is that mid-tier models (DeepSeek V4, Claude Sonnet) achieve the best accuracy-per-dollar ratio for Level 1 tasks, while premium models may be justified for Level 2/3 tasks where correctness is more critical.

### 6.3 Limitations

**SAS implementations are reference-only.** All 16 SAS ground truth scripts have been written following standard SAS programming conventions (PROC LIFETEST, PROC FREQ, PROC PHREG, PROC MEANS), but they have not been executed due to the absence of a SAS license. The SAS implementations serve as documentation of expected SAS code structure and can be validated by WG members with SAS access. Cross-language verification currently relies on R↔Python comparison only.

**Level 1 test cases test computation, not code generation.** Our benchmark evaluates whether an agent produces the correct numerical output, not whether it generates correct, maintainable, well-commented code. A model that hardcodes the expected answer (a form of contamination) would score perfectly on our benchmark without demonstrating any programming capability. Mitigation strategies include parametric variants (10-15 variants per TC with different seeds and sample sizes) and dynamic data generation, but sophisticated contamination remains a risk for frontier models with large training corpora.

**Level 2 and Level 3 test cases are not yet implemented.** The detailed specifications for TC-004 (SAP drafting) and TC-005 (TFL QC review) are complete, but the implementation (error injection framework, TFL package generator, LLM-as-judge integration) requires significant additional effort. The 4 Level 3 test cases (regulatory response, dose-finding design, safety/DMC report, CSR sections) remain at the design stage. These higher-level test cases are essential for a comprehensive benchmark but require human expert review for scoring, which limits scalability.

**Human baseline data has not been collected.** The benchmark framework includes provisions for human baseline performance (expert, intermediate, novice programmers), but no systematic data collection has been conducted. Without human baselines, it is difficult to contextualize agent performance: a score of 0.85 on TC-001 is meaningful only in comparison to what a human programmer achieves. WG volunteer recruitment for baseline collection is planned for Phase 2.

**Contamination risk is difficult to quantify.** Level 1 test cases use well-known statistical methods (KM, log-rank, Cox PH) that are extensively documented in textbooks, papers, and online resources. It is likely that frontier models have seen implementations of these methods during training. Our parametric variants mitigate this risk by varying seed, sample size, and hazard ratios, but the underlying methodology remains standard. Level 3 test cases, which involve domain-specific regulatory language, face higher contamination risk.

### 6.4 Comparison with Existing Benchmarks

No existing benchmark directly evaluates TFL programming capability. The closest comparisons are:

| Benchmark | Domain | What It Tests | Gap Our Benchmark Fills |
|---|---|---|---|
| SWE-bench | Software engineering | Bug fixing, feature implementation | No statistical correctness, no regulatory compliance |
| GAIA | General AI assistants | Multi-step reasoning, tool use | No domain-specific evaluation, no multilingual support |
| AgentBench | Agent capabilities | Web browsing, coding, shopping | No clinical trial domain knowledge |
| HealthBench | Medical decisions | Clinical reasoning, diagnosis | No TFL programming, no statistical accuracy |
| BRIDGE | Multilingual clinical NLP | Translation, entity extraction | No statistical programming, no R/SAS/Python |

Our benchmark is unique in combining statistical correctness (tolerance-based numerical scoring), regulatory compliance (ADaM/TCG/CSR rule checking), safety and robustness (N-count consistency, edge case handling), and operational efficiency (cost/accuracy/time tradeoffs) in a single evaluation framework for TFL programming agents.

### 6.5 Future Directions

**Phase 2 (Days 33-40):** Implement Level 2 test cases (TC-004 SAP drafting, TC-005 TFL QC review). Build error injection framework for TC-005. Begin collecting human baseline data from WG volunteers.

**Phase 3 (Days 41-50):** Extend ARS compliance to all 16 Level 1 test cases. Implement Level 3 test cases (TC-007 through TC-010). Begin vendor evaluation pilot: invite Saama, JDIX/Taimei, and other vendors to run the benchmark on their systems.

**Phase 4 (Days 51-60):** Compile results for publication. Submit to JSM 2027 or ASA Biopharmaceutical Section Workshop. Prepare WG presentation with scoring findings and vendor comparison results.

**Long-term:** Develop a public-facing benchmark server that accepts agent outputs and returns scores. Integrate with CDISCARS testing infrastructure. Expand to therapeutic areas beyond oncology (vaccines, ophthalmology, neurology). Support additional languages (Julia, JavaScript/Node.js).

---

*This section draft covers the core discussion points. The final version will incorporate WG feedback, additional literature review, and updated statistics from completed test runs.*
