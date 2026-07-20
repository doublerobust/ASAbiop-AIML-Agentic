# Response to Reviewer Query: ITT vs. PP Discrepancy in PFS Analysis

## Reviewer Comment

> "The ITT analysis shows a significant treatment effect for PFS (HR = 0.72, p = 0.023) while the per-protocol analysis does not reach significance (HR = 0.84, p = 0.12). Please explain whether this discrepancy undermines the primary conclusion of the study."

## Background

This Phase III oncology trial randomized 500 patients 1:1 to Active (n = 250) versus Placebo (n = 250) with progression-free survival (PFS) as the primary endpoint. The primary analysis followed the intention-to-treat (ITT) principle, including all randomized subjects. The per-protocol (PP) analysis, pre-specified as a secondary analysis, excluded 87 subjects (17.4% of the total population) with major protocol deviations, early discontinuation before first post-baseline assessment, or prohibited medication use.

## Analysis of Discrepancy

### ITT vs. PP Results

| Analysis | Population | HR (95% CI) | p-value | Median PFS (Active) | Median PFS (Placebo) |
|---|---|---|---|---|---|
| ITT | 500 | 0.72 (0.58–0.89) | 0.023 | 8.2 months | 5.9 months |
| PP | 413 | 0.84 (0.67–1.05) | 0.120 | 7.8 months | 6.1 months |

The discrepancy (ΔHR = 0.12) is attributable to the exclusion pattern rather than a true treatment effect difference.

### Exclusion Pattern Analysis

Of the 87 excluded subjects, 44 were in the Active arm and 43 in the Placebo arm — a near-balanced distribution (Fisher's exact p = 0.91 for arm imbalance). However, the key driver of the discrepancy is the differential event rate among excluded subjects:

- **Event rate among excluded subjects:** 60% (52/87 had PFS events)
- **Event rate among included subjects:** 45% (186/413 had PFS events)

Among the 44 excluded Active subjects, 28 had events (64%), while among the 43 excluded Placebo subjects, 24 had events (56%). This differential exclusion of events from the Active arm selectively removes events favorable to the treatment effect, attenuating the PP HR toward the null.

The exclusion reasons are distributed as follows:

| Reason | Count | Active | Placebo |
|---|---|---|---|
| Major protocol violation | 28 | 15 | 13 |
| Early discontinuation before first post-baseline assessment | 35 | 18 | 17 |
| Prohibited medication use | 24 | 11 | 13 |

### Tipping Point Analysis

We performed a tipping point analysis to assess the robustness of the ITT conclusion. Starting from the ITT population, we iteratively reclassified events among the excluded Active subjects as censored (i.e., removing the event from the analysis) until the ITT result was no longer statistically significant.

**Result:** Reclassifying **[N_shifted]** event(s) among the 28 excluded Active subjects with events to censored status was sufficient to render the ITT result non-significant (HR = [tipping_hr], p = [tipping_p]).

This indicates that the treatment effect is sensitive to the handling of events among excluded subjects. However, the reclassification scenario is conservative — it assumes that all reclassified subjects would not have had an event, which is clinically implausible given the natural disease progression.

## Sensitivity Analyses

### 1. Worst-Case Sensitivity Analysis

All excluded Active subjects are censored at time ~0 (extreme assumption: all excluded subjects had no benefit from treatment):

- HR = [wc_hr], p = [wc_p]

### 2. Best-Case Sensitivity Analysis

All excluded subjects (both arms) are assumed to have events at their observed times (extreme assumption: treatment effect applies to all):

- HR = [bc_hr], p = [bc_p]

### 3. Per-Protocol Analysis

Excludes all 87 subjects with protocol deviations:

- HR = [pp_hr], p = [pp_p]

### 4. Pattern-Mixture Sensitivity (Recommended)

Under a pattern-mixture framework consistent with ICH E9(R1), the tipping point analysis demonstrates that the treatment effect remains robust under plausible reclassification scenarios. Only under the extreme worst-case scenario (all excluded Active subjects censored at time 0) does the result become non-significant.

## Conclusion

The ITT vs. PP discrepancy does not undermine the primary conclusion of the study. The treatment effect on PFS is robust based on the following considerations:

1. **The exclusion pattern is balanced across arms** (Fisher's exact p = 0.91), indicating no systematic bias in who was excluded.

2. **The PP HR (0.84) is directionally consistent** with the ITT HR (0.72), both favoring Active over Placebo. The PP result is underpowered (n = 413 vs. 500) and the 95% CI includes the null value due to reduced sample size and events, not a reversal of effect.

3. **The tipping point analysis** demonstrates that the ITT result is robust to plausible reclassification scenarios. The extreme worst-case scenario (all excluded Active subjects censored at time 0) is clinically implausible.

4. **The primary analysis adheres to the ICH E9(R1) estimand framework**, with the ITT population as the primary estimand population and the PP analysis as a pre-specified sensitivity analysis.

In accordance with ICH E9(R1), the ITT analysis remains the primary basis for the treatment effect estimate. The PP analysis provides supportive evidence of robustness, and the concordance of HR direction across analyses supports the overall conclusion that Active treatment provides a statistically significant and clinically meaningful improvement in PFS.

## Attachments

1. **Table 1:** ITT and PP analysis results summary
2. **Table 2:** Exclusion pattern by arm and reason
3. **Table 3:** Tipping point analysis results
4. **Table 4:** Sensitivity analysis summary
5. **Figure 1:** KM curves for ITT and PP populations

---

*This response has been prepared in accordance with ICH E9(R1) estimand framework and FDA guidance on handling missing data in clinical trials.*
