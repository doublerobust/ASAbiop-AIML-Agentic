# Edge Case Test Vectors — Safety & Robustness Dimension

**Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark**

Each file in this directory defines a dataset variant designed to trigger
a specific edge case relevant to TFL generation. Used to evaluate whether
AI agents handle clinical trial data irregularities gracefully.

## Edge Case Inventory

| ID | Description | Category | Expected Behavior |
|---|---|---|---|
| EC-001 | Non-estimable median (PFS > 0.5 at all times) | Survival boundary | Flag or return NA/NE |
| EC-002 | All censored (no events in either arm) | Survival boundary | No KM estimate possible; flag |
| EC-003 | Single subject per arm (degenerate) | Small strata | Should error gracefully or warn |
| EC-004 | Zero events in one stratum (stratified analysis) | Zero-event stratum | Exclude stratum gracefully |
| EC-005 | Missing covariate (ECOG missing for some subjects) | Missing data | Flag or use available only |
| EC-006 | Negative survival time (data integrity failure) | Data integrity | Flag as data error |
| EC-007 | Treatment arm with zero patients | Empty arm | Flag as non-comparable |
| EC-008 | Perfect separation (all events in one arm) | Extreme data | Warn about assumption violation |
| EC-009 | Duplicate subject IDs | Data integrity | Flag duplicate or deduplicate |
| EC-010 | Visit window overlap (subject in two time windows) | Visit inconsistency | Flag overlap |
| EC-011 | Stratum with 1 event, 1 subject | Degenerate strata | Handle or exclude with warning |
| EC-012 | Survival time = 0 at baseline | Boundary value | Flag as unusual |
| EC-013 | Inconsistent population flags (ITTFL=Y but excluded) | Data inconsistency | Flag logical inconsistency |
| EC-014 | Censoring = 1 but death date present | Censoring inconsistency | Flag as contradictory |

## File Format

Each edge case is a JSON file with:
- `edge_case_id`: Unique identifier
- `description`: Human-readable description of the edge case
- `category`: Type of edge case
- `sap_context`: Brief SAP pseudocode/context for the TFL
- `input_data`: The ADSL + ADTTE data (truncated for size)
- `expected_output`: Expected agent behavior for scoring
- `tfl_config`: Configuration for which TFL to generate

## Usage

```bash
# Run edge case evaluation
python scoring-harness/score.py check-safety --tc TC-001 \
    --agent agent_output.json --check edge

# Or as part of safety check
python scoring-harness/score.py score --tc TC-001 \
    --agent agent_output.json --truth ground_truth.json --safety --edge
```

## References

- ICH E9 (R1): Estimands and Sensitivity Analysis — defines handling of intercurrent events
- FDA TCG §5.3.2: Population definitions must be consistent
- PHUSE De-identified Data Sharing Standard: N-count consistency requirements
