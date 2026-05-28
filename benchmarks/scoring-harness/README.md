# Scoring Harness — TFL Benchmark (ASA Biopharm AI/ML WG)

Automated scoring harness for evaluating AI agent TFL generation against
cross-validated ground truth in R, SAS, and Python.

## Architecture

```
scoring-harness/
├── score.py               ← Main scoring, compliance & evaluation entry point
├── compliance.py           ← Regulatory compliance checks (ADaM, TCG, CSR)
├── compliance.yaml         ← Per-TC compliance rule definitions
├── compare.py              ← Numerical comparison with tolerance
├── schema_validator.py     ← JSON Schema validation
├── tolerances.yaml         ← Machine-readable tolerance specs
├── requirements.txt        ← Python dependencies
└── README.md               ← This file
```

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

```bash
python score.py verify \
  --tc TC-001 \
  --r-output references/ground-truth/R/tc-001-output.json \
  --sas-output references/ground-truth/SAS/tc-001-output.json \
  --python-output references/ground-truth/Python/tc-001-output.json
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
