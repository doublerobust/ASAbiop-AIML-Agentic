/* TC-033: Dose Intensity Summary (Relative Dose Intensity) — SAS
 *
 * Computes Relative Dose Intensity (RDI) per subject and summarizes by arm:
 *   RDI = (actual cumulative dose / planned cumulative dose) × 100
 *
 * Output: Arm-level summary (N, mean, SD, median, range),
 *         % subjects with RDI >= 80%, % with dose reduction, % with dose interruption
 *
 * Usage: sas tc-033-dose-intensity.sas -set seed 42 -set n 200
 */

options nosource2 linesize=120;
%let seed = %sysget(seed);
%if &seed = %then %let seed = 42;
%let n = %sysget(n);
%if &n = %then %let n = 200;

/* --- Generate exposure data --- */
data adex;
  call streaminit(&seed);
  array trt_arr[0:1] _temporary_;
  do i = 1 to &n;
    if i <= &n / 2 then trt = 1;
    else trt = 0;
  end;
  /* Shuffle: use random permutation */
  do i = 1 to &n;
    j = rand("integer", 1, &n);
    set adex point=j nobs=nobs;
  end;
run;

/* Simpler: generate fresh */
data adex;
  call streaminit(&seed);
  length USUBJID $8 TRT01A $12;
  do i = 1 to &n;
    if i <= &n / 2 then trt = 1;
    else trt = 0;
  end;
  * Shuffle via random sort ;
  _rand = rand("uniform");
  output;
run;

proc sort data=adex; by _rand; run;

data adex;
  set adex;
  drop i _rand;
  USUBJID = cats("SUB", put(_N_, z4.));
  TRT01PN = trt;
  if trt = 1 then TRT01A = "Experimental";
  else TRT01A = "Control";

  * Treatment duration (weeks) ;
  if trt = 1 then dur = round(rand("normal", 48, 10));
  else dur = round(rand("normal", 27, 7));
  dur = max(dur, 2);

  * Planned daily dose (mg) ;
  if trt = 1 then planned_daily = 12;
  else planned_daily = 6;
  PLANDOSE = planned_daily * dur * 7;

  * Adherence ;
  if trt = 1 then adherence = rand("uniform", 0.70, 1.0);
  else adherence = rand("uniform", 0.80, 1.0);
  ACTUALDOSE = round(PLANDOSE * adherence, 0.01);

  * RDI ;
  RDI = round((ACTUALDOSE / PLANDOSE) * 100, 0.01);

  * Dose reduction ;
  if trt = 1 then DOSERED = rand("bernoulli", 0.15);
  else DOSERED = rand("bernoulli", 0.08);

  * Dose interruption ;
  if trt = 1 then DOSEINT = rand("bernoulli", 0.10);
  else DOSEINT = rand("bernoulli", 0.05);

  TREATDUR = dur;
  drop trt dur planned_daily adherence;
run;

/* --- Summary statistics by arm --- */
proc means data=adex noprint;
  by TRT01PN TRT01A;
  var RDI TREATDUR PLANDOSE ACTUALDOSE;
  output out=rdi_summary
    n= mean= std= median= min= max= q1= q3=
    / autoname;
run;

/* --- Counts: RDI >= 80% --- */
data rdi_flag;
  set adex;
  RDI_GE80 = (RDI >= 80);
run;

proc means data=rdi_flag noprint;
  by TRT01PN TRT01A;
  var RDI_GE80 DOSERED DOSEINT;
  output out=counts
    n= sum= mean=
    / autoname;
run;

/* --- Print summaries --- */
title "TC-033: Dose Intensity Summary";
proc print data=rdi_summary noobs label;
  var TRT01A RDI_N RDI_Mean RDI_StdDev RDI_Median RDI_Min RDI_Max RDI_Q1 RDI_Q3;
run;

proc print data=counts noobs label;
  var TRT01A RDI_GE80_N RDI_GE80_Sum RDI_GE80_Mean DOSERED_Sum DOSERED_Mean DOSEINT_Sum DOSEINT_Mean;
  format RDI_GE80_Mean DOSERED_Mean DOSEINT_Mean percent8.2;
run;

title;
