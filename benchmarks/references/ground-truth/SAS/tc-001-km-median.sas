/* TC-001 Ground Truth: Kaplan-Meier Median PFS Estimation (SAS)
   Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark

   ⚠️  REFERENCE IMPLEMENTATION ONLY — NOT RUN OR VERIFIED
   No SAS license available to execute this code.
   Ground truth established via R (survival) and Python (lifelines) only.
   See cross-language-verification.md §Known Differences for details.

   Default confidence interval method: log-log (Greenwood with log-log transform)

   Usage (batch): sas tc-001-km-median.sas -set seed 42 -set n 200
*/

* ── Configuration parameters ──;
%let seed    = 42;
%let n       = 200;
%let arm     = 1;
%let outpath = .;

* ── Generate synthetic ADTTE data ──;
* Note: In practice, this would read from a pre-generated dataset;
* Here we demonstrate the structure for a self-contained SAS implementation;

data adtte;
  call streaminit(&seed.);
  
  base_rate = log(2) / 6.0;  * median PFS = 6 months;
  hr = 0.75;
  censoring_rate = 0.30;
  
  do subjid = 1 to &n.;
    * Treatment arm;
    trt01pn = rand("TABLE", 0.5, 0.5) - 1;  * 0 or 1;
    trt01p  = ifc(trt01pn = 0, "Placebo", "Active");
    
    * Hazard multiplier;
    haz_mult = ifn(trt01pn = 0, 1.0, hr);
    
    * Survival time (exponential);
    aval = rand("EXPONENTIAL") / (base_rate * haz_mult);
    cens = rand("EXPONENTIAL") / (base_rate * censoring_rate / (1 - censoring_rate));
    
    * Observed time;
    if aval <= cens then do;
      aval_obs = aval;
      cnsr = 0;  * event;
    end;
    else do;
      aval_obs = cens;
      cnsr = 1;  * censored;
    end;
    
    * Stratification factors;
    sex = ifc(rand("TABLE", 0.5, 0.5) = 1, "Male", "Female");
    ecog = rand("TABLE", 0.6, 0.4) - 1;  * 0 or 1;
    
    ittfl = ifc(rand("UNIFORM") < 0.95, "Y", "N");
    saffl = ifc(rand("UNIFORM") < 0.98, "Y", "N");
    
    aval = round(aval_obs, 0.01);
    usubjid = cats("SUBJ-", put(subjid, z4.));
    
    output;
  end;
  
  keep usubjid studyid trt01pn trt01p aval cnsr ittfl saffl sex ecog;
run;

* ── ITT population, specified arm ──;
data analysis;
  set adtte;
  where ittfl = "Y" and trt01pn = &arm.;
run;

* ── KM estimation using PROC LIFETEST ──;
proc lifetest data=analysis outs=outs;
  time aval * cnsr(1);
run;

* ── Extract median and 95% CI — log-log transform (default) ──;
data _null_;
  set outs;
  where quantile = 0.5;
  
  median_val = median;
  lower_val  = lowerlimit;
  upper_val  = upperlimit;
  
  put "──────────────────────────────────────────────";
  put "Median PFS:     " median_val 6.1 " months";
  put "95% CI:         (" lower_val 6.1 ", " upper_val 6.1 ")";
  put "──────────────────────────────────────────────";
  
  * Store as macro variables for downstream use;
  call symputx('median_pfs', put(median, best6.4));
  call symputx('ci_lower', put(lowerlimit, best6.4));
  call symputx('ci_upper', put(upperlimit, best6.4));
run;

* ── Event count ──;
proc sql;
  select count(*) into :n_total
  from analysis;
  
  select sum(1 - cnsr) into :n_events
  from analysis;
quit;

* ── Output structured result ──;
data _null_;
  file "&outpath./tc-001-output.json";
  put '{"test_case_id": "TC-001",';
  put '"language": "SAS",';
  put '"median_pfs": ' "&median_pfs.,";
  put '"ci_lower": ' "&ci_lower.,";
  put '"ci_upper": ' "&ci_upper.,";
  put '"n_events": ' "&n_events.,";
  put '"n_total": ' "&n_total.,";
  put '"ci_method": "log-log"';
  put '}';
run;
