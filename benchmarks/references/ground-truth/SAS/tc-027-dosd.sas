/*
 * TC-027: Duration of Stable Disease (DOSD) — SAS Reference Implementation
 * Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark
 *
 * DOSD is defined as the time from first documentation of Stable Disease (SD)
 * to disease progression or death, among subjects whose Best Overall Response
 * is SD. This is a subset analysis on a non-trivial population (typically
 * 30-45% of ITT).
 *
 * Key distinctions from other time-to-event TCs:
 *   DOR (TC-022): Responders only (CR+PR), time from response to PD/death
 *   DOSD (TC-027): SD subjects only, time from SD documentation to PD/death
 *                  DOSD subjects and DOR subjects are disjoint (SD vs CR+PR)
 *
 * This tests:
 *   1. Correct subset identification (BOR = SD only, not CR/PR/PD/NE)
 *   2. Time-to-event analysis on a non-trivial subset
 *   3. KM estimation with small-to-moderate sample sizes
 *   4. Cross-TFL consistency: DOSD N = SD count from TC-025 BOR Summary
 *   5. DOSD N <= DCR N (TC-023, since SD is a subset of DCR)
 *
 * Dependencies: Base SAS, PROC LIFETEST, PROC PHREG
 * NOTE: Reference implementation — not executed (no SAS license available)
 *
 * Usage: %let seed=42; %let n=200; %include "tc-027-dosd.sas";
 */

/* ───────────────────────────────────────────────────── */
/* 1. Generate synthetic DOSD ADTTE data                 */
/* ───────────────────────────────────────────────────── */

%let seed = 42;
%let n = 200;

data adtte_dosd;
  call streaminit(&seed.);
  length TRT01A $12 SEX $1 AGEGR1 $4 ECOG $1 BOR $2 PARAMCD $4 PARAM $30;
  base_rate = log(2) / 4.5;  /* median DOSD control = 4.5 months */

  do i = 1 to &n.;
    USUBJID = put(i, z4.);
    STUDYID = "BENCHMARK-001";

    /* Treatment assignment */
    TRT01PN = rand("Bernoulli", 0.5);
    if TRT01PN = 1 then TRT01A = "Experimental";
    else TRT01A = "Placebo";

    /* Hazard multiplier */
    if TRT01PN = 0 then hazard_mult = 1.0;
    else hazard_mult = 0.80;

    /* BOR distribution consistent with TC-025 */
    /* Control: CR 2%, PR 18%, SD 45%, PD 30%, NE 5% */
    /* Active: CR 8%, PR 35%, SD 35%, PD 15%, NE 7% */
    r_bor = rand("Uniform");
    if TRT01PN = 0 then do;
      if r_bor < 0.02 then BOR = "CR";
      else if r_bor < 0.20 then BOR = "PR";
      else if r_bor < 0.65 then BOR = "SD";
      else if r_bor < 0.95 then BOR = "PD";
      else BOR = "NE";
    end;
    else do;
      if r_bor < 0.08 then BOR = "CR";
      else if r_bor < 0.43 then BOR = "PR";
      else if r_bor < 0.78 then BOR = "SD";
      else if r_bor < 0.93 then BOR = "PD";
      else BOR = "NE";
    end;

    /* Time to SD documentation (from randomization): ~1-3 months */
    if BOR = "SD" then do;
      time_to_sd = rand("Exponential") / (1.0 / 1.5);
    end;
    else do;
      time_to_sd = .;
    end;

    /* Time from SD documentation to progression or death */
    prog_time = rand("Exponential") / (base_rate * hazard_mult);
    death_time = rand("Exponential") / (base_rate * 0.3 * hazard_mult);
    cens_time = rand("Exponential") / (base_rate * 0.3 / 0.7);

    /* Event time from randomization = time_to_sd + time from SD to event */
    event_from_sd = min(prog_time, death_time);

    /* DOSD time = time from SD documentation to event or censoring */
    /* Only meaningful for SD subjects */
    if BOR = "SD" then do;
      event_time_abs = time_to_sd + event_from_sd;
      if event_time_abs <= cens_time then do;
        AVAL = event_from_sd;
        CNSR = 0;  /* event */
      end;
      else do;
        AVAL = cens_time - time_to_sd;
        CNSR = 1;  /* censored */
      end;
    end;
    else do;
      AVAL = .;
      CNSR = .;
    end;

    if not missing(AVAL) then AVAL = round(AVAL, 0.01);

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

    PARAMCD = "DOSD";
    PARAM = "Duration of Stable Disease";

    output;
  end;

  drop i base_rate hazard_mult r_bor time_to_sd prog_time death_time
       cens_time event_from_sd event_time_abs age;
run;

/* ───────────────────────────────────────────────────── */
/* 2. KM Median DOSD by Arm (SD subjects, ITT population) */
/* ───────────────────────────────────────────────────── */

/* Control arm SD subjects (TRT01PN=0) */
proc lifetest data=adtte_dosd(where=(ITTFL="Y" and TRT01PN=0 and BOR="SD" and not missing(AVAL)))
    method=km confband=loglog outsurv=_null_;
  time AVAL * CNSR(1);
  ods output Quartiles=ctrl_quartiles;
run;

/* Experimental arm SD subjects (TRT01PN=1) */
proc lifetest data=adtte_dosd(where=(ITTFL="Y" and TRT01PN=1 and BOR="SD" and not missing(AVAL)))
    method=km confband=loglog outsurv=_null_;
  time AVAL * CNSR(1);
  ods output Quartiles=exp_quartiles;
run;

/* ───────────────────────────────────────────────────── */
/* 3. Log-rank test (treatment comparison among SD subjects) */
/* ───────────────────────────────────────────────────── */

proc lifetest data=adtte_dosd(where=(ITTFL="Y" and BOR="SD" and not missing(AVAL))) method=km;
  strata TRT01PN;
  time AVAL * CNSR(1);
  ods output HomTests=lr_test;
run;

/* ───────────────────────────────────────────────────── */
/* 4. Cox PH model for Hazard Ratio                      */
/* ───────────────────────────────────────────────────── */

proc phreg data=adtte_dosd(where=(ITTFL="Y" and BOR="SD" and not missing(AVAL)));
  class TRT01PN (ref="0");
  model AVAL * CNSR(1) = TRT01PN / ties=efron risklimits;
  ods output ParameterEstimates=cox_est;
run;

/* ───────────────────────────────────────────────────── */
/* 5. Subgroup analysis: SEX, AGEGR1, ECOG               */
/* ───────────────────────────────────────────────────── */

%macro subgroup_analysis(var);
  proc sort data=adtte_dosd(where=(ITTFL="Y" and BOR="SD" and not missing(AVAL))) out=sub_&var.;
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
/* 6. BOR and SD subject summary                         */
/* ───────────────────────────────────────────────────── */

proc freq data=adtte_dosd(where=(ITTFL="Y"));
  tables BOR * TRT01PN / out=bor_summary;
run;

proc freq data=adtte_dosd(where=(ITTFL="Y" and BOR="SD"));
  tables TRT01PN / out=sd_subjects;
run;

/* ───────────────────────────────────────────────────── */
/* 7. Build JSON output                                  */
/* ───────────────────────────────────────────────────── */

/* Extract median DOSD and CI for control arm */
data ctrl_median;
  set ctrl_quartiles;
  where Percent = 50;
  median_dosd = Estimate;
  ci_lower = LowerLimit;
  ci_upper = UpperLimit;
  keep median_dosd ci_lower ci_upper;
run;

/* Extract median DOSD and CI for experimental arm */
data exp_median;
  set exp_quartiles;
  where Percent = 50;
  median_dosd = Estimate;
  ci_lower = LowerLimit;
  ci_upper = UpperLimit;
  keep median_dosd ci_lower ci_upper;
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
