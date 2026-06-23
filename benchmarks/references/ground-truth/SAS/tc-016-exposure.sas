/* TC-016 Ground Truth: Exposure Summary Table (SAS)
   Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark

   ⚠️  REFERENCE IMPLEMENTATION ONLY — NOT RUN OR VERIFIED
   No SAS license available to execute this code.
   Ground truth established via R and Python only.

   Primary: PROC MEANS for continuous summaries, PROC FREQ for dose reduction

   Usage: sas tc-016-exposure.sas -set seed 42 -set n 200 -set outpath .
*/

%let seed    = 42;
%let n       = 200;
%let outpath = .;

* ── Generate synthetic exposure data ──;
data exposure;
  call streaminit(&seed.);
  length trt01a $13 usubjid $8;
  
  do i = 1 to &n.;
    * Randomize treatment assignment;
    trt01pn = ifc(rand("UNIFORM") < 0.5, 1, 0);
    trt01a = ifc(trt01pn = 1, "Experimental", "Control");
    usubjid = cats("SUB", put(i, z4.));
    
    * Treatment duration (weeks): Exp ~ N(48,12), Ctl ~ N(28,8);
    if trt01pn = 1 then treatdur = round(rand("NORMAL", 48, 12));
    else treatdur = round(rand("NORMAL", 28, 8));
    if treatdur < 2 then treatdur = 2;
    
    * Planned daily dose: Exp=10mg, Ctl=5mg;
    if trt01pn = 1 then planned_daily = 10;
    else planned_daily = 5;
    
    * Adherence 75–100%;
    adherence = 0.75 + 0.25 * rand("UNIFORM");
    
    * Cumulative dose;
    cumdose = planned_daily * treatdur * 7 * adherence;
    cumdose = round(cumdose, 0.01);
    
    * Planned cumulative dose;
    plandose = planned_daily * treatdur * 7;
    
    * Dose intensity (%);
    doseint = (cumdose / plandose) * 100;
    doseint = round(doseint, 0.01);
    
    * Dose reduction (binary);
    if trt01pn = 1 then dose_reduced = rand("BINOMIAL", 0.15, 1);
    else dose_reduced = rand("BINOMIAL", 0.08, 1);
    
    output;
  end;
  
  keep usubjid trt01pn trt01a treatdur cumdose plandose doseint dose_reduced;
run;

* ── Summary statistics for continuous variables by arm ──;
proc means data=exposure n mean std median min max q1 q3 maxdec=4;
  class trt01a;
  var treatdur cumdose doseint;
  output out=exposure_summary
    n(treatdur)=n_dur mean(treatdur)=mean_dur std(treatdur)=sd_dur
    median(treatdur)=med_dur min(treatdur)=min_dur max(treatdur)=max_dur
    n(cumdose)=n_dose mean(cumdose)=mean_dose std(cumdose)=sd_dose
    median(cumdose)=med_dose min(cumdose)=min_dose max(cumdose)=max_dose
    n(doseint)=n_di mean(doseint)=mean_di std(doseint)=sd_di
    median(doseint)=med_di min(doseint)=min_di max(doseint)=max_di;
run;

* ── Dose reduction by arm ──;
proc freq data=exposure;
  tables trt01a * dose_reduced / norow nocol nopercent;
run;

proc sql;
  create table dose_red_summary as
  select
    trt01a,
    count(*) as n,
    sum(dose_reduced = 1) as n_yes,
    sum(dose_reduced = 0) as n_no,
    round(sum(dose_reduced = 1) / count(*) * 100, 2) as pct_yes
  from exposure
  group by trt01a;
quit;

* ── N by arm ──;
proc sql;
  select count(*) into :n_exp from exposure where trt01a = "Experimental";
  select count(*) into :n_ctl from exposure where trt01a = "Control";
  select count(*) into :n_total from exposure;
quit;

* ── Output JSON ──;
data _null_;
  file "&outpath./tc-016-output.json";
  put '{"test_case_id": "TC-016",';
  put '"language": "SAS",';
  put '"tc_name": "Exposure Summary Table",';
  put '"metadata": {';
  put '  "n_total": ' "&n_total.,";
  put '  "n_experimental": ' "&n_exp.,";
  put '  "n_control": ' "&n_ctl.,";
  put '  "population": "SAFETY",';
  put '  "duration_unit": "weeks",';
  put '  "dose_unit": "mg"';
  put '},';
  put '"method": "PROC MEANS + PROC FREQ"';
  put '}';
run;

title "TC-016: Exposure Summary Table (SAS)";
title2 "Safety Population | N=&n_total (Exp=&n_exp, Ctl=&n_ctl)";
proc means data=exposure n mean std median min max q1 q3 maxdec=2;
  class trt01a;
  var treatdur cumdose doseint;
  label treatdur="Duration (weeks)" cumdose="Cumulative dose (mg)" doseint="Dose intensity (%)";
run;
title;

title2 "Dose Reduction by Arm";
proc print data=dose_red_summary noobs;
  var trt01a n n_yes n_no pct_yes;
  label trt01a="Arm" n="N" n_yes="Reduced" n_no="Not reduced" pct_yes="% Reduced";
run;
title;
