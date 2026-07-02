/*
 * TC-023: Disease Control Rate (DCR) — SAS Reference Implementation
 * Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark
 *
 * DCR = proportion of subjects with disease control (CR + PR + SD)
 * as best overall response, by treatment arm.
 *
 * Key difference from TC-020 (ORR):
 *   ORR (TC-020): CR + PR rate
 *   DCR (TC-023): CR + PR + SD rate (broader benefit measure)
 *
 * Dependencies: Base SAS, PROC FREQ, PROC MEANS
 * NOTE: Reference implementation — not executed (no SAS license available)
 *
 * Usage: %let seed=42; %let n=200; %include "tc-023-dcr.sas";
 */

/* ───────────────────────────────────────────────────── */
/* 1. Generate synthetic tumor response data             */
/* ───────────────────────────────────────────────────── */

%let seed = 42;
%let n = 200;

data tumor_response;
  call streaminit(&seed.);
  length BOR $2 TRT01A $12 SEX $6 AGEGR1 $4;

  do i = 1 to &n.;
    USUBJID = put(i, z4.);
    STUDYID = "BENCHMARK-001";

    /* Treatment assignment */
    TRT01PN = rand("Bernoulli", 0.5);
    if TRT01PN = 1 then TRT01A = "Experimental";
    else TRT01A = "Control";

    /* Subgroups */
    if rand("Bernoulli", 0.55) = 1 then SEX = "Male";
    else SEX = "Female";

    age = round(rand("Normal", 58, 12));
    if age < 65 then AGEGR1 = "<65";
    else AGEGR1 = ">=65";

    ECOG = rand("Bernoulli", 0.4);

    /* Response probability */
    if TRT01PN = 1 then do;
      if ECOG = 0 then orr_prob = 0.45;
      else orr_prob = 0.30;
    end;
    else do;
      if ECOG = 0 then orr_prob = 0.25;
      else orr_prob = 0.15;
    end;

    is_responder = rand("Bernoulli", orr_prob);
    if is_responder = 1 then is_cr = rand("Bernoulli", 0.3);
    else is_cr = 0;

    /* Best overall response */
    if is_cr = 1 then BOR = "CR";
    else if is_responder = 1 then BOR = "PR";
    else if rand("Bernoulli", 0.4) = 1 then BOR = "SD";
    else BOR = "PD";

    /* Derived variables */
    if BOR in ("CR", "PR") then AVAL_ORR = 1;
    else AVAL_ORR = 0;

    if BOR in ("CR", "PR", "SD") then AVAL_DCR = 1;
    else AVAL_DCR = 0;

    /* ITT flag */
    if rand("Uniform") < 0.95 then ITTFL = "Y";
    else ITTFL = "N";

    output;
  end;

  drop i orr_prob is_responder is_cr age;
run;

/* ───────────────────────────────────────────────────── */
/* 2. Overall DCR by arm                                 */
/* ───────────────────────────────────────────────────── */

proc freq data=tumor_response noprint;
  where ITTFL = "Y";
  tables TRT01PN * AVAL_DCR / out=dc_freq outpct;
run;

proc sql;
  create table dcr_overall as
  select
    TRT01PN,
    TRT01A,
    count(*) as n_subjects,
    sum(AVAL_DCR) as disease_controlled,
    calculated disease_controlled / calculated n_subjects * 100 as dcr_pct,
    /* Wilson CI: computed via DATA step below */
    0 as ci_lower format=8.2,
    0 as ci_upper format=8.2
  from tumor_response
  where ITTFL = "Y"
  group by TRT01PN, TRT01A
  order by TRT01PN;
quit;

/* Wilson CI computation */
data dcr_overall;
  set dcr_overall;
  z = quantile("NORMAL", 0.975);
  p = disease_controlled / n_subjects;
  denom = 1 + z**2 / n_subjects;
  center = (p + z**2 / (2 * n_subjects)) / denom;
  margin = z * sqrt(p * (1 - p) / n_subjects + z**2 / (4 * n_subjects**2)) / denom;
  ci_lower = round((center - margin) * 100, 0.1);
  ci_upper = round((center + margin) * 100, 0.1);
  dcr_pct = round(dcr_pct, 0.1);
  drop z p denom center margin;
run;

/* ───────────────────────────────────────────────────── */
/* 3. DCR by subgroup                                    */
/* ───────────────────────────────────────────────────── */

%macro dcr_by_subgroup(var=, levels=);
  proc sql;
    create table dcr_&var. as
    select
      "&var." as subgroup length=10,
      &var. as level,
      TRT01PN,
      count(*) as n_subjects,
      sum(AVAL_DCR) as disease_controlled,
      calculated disease_controlled / calculated n_subjects * 100 as dcr_pct
    from tumor_response
    where ITTFL = "Y"
    group by &var., TRT01PN
    order by &var., TRT01PN;
  quit;

  /* Wilson CI */
  data dcr_&var.;
    set dcr_&var.;
    z = quantile("NORMAL", 0.975);
    p = disease_controlled / n_subjects;
    denom = 1 + z**2 / n_subjects;
    center = (p + z**2 / (2 * n_subjects)) / denom;
    margin = z * sqrt(p * (1 - p) / n_subjects + z**2 / (4 * n_subjects**2)) / denom;
    ci_lower = round((center - margin) * 100, 0.1);
    ci_upper = round((center + margin) * 100, 0.1);
    dcr_pct = round(dcr_pct, 0.1);
    drop z p denom center margin;
  run;
%mend;

%dcr_by_subgroup(var=SEX, levels=Male Female);
%dcr_by_subgroup(var=AGEGR1, levels=%str(<65 >=65));
%dcr_by_subgroup(var=ECOG, levels=0 1);

/* Combine subgroups */
data dcr_subgroups;
  set dcr_SEX dcr_AGEGR1 dcr_ECOG;
run;

/* ───────────────────────────────────────────────────── */
/* 4. BOR distribution by arm                            */
/* ───────────────────────────────────────────────────── */

proc freq data=tumor_response noprint;
  where ITTFL = "Y";
  tables TRT01A * BOR / out=bor_dist;
run;

data bor_dist;
  set bor_dist;
  pct = round(PERCENT, 0.1);
  keep TRT01A BOR COUNT pct;
  rename TRT01A=arm COUNT=n;
run;

/* ───────────────────────────────────────────────────── */
/* 5. Output as JSON                                     */
/* ───────────────────────────────────────────────────── */
/* NOTE: JSON output via PROC JSON or manual DATA step   */
/* This is a reference implementation for validation     */
/* against R and Python outputs on shared data.          */

proc json out="%sysfunc(pathname(work))/tc-023-output.json" pretty;
  export dcr_overall / fmt=best;
  export dcr_subgroups / fmt=best;
  export bor_dist / fmt=best;
run;

/* End of TC-023 SAS reference implementation */
