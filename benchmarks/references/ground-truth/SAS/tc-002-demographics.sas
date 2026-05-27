/* TC-002 Ground Truth: Baseline Demographics Table (SAS)
   Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark

   ⚠️  REFERENCE IMPLEMENTATION ONLY — NOT RUN OR VERIFIED
   No SAS license available to execute this code.
   Ground truth established via R (dplyr + Tplyr) and Python (pandas + gtsummary) only.

   Primary: PROC FREQ (categorical), PROC MEANS (continuous)

   Usage: sas tc-002-demographics.sas -set seed 42 -set n 400
*/

%let seed    = 42;
%let n       = 400;
%let outpath = .;

* ── Generate synthetic ADSL data ──;
data adsl;
  call streaminit(&seed.);
  
  length trt01p $7 race $10 region1 $15;
  
  do subjid = 1 to &n.;
    trt01pn = rand("TABLE", 0.5, 0.5) - 1;
    trt01p  = ifc(trt01pn = 0, "Placebo", "Active");
    
    age = round(rand("NORMAL", 58, 12));
    agegr1 = ifc(rand("UNIFORM") < 0.5, "<65", ">=65");
    
    sex_rc = rand("TABLE", 0.55, 0.45);
    sex = ifc(sex_rc = 1, "M", "F");
    
    race_rc = rand("TABLE", 0.60, 0.15, 0.20, 0.05);
    race = choosec(race_rc, "White", "Black", "Asian", "Other");
    
    region_rc = rand("TABLE", 0.35, 0.30, 0.20, 0.15);
    region1 = choosec(region_rc, "North America", "Europe", "Asia", "Rest of World");
    
    ecog = rand("TABLE", 0.4, 0.4, 0.2) - 1;  * 0, 1, 2;
    
    saffl = ifc(rand("UNIFORM") < 0.98, "Y", "N");
    ittfl = ifc(rand("UNIFORM") < 0.95, "Y", "N");
    
    usubjid = cats("SUBJ-", put(subjid, z4.));
    output;
  end;
  
  keep usubjid studyid trt01pn trt01p age sex race region1 ecog saffl ittfl;
run;

* ── Safety population ──;
data safety;
  set adsl;
  where saffl = "Y";
run;

* ── Continuous: Age by treatment arm ──;
proc means data=safety n mean std median min max maxdec=2;
  class trt01pn;
  var age;
  output out=age_stats
    n=n mean=mean std=std median=median min=min max=max;
run;

* ── Categorical: Sex, Race, Region, ECOG by treatment arm ──;
proc freq data=safety;
  tables (sex race region1 ecog) * trt01pn / norow nocol nopercent;
run;

* ── Chi-square p-values ──;
proc freq data=safety;
  tables (sex race region1 ecog) * trt01pn / chisq;
  output out=pvals chisq;
run;

* ── Total summary ──;
proc means data=safety n mean std median min max maxdec=2;
  var age;
run;

* ── Export structured summary ──;
proc sql;
  create table demo_summary as
  select 
    trt01pn,
    count(*) as n_total,
    mean(age) as age_mean,
    std(age)  as age_std
  from safety
  group by trt01pn;
quit;

* ── Output ──;
title "TC-002: Baseline Demographics Summary (SAS)";
title2 "Safety Population";
proc print data=demo_summary;
run;
title;

proc freq data=safety;
  tables sex*trt01p / norow nocol nopercent chisq;
  title "Sex by Treatment Arm (Safety)";
run;
title;
