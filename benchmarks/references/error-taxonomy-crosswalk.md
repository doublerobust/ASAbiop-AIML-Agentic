# Error Taxonomy Crosswalk — Original 17 Types → Current Implementation

**Date:** 2026-07-30
**Purpose:** Map the original 17 error types specified in `benchmark-framework-v1.md` (§4.1) to their current implementation across the scoring harness, or document where they are not yet covered.

## Mapping

### Class A — Critical (would change analysis conclusion)

| Orig ID | Original Description | Current Coverage | Location | Notes |
|---------|---------------------|------------------|----------|-------|
| **A-01** | Wrong statistical method (Cox PH vs log-rank) | ⚠️ Partial | `safety.yaml` cross-TFL agreement rules; `compliance.yaml` method-check rules | Covered for specific TC contexts but no standalone "method verification" check |
| **A-02** | Incorrect denominator (PP vs ITT) | ✅ Covered | `error_catalog.yaml` E-001 (N-count); `safety.yaml` N-count rules across TCs | E-001 explicitly tests ITT population denominator |
| **A-03** | Mis-specified covariate (unstratified vs stratified) | ⚠️ Partial | `compliance.yaml` TCG checklist rules | Covered by compliance framework but not tested as standalone error injection |
| **A-04** | Wrong comparison / reference arm | ❌ Not covered | — | No test case specifically tests arm swap detection |
| **A-05** | Missing multiplicity adjustment | ❌ Not covered | — | No test case tests alpha-correction verification |

### Class B — Major (correction required before submission)

| Orig ID | Original Description | Current Coverage | Location | Notes |
|---------|---------------------|------------------|----------|-------|
| **B-01** | Wrong population label ("Safety" on ITT-only) | ❌ Not covered | — | Header/label verification not implemented |
| **B-02** | Missing subgroup | ✅ Covered | `error_catalog.yaml` E-003 (missing category); `safety.yaml` per-TC cross-checks | |
| **B-03** | Wrong reference arm label | ❌ Not covered | — | Label verification not implemented |
| **B-04** | Incorrect visit window | ⚠️ Partial | `safety.yaml` edge case rules (EC-010 visit window overlap) | Covered as edge case, not as systematic visit-window check |
| **B-05** | Wrong CI type (no 95% label) | ❌ Not covered | — | CI type/coverage verification not implemented |
| **B-06** | N-count mismatch | ✅ Covered | `safety.yaml` N-count rules (42+ rules across TCs); `error_catalog.yaml` E-001, E-007 | Thorough coverage across multiple TCs and contexts |
| **B-07** | Missing category (e.g., "Unknown" race dropped) | ✅ Covered | `error_catalog.yaml` E-003 (missing category); `safety.yaml` cross-TFL agreement | |

### Class C — Minor (cosmetic/formatting)

| Orig ID | Original Description | Current Coverage | Location | Notes |
|---------|---------------------|------------------|----------|-------|
| **C-01** | Decimal places inconsistent | ⚠️ Partial | `tolerances.yaml` — per-field precision specs | Precision is enforced in scoring, but not tested as planted error |
| **C-02** | Alignment error | ❌ Not covered | — | Visual/formatting checks out of scope by design |
| **C-03** | Table title typo | ❌ Not covered | — | Text/spelling checks out of scope by design |
| **C-04** | Missing footnote | ❌ Not covered | — | Footnote verification out of scope by design |
| **C-05** | Font/size inconsistency | ❌ Not covered | — | Visual/formatting out of scope by design |
| **C-06** | Missing page number | ❌ Not covered | — | Page-level formatting out of scope by design |

## Current Error Catalog (TC-005)

The implemented `error_catalog.yaml` for TC-005 uses a different ID scheme (E-001 through E-008) with functional types:

| Current ID | Type | Class | Maps to Original |
|------------|------|-------|------------------|
| E-001 | n_count | B | A-02, B-06 |
| E-002 | missing_category | B | B-07 |
| E-003 | missing_category | B | B-02, B-07 |
| E-004 | denominator | A | A-02 |
| E-005 | sorting | C | (new — not in original) |
| E-006 | typo | C | C-03 (partial) |
| E-007 | method | A | A-01 |
| E-008 | population | A | A-02 |

## Safety Rules Coverage

The `safety.yaml` file (96 rules) provides the most comprehensive coverage of original error types:

- **N-count consistency** (42+ rules): Covers B-06, A-02 comprehensively
- **Denominator validation** (per TC): Covers A-02 for specific TCs
- **Cross-TFL agreement** (14 pairs): Covers B-07, A-01 partially
- **Edge cases** (16 scenarios): Covers B-04 partially

## Gaps Summary

| Status | Count | Types |
|--------|-------|-------|
| ✅ Covered | 5 | A-02, B-02, B-06, B-07, C-03 (partial) |
| ⚠️ Partial | 4 | A-01, A-03, B-04, C-01 |
| ❌ Not covered | 8 | A-04, A-05, B-01, B-03, B-05, C-02, C-04, C-05, C-06 |

### Notes on Deliberate Gaps
- **C-02 through C-06** (alignment, typos, footnotes, fonts, page numbers) are visual/formatting issues that the benchmark explicitly does not test — the output format is structured JSON, not rendered TFLs. These are out of scope by design.
- **A-04** (wrong comparison arm) and **A-05** (missing multiplicity) require domain-specific SAP interpretation not yet encoded in the error injection framework.
- **B-01** (wrong population label) and **B-03** (wrong arm label) are text-label checks that could be added to TC-005 error injection.

## Recommendation
1. Add E-009 (arm_swap, Class A) and E-010 (multiplicity, Class A) to the error catalog
2. Document that C-02 through C-06 are intentionally out of scope for a numerical correctness benchmark
3. Conduct WG calibration survey to validate severity classifications
