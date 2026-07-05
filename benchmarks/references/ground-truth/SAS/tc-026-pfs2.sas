/*
 * TC-026: Time to Second Progression (PFS2) — SAS Reference Implementation
 * Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark
 *
 * PFS2 is defined as the time from randomization to the second disease
 * progression or death, whichever comes first. Unlike PFS (TC-001) which
 * captures time to first progression/death, PFS2 captures the total
 * duration of disease control including post-progression benefit.
 *
 * This tests:
 *   1. Correct identification of PFS2 endpoint (second progression, not first)
 *   2. Handling of subjects without first progression (cannot have PFS2 event)
 *   3. KM median estimation with complex censoring
 *   4. Log-rank test and Cox PH HR
 *   5. Subgroup analysis (SEX, AGEGR1, ECOG)
 *
 * Dependencies: Base SAS, PROC LIFETEST, PROC PHREG
 * NOTE: Reference implementation — not executed (no SAS license available)
 *
 * Usage: %let seed=42; %let n=200; %include "tc-026-pfs2.sas";
 */

/* ───────────────────────────────────────────────────── */
/* 1. Generate synthetic PFS2 ADTTE data                  */
/* ───────────────────────────────────────────────────── */

%let seed = 42;
%let n = 200;

data adtte_pfs2;
  call streaminit(&seed.);
  length TRT01A $12 SEX $1 AGEGR1 $4 ECOG $1 PARAMCD $4 PARAM $35;
  base_rate = log(2) / 9.0;  /* median PFS2 control = 9 months */

  do i = 1 to &n.;
    USUBJID = put(i, z4.);
    STUDYID = "BENCHMARK-001";

    /* Treatment assignment */
    TRT01PN = rand("Bernoulli", 0.5);
    if TRT01PN = 1 then TRT01A = "Experimental";
    else TRT01A = "Placebo";

    /* Hazard multiplier */
    if TRT01PN = 0 then hazard_mult = 1.0;
    else hazard_mult = 0.65;

    /* Time to first progression */
    prog1_time = rand("Exponential") / (base_rate * 1.5 * hazard_mult);

    /* Additional time from first to second progression */
    prog2_gap = rand("Exponential") / (base_rate * 0.8 * hazard_mult);

    /* Absolute time of second progression */
    prog2_time = prog1_time + prog2_gap;

    /* Time to death */
    death_time = rand("Exponential") / (base_rate * 0.4 * hazard_mult);

    /* Censoring (lost to follow-up, study end) */
    cens_time = rand("Exponential") / (base_rate * 0.15);

    /* Determine observed time and event */
    if prog1_time > cens_time then do;
      /* No first progression observed (censored before first progression) */
      AVAL = cens_time;
      CNSR = 1;  /* censored */
    end;
    else do;
      /* First progression observed; check second prog vs death vs censoring */
      t2 = min(prog2_time, death_time);
      if t2 <= cens_time then do;
        AVAL = t2;
        CNSR = 0;  /* event (second progression or death) */
      end;
      else do;
        AVAL = cens_time;
        CNSR = 1;  /* censored */
      end;
    end;

    AVAL = round(AVAL, 0.01);

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

    if rand("Uniform") < 0.98 then SAFFL = "Y";
    else SAFFL = "N";

    PARAMCD = "PFS2";
    PARAM = "Progression-Free Survival 2";

    output;
  end;

  drop i base_rate hazard_mult prog1_time prog2_gap prog2_time
       death_time cens_time t2 age;
run;

/* ───────────────────────────────────────────────────── */
/* 2. KM Median PFS2 by Arm (ITT population)            */
/* ───────────────────────────────────────────────────── */

/* Control arm (TRT01PN=0) */
proc lifetest data=adtte_pfs2(where=(ITTFL="Y" and TRT01PN=0))
    method=km confband=loglog outsurv=_null_;
  time AVAL * CNSR(1);
  ods output Quartiles=ctrl_quartiles;
run;

/* Experimental arm (TRT01PN=1) */
proc lifetest data=adtte_pfs2(where=(ITTFL="Y" and TRT01PN=1))
    method=km confband=loglog outsurv=_null_;
  time AVAL * CNSR(1);
  ods output Quartiles=exp_quartiles;
run;

/* ───────────────────────────────────────────────────── */
/* 3. Log-rank test (treatment comparison)               */
/* ───────────────────────────────────────────────────── */

proc lifetest data=adtte_pfs2(where=(ITTFL="Y")) method=km;
  strata TRT01PN;
  time AVAL * CNSR(1);
  ods output HomTests=lr_test;
run;

/* ───────────────────────────────────────────────────── */
/* 4. Cox PH model for Hazard Ratio                      */
/* ───────────────────────────────────────────────────── */

proc phreg data=adtte_pfs2(where=(ITTFL="Y"));
  class TRT01PN (ref="0");
  model AVAL * CNSR(1) = TRT01PN / ties=efron risklimits;
  ods output ParameterEstimates=cox_est;
run;

/* ───────────────────────────────────────────────────── */
/* 5. Subgroup analysis: SEX, AGEGR1, ECOG               */
/* ───────────────────────────────────────────────────── */

%macro subgroup_analysis(var);
  proc sort data=adtte_pfs2(where=(ITTFL="Y")) out=sub_&var.;
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

proc freq data=adtte_pfs2(where=(ITTFL="Y"));
  tables CNSR / out=cens_summary;
run;

/* ───────────────────────────────────────────────────── */
/* 7. Build JSON output                                  */
/* ───────────────────────────────────────────────────── */

/* Extract median PFS2 and CI for control arm */
data ctrl_median;
  set ctrl_quartiles;
  where Percent = 50;
  median_pfs2 = Estimate;
  ci_lower = LowerLimit;
  ci_upper = UpperLimit;
  keep median_pfs2 ci_lower ci_upper;
run;

/* Extract median PFS2 and CI for experimental arm */
data exp_median;
  set exp_quartiles;
  where Percent = 50;
  median_pfs2 = Estimate;
  ci_lower = LowerLimit;
  ci_upper = UpperLimit;
  keep median_pfs2 ci_lower ci_upper;
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

/* NOTE: Full JSON construction in SAS requires DATA step JSON building
   or PROC JSON with custom templates. The above establishes the
   statistical computations. */
