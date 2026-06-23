/* TC-017 Ground Truth: Laboratory Shift Table (SAS)
   Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark

   ⚠️  REFERENCE IMPLEMENTATION ONLY — NOT RUN OR VERIFIED
   No SAS license available to execute this code.
   Ground truth established via R and Python only.

   Primary: DATA step for categorization, PROC FREQ for 3x3 shift table

   Usage: sas tc-017-shift-table.sas -set seed 42 -set n 200 -set outpath .
*/

%let seed    = 42;
%let n       = 200;
%let outpath = .;

* ── Generate lab data ──;
data labs;
  call streaminit(&seed.);
  length trt01a $13 usubjid $8 lbtest $12 bl_cat $7 post_cat $7;
  
  do i = 1 to &n.;
    * Randomize treatment;
    trt01pn = ifc(rand("UNIFORM") < 0.5, 1, 0);
    trt01a = ifc(trt01pn = 1, "Experimental", "Control");
    usubjid = cats("SUB", put(i, z4.));
    lbtest = "Hemoglobin";
    
    * Baseline hemoglobin (g/L): N(140, 18);
    bl_val = rand("NORMAL", 140, 18);
    
    * Post-baseline: worst of 3 visits;
    * Experimental arm tends to decrease;
    if trt01pn = 1 then effect = -5;
    else effect = 0;
    
    * Generate 3 post-baseline values, take minimum (worst for Hgb);
    v1 = bl_val + effect + rand("NORMAL", 0, 10);
    v2 = bl_val + effect + rand("NORMAL", 0, 10);
    v3 = bl_val + effect + rand("NORMAL", 0, 10);
    post_val = min(v1, v2, v3);
    
    * Categorize: LOW <120, NORMAL 120-160, HIGH >160;
    if bl_val < 120 then bl_cat = "LOW";
    else if bl_val > 160 then bl_cat = "HIGH";
    else bl_cat = "NORMAL";
    
    if post_val < 120 then post_cat = "LOW";
    else if post_val > 160 then post_cat = "HIGH";
    else post_cat = "NORMAL";
    
    bl_val = round(bl_val, 0.01);
    post_val = round(post_val, 0.01);
    
    output;
  end;
  
  keep usubjid trt01pn trt01a lbtest bl_val bl_cat post_val post_cat;
run;

* ── Build 3x3 shift table ──;
* Create a shift variable combining baseline and post categories;
data labs_shift;
  set labs;
  length shift $15;
  shift = cats(bl_cat, "->", post_cat);
run;

* ── Overall shift table ──;
proc freq data=labs_shift;
  tables bl_cat * post_cat / norow nocol nopercent out=shift_overall;
run;

* ── By treatment arm ──;
proc freq data=labs_shift;
  tables bl_cat * post_cat / norow nocol nopercent out=shift_by_arm;
  by trt01a;
run;

* ── Compute summary statistics ──;
proc sql;
  create table shift_summary as
  select
    trt01a,
    sum(bl_cat = "NORMAL" and post_cat = "NORMAL") as n_stable_normal,
    sum(bl_cat = "LOW" and post_cat = "NORMAL") as n_low_to_normal,
    sum(bl_cat = "NORMAL" and post_cat = "LOW") as n_normal_to_low,
    sum(bl_cat = "NORMAL" and post_cat = "HIGH") as n_normal_to_high,
    sum(bl_cat = "HIGH" and post_cat = "NORMAL") as n_high_to_normal,
    count(*) as n_total
  from labs_shift
  group by trt01a;
quit;

* ── Overall summary (both arms) ──;
proc sql;
  create table shift_overall_summary as
  select
    sum(bl_cat = "NORMAL" and post_cat = "NORMAL") as n_stable_normal,
    sum(bl_cat = "LOW" and post_cat = "NORMAL") as n_low_to_normal,
    sum(bl_cat = "NORMAL" and post_cat = "LOW") as n_normal_to_low,
    sum(bl_cat = "NORMAL" and post_cat = "HIGH") as n_normal_to_high,
    sum(bl_cat = "HIGH" and post_cat = "NORMAL") as n_high_to_normal,
    count(*) as n_total
  from labs_shift;
quit;

* ── N by arm ──;
proc sql;
  select count(*) into :n_total from labs;
  select count(*) into :n_exp from labs where trt01a = "Experimental";
  select count(*) into :n_ctl from labs where trt01a = "Control";
quit;

* ── Output JSON ──;
data _null_;
  file "&outpath./tc-017-output.json";
  put '{"test_case_id": "TC-017",';
  put '"language": "SAS",';
  put '"tc_name": "Laboratory Shift Table",';
  put '"metadata": {';
  put '  "n_total": ' "&n_total.,";
  put '  "n_experimental": ' "&n_exp.,";
  put '  "n_control": ' "&n_ctl.,";
  put '  "population": "SAFETY",';
  put '  "lab_test": "Hemoglobin",';
  put '  "lab_unit": "g/L",';
  put '  "categories": ["LOW", "NORMAL", "HIGH"],';
  put '  "thresholds": {"low": 120, "high": 160},';
  put '  "n_post_baseline_visits": 3';
  put '},';
  put '"method": "PROC FREQ 3x3 cross-tabulation"';
  put '}';
run;

title "TC-017: Laboratory Shift Table (SAS)";
title2 "Hemoglobin (g/L) | Safety Population | N=&n_total";
proc tabulate data=labs_shift format=8.;
  class bl_cat post_cat trt01a;
  table bl_cat, post_cat * (N PCTN) * trt01a;
  label bl_cat="Baseline" post_cat="Post-Baseline" trt01a="Treatment";
run;
title;

title2 "Shift Summary by Arm";
proc print data=shift_summary noobs;
  var trt01a n_total n_stable_normal n_low_to_normal n_normal_to_low n_normal_to_high n_high_to_normal;
  label trt01a="Arm" n_total="N" n_stable_normal="N→N" n_low_to_normal="L→N"
        n_normal_to_low="N→L" n_normal_to_high="N→H" n_high_to_normal="H→N";
run;
title;
