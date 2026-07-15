/* TC-031: Time-to-First-Treatment — SAS
 *
 * Time from randomization to first dose of study treatment.
 * Subjects who never receive treatment are censored at their follow-up time.
 *
 * Output:
 *   - KM median time-to-first-treatment by arm with CI
 *   - Log-rank p-value (treatment arm comparison)
 *   - Cox HR for treatment arm
 *   - N received treatment, N censored by arm
 *   - TTT summary statistics by arm (mean, median, range)
 *   - Per-subject TTT details
 *
 * Usage: sas tc-031-time-to-first-treatment.sas -set seed 42 -set n 200
 */

options nosource2 linesize=120;
%let seed = %sysget(seed);
%if &seed = %then %let seed = 42;
%let n = %sysget(n);
%if &n = %then %let n = 200;
%let outpath = .;

/* --- Generate ADSL-style TTT data --- */
data adsl_ttt;
  call streaminit(&seed);
  length USUBJID $8 TRT01A $12 RANDDT FIRSTDOSEDT 4;
  format RANDDT FIRSTDOSEDT yymmdd10.;

  array trt_arr[0:1] _temporary_;
  do i = 1 to &n;
    if i <= &n / 2 then trt = 1;
    else trt = 0;
    _rand = rand("uniform");
    output;
  end;
  drop i;
run;

proc sort data=adsl_ttt; by _rand; run;

data adsl_ttt;
  set adsl_ttt;
  drop _rand trt;
  USUBJID = cats("SUB", put(_N_, z4.));
  TRT01PN = ifn(_N_ <= &n / 2, 1, 0);
  if TRT01PN = 1 then TRT01A = "Experimental";
  else TRT01A = "Control";

  * Randomization date;
  RANDDT = intnx("day", '01JAN2023'd, int(rand("uniform") * 365));

  * Time-to-first-treatment (days);
  if TRT01PN = 1 then ttt_days = round(rand("normal", 3, 2));
  else ttt_days = round(rand("normal", 5, 3));
  ttt_days = max(ttt_days, 0);

  * Some subjects never receive treatment (~5%);
  if rand("uniform") < 0.05 then do;
    received_tx = 0;
    cnsr_ttt = 1;
    * Censored at follow-up time;
    ttt_days = max(round(rand("normal", 180, 60)), 30);
    FIRSTDOSEDT = .;
  end;
  else do;
    received_tx = 1;
    cnsr_ttt = 0;
    FIRSTDOSEDT = RANDDT + ttt_days;
  end;

  * TTT in months;
  ttt_months = round(ttt_days / 30.4375, 0.0001);

  * Stratification factors;
  if rand("uniform") < 0.5 then sex = "M"; else sex = "F";
  if rand("uniform") < 0.5 then agegr1 = "<65"; else agegr1 = ">=65";
  ecog = ifn(rand("uniform") < 0.6, 0, 1);

  * Flags;
  if rand("uniform") < 0.95 then ittfl = "Y"; else ittfl = "N";
  if rand("uniform") < 0.98 then saffl = "Y"; else saffl = "N";

  TTT_DAYS = ttt_days;
  TTT_MONTHS = ttt_months;
  RECEIVED_TX = received_tx;
  CNSR_TTT = cnsr_ttt;
  drop ttt_days ttt_months received_tx cnsr_ttt;
run;

/* --- ITT population --- */
data analysis;
  set adsl_ttt;
  where ittfl = "Y";
run;

/* --- KM estimation per arm using PROC LIFETEST --- */
ods output Quartiles=quartiles_exp ProductLimitEstimates=_ple_exp;
proc lifetest data=analysis(where=(TRT01PN = 1)) conftype=loglog;
  time TTT_DAYS * CNSR_TTT(1);
run;
ods output close;

ods output Quartiles=quartiles_ctl ProductLimitEstimates=_ple_ctl;
proc lifetest data=analysis(where=(TRT01PN = 0)) conftype=loglog;
  time TTT_DAYS * CNSR_TTT(1);
run;
ods output close;

/* --- Log-rank test (both arms) --- */
ods output HomTests=lr_test;
proc lifetest data=analysis conftype=loglog;
  time TTT_DAYS * CNSR_TTT(1);
  strata TRT01A / test=logrank;
run;
ods output close;

/* --- Cox proportional hazards --- */
ods output ParameterEstimates=cox_est HazardRatios=cox_hr;
proc phreg data=analysis;
  class TRT01PN;
  model TTT_DAYS * CNSR_TTT(1) = TRT01PN;
  hazardratio TRT01PN;
run;
ods output close;

/* --- TTT summary stats --- */
proc means data=analysis noprint;
  by TRT01PN TRT01A;
  var TTT_DAYS;
  output out=ttt_summary n= mean= std= median= min= max= q1= q3=/ autoname;
run;

/* --- Received treatment counts --- */
proc means data=analysis noprint;
  by TRT01PN TRT01A;
  var RECEIVED_TX CNSR_TTT;
  output out=rx_counts sum=/ autoname;
run;

/* --- Print summaries --- */
title "TC-031: Time-to-First-Treatment";
proc print data=quartiles_exp noobs label;
  where percent = 50;
  var estimate lowerlimit upperlimit;
  label estimate="Median TTT (Exp)" lowerlimit="95% LCL" upperlimit="95% UCL";
run;

proc print data=quartiles_ctl noobs label;
  where percent = 50;
  var estimate lowerlimit upperlimit;
  label estimate="Median TTT (Ctl)" lowerlimit="95% LCL" upperlimit="95% UCL";
run;

proc print data=lr_test noobs label;
  where test = "Log-Rank";
  var chisq probchisq;
  label chisq="Log-Rank Chi-Sq" probchisq="p-value";
run;

proc print data=cox_hr noobs label;
  var description HazardRatio LowerCL UpperCL;
run;

proc print data=ttt_summary noobs label;
  var TRT01A TTT_DAYS_Mean TTT_DAYS_Median TTT_DAYS_Min TTT_DAYS_Max;
run;

proc print data=rx_counts noobs label;
  var TRT01A RECEIVED_TX_Sum CNSR_TTT_Sum;
  label RECEIVED_TX_Sum="N Received" CNSR_TTT_Sum="N Censored";
run;

title;
