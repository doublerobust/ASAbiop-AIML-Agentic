# Scoring Harness — TFL Benchmark (ASA Biopharm AI/ML WG)

Automated scoring harness for evaluating AI agent TFL generation against
cross-validated ground truth in R, SAS, and Python.

## Architecture

```
scoring-harness/
├── score.py               ← Main scoring entry point
├── compare.py             ← Numerical comparison with tolerance
├── schema_validator.py    ← JSON Schema validation
├── tolerances.yaml        ← Machine-readable tolerance specs
├── requirements.txt       ← Python dependencies
└── README.md              ← This file
```

## Usage

```bash
# Score an agent's TC-001 output against ground truth
python score.py score \
  --tc TC-001 \
  --agent-output agent_results.json \
  --ground-truth references/ground-truth/output_R.json

# Run full verification across all three languages
python score.py verify \
  --tc TC-001 \
  --r-output references/ground-truth/R/tc-001-output.json \
  --sas-output references/ground-truth/SAS/tc-001-output.json \
  --python-output references/ground-truth/Python/tc-001-output.json

# Validate an output against its schema
python score.py validate \
  --tc TC-001 \
  --input agent_results.json
```

## Scoring Components

| Component | Weight | Description |
|---|---|---|
| Exact match | 0-1.0 | Integer counts, categorical labels must match exactly |
| Numerical tolerance | 0-1.0 | Continuous values checked against per-TC tolerance spec |
| Functional equivalence | 0-1.0 | Method choice and specification correctness |

## Tolerance Specification

Defined in `tolerances.yaml` per test case and field.
