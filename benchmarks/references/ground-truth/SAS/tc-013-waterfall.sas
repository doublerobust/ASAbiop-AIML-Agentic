/* TC-013 Ground Truth: Waterfall Plot Data — Best % Change in Tumor Size (SAS)
   Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark

   ⚠️  REFERENCE IMPLEMENTATION ONLY — NOT RUN OR VERIFIED
   No SAS license available to execute this code.
   Ground truth established via R and Python only.

   Primary: DATA step for RECIST categorization, PROC SORT, PROC FREQ

   Usage: sas tc-013-waterfall.sas -set seed 42 -set n 150 -set outpath .
*/

%let seed    = 42;
%let n       = 150;
%let outpath = .;

* ── Generate tumor response data ──;
data response;
  call streaminit(&seed.);
  length trt01a $13 usubjid $9 bor $2;
  
  do i = 1 to &n.;
    if i <= &n. / 2 then do;
      trt01a = "Experimental";
      trt01pn = 1;
    end;
    else do;
      trt01a = "Control";
      trt01pn = 0;
    end;
    
    usubjid = cats("SUBJ-", put(i, z4.));
    baseline = round(15 + 85 * rand("UNIFORM"), 0.1);
    
    * Assign BOR category;
    if trt01a = "Experimental" then do;
      cat_prob = rand("UNIFORM");
      if cat_prob < 0.15 then bor = "CR";
      else if cat_prob < 0.50 then bor = "PR";
      else if cat_prob < 0.80 then bor = "SD";
      else bor = "PD";
    end;
    else do;
      cat_prob = rand("UNIFORM");
      if cat_prob < 0.05 then bor = "CR";
      else if cat_prob < 0.25 then bor = "PR";
      else if cat_prob < 0.60 then bor = "SD";
      else bor = "PD";
    end;
    
    * Best % change based on BOR;
    if bor = "CR" then bestpchg = -100.0;
    else if bor = "PR" then bestpchg = -99.0 + 69.0 * rand("UNIFORM");
    else if bor = "SD" then bestpchg = -29.9 + 49.8 * rand("UNIFORM");
    else bestpchg = 20.0 + 180.0 * rand("UNIFORM");
    
    bestpchg = round(bestpchg, 0.1);
    output;
  end;
  
  keep usubjid trt01a trt01pn baseline bestpchg bor;
run;

* ── Sort by bestpchg ascending (for waterfall) ──;
proc sort data=response out=waterfall;
  by bestpchg;
run;

* ── Summary statistics by treatment arm ──;
proc means data=response n mean median min max maxdec=1;
  class trt01a;
  var bestpchg;
  output out=chg_summary n=n mean=mean median=median min=min max=max;
run;

* ── BOR counts by treatment arm ──;
proc freq data=response;
  tables trt01a * bor / norow nocol nopercent;
  tables bor / out=bor_counts;
run;

* ── Compute ORR and DCR ──;
proc sql;
  create table response_summary as
  select
    trt01a,
    count(*) as n,
    sum(bor = "CR") as n_cr,
    sum(bor = "PR") as n_pr,
    sum(bor = "SD") as n_sd,
    sum(bor = "PD") as n_pd,
    calculated n_cr + calculated n_pr as n_orr,
    calculated n_cr + calculated n_pr + calculated n_sd as n_dcr,
    round(calculated n_orr / count(*) * 100, 1) as orr_pct,
    round(calculated n_dcr / count(*) * 100, 1) as dcr_pct
  from response
  group by trt01a;
quit;

* ── Overall summary ──;
proc sql;
  create table overall_summary as
  select
    count(*) as n,
    sum(bor = "CR") as n_cr,
    sum(bor = "PR") as n_pr,
    sum(bor = "SD") as n_sd,
    sum(bor = "PD") as n_pd,
    calculated n_cr + calculated n_pr as n_orr,
    calculated n_cr + calculated n_pr + calculated n_sd as n_dcr,
    round(calculated n_orr / count(*) * 100, 1) as orr_pct,
    round(calculated n_dcr / count(*) * 100, 1) as dcr_pct,
    round(median(bestpchg), 1) as median_chg,
    round(mean(bestpchg), 1) as mean_chg
  from response;
quit;

* ── Output JSON ──;
data _null_;
  file "&outpath./tc-013-output.json";
  put '{"test_case_id": "TC-013",';
  put '"language": "SAS",';
  put '"title": "Waterfall Plot — Best Percentage Change in Tumor Size",';
  put '"response_criteria": "RECIST 1.1",';
  put '"thresholds": {"CR": -100.0, "PR": -30.0, "PD": 20.0}';
  put '}';
run;

title "TC-013: Waterfall Plot Data (SAS)";
title2 "Best % Change in Tumor Size by RECIST 1.1";
proc print data=response_summary noobs;
  var trt01a n n_cr n_pr n_sd n_pd n_orr orr_pct n_dcr dcr_pct;
  label trt01a="Arm" n="N" n_cr="CR" n_pr="PR" n_sd="SD" n_pd="PD"
        n_orr="ORR" orr_pct="ORR%" n_dcr="DCR" dcr_pct="DCR%";
run;
title;

title2 "Overall";
proc print data=overall_summary noobs;
run;
title;
