# Frontier Model Evaluation Runner — Project Handoff

**Date:** 2026-07-28
**Author:** Hermes (for Yue Shentu → Codex CLI)

## What We Need

Build an **evaluation runner** that feeds the ASA Biopharm Agentic AI Benchmark test cases to frontier LLMs (DeepSeek V4, Claude, GPT-4o, etc.) and collects structured scores. The runner orchestrates: prompt construction → API call → output parsing → scoring → results aggregation.

## What Already Exists (Don't Rebuild)

The repo at `benchmarks/` contains everything except the runner:

### Scoring Infrastructure
- **`scoring-harness/score.py`** — Main CLI with commands:
  - `python score.py score --tc TC-001 --agent output.json --truth ground_truth.json` — numerical comparison
  - `python score.py evaluate --tc TC-001 --agent output.json --truth ground_truth.json --compliance --safety` — full eval
  - `python score.py efficiency --tc TC-001 --accuracy 0.95 --cost 0.02 --time 120` — efficiency scoring
  - `python score.py validate --tc TC-001 --input output.json` — schema validation
- **`scoring-harness/score.py`** has a `compute_efficiency_score()` function that takes accuracy, cost, wall_time, language, retries, tokens_in, tokens_out, tc_level
- **`scoring-harness/compliance.py`** + `compliance.yaml` — 242 regulatory compliance rules
- **`scoring-harness/safety.py`** + `safety.yaml` — safety/robustness checks
- **`scoring-harness/efficiency.yaml`** — human baseline times, model pricing, weight profiles

### Test Case Definitions (The "Prompts")
Each test case in **`test-case-design.md`** (2004 lines) contains:
- Full task specification in domain language (tool-agent specification per TCD-P4)
- Acceptance criteria and output format
- Contamination-resistant parametrizable params
- Example ground truth in R/SAS/Python for human reference

The TCs span across `test-case-design.md`, `tc-004-level2-spec.md`, `tc-005-level2-spec.md`, `tc-006-level2-spec.md`, `tc-021-023-candidates.md`, `tc-026-027-candidates.md`, `tc-028-spec.md`, `tc-029-035-candidates.md`.

### Ground Truth & Cross-Language Verification
- **`references/ground-truth/R/`** — R reference implementations (35 TC scripts)
- **`references/ground-truth/Python/`** — Python reference implementations (35 TC scripts)
- **`references/ground-truth/SAS/`** — SAS reference implementations (27+ TC scripts)
- **`references/output-schemas/`** — JSON Schema definitions for every TC's expected output format
- **`cross-lang-results/r-output/`** and **`python-output/`** — pre-computed ground truth JSONs
- All Level 1 TCs verified at **1.0000 cross-language agreement** (R↔Python)
- Cross-language verification script: `references/verification/cross-language-compare.R`

### Test Case Inventory (35 Total)
| Level | Count | Scope | Scoring |
|-------|-------|-------|---------|
| Level 1 | 27 | Single-step TFL generation | Fully auto-scored (numerical + schema) |
| Level 2 | 4 | Multi-step with interpretation | Partial auto + rubric |
| Level 3 | 4 | Complex regulatory scenarios | Expert review + auto-scored components |

All 35 TCs are listed in `test-case-design.md` with IDs TC-001 through TC-035.

### Level 3 Reference Materials
- `references/ground-truth/reference-memos/tc-007-reference-memo.md` — Regulatory response
- `references/ground-truth/reference-memos/tc-008-reference-design.md` — Dose-finding protocol
- `references/ground-truth/reference-memos/tc-009-reference-dmc-report.md` — DMC safety report
- `references/ground-truth/reference-memos/tc-010-reference-csr.md` — CSR statistical sections

### Domain Knowledge (Critical — Read First)
- **ITT-only for Phase III oncology:** Per-protocol population analyses are NOT performed in Phase III oncology studies. ITT is the sole primary analysis population for superiority claims per FDA/EMA standards.
- For dose-finding (Phase I), ITT/PP distinction doesn't apply — all treated patients are the analysis set.

## What the Eval Runner Must Do

### Architecture
```
eval-runner/
├── run_eval.py              ← Main entry point
├── config.yaml              ← Model configs, API keys, TC selection
├── prompt_builder.py        ← Constructs task prompts from TC definitions
├── model_clients.py         ← API wrappers (DeepSeek, Anthropic, OpenAI)
├── output_parser.py         ← Parses model responses into structured JSON
├── results_aggregator.py    ← Collects scores, produces leaderboard
├── run-all.sh               ← Convenience script to run full eval suite
└── sample-output/           ← Directory for eval results (gitignored)
```

### Required Capabilities

#### 1. TC Selection & Prompt Construction
- Read TC definitions from `test-case-design.md` — extract task description, output spec, acceptance criteria
- Support running a subset: `--tcs TC-001,TC-002,TC-003` or `--level 1` or `--all`
- Support parametrizable variants (contamination resistance): `--variant 3` generates different sample sizes/effect sizes
- Construct a self-contained prompt per TC with:
  - Task description (domain language, tool-agnostic)
  - Output format specification (JSON schema or structured format)
  - Dataset description (what ADaM datasets to use, key variables)
  - Any relevant background context

#### 2. Model API Clients
Support at minimum three frontier models:
- **DeepSeek V4 Flash** — OpenRouter (`openrouter/deepseek/deepseek-v4-flash` or direct API)
- **Claude Sonnet 5** — Anthropic API (`claude-sonnet-5`, `$ANTHROPIC_API_KEY`)
- **GPT-4o** — OpenAI API (`gpt-4o`, `$OPENAI_API_KEY`)

Each client must:
- Accept a prompt string and return structured output
- Track: wall-clock time, tokens in/out, cost, retries, errors
- Handle rate limits and API errors gracefully (exponential backoff)
- Support configurable model parameters (temperature=0 for reproducibility)

#### 3. Output Parsing
- Models return text; the parser extracts structured JSON matching the TC's output schema
- Handle common failure modes: markdown-wrapped JSON, inline code fences, partial outputs
- Validate parsed output against `references/output-schemas/tc-XXX-output-schema.json`
- Return parse-failure details if schema validation fails

#### 4. Scoring Pipeline
For each (model, TC, variant) combination:
1. **Parse output** → structured JSON
2. **Schema validate** against TC's output schema → schema score
3. **Numerical scoring** via `score.py score --tc ... --agent ... --truth ...` → numerical score
4. **Safety checks** via `score.py evaluate --tc ... --agent ... --truth ... --safety` → safety score
5. **Compliance checks** via `score.py evaluate --tc ... --agent ... --truth ... --compliance` → compliance score
6. **Efficiency** via `score.py efficiency --tc ... --accuracy ... --cost ... --time ...` → efficiency score
7. **Aggregate** per the scoring framework weights from `scoring-framework.md`

#### 5. Results Output
For each eval run, produce:
- **`results/{model}-{tc}-{variant}.json`** — Per-run detailed results with all sub-scores
- **`results/summary.json`** — Aggregated results across all TCs for all models
- **Markdown summary** printed to stdout (for cron job delivery):
```markdown
## Frontier Model Eval — 2026-07-28

| Model | TC-001 | TC-002 | ... | Avg Score | Avg Cost | Avg Time |
|-------|--------|--------|-----|-----------|----------|----------|
| DeepSeek V4 | 0.95 | 0.92 | ... | 0.93 | $0.02 | 45s |
| Claude S5 | 0.98 | 0.97 | ... | 0.97 | $0.15 | 60s |
| GPT-4o | 0.97 | 0.96 | ... | 0.96 | $0.12 | 55s |
```

#### 6. Error Handling
- Continue on individual TC failures (don't abort the whole batch)
- Log parse failures and API errors per TC
- Retry up to 3 times on transient API errors (rate limit, 5xx)
- Support resume: if a run is interrupted, skip already-completed (model, TC, variant) combos

## Data Dependencies

### Ground Truth Paths
- R ground truth: `references/ground-truth/R/tc-XXX-*.R`
- Python ground truth: `references/ground-truth/Python/tc_XXX_*.py`
- Pre-computed JSON outputs: `cross-lang-results/r-output/TC-XXX.json` and `python-output/TC-XXX.json`
- Output schemas: `references/output-schemas/tc-XXX-output-schema.json`
- Common data generation: `references/ground-truth/R/common/data-generation.R` and `Python/common/data_generation.py`

### Scoring Harness
- `scoring-harness/score.py` — main scoring CLI
- Run from `benchmarks/` directory (paths are relative)
- Dependencies in `scoring-harness/requirements.txt`

### Baseline Efficiencies
- `scoring-harness/efficiency.yaml` — human baseline times, model pricing, weight profiles
- `scoring-framework.md` — aggregation methodology, dimension weights

## Acceptance Criteria

The runner passes when:

1. ✅ Running `python run_eval.py --model deepseek-v4-flash --tcs TC-001,TC-002 --variant 1` produces scored JSON outputs for both TCs under `results/`
2. ✅ Scores match manual invocation of `score.py score` with the same inputs
3. ✅ Schema validation is integrated (not a separate step)
4. ✅ Efficiency scores are computed from wall-clock time and token counts
5. ✅ A markdown summary is printed to stdout after completion
6. ✅ API errors on one TC don't block other TCs
7. ✅ Running with `--model all --level 1` runs all 27 Level 1 TCs across all configured models

## Future Enhancements (Out of Scope — Mark with `TODO:` Comments)
- LLM-as-judge integration for TC-004 (SAP drafting) — currently requires human review
- SAS ground truth scoring (R/Python only for now)
- TPP-style curves from results data
- Multi-run stability assessment (requires multiple eval runs at different seeds)
- CIS (Contamination Impact Score) computation

## Quick Start for Codex
```bash
cd benchmarks/
pip install -r scoring-harness/requirements.txt

# Explore structure
ls references/ground-truth/Python/
ls references/output-schemas/
cat test-case-design.md | head -200

# Test scoring manually
python scoring-harness/score.py score --tc TC-001 \
  --agent cross-lang-results/python-output/TC-001.json \
  --truth cross-lang-results/r-output/TC-001.json
```

## Contact
- **Repo owner:** Yue Shentu (doublerobust)
- **Questions about domain logic:** Check `progress-log.md` (57 days of development history)
- **Scoring questions:** README at `scoring-harness/README.md`
