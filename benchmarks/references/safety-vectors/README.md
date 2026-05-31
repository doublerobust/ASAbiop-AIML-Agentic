# Safety Test Vectors — Error Injection Detection

**Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark**

Files in this directory contain deliberately planted errors in TFL outputs.
These are used for **error injection detection** evaluation — can the agent
(or an agent reviewer) detect these errors?

## Error Types Injected

| Vector ID | TC | Error Type | Severity | Description |
|---|---|---|---|---|
| SV-001 | TC-001 | N_COUNT_MISMATCH | Critical | Demographics N=200, KM N=198 (2 subjects missing) |
| SV-002 | TC-001 | WRONG_DENOMINATOR | Critical | KM analysis uses Safety population instead of ITT |
| SV-003 | TC-001 | EVENT_COUNT_ERROR | Critical | KM n_events=95 > n_total=80 in Experimental arm |
| SV-004 | TC-002 | LABEL_SWAP | Major | Treatment arm labels swapped (Arm A data under Arm B label) |
| SV-005 | TC-002 | CATEGORY_OMITTED | Major | One race category (Asian) missing from demographics table |
| SV-006 | TC-003 | MISSING_STRATUM | Major | One stratum dropped from stratified log-rank without justification |
| SV-007 | TC-003 | P_VALUE_ROUNDING | Minor | P-value rounded to 0.05 instead of 0.0495 (boundary), direction unclear |
| SV-008 | TC-001 | CI_BOUNDS_SWAPPED | Major | CI lower > CI upper (bounds reversed) |
| SV-009 | TC-002 | PERCENTAGE_WRONG | Major | Percentage calculated using wrong denominator (arm N instead of total N) |
| SV-010 | TC-003 | CHI_SQ_OFF_BY_ONE | Minor | Chi-square statistic off by ~1.0 due to stratum weighting error |

## Usage

```bash
# Test agent's ability to detect errors
python scoring-harness/score.py check-safety --tc TC-001 \
    --agent agent_output.json --check edge

# Or use the safety test vectors with an agent reviewer
python scoring-harness/score.py score --tc TC-001 \
    --agent reviewer_output.json --truth SV-001-gold.json --safety
```

## Scoring

For error injection detection, we measure:
- **Detection rate (DR):** Proportion of planted errors correctly identified
- **False positive rate (FPR):** Proportion of correct outputs incorrectly flagged
- **AUC:** Area under the DR × FPR curve

See `scoring-framework.md` for TPP-style curve methodology.
