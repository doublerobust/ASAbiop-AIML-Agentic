# Scoring Harness — TFL Benchmark (ASA Biopharm AI/ML WG)

Automated scoring harness for evaluating AI agent TFL generation against
cross-validated ground truth in R, SAS, and Python.

## Architecture

```
scoring-harness/
├── score.py            ← Main CLI: score / verify / validate / compliance /
│                          check-safety / evaluate / efficiency (numerical
│                          comparison + JSON Schema validation are built in)
├── compliance.py       ← Regulatory compliance checks (ADaM, TCG, CSR)
├── compliance.yaml     ← Per-TC compliance rule definitions
├── safety.py           ← Safety & robustness checks (N-counts, denominators,
│                          cross-TFL agreement, edge cases, stability)
├── safety.yaml         ← Safety rule definitions
├── efficiency.yaml     ← Operational-efficiency scoring configuration
├── tolerances.yaml     ← Machine-readable numerical tolerance specs
├── requirements.txt    ← Python dependencies
└── README.md           ← This file
```

> NOTE (QC review): numerical comparison and schema validation are implemented
> directly inside `score.py` (functions `compare_numeric`, `compare_count`,
> `load_schema`/`validate`). There are no separate `compare.py` or
> `schema_validator.py` modules; earlier versions of this README listed files
> that never existed.

## Commands

### score — Numerical Scoring (with optional compliance)

```bash
# Score an agent's TC-001 output against ground truth (numerical only)
python score.py score \
  --tc TC-001 \
  --agent agent_results.json \
  --truth references/ground-truth/output_R.json

# Score with compliance checks
python score.py score \
  --tc TC-001 \
  --agent agent_results.json \
  --truth references/ground-truth/output_R.json \
  --compliance          # Include ADaM variable mapping checks
  --tcg-check           # Include FDA Study Data TCG checklist
  --csr-format          # Include ICH E3 CSR appendix formatting
```

### compliance — Standalone Compliance Check

```bash
python score.py compliance \
  --tc TC-001 \
  --agent agent_results.json \
  --check all           # Choices: adam, tcg, csr, all
```

### evaluate — Full Evaluation (Score + Schema + Compliance)

```bash
python score.py evaluate \
  --tc TC-001 \
  --agent agent_results.json \
  --truth references/ground-truth/output_R.json
```

### verify — Cross-Language Verification

**IMPORTANT:** verification is only meaningful when every language was run on the
**same shared dataset**. Generate the canonical dataset once (R
`write_shared_data()` → `adtte_<seed>.csv`) and run each TC script with
`--data <shared.csv>`. SAS is **optional** (no license in CI; TC-011..014 have
no SAS reference).

```bash
# 1) create shared data and per-language outputs
Rscript ../references/ground-truth/R/tc-001-km-median.R \
  --data adtte_42.csv --arm 1 --output r1.json
python3 ../references/ground-truth/Python/tc_001_km_median.py \
  --data adtte_42.csv --arm 1 --output p1.json

# 2) verify (flags are --r / --python / optional --sas)
python score.py verify \
  --tc TC-001 \
  --r r1.json \
  --python p1.json \
  # --sas sas1.json   # optional
```

### validate — Schema Validation

```bash
python score.py validate \
  --tc TC-001 \
  --input agent_results.json
```

## Compliance Checks

Three dimensions of regulatory compliance are evaluated:

| Dimension | Description | Config File |
|---|---|---|
| **ADaM Mapping** | Verifies required variables present, population flag correct (ITTFL/SAFFL=Y), treatment variable (TRT01PN), censoring (CNSR 0/1), strata variables | `compliance.yaml` → `adam_mapping` |
| **FDA TCG Checklist** | Validates population filter, treatment variable, event/censoring handling, analysis time variable, statistical method doc, software version doc | `compliance.yaml` → `tcg_rules` |
| **ICH E3 CSR Formatting** | Checks table numbering, title includes population/endpoint, footnotes, p-value type, CI method | `compliance.yaml` → `csr_rules` |

Each check returns `{passed: [rule_ids], failed: [rule_ids], score: float}`.
The composite compliance score is weighted: ADaM 40%, TCG 35%, CSR 25%.

## Scoring Components

| Component | Weight | Description |
|---|---|---|
| Exact match | 0-1.0 | Integer counts, categorical labels must match exactly |
| Numerical tolerance | 0-1.0 | Continuous values checked against per-TC tolerance spec |
| Functional equivalence | 0-1.0 | Method choice and specification correctness |

## Tolerance Specification

Defined in `tolerances.yaml` per test case and field.
