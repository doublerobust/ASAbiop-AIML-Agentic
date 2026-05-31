# Scoring Framework — Multi-Language Aggregation & TPP Curves

**Version:** 0.1 (Day 7)
**Date:** 2026-05-30
**Status:** 🟢 Complete
**Dimension:** Scoring Framework — Aggregation Methodology for Multi-Dimensional Benchmarking

---

## 1. Purpose & Scope

### 1.1 Why a Scoring Framework Matters

The benchmark generates scores across **multiple dimensions** (numerical correctness, schema compliance, safety/consistency, regulatory compliance, operational efficiency) and across **multiple languages** (R, SAS, Python). A coherent aggregation framework is needed to:

1. Define how per-language scores combine into a single meaningful metric
2. Generate TPP-style (Target Product Profile) curves for interpretable benchmark results
3. Support both **per-language** and **aggregated** reporting
4. Enable cross-agent comparisons with statistical rigor
5. Produce WG-ready publication figures

### 1.2 Scope

| Component | Description | Status |
|---|---|---|
| Multi-language aggregation | How R/SAS/Python scores combine | ✅ Complete |
| Dimension weighting | Weighting scheme for 5 scoring dimensions | ✅ Complete |
| TPP-style curves | Detection rate × false positive rate visualization | ✅ Complete |
| Normalization | z-score vs. min-max vs. percentile normalization | ✅ Complete |
| Reporting format | Structured JSON for tables + markdown summaries | ✅ Complete |
| Uncertainty quantification | Bootstrap CIs for benchmark rankings | ✅ Complete |

---

## 2. Scoring Architecture

### 2.1 Score Hierarchy

```
Aggregate Benchmark Score (ABS)
│
├── Language-Aggregated Per-TC Score (× N test cases)
│   ├── Language-Averaged Score (R / SAS / Python)
│   │   ├── Numerical Correctness Score (0-100)
│   │   ├── Schema Compliance Score (0-100)
│   │   ├── Safety Score (0-100, penalty-based)
│   │   ├── Regulatory Compliance Score (0-100)
│   │   └── Operational Efficiency Score (0-100)
│   │
│   └── Language-Specific Override Flag
│       (e.g., SAS reference-only → weight = 0)
│
└── Cross-Cutting Metrics
    ├── Consistency Score (agreement across languages)
    ├── Stability Score (repeated-run variance)
    └── Edge-Case Resilience Score
```

### 2.2 Dimension Weights (v0.1)

| Dimension | Weight | Rationale |
|---|---|---|
| Numerical Correctness | 0.35 | Primary signal — is the output numerically correct? |
| Schema Compliance | 0.10 | Structural validation — is the output well-formed? |
| Safety & Consistency | 0.25 | Critical — internal consistency prevents regulatory findings |
| Regulatory Compliance | 0.15 | Required for submission use |
| Operational Efficiency | 0.15 | Practical deployment consideration |

**Language weights (when aggregating):**
- R: 0.50 (primary ground truth, pharmaverse ecosystem)
- Python: 0.35 (growing adoption, open source)
- SAS: 0.15 (industry standard but declining, reference-only)

---

## 3. Aggregation Methods

### 3.1 Per-Language Aggregation (within one language)

For a single language $L$ and test case $TC_i$:

$$S_{i,L} = \sum_{d \in D} w_d \cdot s_{i,L,d}$$

where:
- $D$ = {numerical, schema, safety, compliance, efficiency}
- $w_d$ = dimension weight
- $s_{i,L,d}$ = score in dimension $d$ for test case $i$ in language $L$
- All scores normalized to [0, 100]

### 3.2 Multi-Language Aggregation (across languages)

For a test case $TC_i$ across all languages:

$$S_i = \sum_{L \in \{R, Python, SAS\}} w_L \cdot S_{i,L}$$

where $w_L$ are language weights (R: 0.50, Python: 0.35, SAS: 0.15).

### 3.3 Overall Benchmark Score

The aggregate benchmark score (ABS) across all $N$ test cases:

$$\text{ABS} = \frac{1}{N} \sum_{i=1}^{N} S_i$$

### 3.4 Handling Missing Languages

If an agent only produces output in one language (e.g., R-only):

- **Method A** (recommended): Report per-language score only. No cross-language aggregation.
- **Method B** (cross-language extrapolation): Apply language weight renormalization.
- **Method C** (explicit): Flag as "R-only" — no SAS/Python comparison possible.

For ABL (Agentic Benchmark Launch), Method A is used with optional Method B for WG reporting.

---

## 4. TPP-Style Curves

### 4.1 Motivation

Following the WG discussion (Parsa 2026, NEJM AI), we adopt a **Target Product Profile (TPP)** framework for evaluating agent performance. Instead of a single composite score, we plot **detection rate** (sensitivity) against **false positive rate** (1 − specificity).

This is analogous to:
- **ROC curves** in diagnostic testing
- **Operating characteristic curves** in acceptance sampling
- **Detection/false-positive tradeoff** in AI evaluation (Rodman 2025)

### 4.2 Definitions

| Metric | Definition | Range |
|---|---|---|
| **Detection Rate (DR)** | Proportion of seeded errors correctly flagged by agent | [0, 1] |
| **False Positive Rate (FPR)** | Proportion of correct outputs incorrectly flagged as erroneous | [0, 1] |
| **Accuracy** | Overall proportion correct | [0, 1] |
| **F1 Score** | Harmonic mean of precision and recall | [0, 1] |
| **Matthews Correlation** | Balanced measure for imbalanced error injection | [-1, 1] |

### 4.3 Operating Points

Three clinically meaningful operating points:

| Operating Point | DR Target | FPR Tolerance | Use Case |
|---|---|---|---|
| **Conservative (QC)** | ≥ 0.95 | ≤ 0.01 | Submission QC — must not miss errors |
| **Balanced (Review)** | ≥ 0.90 | ≤ 0.05 | Routine TFL review |
| **Efficient (Scout)** | ≥ 0.80 | ≤ 0.10 | Early draft checking |

### 4.4 Curve Generation

For each agent and test case:

1. Vary the detection threshold from 0 to 1 in 0.01 steps
2. At each threshold, compute DR and FPR
3. Plot DR (y-axis) vs. FPR (x-axis)
4. Compute AUC (area under curve)
5. Mark the 3 operating points (Conservative, Balanced, Efficient)

**Visualization format:** Mermaid XY chart (for README) + PDF (for paper).

---

## 5. Normalization Strategies

### 5.1 Score Normalization

| Method | Formula | When to Use |
|---|---|---|
| **Min-Max** | $x' = (x - x_{min}) / (x_{max} - x_{min})$ | Fixed range [0,1], easy to interpret |
| **z-Score** | $z = (x - \mu) / \sigma$ | Comparing across different agents |
| **Percentile** | Rank-based | Non-parametric comparison |
| **Sigmoid** | $\sigma(x) = 1 / (1 + e^{-k(x - x_0)})$ | Smooth normalization, handles extremes |

### 5.2 Recommended Default

For v0.1, use **min-max normalization** per dimension with fixed bounds:
- Numerical correctness: [0, 100]
- Schema compliance: {0, 100} (binary pass/fail per schema field)
- Safety: [-100, 100] (penalty-based, can be negative for critical failures)
- Regulatory compliance: [0, 100]
- Operational efficiency: [0, 150] (can exceed 100 for fast/cheap agents)

---

## 6. Uncertainty Quantification

### 6.1 Bootstrap Confidence Intervals

To compare two agents' scores:

1. Draw $B = 1000$ bootstrap samples of test cases (with replacement)
2. Compute ABS for each bootstrap sample
3. Report median and 95% CI (2.5th and 97.5th percentiles)
4. Two agents differ meaningfully if their 95% CIs don't overlap

### 6.2 Minimum Test Cases for Statistical Power

| Effect Size (Δ ABS) | Cases Needed (80% power, α = 0.05) |
|---|---|
| 10 points | 8 |
| 5 points | 25 |
| 3 points | 65 |
| 1 point | 520 |

With a target of 20-50 test cases, the benchmark can detect Δ ≥ 5 points.

---

## 7. Reporting Format

### 7.1 Structured JSON Output

```json
{
  "benchmark_version": "0.1",
  "agent": {
    "name": "AgentName-v1",
    "model": "deepseek/deepseek-v4-flash",
    "language": "R"
  },
  "overall": {
    "abs": 82.3,
    "abs_ci_95": [78.1, 86.0],
    "n_test_cases": 10,
    "n_languages": 1
  },
  "dimensions": {
    "numerical_correctness": {"score": 88.5, "weight": 0.35},
    "schema_compliance": {"score": 95.0, "weight": 0.10},
    "safety_consistency": {"score": 75.0, "weight": 0.25},
    "regulatory_compliance": {"score": 80.0, "weight": 0.15},
    "operational_efficiency": {"score": 90.0, "weight": 0.15}
  },
  "per_test_case": {
    "TC-001": {"score": 85.0, "dimensions": {...}},
    "TC-002": {"score": 90.0, "dimensions": {...}},
    "TC-003": {"score": 72.0, "dimensions": {...}}
  },
  "tpp_curve": {
    "auc": 0.87,
    "operating_points": {
      "conservative": {"dr": 0.95, "fpr": 0.01},
      "balanced": {"dr": 0.90, "fpr": 0.05},
      "efficient": {"dr": 0.80, "fpr": 0.10}
    }
  },
  "bootstrap": {
    "n_replicates": 1000,
    "median": 82.3,
    "ci_95": [78.1, 86.0],
    "ci_90": [79.2, 85.1]
  }
}
```

### 7.2 Markdown Summary Table

```markdown
| Agent | ABS | Num | Schema | Safety | Reg | Eff | AUC |
|---|---|---|---|---|---|---|---|
| AgentName-v1 | 82.3 | 88.5 | 95.0 | 75.0 | 80.0 | 90.0 | 0.87 |
| Baseline (human) | 95.0 | 98.0 | 100.0 | 90.0 | 95.0 | 40.0 | 0.95 |
```

---

## 8. Implementation Plan

### 8.1 score.py Extensions

| Function | Description | Priority |
|---|---|---|
| `compute_per_language_score()` | Aggregate dimensions for one language | P0 |
| `compute_aggregate_score()` | Multi-language weighted aggregation | P0 |
| `compute_tpp_curve()` | Detection rate × FPR curve | P1 |
| `bootstrap_ci()` | Bootstrap confidence intervals | P1 |
| `generate_report()` | JSON + markdown report output | P0 |

### 8.2 CLI Extensions

```bash
# Full evaluation with scoring framework
python score.py evaluate --tc TC-001 --agent agent.json --truth truth.json \
    --language R --compliance --safety

# Multi-language aggregate score
python score.py aggregate --tc TC-001 \
    --agent-r agent_r.json --agent-py agent_python.json

# TPP curve (requires error-injection runs)
python score.py tpp --agent agent.json --injection-dir ./injections/

# Report generation
python score.py report --results results.json --format markdown
```

### 8.3 Integration with Progress Log

| Day | Dimension | Integration Point |
|---|---|---|
| Day 1-2 | Foundation + Test Cases | YAML specs |
| Day 3 | Scoring Harness | `score.py` |
| Day 4 | Compliance | `compliance.py` |
| Day 5 | Safety | `safety.py` |
| Day 6 | Efficiency | `efficiency.yaml` |
| **Day 7** | **Scoring Framework** | **`score.py:aggregate`, `score.py:tpp`** |

---

## 9. Next Steps

1. **Implement score.py aggregation functions** — `compute_per_language_score()`, `compute_aggregate_score()`, `compute_tpp_curve()`, `bootstrap_ci()`
2. **Add CLI subcommands** — `aggregate`, `tpp`, `report`
3. **Write integration tests** — end-to-end with all 3 ground truth outputs
4. **WG review** — validate dimension weights and operating points
5. **Pilot run** — evaluate 2-3 agents against TC-001 through TC-003
