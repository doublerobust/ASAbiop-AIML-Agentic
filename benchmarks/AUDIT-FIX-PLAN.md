# Project Freeze & Fix Plan — Audit Resolution

**Date:** 2026-08-01
**Status:** ACTIVE — daily development cron PAUSED until this plan completes
**Source audit:** GPT 5.6 "Sol" audit (2026-07-30) + Hermes independent verification (2026-08-01)
**Decision:** Freeze feature accumulation. Fix validity infrastructure. Re-scope deliverable. Then resume.

---

## 1. Why We Froze

Two decisive, reproducible defects invalidate the project's current validation narrative:

1. **Scorer comparator bug** (`scoring-harness/score.py:181`): when a tolerance spec omits
   `relative`, `within_rel` is unconditionally `True`, so `passed = within_abs or within_rel`
   is always true. **197 of 261 tolerance entries (75%) omit `relative`** — meaning 75% of
   numerical comparisons are pass-everything. Reproduced: `compare_numeric(999, 0, {'absolute': 0.01})`
   → score 1.0, "within tolerance".

2. **TC-006 common-mode statistical error** (`references/ground-truth/Python/tc_006_ssr_interim.py:88`):
   the Schoenfeld sample-size formula omits the equal-allocation factor (`p_A·p_B = 0.25`),
   producing ~127 required events instead of ~508. Both R and Python implement the same
   omission — bilingual agreement certified a wrong answer.

Additional confirmed findings:
- **Compliance rules not executable**: `compliance.yaml` configures 208 rule IDs; code
  implements 11 executable predicates (6 TCG + 5 CSR), all keyword-substring checks.
- **GitHub Actions workflow does not exist** despite manuscript claiming every push runs the suite.
- **Eval-runner sends prose + schema through plain chat API** — no datasets, no code/tool sandbox.
  It currently tests guessing/memorization, not agentic analysis.
- **Manuscript contains incompatible totals** (Level 1 variously 19/20/21/23/27; compliance counts,
  ARS counts, SAS coverage inconsistent between sections).
- **ARS files pass a project-authored schema**, not an official CDISC conformance test.
- **"155+ variants verified" unsupported** — corpus is overwhelmingly one canonical run.
- **SAS written but never executed** — "multilingual" claim is R↔Python only.
- **No frontier model results, no human baselines** — manuscript "Results" are R-vs-Python
  reference agreement, not AI-agent performance.

## 2. Minimum Path to a Defensible v0.1

### Phase A — Fix the scoring core (do FIRST)
1. **Fix `compare_numeric`**: default `relative` to a sane value (e.g. `1e-6`) OR require an
   explicit tolerance mode. Never let a missing key produce unconditional pass.
2. **Fix TC-006 formula**: add the equal-allocation factor; regenerate ground truth; re-verify
   R↔Python.
3. **Mutation-test every TC**: for each TC, corrupt every float in the checked-in output
   (wrong-but-plausible values) and confirm the scorer FAILS. Add this as
   `scripts/mutation-test.py` + CI.
4. **Add a real CI workflow** (`.github/workflows/verify.yml`): run cross-language verification,
   schema validation, and mutation tests on every push/PR.

### Phase B — Independent validation
5. **Independent statistical review**: 3–5 biostatisticians/statistical programmers validate a
   sentinel subset of TCs covering every method family (KM, log-rank, Cox, CMH, Schoenfeld/SSR,
   BOIN, DMC, CSR). Log adjudication.
6. **Execute SAS or re-scope**: run SAS in a licensed CI environment, OR explicitly document
   SAS as reference-only and rename the claim to "R↔Python cross-verified, SAS reference."
7. **Hidden cases**: generate held-out variants with frozen answers; keep them out of the repo
   until evaluation time.

### Phase C — Real evaluation
8. **Eval-runner v2**: give models actual datasets (ADaM CSVs) and a code-execution sandbox
   (R/Python). The current chat-API-only runner tests memorization — unusable as-is.
9. **Human baselines**: measure 2–3 statisticians on the same sentinel TCs.
10. **Multiple model runs + uncertainty**: per-case metrics, repeated runs, bootstrap CIs.
11. **Calibrate LLM-judge against blinded experts**; report inter-rater agreement.

### Phase D — Honest manuscript
12. **Regenerate all manuscript numbers from a versioned results manifest** — no hand-edited counts.
13. **Rewrite as protocol/resource paper** until real performance results exist.
14. **Restrain novelty language**: document CTBench, TrialBench, TrialDesignBench; position as
    "focused TFL statistical-programming benchmark," not "first."
15. **Correct CDISC ARS v1.0 publication date** (19 April 2024, not 2025); state ARS files pass
    a project-authored schema, not official conformance.

## 3. Immediate Actions Taken (2026-08-01)

- ✅ Daily development cron **paused** (job `dc5bd90b7093`).
- ✅ This document created and committed.
- ⏳ Next: Phase A fix 1 (comparator) — small, high-value; do before any other work.

## 4. What Is NOT Changing

- The paired R/Python corpus, synthetic data generators, SAS reference programs, schemas,
  error taxonomy, multi-level progression, provenance metadata — these are the project's
  real asset and stay.
- The daily cron will resume AFTER Phase A completes and the comparator fix is verified by
  mutation tests — with a rewritten prompt focused on validity work, not new TCs.

## 5. Communication

- This decision was made by Yue Shentu (project lead) after reviewing the GPT 5.6 audit and
  Hermes's independent verification.
- Next WG-facing artifact: the corrected v0.1 corpus/resource summary, not an empirical paper.
