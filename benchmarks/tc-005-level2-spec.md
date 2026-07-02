# TC-005 Detailed Specification — TFL Package QC Review (Level 2)

**Date:** 2026-07-02 (Day 32)
**Status:** Draft for WG Review
**Level:** 2 (Multi-step, moderately ambiguous, partial auto-scoring)

---

## Overview

TC-005 evaluates an AI agent's ability to perform a quality control (QC) review of a pre-generated TFL (Tables, Figures, Listings) package. The agent must identify, classify, and report discrepancies between the TFL outputs and the SAP specification.

Unlike Level 1 test cases that produce numerical outputs, TC-005 produces a structured QC report that tests the agent's ability to:
1. Parse and understand TFL outputs in structured format
2. Cross-reference TFL content against SAP requirements
3. Detect planted errors across multiple TFL types
4. Classify errors by severity using the A/B/C taxonomy
5. Recommend corrections

---

## Design Parameters

### TFL Package Contents

| # | TFL Type | Title | Domain | Planted Errors |
|---|---|---|---|---|
| 1 | Table | Baseline Demographics | ADSL | 2 (N mismatch, missing category) |
| 2 | Table | Efficacy Summary (ORR) | ADRS | 1 (wrong denominator) |
| 3 | Table | Adverse Event Summary | ADAE | 3 (SOC sort, PT spelling, n/N error) |
| 4 | Figure | KM PFS Curve | ADTTE | 1 (wrong censoring indicator) |
| 5 | Figure | Forest Plot HR | ADTTE | 0 (clean — no errors) |
| 6 | Listing | Protocol Deviations | ADPD | 1 (wrong population filter) |

**Total planted errors:** 8
**Clean TFLs:** 1 (Figure 2 — Forest Plot)

### Error Taxonomy (Class A/B/C)

| Class | Severity | Definition | Example |
|---|---|---|---|
| A | Critical | Errors that could lead to regulatory rejection or patient harm | Wrong primary endpoint p-value, wrong population used |
| B | Major | Errors that require correction before submission but don't affect conclusions | Incorrect footnotes, wrong sorting, missing categories |
| C | Minor | Cosmetic or stylistic issues that don't affect data integrity | Formatting inconsistencies, title capitalization |

### Planted Error Catalog (Ground Truth)

| Error ID | TFL | Location | Type | Class | Description | Correction |
|---|---|---|---|---|---|---|
| E-001 | Table 1 | Column "Experimental", N row | N-count | B | N=98 but should be N=100 (2 subjects lost) | Re-run with ITTFL="Y" |
| E-002 | Table 1 | RACE category | Missing | B | "Asian" category missing from race breakdown | Check ADSL RACE derivation |
| E-003 | Table 2 | ORR denominator | Value | A | Denominator=85 (evaluable) instead of 100 (ITT) | Use ITT population denominator |
| E-004 | Table 3 | SOC column | Sorting | C | SOC sorted alphabetically instead of by frequency | Re-sort by descending AE count |
| E-005 | Table 3 | PT "Dyspnoea" | Typo | C | "Dyspnoea" misspelled as "Dysponea" | Correct spelling |
| E-006 | Table 3 | n/N for "Nausea" | Value | B | Shows 15/85 instead of 15/100 | Correct denominator to safety N |
| E-007 | Figure 1 | KM curve | Method | A | Uses 1-CNSR instead of event indicator (CNSR=0 → event) | Fix event indicator: event = (1-CNSR) |
| E-008 | Listing 1 | PD listing | Population | A | Uses SAFETY population instead of ITT | Re-run with ITTFL="Y" |

**Error distribution by class:**
- Class A (Critical): 3 errors (E-003, E-007, E-008)
- Class B (Major): 3 errors (E-001, E-002, E-006)
- Class C (Minor): 2 errors (E-004, E-005)

### Variant Parameters (10 variants)

| Parameter | Options | Impact |
|---|---|---|
| Error locations | Shuffle which TFLs contain which errors | Tests robustness to error positioning |
| Error types | Swap N-count errors with value errors | Tests error classification ability |
| N errors | 6, 8, 10 total planted errors | Tests detection sensitivity |
| Dataset variant | Different seeds for underlying data | Tests whether agent detects data vs. presentation errors |
| SAP specificity | Explicit vs. implicit SAP requirements | Tests agent's ability to infer requirements |

---

## Input Specification

### Input Format (YAML)

```yaml
task: "QC Review of TFL Package"
sap_reference: "SAP Section 14.1-14.3"
tfl_package:
  - id: "table-001"
    title: "Table 14.1: Baseline Demographics and Clinical Characteristics"
    format: "json"
    path: "tfl_package/table_001.json"
  - id: "table-002"
    title: "Table 14.2: Objective Response Rate"
    format: "json"
    path: "tfl_package/table_002.json"
  - id: "table-003"
    title: "Table 14.3: Adverse Events (≥5% in Either Arm)"
    format: "json"
    path: "tfl_package/table_003.json"
  - id: "figure-001"
    title: "Figure 14.1: Kaplan-Meier Plot of Progression-Free Survival"
    format: "json"
    path: "tfl_package/figure_001.json"
  - id: "figure-002"
    title: "Figure 14.2: Forest Plot of Subgroup Analysis"
    format: "json"
    path: "tfl_package/figure_002.json"
  - id: "listing-001"
    title: "Listing 14.1: Protocol Deviations"
    format: "json"
    path: "tfl_package/listing_001.json"
error_taxonomy:
  class_A: "Critical — regulatory rejection risk"
  class_B: "Major — correction required before submission"
  class_C: "Minor — cosmetic/stylistic"
sap_context:
  primary_endpoint: "PFS"
  primary_analysis: "Stratified log-rank (SEX, ECOG)"
  efficacy_population: "ITT (ITTFL='Y')"
  safety_population: "SAFETY (SAFFL='Y')"
  secondary_endpoints: ["ORR", "OS"]
  multiplicity: "Hochberg for secondary endpoints"
```

---

## Expected Output Specification

### Output Format (JSON)

```json
{
  "test_case_id": "TC-005",
  "variant_id": "v1",
  "language": "agent",
  "review_summary": {
    "total_tfls_reviewed": 6,
    "total_errors_found": 8,
    "class_A_count": 3,
    "class_B_count": 3,
    "class_C_count": 2,
    "clean_tfls": ["figure-002"]
  },
  "discrepancies": [
    {
      "error_id": "E-001",
      "tfl_id": "table-001",
      "location": "Column 'Experimental', N row",
      "type": "N-count",
      "class": "B",
      "description": "N=98 reported but ITT population should be N=100",
      "sap_reference": "Section 14.1.1: ITT population defined as all randomized",
      "recommended_correction": "Re-run demographics with ITTFL='Y'",
      "confidence": 0.95
    }
  ],
  "cross_tfl_checks": [
    {
      "check": "N-count consistency",
      "tfls": ["table-001", "table-002", "table-003"],
      "result": "inconsistent",
      "details": "Table 1 N=98, Table 2 N=100, Table 3 N=85"
    }
  ],
  "seed": 42
}
```

---

## Scoring Rubric

### Auto-Scoreable Components (60%)

| Component | Weight | Scoring Method |
|---|---|---|
| Error detection (true positives) | 0.30 | Exact match: error ID present in agent output |
| Error classification (A/B/C) | 0.15 | Exact match: class label matches ground truth |
| Error location accuracy | 0.10 | Fuzzy match: location string similarity ≥0.8 |
| Cross-TFL consistency checks | 0.05 | Binary: check present and correctly identified |

### LLM-as-Judge Components (25%)

| Component | Weight | Scoring Method |
|---|---|---|
| Description quality | 0.10 | LLM judge: does description accurately characterize the error? |
| SAP reference accuracy | 0.10 | LLM judge: is the SAP citation correct and relevant? |
| Recommended correction | 0.05 | LLM judge: is the correction actionable and correct? |

### Human Expert Review (15%)

| Component | Weight | Scoring Method |
|---|---|---|
| Completeness | 0.10 | Expert: were all errors found? Any false positives? |
| Clinical judgment | 0.05 | Expert: are severity classifications clinically appropriate? |

### Composite Score Formula

```
score = 0.60 × auto_score + 0.25 × llm_judge_score + 0.15 × human_score
```

**Pass threshold:** ≥ 0.80 (80%)
**Distinction threshold:** ≥ 0.95 (95%)

### Partial Credit Rules

- **False negative** (missed error): 0 points for that error
- **False positive** (hallucinated error): −0.05 penalty per false positive (capped at −0.20)
- **Correct detection, wrong class**: 50% credit for that error
- **Correct detection, wrong location**: 70% credit for that error
- **Correct detection, correct class, partial description**: 80% credit for that error

---

## TFL Data Generation Strategy

### Step 1: Generate Clean TFLs

Use existing ground truth scripts (TC-001 through TC-020) to generate clean TFL outputs:
- Table 1: TC-002 (demographics) output
- Table 2: TC-020 (ORR by subgroup) output
- Table 3: TC-011 (AE summary) output
- Figure 1: TC-015 (KM curve) output
- Figure 2: TC-012 (forest plot HR) output
- Listing 1: TC-014 (PD listing) output

### Step 2: Inject Errors

Apply error injection functions to the clean TFLs:

```python
def inject_error_n_count(tfl_data, tfl_id, delta=-2):
    """Reduce N by delta in specified column."""
    # Modifies the N field in the output

def inject_error_missing_category(tfl_data, category_field, category_value):
    """Remove a category from a categorical variable."""
    # Removes the specified category from the output

def inject_error_denominator(tfl_data, old_denom, new_denom):
    """Replace denominator in n/N calculations."""
    # Modifies percentage calculations

def inject_error_sorting(tfl_data, sort_field, old_order, new_order):
    """Change sort order of a field."""
    # Re-sorts the output

def inject_error_typo(tfl_data, field, old_value, new_value):
    """Inject a spelling error."""
    # String replacement

def inject_error_method(tfl_data, method_field, old_method, new_method):
    """Change statistical method used."""
    # Modifies the method description

def inject_error_population(tfl_data, old_pop, new_pop):
    """Change population filter applied."""
    # Modifies population flag
```

### Step 3: Package TFLs

Bundle the injected TFLs into a JSON package with the YAML input specification.

---

## Cross-TC Relationships

| Relationship | Description |
|---|---|
| TC-005 ↔ TC-001 | Figure 1 uses TC-001 (KM PFS) output as base |
| TC-005 ↔ TC-002 | Table 1 uses TC-002 (demographics) output as base |
| TC-005 ↔ TC-011 | Table 3 uses TC-011 (AE summary) output as base |
| TC-005 ↔ TC-012 | Figure 2 uses TC-012 (forest plot) output as base |
| TC-005 ↔ TC-014 | Listing 1 uses TC-014 (PD listing) output as base |
| TC-005 ↔ TC-020 | Table 2 uses TC-020 (ORR by subgroup) output as base |
| TC-005 ↔ TC-004 | SAP context comes from TC-004-style SAP section |

---

## Implementation Plan

### Phase 1: Error Injection Framework
- Create `error_injection.py` module in scoring-harness
- Implement 7 error injection functions (one per error type)
- Create error catalog YAML with all 8 planted errors

### Phase 2: TFL Package Generator
- Script to run clean ground truth TCs and capture outputs
- Apply error injection to create variant TFL packages
- Bundle into standardized JSON package format

### Phase 3: Scorer Implementation
- `score_tc005()` function in score.py
- Auto-scorable components: error detection, classification, location
- LLM-as-judge integration for description/SAP/correction quality
- Human review interface (deferred to WG review phase)

### Phase 4: Validation
- Self-test: run clean package (0 errors) → agent should report 0 errors
- Error detection test: run package with 8 errors → agent should find all 8
- False positive test: run clean package → agent should not hallucinate errors

---

## Contamination Mitigation

1. **Parametric variants:** 10 variants with different error locations/types
2. **Seed-controlled data:** Different underlying data per variant
3. **Dynamic error injection:** Error positions change across variants
4. **Private error catalog:** Ground truth not in public training data
5. **SAP variation:** Different SAP specifications across variants

---

## Timeline

| Phase | Estimated Effort | Target |
|---|---|---|
| Phase 1: Error injection | 2-3 hours | Day 33 |
| Phase 2: Package generator | 2-3 hours | Day 34 |
| Phase 3: Scorer | 3-4 hours | Day 35 |
| Phase 4: Validation | 1-2 hours | Day 36 |
| WG review | 1 week | Day 40 |

---

## Open Questions for WG

1. **Error injection depth:** Should we inject errors at the data level (wrong dataset used) or only at the presentation level (wrong formatting/labeling)?
2. **LLM-as-judge model:** Which model should serve as the judge? GPT-4o, Claude Opus, or ensemble?
3. **Human reviewer pool:** How many WG members should review each variant? Minimum 2 for inter-rater reliability.
4. **RTF/PDF format:** Should we test with structured JSON only, or also with rendered RTF/PDF outputs?
5. **False positive tolerance:** Should excessive false positives (>3) result in automatic failure?
