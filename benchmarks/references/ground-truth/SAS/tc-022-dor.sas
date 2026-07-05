/*
 * TC-022: Duration of Response (DOR) — SAS Reference Implementation
 * Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark
 *
 * DOR is defined as the time from first documented response (CR or PR)
 * to disease progression or death, among subjects who achieved a response.
 *
 * Key differences from TC-001 (PFS) and TC-021 (TTP):
 *   PFS (TC-001): All subjects, event = progression OR death
 *   TTP (TC-021): All subjects, event = progression only (death censored)
 *   DOR (TC-022): Responders only, event = progression OR death
 *                 Left-truncated: entry time = time to first response
 *
 * This tests:
 *   1. Correct subsetting to responder population (CR + PR)
 *   2. KM estimation on a selected subset (not full ITT)
 *   3. Handling of left truncation (response occurs after randomization)
 *
 * Dependencies: Base SAS, PROC LIFETEST, PROC PHREG
 * NOTE: Reference implementation — not executed (no SAS license available)
 *
 * Usage: %let seed=42; %let n=200; %include "tc-022-dor.sas";
 */

/* ───────────────────────────────────────────────────── */
/* 1. Generate synthetic DOR ADTTE data                   */
/* ───────────────────────────────────────────────────── */

%let seed = 42;
%let n = 200;

data adtte_dor;
  call streaminit(&seed.);
  length TRT01A $12 SEX $1 AGEGR1 $4 ECOG $1 BOR $2 PARAMCD $3 PARAM $25;
  base_rate = log(2) / 6.0;  /* median PFS control = 6 months */

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

    /* Response probability depends on treatment */
    if TRT01PN = 1 then orr_prob = 0.40;
    else orr_prob = 0.20;

    is_responder = rand("Bernoulli", orr_prob);

    /* Time to first response (among responders): exp mean ~2 months */
    if is_responder = 1 then do;
      time_to_response = rand("Exponential") / (1.0 / 2.0);
    end;
    else do;
      time_to_response = .;
    end;

    /* Time to progression or death (from randomization) */
    prog_time = rand("Exponential") / (base_rate * hazard_mult);
    death_time = rand("Exponential") / (base_rate * 0.3 * hazard_mult);
    cens_time = rand("Exponential") / (base_rate * 0.3 / 0.7);

    /* Event time from randomization (progression or death) */
    event_time_from_rand = min(prog_time, death_time);

    /* DOR only for responders with event after response */
    if is_responder = 1 and event_time_from_rand > time_to_response then do;
      if cens_time > time_to_response and cens_time < event_time_from_rand then do;
        /* Censored before event but after response */
        AVAL = cens_time - time_to_response;
        CNSR = 1;
      end;
      else do;
        /* Event occurred */
        AVAL = event_time_from_rand - time_to_response;
        CNSR = 0;
      end;
      BOR = ifc(rand("Uniform") < 0.5, "CR", "PR");
    end;
    else if is_responder = 1 then do;
      /* Responder but event/censoring before response — not analyzable */
      AVAL = .;
      CNSR = .;
      BOR = ifc(rand("Uniform") < 0.5, "CR", "PR");
    end;
    else do;
      AVAL = .;
      CNSR = .;
      BOR = "NE";
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

    PARAMCD = "DOR";
    PARAM = "Duration of Response";

    output;
  end;

  drop i base_rate hazard_mult orr_prob is_responder time_to_response
       prog_time death_time cens_time event_time_from_rand age;
run;

/* ───────────────────────────────────────────────────── */
/* 2. KM Median DOR by Arm (Responders only)             */
/* ───────────────────────────────────────────────────── */

/* Control arm responders (TRT01PN=0) */
proc lifetest data=adtte_dor(where=(ITTFL="Y" and TRT01PN=0 and not missing(AVAL)))
    method=km confband=loglog outsurv=_null_;
  time AVAL * CNSR(1);
  ods output Quartiles=ctrl_quartiles;
run;

/* Experimental arm responders (TRT01PN=1) */
proc lifetest data=adtte_dor(where=(ITTFL="Y" and TRT01PN=1 and not missing(AVAL)))
    method=km confband=loglog outsurv=_null_;
  time AVAL * CNSR(1);
  ods output Quartiles=exp_quartiles;
run;

/* ───────────────────────────────────────────────────── */
/* 3. Log-rank test (treatment comparison among responders) */
/* ───────────────────────────────────────────────────── */

proc lifetest data=adtte_dor(where=(ITTFL="Y" and not missing(AVAL))) method=km;
  strata TRT01PN;
  time AVAL * CNSR(1);
  ods output HomTests=lr_test;
run;

/* ───────────────────────────────────────────────────── */
/* 4. Cox PH model for Hazard Ratio                      */
/* ───────────────────────────────────────────────────── */

proc phreg data=adtte_dor(where=(ITTFL="Y" and not missing(AVAL)));
  class TRT01PN (ref="0");
  model AVAL * CNSR(1) = TRT01PN / ties=efron risklimits;
  ods output ParameterEstimates=cox_est;
run;

/* ───────────────────────────────────────────────────── */
/* 5. Subgroup analysis: SEX, AGEGR1, ECOG               */
/* ───────────────────────────────────────────────────── */

%macro subgroup_analysis(var);
  proc sort data=adtte_dor(where=(ITTFL="Y" and not missing(AVAL))) out=sub_&var.;
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
/* 6. Responder summary                                  */
/* ───────────────────────────────────────────────────── */

proc freq data=adtte_dor(where=(ITTFL="Y"));
  tables BOR * TRT01PN / out=responder_summary;
run;

/* ───────────────────────────────────────────────────── */
/* 7. Build JSON output                                  */
/* ───────────────────────────────────────────────────── */

/* Extract median DOR and CI for control arm */
data ctrl_median;
  set ctrl_quartiles;
  where Percent = 50;
  median_dor = Estimate;
  ci_lower = LowerLimit;
  ci_upper = UpperLimit;
  keep median_dor ci_lower ci_upper;
run;

/* Extract median DOR and CI for experimental arm */
data exp_median;
  set exp_quartiles;
  where Percent = 50;
  median_dor = Estimate;
  ci_lower = LowerLimit;
  ci_upper = UpperLimit;
  keep median_dor ci_lower ci_upper;
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
