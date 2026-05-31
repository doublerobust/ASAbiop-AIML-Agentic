# Operational Efficiency Dimension — TFL Benchmark

**Version:** 0.1 (Day 5)
**Date:** 2026-05-29
**Status:** 🟢 Draft
**Dimension:** Operational Efficiency — Language-Specific Cost/Time Benchmarks for TFL Generation

---

## 1. Purpose & Scope

### 1.1 Why Operational Efficiency Matters

AI agents generating TFLs need to be evaluated not just on **correctness** and **compliance**, but also on **efficiency**. In pharmaceutical development, time and cost are critical:

- A submission-ready TFL package (12-15 tables, 4-6 figures, 3-5 listings) can take **2-5 business days** for an experienced programmer
- CRO programming costs range from **$150-$300/hour** depending on language expertise
- Late-stage submission delays cost **$1-8M/day** in lost drug revenue (Tufts CSDD)
- If an AI agent takes 45 minutes to generate a table that costs $50 in API calls vs. 2 minutes at $2, the tradeoff matters

This dimension defines:
1. **Cost metrics** — API token costs, compute costs, licensing costs ($0 for R/Python, proprietary for SAS)
2. **Time metrics** — wall-clock time, thinking/reasoning time, code execution time
3. **Language-specific overhead** — validation cost, review overhead, integration cost
4. **Efficiency scoring** — accuracy × speed × cost composite
5. **Tracking protocol** — how efficiency data is collected, recorded, and reported

### 1.2 Scope

| Metric | TC-001 | TC-002 | TC-003 | TC-004+ | Unit |
|---|---|---|---|---|---|
| API token cost (input) | ✅ | ✅ | ✅ | ⬜ | USD / tokens |
| API token cost (output) | ✅ | ✅ | ✅ | ⬜ | USD / tokens |
| Wall-clock time (agent) | ✅ | ✅ | ✅ | ⬜ | seconds |
| Code execution time | ✅ | ✅ | ✅ | ⬜ | seconds |
| Thinking / reasoning time | ✅ | ✅ | ✅ | ⬜ | seconds |
| Retry count (first-pass success) | ✅ | ✅ | ✅ | ⬜ | count |
| Number of agent steps | ✅ | ✅ | ✅ | ⬜ | count |
| Output size (tokens/bytes) | ✅ | ✅ | ✅ | ⬜ | tokens / bytes |
| Validation time (human review) | ⬜ | ⬜ | ⬜ | ⬜ | minutes |
| SAS licensing cost | ⬜ | ⬜ | ⬜ | ⬜ | $ per run |

---

## 2. Efficiency Metrics Taxonomy

### 2.1 Direct Metrics (Measurable)

| Metric ID | Name | Definition | Unit | Source |
|---|---|---|---|---|
| E-001 | `input_tokens` | Total prompt tokens consumed | tokens | API response metadata |
| E-002 | `output_tokens` | Total completion tokens produced | tokens | API response metadata |
| E-003 | `total_tokens` | input_tokens + output_tokens | tokens | Calculated |
| E-004 | `token_cost` | Cost based on model pricing (input×rate_in + output×rate_out) | USD | Calculated from token counts |
| E-005 | `wall_clock_s` | Total wall-clock time from first API call to final output | seconds | Timer |
| E-006 | `thinking_time_s` | Time spent in reasoning/thinking (if available) | seconds | API metadata |
| E-007 | `code_exec_time_s` | Time for generated code to execute against data | seconds | Timer |
| E-008 | `retry_count` | Number of API retries / correction iterations | count | Log analysis |
| E-009 | `agent_steps` | Number of tool calls / sub-agent invocations | count | Session log |
| E-010 | `first_pass_success` | Whether output passed ground truth on first attempt | boolean | Score result |

### 2.2 Derived Metrics (Computed)

| Metric ID | Name | Formula | Unit | Interpretation |
|---|---|---|---|---|
| E-011 | `efficiency_ratio` | accuracy_score / (wall_clock_s × token_cost + 1) | points/USD/s | Higher = more efficient |
| E-012 | `token_performance` | correctness_score / (total_tokens / 1000) | points/KT | Correctness per 1000 tokens |
| E-013 | `time_performance` | correctness_score / (wall_clock_s / 60) | points/min | Correctness per minute |
| E-014 | `cost_per_run` | token_cost + inference_compute_cost | USD | Total monetary cost |
| E-015 | `cost_per_correct_point` | cost_per_run / accuracy_score | USD/point | Dollars per percentage point of accuracy |

### 2.3 Language-Adjusted Metrics

These metrics account for inherent advantages/disadvantages of each language:

| Metric ID | Name | Rationale | Adjustment |
|---|---|---|---|
| E-016 | `adjusted_time_R` | R has richer pharma ecosystem (Pharmaverse), faster coding | ×0.9 (R is 10% faster baseline) |
| E-017 | `adjusted_time_SAS` | SAS is less well-served by LLMs, smaller training footprint | ×1.3 (SAS is 30% slower baseline) |
| E-018 | `adjusted_time_Python` | Python has largest LLM training footprint | ×0.85 (Python is 15% faster baseline) |
| E-019 | `validation_overhead_R` | R requires package version validation (renv/lockfile) | 2-5 min per package set |
| E-020 | `validation_overhead_SAS` | SAS has built-in validation, no package versioning needed | 1-2 min per run |
| E-021 | `validation_overhead_Python` | Python needs environment reproduction (uv/conda lock) | 3-7 min per environment |

> **Note on language adjustments:** These are starting estimates based on industry literature and empirical testing. The benchmark should refine them as more data accumulates. The adjusted metrics are always reported **alongside** raw metrics, never instead of them.

---

## 3. Language-Specific Cost Benchmarks

### 3.1 LLM API Pricing (May 2026 Reference)

| Model | Input $/1M tokens | Output $/1M tokens | Category | Notes |
|---|---|---|---|---|
| DeepSeek V4 Flash | $0.30 | $0.60 | Budget | Yue's daily driver |
| GPT-4o mini | $0.15 | $0.60 | Budget | Fast, reasonable quality |
| Claude 3.5 Sonnet | $3.00 | $15.00 | Premium | High quality, expensive |
| Claude 3.5 Haiku | $0.80 | $4.00 | Mid-range | Fast, good quality |
| Gemini 2.5 Flash | $0.15 | $0.60 | Budget | Free tier available |
| Gemini 2.5 Pro | $1.25 | $5.00 | Premium | Highest context window |
| Qwen 3.6 MoE (local) | $0.00 | $0.00 | Free* | On Omen RTX 5090 |
| openclaw-qwen (local) | $0.00 | $0.00 | Free* | Local inference, no API cost |
| SAS Viya (cloud) | $0.00 | $0.00 | License-based | ~$15k-50k/user/year |

*\* Local inference costs: electricity only (~$0.10-0.30/hr GPU runtime)*

### 3.2 Estimated Cost per TFL Test Case

| Test Case | R (GPT-4o mini) | SAS (Claude) | Python (DeepSeek V4) | R (local Qwen) |
|---|---|---|---|---|
| **TC-001** (KM median) | $0.02-0.05 | $0.08-0.20 | $0.01-0.03 | $0.00 |
| **TC-002** (Demographics) | $0.03-0.08 | $0.10-0.30 | $0.02-0.05 | $0.00 |
| **TC-003** (Log-rank) | $0.02-0.05 | $0.08-0.20 | $0.01-0.03 | $0.00 |
| **TC-004** (SAP section) | $0.10-0.50 | $0.30-1.00 | $0.05-0.20 | $0.00 |
| **TC-005** (QC review) | $0.15-0.50 | $0.40-1.50 | $0.08-0.25 | $0.00 |
| **TC-007** (Reg response) | $0.50-2.00 | $2.00-5.00 | $0.20-1.00 | $0.00 |
| **TC-009** (Safety report) | $1.00-5.00 | $3.00-10.00 | $0.50-2.00 | $0.00 |
| **TC-010** (CSR section) | $1.00-5.00 | $3.00-10.00 | $0.50-2.00 | $0.00 |

**Key finding:** For Level 1 test cases (TC-001 through TC-003), the **token cost is negligible** (<$0.10 even with premium models). The primary cost driver is human review time.

### 3.3 Time Benchmarks (Expected Ranges)

| Test Case | Human Baseline | LLM Agent (estimated) | Best-Case Agent | Notes |
|---|---|---|---|---|
| **TC-001** | 5 min | 30-90 sec | 10 sec (direct code gen) | Near-instant with preprompt |
| **TC-002** | 10 min | 60-180 sec | 20 sec | Tabular formatting takes more tokens |
| **TC-003** | 5 min | 30-90 sec | 15 sec | Statistical complexity adds thinking time |
| **TC-004** | 120 min | 5-20 min | 2 min | Long form generation |
| **TC-005** | 30 min | 3-10 min | 1 min | Pattern matching task |
| **TC-007** | 180 min | 10-30 min | 5 min | Multi-step reasoning |
| **TC-009** | 480 min | 20-60 min | 10 min | Full safety report |
| **TC-010** | 480 min | 20-60 min | 10 min | CSR sections |

**Key finding:** AI agents are **50-100× faster than humans** for single-step TFL generation. The bottleneck shifts from production to **verification** — which remains human-in-the-loop.

### 3.4 Cost-Efficiency Frontier Concept

Define the Pareto-optimal frontier for the benchmark:

```
cost-efficiency-frontier:
  definition: >
    A submission is Pareto-optimal if no other submission achieves
    both higher accuracy AND lower cost (or faster time).
  plotting:
    x-axis: normalized accuracy score (0-1)
    y-axis: log10(total cost in USD) or log10(wall-clock time in seconds)
    frontier: lower-right = better (high accuracy, low cost/time)
  language_colors:
    R: blue
    SAS: red
    Python: green
  marker_shape:
    budget_model: circle
    premium_model: diamond
    local_inference: square
```

---

## 4. Efficiency Scoring Protocol

### 4.1 Data Collection

Every benchmark run must record the following metadata:

```yaml
efficiency_metadata:
  agent_info:
    agent_name: <string>           # e.g., "Cline"
    model_name: <string>            # e.g., "deepseek-v4-flash"
    model_provider: <string>        # e.g., "OpenRouter" or "local"
    language: <R | SAS | Python>    # Which language agent was prompted for
    agent_version: <string>         # Version/hash of agent tooling
  
  environment:
    host: <string>                  # e.g., "agent-server" or "omen"
    gpu: <string>                   # e.g., "RTX 5090" or "none"
    inference_type: <cloud | local>  # Cloud API or local inference
    date: <YYYY-MM-DD>
  
  cost_breakdown:
    input_tokens: <int>
    output_tokens: <int>
    total_tokens: <int>
    input_token_cost_per_m: <float> # Cost per million input tokens (USD)
    output_token_cost_per_m: <float># Cost per million output tokens (USD)
    total_token_cost: <float>       # Calculated total (USD)
    compute_cost: <float>           # GPU/compute cost if local
    total_cost: <float>             # token_cost + compute_cost (USD)
  
  timing:
    start_timestamp: <ISO8601>
    first_token_timestamp: <ISO8601> # TTFB
    last_output_timestamp: <ISO8601> # End of agent output
    end_timestamp: <ISO8601>         # End of code execution
    wall_clock_seconds: <float>      # end - start
    thinking_seconds: <float>        # if available
    code_exec_seconds: <float>       # code execution duration
    total_seconds: <float>           # wall_clock_seconds + code_exec_seconds
  
  reliability:
    retry_count: <int>              # How many API retries
    agent_steps: <int>              # Tool call count
    first_pass: <boolean>           # Did first attempt pass scoring?
    errors_encountered: [<string>]  # Error types if any
```

### 4.2 Scoring Formula

```python
def compute_efficiency_score(
    accuracy_score: float,      # From scoring harness (0-1)
    total_cost: float,          # Total monetary cost in USD
    total_time_s: float,        # Total wall-clock time in seconds
    language: str,              # "R", "SAS", or "Python"
    retry_count: int = 0,
    human_review_minutes: float = 0
) -> dict:
    """
    Compute operational efficiency scores from raw metrics.
    
    Three component scores + composite:
    1. COST efficiency: (accuracy / max(total_cost, 0.01)) normalized
    2. TIME efficiency: (accuracy / max(total_time_s/60, 0.1)) normalized  
    3. RELIABILITY score: deducts for retries and errors
    4. COMPOSITE: weighted average of the three
    """
    # Avoid division by zero with small floor values
    cost_safe = max(total_cost, 0.001)
    time_safe = max(total_time_s / 60, 0.01)  # Convert to minutes
    
    # Raw efficiency metrics
    cost_efficiency_raw = accuracy_score / cost_safe  # points per dollar
    time_efficiency_raw = accuracy_score / time_safe   # points per minute
    
    # Normalize to 0-1 scale using sigmoid-like transformation
    # Cost: $0.10 target for Level 1 (TCs 1-3), $2 target for Level 2/3
    cost_scale = 2.0  # $2 is reference point
    cost_efficiency = 1 / (1 + (cost_efficiency_raw / cost_scale) ** (-1))
    
    # Time: 2 min target for Level 1, 15 min for Level 2/3
    time_scale = 5.0  # 5 minutes reference
    time_efficiency = 1 / (1 + (time_efficiency_raw / time_scale) ** (-1))
    
    # Reliability penalty
    retry_penalty = min(retry_count * 0.05, 0.25)  # Max 25% penalty
    reliability = max(0.0, 1.0 - retry_penalty if retry_count > 0 else 1.0)
    
    # Composite: weighted equally
    composite = 0.40 * cost_efficiency + 0.35 * time_efficiency + 0.25 * reliability
    
    return {
        "cost_efficiency_score": round(cost_efficiency, 4),
        "cost_efficiency_raw": round(cost_efficiency_raw, 2),
        "total_cost_usd": round(total_cost, 6),
        "time_efficiency_score": round(time_efficiency, 4),
        "time_efficiency_raw": round(time_efficiency_raw, 2),
        "total_time_minutes": round(total_time_s / 60, 2),
        "reliability_score": round(reliability, 4),
        "retry_count": retry_count,
        "composite_efficiency_score": round(composite, 4),
    }
```

### 4.3 Efficiency Weighting in Total Benchmark Score

```yaml
total_benchmark_score:
  formula: |
    Total = 0.50 × Correctness + 0.25 × Compliance + 0.15 × Efficiency + 0.10 × Efficiency_Stability
    
    Where:
      Correctness = numerical_accuracy_score
      Compliance = regulatory_compliance_score
      Efficiency = composite_efficiency_score (from §4.2)
      Efficiency_Stability = 1 - CV(efficiency_scores across 5 runs)
                             (CV = coefficient of variation)
```

Suggested weights for different use cases:

| Use Case | Correctness | Compliance | Efficiency | Stability |
|---|---|---|---|---|
| **General leaderboard** | 0.50 | 0.25 | 0.15 | 0.10 |
| **Cost-sensitive deployment** | 0.40 | 0.20 | 0.30 | 0.10 |
| **Regulatory submission** | 0.35 | 0.50 | 0.10 | 0.05 |
| **Internal development iteration** | 0.40 | 0.15 | 0.30 | 0.15 |

---

## 5. Language-Specific Efficiency Profiles

### 5.1 R — Open-Source Statistical Power

**Strengths:**
- Rich Pharmaverse ecosystem (admiral, Tplyr, rtables)
- Most accurate LLM-generated code for clinical stats (training data abundance)
- CRAN quality gate provides add-on package reliability
- Free, no licensing cost; runs in Docker/GitHub Actions
- Industry standard for survival analysis (survival, survminer)

**Weaknesses:**
- Package versioning overhead (renv lockfile needed for validation)
- GC and memory management less intuitive than Python
- Smaller non-stats ML ecosystem than Python
- Need to validate each package → adds 2-5 min per environment setup

**Estimated LLM Accuracy for Code Generation:**
| Task Type | R Accuracy | SAS Accuracy | Python Accuracy |
|---|---|---|---|
| Survival analysis (KM, log-rank) | ★★★★★ (best) | ★★★☆☆ (good) | ★★★★☆ (very good) |
| Demographics tables | ★★★★☆ (very good) | ★★★★★ (best) | ★★★☆☆ (good) |
| Safety tables | ★★★★☆ (very good) | ★★★★★ (best) | ★★★☆☆ (good) |
| Data transformation (ADaM) | ★★★★★ (best; admiral) | ★★★★☆ (good) | ★★★☆☆ (fair) |
| Bayesian methods | ★★★★★ (best) | ★★★☆☆ (fair) | ★★★★☆ (good) |

### 5.2 SAS — Regulatory Gold Standard

**Strengths:**
- Gold standard for submission-ready TFLs
- Built-in validation (no package version issue)
- PROC LIFETEST, FREQ, MEANS, TABULATE well-documented
- Regulators most familiar with SAS outputs
- Less validation overhead per run (1-2 min)

**Weaknesses:**
- **Proprietary licensing: $15k-50k/user/year** — cannot run in open CI/CD pipeline
- LLMs generate lower-quality SAS code (less training data in open source)
- Fewer public examples for modern methods (tie handling, competing risks)
- Cannot containerize without licensing; Docker = no-go
- SAS Viya cloud offers limited free tiers

**Key LLM gap:** SAS code examples are primarily in closed vendor documentation. LLMs see far fewer SAS examples during training than R/Python code on GitHub.

**Impact on benchmark:**
- SAS-based agent runs must note: `license_available: true|false`
- Cannot run SAS in the benchmark's automated CI/CD pipeline
- SAS evaluation requires either (a) a licensed SAS environment or (b) SAS references as human-reviewed gold standards only

### 5.3 Python — ML Ecosystem Breadth

**Strengths:**
- Largest LLM training data footprint → most accurate code generation
- Free, open-source; runs on any infrastructure
- Strong data engineering/ML ecosystem beyond statistical computing
- Pandas/Numpy ecosystem ubiquitous; lifelines for survival analysis
- Scalable to large datasets (Dask, Spark)

**Weaknesses:**
- Less pharma-specific tooling than R (no Pharmaverse equivalent)
- PyPI lacks CRAN's quality gate → validation is more manual
- lifelines has narrower functionality than survival/survminer
- Less regulatory submission precedent
- Environment space is larger → validation overhead 3-7 min

**Key finding:** Python is strongest for TC-001 and TC-003 (survival-focused) but weakest for TC-002 (demographics tables, where SAS PROC TABULATE and R Tplyr dominate).

### 5.4 Hybrid / Multi-Language Agents

The benchmark should track whether agents use:

1. **Single-language** — pure R, SAS, or Python
2. **Dual-language** — e.g., R for analysis + Python for data prep
3. **All three** — R for modeling, SAS for submission outputs, Python for orchestration
4. **Non-code** — agent provides human-readable answers without running code

For multi-language agents, efficiency tracking separates per-language metrics:

```yaml
hybrid_efficiency:
  languages_used: [R, Python]
  per_language:
    R:
      input_tokens: 450
      output_tokens: 230
      code_exec_time_s: 0.8
    Python:
      input_tokens: 320
      output_tokens: 180
      code_exec_time_s: 1.2
  total_wall_clock_s: 45.0  # Wall clock includes sequential execution
  total_token_cost: 0.0032  # Sum of all API calls
```

---

## 6. Efficiency Tracking in the Scoring Harness

### 6.1 YAML Specification

File: `scoring-harness/efficiency.yaml`

```yaml
# efficiency.yaml — Operational efficiency specifications for TFL benchmark
# Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark

meta:
  version: "0.1"
  updated: "2026-05-29"

# Model pricing reference for cost calculation
model_pricing:
  # Format: <model_id>: {input_per_m: $, output_per_m: $}
  # Will be updated as pricing changes
  deepseek-v4-flash:
    input_per_m: 0.30
    output_per_m: 0.60
    provider: OpenRouter
  gpt-4o-mini:
    input_per_m: 0.15
    output_per_m: 0.60
    provider: OpenAI
  claude-3.5-sonnet:
    input_per_m: 3.00
    output_per_m: 15.00
    provider: Anthropic
  claude-3.5-haiku:
    input_per_m: 0.80
    output_per_m: 4.00
    provider: Anthropic
  gemini-2.5-flash:
    input_per_m: 0.15
    output_per_m: 0.60
    provider: Google
  gemini-2.5-pro:
    input_per_m: 1.25
    output_per_m: 5.00
    provider: Google
  qwen-3.6-moe-local:
    input_per_m: 0.00
    output_per_m: 0.00
    provider: local
    notes: "Electricity ~$0.10-0.30/hr GPU runtime"

# Language adjustment factors (see §2.3)
language_adjustments:
  R:
    time_factor: 0.9      # 10% faster due to Pharmaverse ecosystem
    validation_overhead_min: 3.0  # Average validation prep time
    notes: "Package version lockfile needed (renv)"
  SAS:
    time_factor: 1.3      # 30% slower due to smaller LLM training data
    validation_overhead_min: 1.5  # Built-in validation
    notes: "No package versioning needed; proprietary license required"
  Python:
    time_factor: 0.85     # 15% faster due to largest LLM training data
    validation_overhead_min: 5.0  # Environment reproduction time
    notes: "PyPI quality gate less strict; uv/conda lock recommended"

# Reference targets for normalization
efficiency_targets:
  level_1:
    cost_target_usd: 0.10    # Target cost per Level 1 test case
    time_target_min: 2.0     # Target wall-clock time in minutes
  level_2:
    cost_target_usd: 2.00
    time_target_min: 10.0
  level_3:
    cost_target_usd: 5.00
    time_target_min: 30.0

# Scoring weights for composite efficiency
scoring_weights:
  default:
    cost_efficiency: 0.40
    time_efficiency: 0.35
    reliability: 0.25
  cost_sensitive:
    cost_efficiency: 0.55
    time_efficiency: 0.25
    reliability: 0.20
  time_sensitive:
    cost_efficiency: 0.25
    time_efficiency: 0.55
    reliability: 0.20
```

### 6.2 CLI Integration (`katsu efficiency`)

The scoring harness will gain an `efficiency` subcommand:

```bash
# Compute efficiency from agent run metadata
python score.py efficiency --run run_metadata.json --tc TC-001

# Batch compute from multiple runs
python score.py efficiency-batch --runs runs/*.json --output report.csv

# Compare two agents' efficiency
python score.py efficiency-compare --agent1 agent1.json --agent2 agent2.json
```

Output JSON format:

```json
{
  "test_case_id": "TC-001",
  "agent": {
    "name": "Cline",
    "model": "deepseek-v4-flash",
    "language": "R",
    "inference_type": "cloud"
  },
  "raw_metrics": {
    "input_tokens": 1250,
    "output_tokens": 480,
    "total_tokens": 1730,
    "wall_clock_seconds": 35.2,
    "thinking_seconds": 12.1,
    "code_exec_seconds": 0.8,
    "retry_count": 0,
    "agent_steps": 4,
    "first_pass": true
  },
  "cost": {
    "total_token_cost": 0.000849,
    "compute_cost": 0.0,
    "total_cost_usd": 0.000849
  },
  "efficiency_scores": {
    "cost_efficiency_score": 0.9996,
    "cost_efficiency_raw": 1060.07,
    "time_efficiency_score": 0.9984,
    "time_efficiency_raw": 56.82,
    "total_time_minutes": 0.59,
    "reliability_score": 1.0,
    "retry_count": 0,
    "first_pass": true,
    "composite_efficiency_score": 0.9993
  },
  "accuracy_reference": {
    "ground_truth_score": 1.0,
    "source": "scoring_harness"
  }
}
```

### 6.3 Integrating Efficiency into `evaluate` Command

```python
# Pseudocode for extended evaluate command

def evaluate_with_efficiency(agent_output, ground_truth, tc, efficiency_meta):
    # Step 1: Numerical scoring (existing)
    accuracy = score_tc(agent_output, ground_truth, tc)
    
    # Step 2: Compliance scoring (existing)
    compliance = compute_compliance(agent_output, tc)
    
    # Step 3: Efficiency scoring (new)
    efficiency = compute_efficiency_score(
        accuracy_score=accuracy["score"],
        total_cost=efficiency_meta["total_cost"],
        total_time_s=efficiency_meta["wall_clock_seconds"],
        language=agent_output.get("language", "unknown"),
        retry_count=efficiency_meta.get("retry_count", 0)
    )
    
    # Step 4: Combined score
    total = 0.50 * accuracy["score"] + 0.25 * compliance["score"] + 0.15 * efficiency["composite_efficiency_score"] + 0.10 * efficiency["reliability_score"]
    
    return {
        "accuracy": accuracy,
        "compliance": compliance,
        "efficiency": efficiency,
        "total_score": total
    }
```

---

## 7. Efficiency Reporting Standards

### 7.1 Report Format

Every evaluation report should include:

```
┌─────────────────────────────────────────────────┐
│         Efficiency Report — Agent X              │
├─────────────────────────────────────────────────┤
│ Test Case: TC-001  |  Language: R               │
│ Model: DeepSeek V4 Flash  |  Inference: Cloud    │
├─────────────────────────────────────────────────┤
│ RAW METRICS                                      │
│   Input tokens:    1,250  │  Output: 480         │
│   Wall clock:      35.2s  │  Think: 12.1s         │
│   Code exec:       0.8s   │  Retries: 0           │
│   Agent steps:     4      │  First pass: ✅       │
├─────────────────────────────────────────────────┤
│ COST                                              │
│   Token cost:     $0.0008  │  Compute: $0.00      │
│   Total cost:     $0.0008                          │
├─────────────────────────────────────────────────┤
│ EFFICIENCY SCORES                                 │
│   Cost efficiency:    0.9996  (raw: 1060 pt/$)    │
│   Time efficiency:    0.9984  (raw: 56.8 pt/min)  │
│   Reliability:        1.0000  (no retries)        │
│   Composite:          0.9993                       │
├─────────────────────────────────────────────────┤
│ ADJUSTED (Language: R)                            │
│   Time factor:            ×0.90                   │
│   Validation overhead:    +3.0 min                │
│   Adjusted time:          38.2s                   │
├─────────────────────────────────────────────────┤
│ COMPARISON TO HUMAN BASELINE                      │
│   Human: 5 min, $150/hr → $12.50 labor           │
│   Agent: 0.59 min, $0.0008 → $0.0008             │
│   Speedup: 8.5×                                    │
│   Cost savings: 15,625×                            │
└─────────────────────────────────────────────────┘
```

### 7.2 Cost Transparency Flag

All efficiency reports must include a **cost transparency flag**:

```yaml
cost_transparency:
  infrastructure_included:
    - api_token_cost: true
    - compute_gpu_cost: optional
    - human_review_time: optional
    - software_licensing: optional
    - environment_setup_time: optional
  infrastructure_excluded:
    - agent_development_cost
    - prompt_engineering_time
    - model_training_cost
    - opportunity_cost
```

This ensures fair comparison: a local agent incurs $0 API cost but requires GPU hardware; a cloud API agent costs per-token but requires no hardware investment.

---

## 8. Human vs. Agent Efficiency Comparison

### 8.1 Human Baseline Estimates

| Role | Typical Rate | Source |
|---|---|---|
| Biostatistician (PhD, 5+ yr) | $175-250/hr | Industry average |
| Statistical programmer (SAS) | $120-200/hr | Industry average |
| CRO programming (offshore) | $40-80/hr | CRO rate card |
| CRO programming (onshore) | $120-180/hr | CRO rate card |
| FTE biostatistician (total burden) | $200-300/hr | Fully loaded cost |

### 8.2 Cost Comparison: Agent vs. Human

| Test Case | Human Labor Cost | Agent Cost (API) | Savings Factor |
|---|---|---|---|
| TC-001 (5 min) | $12.50 | $0.0008-$0.05 | 250-15,625× |
| TC-005 (30 min QC) | $75.00 | $0.08-$1.50 | 50-937× |
| TC-007 (180 min reg response) | $450.00 | $0.20-$5.00 | 90-2,250× |
| TC-010 (480 min CSR section) | $1,200.00 | $0.50-$10.00 | 120-2,400× |

### 8.3 Verification Time: The Hidden Cost

The bottleneck is **not generation** but **verification**. A human reviewer must still verify agent-generated TFLs. The benchmark must account for:

```yaml
verification_efficiency:
  concept: >
    Total time = generation_time + verification_time.
    An agent that generates fast but produces hard-to-verify output
    may be less efficient overall than a slower agent with clearer output.
  
  verification_time_estimates:
    TC-001:
      human_from_scratch: 5 min
      human_verify_agent_R: 1-2 min  # R code is readable
      human_verify_agent_SAS: 1-2 min  # SAS PROC code is standard
      human_verify_agent_Python: 2-3 min  # Python needs more inspection
    TC-002:
      human_from_scratch: 10 min
      human_verify_agent_R: 2-4 min  # Tplyr code is declarative
      human_verify_agent_SAS: 2-3 min  # TABULATE is standard
      human_verify_agent_Python: 3-5 min  # Pandas code more nested
    TC-005:
      human_from_scratch: 30 min
      human_verify_agent: 5-10 min  # QC review of QC review
```

> **Insight:** Verification time is likely to be the **dominant cost** in production use, not generation cost. An agent that generates 95%-accurate code quickly may be more cost-effective than one that generates 99%-accurate code slowly, if the 4% difference takes 10 minutes of human review to catch.

---

## 9. Open Questions & Decisions Needed

### 9.1 Open Questions for WG

| # | Question | Suggested Resolution |
|---|---|---|
| 1 | Should the benchmark include a separate **Human Baseline** track? | Yes — recruit 2-3 volunteers to run TC-001 through TC-003, record time/accuracy. |
| 2 | How should we handle SAS licensing cost in the benchmark? | Report SAS cost as `[license_cost_per_run]` = total annual license / (runs_per_year × users). Flag as estimate. |
| 3 | Should efficiency scores be **language-normalized** or **language-agnostic**? | Report both: raw (agnostic) and adjusted (normalized). Let consumers choose. |
| 4 | What is the minimum acceptable accuracy threshold for efficiency scoring? | Only compute efficiency for runs with accuracy ≥ 0.50. Below that, cost savings are irrelevant. |
| 5 | Should verification time be included in total cost? | Yes, but as a separate metric. Report `generation_cost` and `verification_cost` separately. |
| 6 | How do we model the cost of **infrastructure** (GPU, Docker, CI/CD)? | Add optional `infra_cost` field. Default to $0 for API calls, electricity cost for local. |
| 7 | Should multi-turn / iterative agents be penalized or rewarded for more steps? | Treated neutrally: more steps → more tokens → higher cost → lower cost efficiency. But may improve accuracy. |
| 8 | How often should model pricing be updated? | Monthly check; update `efficiency.yaml` pricing table. |

### 9.2 Immediate Decisions Needed

| Decision | Options | Recommendation |
|---|---|---|
| **Default pricing model** for benchmark runs | DeepSeek V4 vs GPT-4o mini vs average | DeepSeek V4 (Yue's daily driver, budget tier) |
| **Efficiency weight** in total score | 10% / 15% / 20% | 15% (as defined in §4.3) |
| **Include local inference** as separate track | Yes / No | Yes — separate "Cloud API" and "Local Inference" leaderboards |
| **Efficiency score floor** | 0% / 25% / 50% of accuracy score | 0.50 floor (don't reward fast wrong answers) |

---

## 10. Next Steps

1. ✅ **Operational efficiency dimension defined** (this document)
2. ✅ **Cost/time metric taxonomy** (§2) with 21 metrics across direct, derived, and adjusted categories
3. ✅ **Language-specific efficiency profiles** (§5) with accuracy estimates per method
4. ✅ **Efficiency scoring formula** (§4.2) with cost/time/reliability components
5. ✅ **Efficiency YAML spec** (§6.1) for machine-readable configuration
6. ⏳ **Implement `katsu efficiency` CLI command** — add to `scoring-harness/score.py`
7. ⏳ **Create `efficiency.yaml`** — machine-readable configuration file
8. ⏳ **WG review:** Accept efficiency weight allocation, model pricing, language adjustments
9. ⏳ **Human baseline study:** Recruit WG volunteers to benchmark human performance
10. ⏳ **Integration test:** Run TC-001 through TC-003 with efficiency tracking

---

## References

1. Appsilon. "R vs Python vs SAS in a Modern SCE: What Pharma Teams Should Choose." 2026.
2. Quanticate. "SAS vs R vs Python in Clinical Trials: What's the Difference?" 2026.
3. WUSS 2025. "Prompt, Program, Submit: Generative AI for Faster Clinical Programming." Paper SAS154-2025.
4. PharmaSUG China 2025. "AutoList: AI-Enhanced End-to-End Automation for Clinical Trial Listings." Paper AA168.
5. PharmaSUG China 2025. "Integrating R Shiny and Python for Dynamic AI Agent Development." Paper AI160.
6. medRxiv. "Automation in Clinical Trial Statistical Programming: A Structured Review." 2025. doi:10.64898/2025.12.24.25342988.
7. McKinsey. "Unlocking peak operational performance in clinical development with AI." 2025.
8. Tufts CSDD. "Cost of Drug Development." 2024 update.
9. R Validation Hub. "Risk-based framework for package assessment." 2023-2025.
10. FDA/EMA. "Joint Principles on AI in Medicine." January 2026.
