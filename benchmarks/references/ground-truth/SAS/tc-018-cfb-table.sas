/* TC-018 Ground Truth: Change from Baseline Table (SAS)
   Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark

   ⚠️  REFERENCE IMPLEMENTATION ONLY — NOT RUN OR VERIFIED
   No SAS license available to execute this code.
   Ground truth established via R and Python only.

   Primary: PROC MEANS for summary stats, PROC TTEST for treatment comparisons

   Usage: sas tc-018-cfb-table.sas -set seed 42 -set n 200 -set outpath .
*/

%let seed    = 42;
%let n       = 200;
%let outpath = .;

* ── Generate longitudinal CFB data ──;
data cfb;
  call streaminit(&seed.);
  length trt01a $13 usubjid $8 avisit $10;
  
  * Visits: BASELINE, WEEK_6, WEEK_12, WEEK_18, WEEK_24;
  array visits{5} $10 ("BASELINE" "WEEK_6" "WEEK_12" "WEEK_18" "WEEK_24");
  array weeks{5} (0 6 12 18 24);
  
  do i = 1 to &n.;
    * Randomize treatment;
    trt01pn = ifc(rand("UNIFORM") < 0.5, 1, 0);
    trt01a = ifc(trt01pn = 1, "Experimental", "Control");
    usubjid = cats("SUB", put(i, z4.));
    
    * Baseline tumor size (mm): N(50, 15);
    baseline = rand("NORMAL", 50, 15);
    
    do v = 1 to 5;
      avisit = visits{v};
      avisitn = v - 1;
      wk = weeks{v};
      
      if avisit = "BASELINE" then do;
        aval = baseline;
        chg = 0;
      end;
      else do;
        * Experimental: -0.8 mm/week + noise;
        * Control: -0.1 mm/week + noise;
        if trt01pn = 1 then change = -0.8 * wk + rand("NORMAL", 0, 8);
        else change = -0.1 * wk + rand("NORMAL", 0, 8);
        
        aval = baseline + change;
        chg = change;
      end;
      
      base = baseline;
      aval = round(aval, 0.01);
      chg = round(chg, 0.01);
      base = round(base, 0.01);
      
      output;
    end;
  end;
  
  keep usubjid trt01pn trt01a avisit avisitn aval chg base;
run;

* ── Summary statistics by visit and treatment arm ──;
proc means data=cfb n mean std median min max maxdec=4;
  class avisit trt01a;
  var aval chg;
  output out=cfb_summary
    n(chg)=n mean(chg)=mean_chg std(chg)=sd_chg
    median(chg)=med_chg mean(aval)=mean_aval std(aval)=sd_aval;
run;

* ── CI calculation: mean +/- 1.96 * SE ──;
data cfb_ci;
  set cfb_summary;
  if _n_ > 0 and n > 0 then do;
    se_chg = sd_chg / sqrt(n);
    ci_lower = mean_chg - 1.96 * se_chg;
    ci_upper = mean_chg + 1.96 * se_chg;
  end;
  keep avisit trt01a n mean_chg sd_chg med_chg se_chg ci_lower ci_upper mean_aval sd_aval;
run;

* ── Treatment comparison t-tests at each post-baseline visit ──;
ods output TTests=ttest_results;
proc ttest data=cfb;
  by avisit;
  where avisit ^= "BASELINE";
  class trt01a;
  var chg;
run;
ods output close;

* ── Baseline: test AVAL equivalence ──;
ods output TTests=baseline_ttest;
proc ttest data=cfb;
  where avisit = "BASELINE";
  class trt01a;
  var aval;
run;
ods output close;

* ── N by arm ──;
proc sql;
  select count(distinct usubjid) into :n_total from cfb;
  select count(distinct usubjid) into :n_exp from cfb where trt01a = "Experimental";
  select count(distinct usubjid) into :n_ctl from cfb where trt01a = "Control";
quit;

* ── Output JSON ──;
data _null_;
  file "&outpath./tc-018-output.json";
  put '{"test_case_id": "TC-018",';
  put '"language": "SAS",';
  put '"tc_name": "Change from Baseline Table",';
  put '"metadata": {';
  put '  "n_total": ' "&n_total.,";
  put '  "n_experimental": ' "&n_exp.,";
  put '  "n_control": ' "&n_ctl.,";
  put '  "population": "ITT",';
  put '  "endpoint": "Tumor Size",';
  put '  "endpoint_unit": "mm"';
  put '},';
  put '"method": "PROC MEANS + PROC TTEST"';
  put '}';
run;

title "TC-018: Change from Baseline Table (SAS)";
title2 "ITT Population | N=&n_total (Exp=&n_exp, Ctl=&n_ctl)";
proc print data=cfb_ci noobs;
  by avisit;
  var trt01a n mean_chg sd_chg med_chg ci_lower ci_upper;
  label trt01a="Arm" n="N" mean_chg="Mean Chg" sd_chg="SD"
        med_chg="Median" ci_lower="95% LCL" ci_upper="95% UCL";
run;
title;

title2 "Treatment Comparison p-values (post-baseline visits)";
proc print data=ttest_results noobs;
  by avisit;
  var Variable Method tValue Probt;
  label Variable="Variable" Method="Test" tValue="t" Probt="p-value";
run;
title;
