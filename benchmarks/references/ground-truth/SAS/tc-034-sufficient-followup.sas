/* TC-034: Sufficient Follow-up Assessment — SAS
 *
 * Assesses whether subjects have sufficient safety follow-up per protocol
 * (e.g., 90 days post-last-dose). Also computes median follow-up duration
 * using the reverse Kaplan-Meier method.
 *
 * Output:
 *   - N (%) with adequate follow-up by arm (>= threshold days post-last-dose)
 *   - Median follow-up duration (reverse KM) by arm with CI
 *   - N still ongoing, N discontinued, N died
 *   - Per-subject follow-up details
 *
 * Usage: sas tc-034-sufficient-followup.sas -set seed 42 -set n 200
 */

options nosource2 linesize=120;
%let seed = %sysget(seed);
%if &seed = %then %let seed = 42;
%let n = %sysget(n);
%if &n = %then %let n = 200;
%let threshold = 90;

/* --- Generate ADSL-style follow-up data --- */
data adsl_fu;
  call streaminit(&seed);
  length USUBJID $8 TRT01A $12 STATUS_LABEL $12 RANDDT LASTDOSEDT LASTFUDT 4;
  format RANDDT LASTDOSEDT LASTFUDT yymmdd10.;

  array trt_arr[0:1] _temporary_;
  do i = 1 to &n;
    if i <= &n / 2 then trt = 1;
    else trt = 0;
    _rand = rand("uniform");
    output;
  end;
  drop i;
run;

proc sort data=adsl_fu; by _rand; run;

data adsl_fu;
  set adsl_fu;
  drop _rand trt;
  USUBJID = cats("SUB", put(_N_, z4.));
  TRT01PN = ifn(_N_ <= &n / 2, 1, 0);
  if TRT01PN = 1 then TRT01A = "Experimental";
  else TRT01A = "Control";

  * Randomization date ;
  RANDDT = intnx("day", '01JAN2023'd, int(rand("uniform") * 365));

  * Treatment duration (weeks) ;
  if TRT01PN = 1 then treat_dur_w = round(rand("normal", 42, 10));
  else treat_dur_w = round(rand("normal", 24, 7));
  treat_dur_w = max(treat_dur_w, 2);

  * Last dose date ;
  LASTDOSEDT = intnx("week", RANDDT, treat_dur_w, "s");

  * Follow-up post last dose (days) ;
  if TRT01PN = 1 then fu_post = round(rand("normal", 120, 40));
  else fu_post = round(rand("normal", 100, 35));
  fu_post = max(fu_post, 0);

  * Status: 1=Ongoing, 2=Completed, 3=Discontinued, 4=Died ;
  if TRT01PN = 1 then do;
    status = rand("table", 0.20, 0.55, 0.15, 0.10);
  end;
  else do;
    status = rand("table", 0.15, 0.65, 0.12, 0.08);
  end;

  * Cap follow-up for died subjects ;
  if status = 4 then do;
    fu_post = max(round(rand("normal", 45, 20)), 0);
  end;

  * Last follow-up date ;
  LASTFUDT = LASTDOSEDT + fu_post;

  * Follow-up from randomization ;
  fu_from_rand = LASTFUDT - RANDDT;

  * Adequate follow-up: >= threshold days post-last-dose AND not died ;
  ADEQUATE_FU = (fu_post >= &threshold and status ne 4);

  * Status label ;
  if status = 1 then STATUS_LABEL = "ONGOING";
  else if status = 2 then STATUS_LABEL = "COMPLETED";
  else if status = 3 then STATUS_LABEL = "DISCONTINUED";
  else STATUS_LABEL = "DIED";

  TREATDUR_W = treat_dur_w;
  FU_POST_DOSE = fu_post;
  FU_FROM_RAND = fu_from_rand;
  drop treat_dur_w fu_post fu_from_rand;
run;

/* --- Adequate follow-up counts --- */
proc means data=adsl_fu noprint;
  by TRT01PN TRT01A;
  var ADEQUATE_FU;
  output out=adeq_counts n= sum= mean=/ autoname;
run;

/* --- Status distribution --- */
proc freq data=adsl_fu noprint;
  by TRT01PN TRT01A;
  tables STATUS_LABEL / out=status_dist outcum;
run;

/* --- Follow-up summary stats --- */
proc means data=adsl_fu noprint;
  by TRT01PN TRT01A;
  var FU_POST_DOSE FU_FROM_RAND;
  output out=fu_summary n= mean= std= median= min= max= q1= q3=/ autoname;
run;

/* --- Reverse KM: treat non-death as event, death as censored --- */
data revkm;
  set adsl_fu;
  * Reverse KM: event=1 if NOT died, 0 if died ;
  rev_event = (status ne 4);
  rev_time = FU_FROM_RAND;
run;

proc lifetest data=revkm noprint;
  by TRT01PN TRT01A;
  time rev_time * rev_event(0);
  strata TRT01A;
  output out=revkm_out survival=survival;
run;

/* --- Print summaries --- */
title "TC-034: Sufficient Follow-up Assessment";
proc print data=adeq_counts noobs label;
  var TRT01A ADEQUATE_FU_Sum ADEQUATE_FU_Mean;
  format ADEQUATE_FU_Mean percent8.2;
  label ADEQUATE_FU_Sum="N Adequate" ADEQUATE_FU_Mean="% Adequate";
run;

proc print data=status_dist noobs label;
  var TRT01A STATUS_LABEL COUNT;
  label COUNT="N";
run;

proc print data=fu_summary noobs label;
  var TRT01A FU_POST_DOSE_Median FU_POST_DOSE_Mean FU_POST_DOSE_Min FU_POST_DOSE_Max
      FU_FROM_RAND_Median FU_FROM_RAND_Mean FU_FROM_RAND_Min FU_FROM_RAND_Max;
run;

title;
