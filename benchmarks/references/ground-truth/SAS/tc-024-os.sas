/*
 * TC-024: Overall Survival (OS) — SAS Reference Implementation
 * Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark
 *
 * OS is defined as the time from randomization to death from any cause.
 * Event = death only (not progression, unlike PFS in TC-001).
 * Censoring: alive at data cutoff.
 *
 * This tests:
 *   1. Correct identification of OS endpoint (death event, not progression)
 *   2. KM median estimation with death-only event
 *   3. Log-rank test for treatment comparison
 *   4. Hazard ratio from Cox PH model
 *   5. Subgroup analysis (SEX, AGEGR1, ECOG)
 *
 * Dependencies: Base SAS, PROC LIFETEST, PROC PHREG
 * NOTE: Reference implementation — not executed (no SAS license available)
 *
 * Usage: %let seed=42; %let n=200; %include "tc-024-os.sas";
 */

/* ───────────────────────────────────────────────────── */
/* 1. Generate synthetic OS ADTTE data                   */
/* ───────────────────────────────────────────────────── */

%let seed = 42;
%let n = 200;

data adtte_os;
  call streaminit(&seed.);
  length TRT01A $12 SEX $1 AGEGR1 $4 PARAMCD $2 PARAM $20;
  base_rate = log(2) / 14.0;  /* median OS control = 14 months */

  do i = 1 to &n.;
    USUBJID = put(i, z4.);
    STUDYID = "BENCHMARK-001";

    /* Treatment assignment */
    TRT01PN = rand("Bernoulli", 0.5);
    if TRT01PN = 1 then TRT01A = "Experimental";
    else TRT01A = "Placebo";

    /* Hazard multiplier */
    if TRT01PN = 0 then hazard_mult = 1.0;
    else hazard_mult = 0.75;

    /* Time to death (exponential) */
    death_time = rand("Exponential") / (base_rate * hazard_mult);

    /* Censoring (lost to follow-up, study end) */
    cens_time = rand("Exponential") / (base_rate * 0.2);

    /* Observed time */
    if death_time <= cens_time then do;
      AVAL = death_time;
      CNSR = 0;  /* event (death) */
    end;
    else do;
      AVAL = cens_time;
      CNSR = 1;  /* censored */
    end;

    AVAL = round(AVAL, 0.01);

    /* Stratification factors */
    if rand("Bernoulli", 0.55) = 1 then SEX = "M";
    else SEX = "F";

    age = round(rand("Normal", 58, 12));
    if age < 65 then AGEGR1 = "<65";
    else AGEGR1 = ">=65";

    ECOG = rand("Bernoulli", 0.4);

    /* Flags */
    if rand("Uniform") < 0.95 then ITTFL = "Y";
    else ITTFL = "N";

    if rand("Uniform") < 0.98 then SAFFL = "Y";
    else SAFFL = "N";

    PARAMCD = "OS";
    PARAM = "Overall Survival";

    output;
  end;

  drop i base_rate hazard_mult death_time cens_time age;
run;

/* ───────────────────────────────────────────────────── */
/* 2. KM Median OS by Arm (ITT population)               */
/* ───────────────────────────────────────────────────── */

/* Control arm (TRT01PN=0) */
proc lifetest data=adtte_os(where=(ITTFL="Y" and TRT01PN=0))
    method=km confband=loglog outsurv=_null_;
  time AVAL * CNSR(1);
  ods output Quartiles=ctrl_quartiles;
run;

/* Experimental arm (TRT01PN=1) */
proc lifetest data=adtte_os(where=(ITTFL="Y" and TRT01PN=1))
    method=km confband=loglog outsurv=_null_;
  time AVAL * CNSR(1);
  ods output Quartiles=exp_quartiles;
run;

/* ───────────────────────────────────────────────────── */
/* 3. Log-rank test (treatment comparison)               */
/* ───────────────────────────────────────────────────── */

proc lifetest data=adtte_os(where=(ITTFL="Y")) method=km;
  strata TRT01PN;
  time AVAL * CNSR(1);
  ods output HomTests=lr_test;
run;

/* ───────────────────────────────────────────────────── */
/* 4. Cox PH model for Hazard Ratio                      */
/* ───────────────────────────────────────────────────── */

proc phreg data=adtte_os(where=(ITTFL="Y"));
  class TRT01PN (ref="0");
  model AVAL * CNSR(1) = TRT01PN / ties=efron risklimits;
  ods output ParameterEstimates=cox_est;
run;

/* ───────────────────────────────────────────────────── */
/* 5. Subgroup analysis: SEX, AGEGR1, ECOG               */
/* ───────────────────────────────────────────────────── */

/* Subgroup KM medians by TRT01PN within each subgroup level */
%macro subgroup_analysis(var);
  proc sort data=adtte_os(where=(ITTFL="Y")) out=sub_&var.;
    by &var. TRT01PN;
  run;

  proc lifetest data=sub_&var. method=km;
    strata TRT01PN;
    time AVAL * CNSR(1);
    by &var.;
    ods output Quartiles=sub_&var._q;
  run;

  proc phreg data=sub_&var.;
    class TRT01PN (ref="0");
    model AVAL * CNSR(1) = TRT01PN / ties=efron risklimits;
    by &var.;
    ods output ParameterEstimates=sub_&var._cox;
  run;
%mend;

%subgroup_analysis(SEX);
%subgroup_analysis(AGEGR1);
%subgroup_analysis(ECOG);

/* ───────────────────────────────────────────────────── */
/* 6. Censoring summary                                  */
/* ───────────────────────────────────────────────────── */

proc freq data=adtte_os(where=(ITTFL="Y"));
  tables CNSR / out=cens_summary;
run;

/* ───────────────────────────────────────────────────── */
/* 7. Build JSON output                                  */
/* ───────────────────────────────────────────────────── */

/* Extract median OS and CI for control arm */
data ctrl_median;
  set ctrl_quartiles;
  where Percent = 50;
  median_os = Estimate;
  ci_lower = LowerLimit;
  ci_upper = UpperLimit;
  keep median_os ci_lower ci_upper;
run;

/* Extract median OS and CI for experimental arm */
data exp_median;
  set exp_quartiles;
  where Percent = 50;
  median_os = Estimate;
  ci_lower = LowerLimit;
  ci_upper = UpperLimit;
  keep median_os ci_lower ci_upper;
run;

/* Extract log-rank p-value */
data lr_p;
  set lr_test;
  where Test = "Log-Rank";
  logrank_chisq = ChiSquare;
  logrank_p = ProbChiSq;
  keep logrank_chisq logrank_p;
run;

/* Extract HR and CI from Cox model */
data hr_est;
  set cox_est;
  hazard_ratio = ExpEst;
  hr_ci_lower = LowerExpEst;
  hr_ci_upper = UpperExpEst;
  keep hazard_ratio hr_ci_lower hr_ci_upper;
run;

/* Combine into final JSON using PROC JSON */
data _null_;
  file _webout;
  put '{"test_case_id":"TC-024","endpoint":"Overall Survival","language":"SAS"}';
run;

/* NOTE: Full JSON construction in SAS requires DATA step JSON building
   or PROC JSON with custom templates. The above establishes the
   statistical computations. A complete JSON builder would follow
   the same pattern as tc-023-dcr.sas. */
