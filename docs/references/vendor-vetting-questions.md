# Vendor Vetting Questions — TFL Review AI
## Agentic AI Workstream, ASA Biopharm AI/ML Working Group
**Date:** May 22, 2026
**Author:** Yue Shentu / Natasha

---

## Scope & Depth

### 1. Atomic vs. Holistic (MOST IMPORTANT)
Does it check each TFL against its individual SAP + shell spec, or does it read the *entire package* and flag cross-table inconsistencies? e.g., should Table 14.2.1.1 (baseline characteristics) and Figure 14.2.1.1 (KM curve) agree on the same N-count for the same arm?

### 2. Numbers or just structure?
Does it verify that p-values, hazard ratios, and confidence intervals in the *body* of each table match the corresponding SAS output? Or does it only check headers, footers, variable labels, and formatting? If it can't validate the numbers, it's a formatting checker with an LLM wrapper.

### 3. Traceability back to SAP
Can it link every TFL element to its originating language in the SAP? If the SAP says "The primary analysis will use a Cox proportional hazards model stratified by geographic region" — does it verify the TFL footnotes and methods headers reflect *exactly* that? Or does it just check for the presence of "Cox" somewhere in the table?

---

## Coherence & Logic

### 4. Flow consistency across a submission
Can it verify that patient counts flow consistently from the disposition table → baseline characteristics → analysis populations → safety summaries → efficacy results? Does it catch the case where 48 patients are "randomized" in Table 1 but only 46 appear in the ITT population in Table 3?

### 5. Logic cross-checks
Does it flag logical impossibilities? e.g., a median follow-up shorter than median time-to-event, or a subgroup N larger than the overall population N for that arm?

### 6. Programming-to-spec linkage
Does it actually read the SAS programs and verify that the code implements what the specs say? Or does it compare TFLs to shells only — leaving a gap between "what the shell says" and "what the code actually does"?

---

## Validation & Governance

### 7. Error rate
What's its false positive rate (flags something that's actually correct) and false negative rate (misses a real error)? How was this measured? On what corpus? If the answer is "we haven't measured it," that's a red flag.

### 8. Audit trail
Can it produce an inspection-ready record: "On date/time, agent X checked TFL 14.2.1.1 against SAP section 9.3 and spec v2.1, found discrepancy in N-count (shell=48, program=46), escalated to Reviewer Y, resolved on date Z"?

### 9. Version awareness
If the SAP is amended or a shell is updated, does it re-check *only the affected TFLs* or the entire package from scratch? Can it handle a mid-submission amendment without re-auditing everything?

---

## Integration & Workflow

### 10. Where does it fit in the timeline?
Is it designed to be used *during* programming (before the stat reviewer sees the TFLs), or *after* the package is submitted for review? These are very different workflows with different value propositions.

### 11. What does the human still do?
Be specific. If the agent flags 30 issues and 28 are false positives, the stat reviewer now has *more* work, not less. What's the typical false-positive rate per 100 TFLs?

### 12. What does it NOT check?
The most revealing question. If they can articulate clear boundaries (e.g., "we don't check N-counts across tables" or "we don't verify SAS code"), that's more trustworthy than "we do everything."

---

## Regulatory

### 13. FDA inspection readiness
Has this been used in any regulatory submission that passed inspection without findings related to the AI review tool? If not, what's the validation pathway?

### 14. Model transparency
Which LLM is running the checks? If it's Claude/GPT/Gemini, which version? Is there prompt engineering happening, and can the customer see/edit the prompts? If the underlying model changes, does the error rate change?

---

## The One Question That Separates Real from Slideware

> *"Show me a side-by-side: the same TFL error caught by your agent vs. caught by a human senior statistician. Walk me through what each one checked, how long it took, and which one caught something the other missed."*

If they can produce a real example, they're serious. If they can't, it's a demo.
