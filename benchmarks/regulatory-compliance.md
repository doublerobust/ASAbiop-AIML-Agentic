# Regulatory Compliance Dimension — TFL Benchmark

**Version:** 0.1 (Day 4 preparation)
**Date:** 2026-05-27
**Status:** 🟡 Draft — foundation document, ready for Day 4 expansion
**Dimension:** Regulatory Compliance — CDISC ADaM-to-TFL Mapping, CSR Appendix Standards, FDA TCG

---

## 1. Purpose & Scope

### 1.1 Why Regulatory Compliance Matters

AI agents generating TFLs for clinical trials must produce outputs that satisfy regulatory submission requirements. A statistically correct table that fails CDISC ADaM mapping, omits FDA-required elements, or doesn't match ICH E3 CSR appendix standards is not acceptable for submission.

This dimension evaluates:
1. **ADaM-to-TFL traceability** — Can the agent correctly map ADaM variables to TFL outputs?
2. **FDA Study Data TCG compliance** — Does the output meet FDA Technical Conformance Guide requirements?
3. **ICH E3 CSR appendix standards** — Do tables and listings follow CSR appendix formatting conventions?
4. **CDISC conformance rules** — Do datasets and outputs pass Pinnacle 21 equivalent checks?
5. **Define-XML metadata** — Can the agent produce or verify analysis results metadata?

### 1.2 Scope for This Dimension

| Area | Priority | Coverage in Test Cases |
|---|---|---|
| ADaM variable mapping to TFLs | 🔴 Critical | TC-001, TC-002, TC-003, TC-010 |
| Population filter correctness (ITT/SAFETY/PP) | 🔴 Critical | TC-001, TC-002, TC-007 |
| FDA TCG §5.3 analysis datasets | 🟡 High | TC-010 (CSR section) |
| ICH E3 §14 appendix tables/figures | 🟡 High | TC-010, TC-009 |
| CDISC Analysis Results Metadata | 🟡 High | TC-004 (SAP), TC-010 |
| Pinnacle 21 rule compliance | 🟢 Medium | All auto-scorable |
| Define-XML generation | 🟢 Medium | Future TC |

---

## 2. ADaM-to-TFL Mapping Standards

### 2.1 Core ADaM Variables for TFL Generation

For each test case, the following ADaM variables must be mapped correctly:

| Test Case | ADaM Dataset | Key Variables | TFL Output Mapping |
|---|---|---|---|
| TC-001 | ADTTE | PARAM, PARAMCD, AVAL, CNSR, TRT01PN, ITTFL | KM median, CI, event count |
| TC-002 | ADSL | AGE, SEX, RACE, REGION1, ECOG, TRT01PN, SAFFL | Descriptive stats by arm |
| TC-003 | ADTTE | AVAL, CNSR, TRT01PN, SEX, ECOG, ITTFL | Stratified log-rank statistic |
| TC-007 | ADSL + ADTTE | All + PP population flags | ITT vs PP comparison |
| TC-009 | ADSL + ADAE + ADLB | All + AESEV, AESER, AESDTH, MEDDRA codes | Safety tables |
| TC-010 | Full ADaM suite | All above | CSR sections |

### 2.2 ADaM Conformance Rules Relevant to TFL

From CDISC ADaMIG v1.3 and ADaM Conformance Rules:

```
CR-AD-001: ADSL must contain one record per subject
CR-AD-002: ADTTE must contain one record per subject per parameter
CR-AD-003: Population flags (ITTFL, SAFFL, PPROTFL) must be populated
CR-AD-004: TRT01PN/TRT01P must match across datasets
CR-AD-005: PARAM/PARAMCD must match between ADTTE and analysis metadata
CR-AD-006: Analysis dates must not contain missing values for analyzed subjects
CR-AD-007: CNSR values must be 0 (event) or 1 (censored)
```

### 2.3 Population Filter Correctness

| Population | Flag | Valid Values | Applied To |
|---|---|---|---|
| ITT | ITTFL | Y/N | TC-001, TC-003, TC-004, TC-007 |
| Safety | SAFFL | Y/N | TC-002, TC-009 |
| Per-Protocol | PPROTFL | Y/N | TC-007 |
| Evaluable | EFFFL | Y/N | TC-008 |

**Scoring rule:** Population filter mismatch = critical error (0 score for that component).

---

## 3. FDA Study Data Technical Conformance Guide (TCG)

### 3.1 Key TCG Sections for TFL Generation

The FDA Study Data TCG (current version) specifies:

**Section 5.3 — Analysis Data:**
- ADaM datasets must be submitted with Define-XML
- Analysis datasets must be traceable to SDTM
- All ADaM variables must be documented in the define file
- "No analysis should be performed that cannot be reproduced from the submitted data"

**Section 7 — Analysis Results Metadata (ARM):**
- ARM must document all analysis results in the submission
- ARM must include: analysis ID, description, reason, documentation, datasets used, selection criteria, documentation ID
- ARM must be in a standardized structured format

**Section 12 — Programs:**
- Analysis programs should be submitted
- Programs must be well-documented and reproducible

### 3.2 TFL-Specific TCG Requirements

| Requirement | TCG Section | Impact on Scoring |
|---|---|---|
| TFL titles must match SAP | §5.3.1 | TC-005, TC-010 |
| Population definitions must be consistent | §5.3.2 | All TCs |
| Analysis windows must be documented | §5.3.3 | TC-001, TC-003 |
| Subgroup analyses must be pre-specified | §5.3.4 | TC-004, TC-007 |
| Sensitivity analyses must be documented | §5.3.5 | TC-004, TC-007 |
| Multiplicity adjustment must be documented | §5.3.6 | TC-004 |
| Missing data handling must be documented | §5.3.7 | TC-007, TC-010 |

### 3.3 TCG Compliance Checklist for Benchmark

```yaml
tcg_compliance_checklist:
  - id: TCG-01
    description: "Analysis population correctly filtered"
    test_cases: [TC-001, TC-002, TC-003]
    scoring: "critical — must match exactly"
    
  - id: TCG-02
    description: "Treatment arm variable correctly referenced"
    test_cases: [TC-001, TC-002, TC-003, TC-005]
    scoring: "critical — must match exactly"
    
  - id: TCG-03
    description: "Event/censoring indicator correctly handled (CNSR)"
    test_cases: [TC-001, TC-003]
    scoring: "critical — must match exactly"
    
  - id: TCG-04
    description: "Analysis time variable correctly specified (AVAL)"
    test_cases: [TC-001, TC-003]
    scoring: "critical — must match exactly"
    
  - id: TCG-05
    description: "Statistical method documented (method description)"
    test_cases: [TC-003, TC-004]
    scoring: "major — 0.5 penalty if missing"
    
  - id: TCG-06
    description: "Software version documented in output"
    test_cases: [TC-001, TC-002, TC-003]
    scoring: "minor — 0.1 penalty if missing"
```

---

## 4. ICH E3 CSR Appendix Standards

### 4.1 CSR Appendix Structure

ICH E3 specifies the following appendix structure relevant to TFL:

| Appendix | Content | Relevant TC |
|---|---|---|
| §14.1 | Patient disposition and demographics | TC-002, TC-010 |
| §14.2 | Efficacy tables (primary + secondary endpoints) | TC-001, TC-003, TC-010 |
| §14.3 | Safety tables (AEs, labs, vitals) | TC-009, TC-010 |
| §14.4 | Individual patient listings (deaths, SAEs) | TC-009 |
| §16.1 | Study documentation (protocol, SAP) | TC-004, TC-010 |

### 4.2 ICH E3 Formatting Requirements

| Requirement | Impact on TFL |
|---|---|
| Table numbering must follow appendix convention | e.g., Table 14-1, Table 14-2.2 |
| Titles must include: study ID, population, endpoint, time point | Required in all table captions |
| Footnotes must specify: analysis method, software version, data cut | Required in all TFLs |
| Abbreviations must be defined in table footnote | Industry standard |
| Missing values must be noted (e.g., "NE" for not estimable) | TC-001 CI bounds |
| p-values must specify: test type, direction (1/2-sided), adjustment | TC-003 |
| Confidence intervals must specify: method, confidence level | TC-001 |

### 4.3 CSR Checklist for Benchmark Scoring

```yaml
csr_compliance_checklist:
  - id: CSR-01
    description: "Table numbered per appendix convention"
    type: "formatting"
    penalty: 0.1
    
  - id: CSR-02
    description: "Title includes population, endpoint, time point"
    type: "formatting" 
    penalty: 0.2
    
  - id: CSR-03
    description: "Footnotes document method, software, data cut"
    type: "formatting"
    penalty: 0.1
    
  - id: CSR-04
    description: "p-value type (1/2-sided) documented"
    type: "content"
    penalty: 0.2
    
  - id: CSR-05
    description: "CI method documented"
    type: "content"
    penalty: 0.2
    
  - id: CSR-06
    description: "Missing values properly noted"
    type: "content"
    penalty: 0.1
```

---

## 5. CDISC Analysis Results Metadata (ARM)

### 5.1 ARM Structure

CDISC ARM defines a standardized way to document analysis results:

```yaml
analysis_result:
  id: AR-001
  display_identifier: "Table 14-2.1"
  description: "Primary Efficacy Analysis — Stratified Log-Rank Test"
  reason: "Primary endpoint analysis per SAP Section 9.2"
  documentation: "SAP v2.0, Section 9.2.1"
  datasets:
    - name: "ADTTE"
      filter: "ITTFL = 'Y'"
      variables: ["AVAL", "CNSR", "TRT01PN", "SEX", "ECOG"]
  documentation_id: "SAP-2025-001"
  results:
    - statistical_method: "Stratified log-rank test"
      statistical_software: "R v4.4.1, survival v3.7-0"
      parameter_estimates:
        chi_square: 4.523
        df: 1
        p_value: 0.0334
```

### 5.2 ARM Test Case Integration

| Test Case | ARM Elements Required | Scoring |
|---|---|---|
| TC-001 | Analysis ID, dataset, method, result | +10% bonus for ARM format output |
| TC-003 | Analysis ID, strata, method, chi-sq, p-value | +10% bonus for ARM format output |
| TC-010 | Full ARM for all analyses | Required for full score |

---

## 6. Pinnacle 21 Rule Integration

### 6.1 Key Pinnacle 21 Rules for TFL-Related Data

Pinnacle 21 Community/Enterprise rules that apply to ADaM datasets used in TFL generation:

| Rule ID | Description | Severity | Apply to TCs |
|---|---|---|---|
| AD0001 | ADaM dataset must have a corresponding define file | Error | All data-driven TCs |
| AD0010 | Required variables must be populated | Error | TC-001, TC-002, TC-003 |
| AD0015 | TRT01PN must match between ADSL and ADTTE | Error | TC-001, TC-003 |
| AD0020 | Population flags must be Y or N | Warning | TC-001, TC-002, TC-003 |
| AD0030 | Analysis dates must not be missing for analyzed subjects | Error | TC-001, TC-003 |
| AD0040 | CNSR values must be 0 or 1 | Error | TC-001, TC-003 |

### 6.2 Benchmark Integration Strategy

Rather than running full Pinnacle 21 validation (which requires a commercial license), the benchmark will:

1. **Encode critical rules** as ADaM schema validation in the scoring harness
2. **Check dataset integrity** before running test cases (pre-condition check)
3. **Score dataset compliance** as a separate component (10-15% of total TC score for Level 1)
4. **Document Pinnacle 21 equivalency** for each rule checked

---

## 7. Regulatory Compliance Scoring Framework

### 7.1 Scoring Components

| Component | Weight | Applies To | Method |
|---|---|---|---|
| ADaM variable mapping correctness | 25% | TC-001, TC-002, TC-003 | Schema + exact match |
| Population filter correctness | 20% | All data-driven TCs | Exact match |
| FDA TCG checklist compliance | 15% | TC-001, TC-003, TC-010 | Checklist scoring |
| ICH E3 formatting compliance | 15% | TC-002, TC-009, TC-010 | Checklist scoring |
| ARM metadata documentation | 10% | TC-001, TC-003, TC-010 | Check present + correct |
| Dataset integrity checks | 10% | All data-driven TCs | Pre-scripted P21 rules |
| Documentation (software, method) | 5% | All TCs | Check present |

### 7.2 Penalty Structure

| Violation | Penalty | Example |
|---|---|---|
| Wrong population (ITT vs PP vs SAFETY) | ⛔ Score = 0 (critical) | TC-007 PP analysis on ITT population |
| Wrong treatment arm grouping | ⛔ Score = 0 (critical) | TC-001 combining arms |
| Missing required metadata | −20% of TC score | No software version in output |
| Wrong variable name/meaning | ⛔ Score = 0 (critical) | Using wrong ADaM variable |
| Table formatting non-compliant | −10% (minor) | Missing footnotes |
| Missing analysis documentation | −15% (major) | No CI method specified |

### 7.3 Automated Compliance Checks (via Scoring Harness)

```python
def check_adam_compliance(agent_output: dict, schema: dict) -> dict:
    """Check ADaM variable mapping compliance."""
    checks = {}
    
    # Check population flag
    if "ittfl" in agent_output.get("population", "").lower():
        checks["population"] = check_flag_field(agent_output, "ITTFL")
    
    # Check treatment variable
    if "trt01pn" in agent_output.get("variables", []):
        checks["treatment"] = check_variable_exists(agent_output, "TRT01PN")
    
    # Check event/censoring variable
    if "cnsr" in agent_output.get("variables", []):
        checks["censoring"] = check_variable_valid(agent_output, "CNSR", [0, 1])
    
    return checks


def check_tcg_compliance(tfl_output: dict, test_case: str) -> dict:
    """Check FDA TCG compliance checklist."""
    # Cross-reference test_case to TCG requirements
    tcg_rules = get_tcg_rules_for(test_case)
    passed = []
    failed = []
    
    for rule in tcg_rules:
        if check_rule_match(tfl_output, rule):
            passed.append(rule["id"])
        else:
            failed.append(rule["id"])
    
    return {"passed": passed, "failed": failed, "score": len(passed) / len(tcg_rules)}
```

---

## 8. Integration with Existing Framework

### 8.1 Adding Regulatory Compliance to Scoring

The existing scoring harness (`katsu`) will be extended with:

```
katsu score --tc TC-001 --agent agent.json --truth truth.json \
    --compliance                     # Flag: include regulatory compliance check
    --tcg-check                      # Flag: run FDA TCG checks
    --csr-format                     # Flag: check ICH E3 formatting
```

A new `compliance` module will be added:

```
scoring-harness/
├── score.py                         # Main CLI (existing)
├── tolerances.yaml                  # Numerical tolerances (existing)
├── compliance.py                    # NEW: Regulatory compliance checks
├── requirements.txt                 # Updated
└── README.md                        # Updated
```

### 8.2 Compliance YAML Configuration

```yaml
# compliance.yaml — Regulatory compliance rules per test case

TC-001:
  adam_mapping:
    required_variables: [AVAL, CNSR, TRT01PN, ITTFL]
    population_flag: ITTFL
    population_value: Y
    treatment_variable: TRT01PN
  tcg_rules:
    - TCG-01: "Population filter: ITTFL='Y'"
    - TCG-02: "Treatment variable: TRT01PN=1"
    - TCG-03: "CNSR handling: 0=event, 1=censored"
    - TCG-06: "Software version documented"
  csr_formatting:
    - CSR-03: "Method documented in footnotes"
    - CSR-05: "CI method documented"

TC-002:
  adam_mapping:
    required_variables: [AGE, SEX, RACE, REGION1, ECOG, TRT01PN, SAFFL]
    population_flag: SAFFL
    population_value: Y
    treatment_variable: TRT01PN
  tcg_rules:
    - TCG-01: "Population filter: SAFFL='Y'"
    - TCG-02: "Treatment variable: TRT01PN"
  csr_formatting:
    - CSR-01: "Table numbered per appendix"
    - CSR-02: "Title includes population"
    - CSR-03: "Footnotes documented"

TC-003:
  adam_mapping:
    required_variables: [AVAL, CNSR, TRT01PN, SEX, ECOG, ITTFL]
    population_flag: ITTFL
    population_value: Y
    treatment_variable: TRT01PN
    strata_variables: [SEX, ECOG]
  tcg_rules:
    - TCG-01: "Population filter: ITTFL='Y'"
    - TCG-02: "Treatment variable: TRT01PN"
    - TCG-03: "CNSR handling: 0=event, 1=censored"
    - TCG-05: "Statistical method documented"
    - TCG-06: "Software version documented"
  csr_formatting:
    - CSR-04: "p-value type documented"
    - CSR-05: "CI method documented"
```

---

## 9. Next Steps for Day 4

1. **Implement `compliance.py`** — regulatory compliance check module for scoring harness
   - ADaM variable mapping validator
   - TCG checklist scorer
   - CSR formatting checker

2. **Create `compliance.yaml`** — per-test-case compliance rule specifications (draft above)

3. **Extend `katsu` CLI** — add `--compliance`, `--tcg-check`, `--csr-format` flags

4. **Integration testing** — run compliance checks on existing ground truth outputs

5. **Research** — confirm latest FDA TCG version requirements, review CDISC CORE (Conformance Rules) initiative status

6. **WG input needed:**
   - Should compliance be a separate score dimension or folded into the main TC score?
   - What level of ICH E3 formatting is expected from agents vs. assumed post-processing?
   - Should ARM metadata generation be a standalone test case or a bonus criterion?

---

## References

1. ICH E3: Structure and Content of Clinical Study Reports, 1996.
2. ICH E9: Statistical Principles for Clinical Trials, 1998.
3. ICH E9(R1): Estimands and Sensitivity Analysis, 2019.
4. FDA Study Data Technical Conformance Guide (current version).
5. CDISC ADaM Implementation Guide v1.3.
6. CDISC Analysis Results Metadata v1.0.
7. Pinnacle 21 Community Rules (latest release).
8. CDISC CORE (Clinical Open Rules Engine) Initiative.
9. Barry M, Edgman-Levitan S. "Shared Decision Making — Pinnacle of Patient-Centered Care." *NEJM*, 2012. (Note: the NEJM article is unrelated; the Pinnacle 21 name coincidence)
