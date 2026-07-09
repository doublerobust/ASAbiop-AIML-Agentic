/*
 * TC-028: Change in Tumor Size by Cycle (Longitudinal) — SAS Reference Implementation
 * Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark
 *
 * Computes percentage change from baseline in tumor size (SLD) at each
 * treatment cycle (C1D1 through C6D1) for each subject. Produces:
 *   - Per-subject longitudinal trajectory
 *   - Visit-wise summary statistics (mean, median, n, SE) by arm
 *   - Overall summary (best response, worst response, time to best response)
 *
 * Key distinctions from other tumor response TCs:
 *   TC-013 (Waterfall): Best % change only (single timepoint)
 *   TC-028 (This):       Trajectory across all cycles (longitudinal)
 *
 * Dependencies: Base SAS, PROC MEANS, PROC UNIVARIATE
 * NOTE: Reference implementation — not executed (no SAS license available)
 *
 * Usage: %let seed=42; %let n=150; %include "tc-028-tumor-size-by-cycle.sas";
 */

/* ───────────────────────────────────────────────────── */
/* 1. Generate synthetic longitudinal tumor data         */
/* ───────────────────────────────────────────────────── */

%let seed = 42;
%let n = 150;
%let n_exp = %eval(&n. / 2);  /* 75 experimental */
%let n_ctrl = %eval(&n. - &n_exp.);  /* 75 control */

data adtr_long;
  call streaminit(&seed. + 200);
  length USUBJID $10 TRT01A $12 CYCLE $6 TIME_TO_BEST $6;
  array cycles{6} $6 _temporary_ ("C1D1", "C2D1", "C3D1", "C4D1", "C5D1", "C6D1");

  do i = 1 to &n.;
    USUBJID = cats("SUBJ-", put(i, z4.));
    STUDYID = "BENCHMARK-001";

    /* Treatment assignment */
    if i <= &n_exp. then do;
      TRT01A = "Experimental";
      TRT01PN = 1;
    end;
    else do;
      TRT01A = "Control";
      TRT01PN = 0;
    end;

    /* Baseline SLD (sum of longest diameters) in mm */
    baseline_sld = round(rand("Uniform") * 100 + 20, 0.1);

    /* Treatment effect parameters */
    if TRT01PN = 1 then do;
      initial_response = rand("Normal", -25, 15);
      regrowth_rate = rand("Normal", 5, 3);
      nadir_cycle = rand("Table"); /* 1-4 with equal prob for now */
      if nadir_cycle > 4 then nadir_cycle = 4;
    end;
    else do;
      initial_response = rand("Normal", -8, 12);
      regrowth_rate = rand("Normal", 8, 4);
      nadir_cycle = rand("Table"); /* 1-3 */
      if nadir_cycle > 3 then nadir_cycle = 3;
    end;

    /* Stratification factors */
    if rand("Bernoulli", 0.55) = 1 then SEX = "M";
    else SEX = "F";

    age = round(rand("Normal", 58, 12));
    if age < 65 then AGEGR1 = "<65";
    else AGEGR1 = ">=65";

    ECOG = put(rand("Bernoulli", 0.4), 1.);

    /* Flags */
    if rand("Uniform") < 0.95 then ITTFL = "Y";
    else ITTFL = "N";

    /* Generate visits */
    base_dropout = 0.05;
    stopped = 0;

    do cycle_idx = 1 to 6;
      cycle = cycles{cycle_idx};

      if stopped = 1 then leave;

      if cycle = "C1D1" then do;
        /* Baseline visit */
        sld = baseline_sld;
        pct_change = 0.0;
        cycle_num = 0;
        available = 1;
      end;
      else do;
        /* Check dropout */
        dropout_prob = base_dropout * (cycle_idx - 1);
        if rand("Uniform") < dropout_prob then do;
          stopped = 1;
          leave;
        end;

        cycle_num = cycle_idx;  /* 2, 3, 4, 5, 6 */

        /* Compute % change from baseline */
        if cycle_num <= nadir_cycle then do;
          pct = initial_response * cycle_num;
        end;
        else do;
          nadir_pct = initial_response * nadir_cycle;
          cycles_since_nadir = cycle_num - nadir_cycle;
          pct = nadir_pct + regrowth_rate * cycles_since_nadir;
        end;

        /* Add noise */
        pct = pct + rand("Normal", 0, 3);
        sld = max(baseline_sld * (1 + pct / 100), 0);
        sld = round(sld, 0.1);
        pct_change = round(pct, 0.1);
        available = 1;
      end;

      output;
    end;
  end;

  drop i base_dropout stopped cycle_idx nadir_pct cycles_since_nadir
       initial_response regrowth_rate nadir_cycle age;
run;

/* ───────────────────────────────────────────────────── */
/* 2. Visit-wise summary statistics by arm               */
/* ───────────────────────────────────────────────────── */

/* All subjects combined */
proc means data=adtr_long(where=(ITTFL="Y" and available=1 and cycle ^= "C1D1"))
    noprint;
  by cycle;
  var pct_change sld;
  output out=visit_all
    n=pct_n sld_n
    mean=pct_mean sld_mean
    median=pct_median sld_median
    std=pct_std sld_std
    min=pct_min sld_min
    max=pct_max sld_max;
run;

/* Experimental arm */
proc means data=adtr_long(where=(ITTFL="Y" and available=1 and TRT01A="Experimental" and cycle ^= "C1D1"))
    noprint;
  by cycle;
  var pct_change sld;
  output out=visit_exp
    n=pct_n sld_n
    mean=pct_mean sld_mean
    median=pct_median sld_median
    std=pct_std sld_std
    min=pct_min sld_min
    max=pct_max sld_max;
run;

/* Control arm */
proc means data=adtr_long(where=(ITTFL="Y" and available=1 and TRT01A="Control" and cycle ^= "C1D1"))
    noprint;
  by cycle;
  var pct_change sld;
  output out=visit_ctrl
    n=pct_n sld_n
    mean=pct_mean sld_mean
    median=pct_median sld_median
    std=pct_std sld_std
    min=pct_min sld_min
    max=pct_max sld_max;
run;

/* Calculate SE from std and n */
data visit_all_se;
  set visit_all;
  se_pct = pct_std / sqrt(pct_n);
  n_total = &n.;
  n_missing = n_total - pct_n;
  arm = "All";
  keep cycle arm pct_n n_total n_missing pct_mean pct_median se_pct
       sld_mean sld_median pct_min pct_max;
run;

data visit_exp_se;
  set visit_exp;
  se_pct = pct_std / sqrt(pct_n);
  n_total = &n_exp.;
  n_missing = n_total - pct_n;
  arm = "Experimental";
  keep cycle arm pct_n n_total n_missing pct_mean pct_median se_pct
       sld_mean sld_median pct_min pct_max;
run;

data visit_ctrl_se;
  set visit_ctrl;
  se_pct = pct_std / sqrt(pct_n);
  n_total = &n_ctrl.;
  n_missing = n_total - pct_n;
  arm = "Control";
  keep cycle arm pct_n n_total n_missing pct_mean pct_median se_pct
       sld_mean sld_median pct_min pct_max;
run;

data visit_summaries;
  set visit_all_se visit_exp_se visit_ctrl_se;
run;

/* ───────────────────────────────────────────────────── */
/* 3. Per-subject best/worst response summary            */
/* ───────────────────────────────────────────────────── */

/* For each subject, find best (min) and worst (max) pct_change
   across non-baseline visits */
proc sort data=adtr_long(where=(ITTFL="Y" and available=1 and cycle ^= "C1D1"))
    out=adtr_nonbaseline;
  by USUBJID;
run;

/* Best (minimum) % change per subject */
proc means data=adtr_nonbaseline noprint;
  by USUBJID TRT01A;
  var pct_change;
  output out=subject_best
    min=best_pct_change
    max=worst_pct_change
    n=n_assessments;
run;

/* Time to best response: find the cycle at which best_pct_change occurred */
proc sql;
  create table subject_best_cycle as
  select b.USUBJID, b.TRT01A, b.best_pct_change, b.worst_pct_change,
         b.n_assessments,
         (select a.cycle from adtr_nonbaseline a
          where a.USUBJID = b.USUBJID and a.pct_change = b.best_pct_change
          fetch first 1 rows only) as time_to_best_cycle,
         (select a.cycle from adtr_nonbaseline a
          where a.USUBJID = b.USUBJID and a.pct_change = b.worst_pct_change
          fetch first 1 rows only) as time_to_worst_cycle
  from subject_best b;
quit;

/* ───────────────────────────────────────────────────── */
/* 4. Overall arm-level summaries                        */
/* ───────────────────────────────────────────────────── */

proc means data=subject_best_cycle noprint;
  by TRT01A;
  var best_pct_change worst_pct_change n_assessments;
  output out=overall_summary
    mean(best_pct_change)=mean_best_pct_change
    median(best_pct_change)=median_best_pct_change
    mean(worst_pct_change)=mean_worst_pct_change
    median(worst_pct_change)=median_worst_pct_change
    mean(n_assessments)=mean_n_assessments
    n(best_pct_change)=n_subjects;
run;

/* ───────────────────────────────────────────────────── */
/* 5. N assessed per visit per arm                       */
/* ───────────────────────────────────────────────────── */

proc freq data=adtr_long(where=(ITTFL="Y" and available=1)) noprint;
  tables cycle * TRT01A / out=visit_counts;
run;

/* ───────────────────────────────────────────────────── */
/* 6. Build JSON output                                  */
/* ───────────────────────────────────────────────────── */
/* NOTE: Full JSON construction in SAS requires DATA step JSON building
   or PROC JSON with custom templates. The above establishes the
   statistical computations.

   Key output values that would be placed in the JSON:

   visit_summaries:
     For each cycle (C1D1-C6D1) and arm (All/Experimental/Control):
       - n_total, n_assessed, n_missing
       - mean_pct_change, median_pct_change, se_pct_change
       - mean_sld, median_sld
       - min_pct_change, max_pct_change

   overall_summary:
     For each arm (Experimental/Control):
       - n_subjects
       - mean_best_pct_change, median_best_pct_change
       - mean_worst_pct_change, median_worst_pct_change
       - mean_n_assessments

   subject_summaries:
     For each subject:
       - USUBJID, TRT01A
       - best_pct_change, worst_pct_change
       - time_to_best_cycle, time_to_worst_cycle
       - n_assessments
 */

/* Optional: ARS envelope output would follow the same pattern as the R
   implementation, wrapping the key statistics in CDISC ARS v1.0 structure. */
