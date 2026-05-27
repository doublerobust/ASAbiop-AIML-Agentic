/* TC-003 Ground Truth: Stratified Log-Rank Test (SAS)
   Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark
   
   Cross-validated against: R survival::survdiff(), Python lifelines
   Note: SAS uses equal stratum weights (same as R default)
   
   Usage: sas tc-003-stratified-logrank.sas -set seed 42 -set n 400
*/

%let seed    = 42;
%let n       = 400;
%let outpath = .;

* ── Generate synthetic ADTTE data ──;
data adtte;
  call streaminit(&seed.);
  
  base_rate = log(2) / 6.0;
  hr = 0.75;
  censoring_rate = 0.30;
  
  do subjid = 1 to &n.;
    trt01pn = rand("TABLE", 0.5, 0.5) - 1;
    trt01p  = ifc(trt01pn = 0, "Placebo", "Active");
    
    haz_mult = ifn(trt01pn = 0, 1.0, hr);
    
    aval = rand("EXPONENTIAL") / (base_rate * haz_mult);
    cens = rand("EXPONENTIAL") / (base_rate * censoring_rate / (1 - censoring_rate));
    
    if aval <= cens then do;
      aval_obs = aval;
      cnsr = 0;
    end;
    else do;
      aval_obs = cens;
      cnsr = 1;
    end;
    
    * Stratification factors;
    sex = ifc(rand("TABLE", 0.5, 0.5) = 1, "Male", "Female");
    ecog = rand("TABLE", 0.6, 0.4) - 1;
    
    ittfl = ifc(rand("UNIFORM") < 0.95, "Y", "N");
    saffl = ifc(rand("UNIFORM") < 0.98, "Y", "N");
    
    aval = round(aval_obs, 0.01);
    usubjid = cats("SUBJ-", put(subjid, z4.));
    
    output;
  end;
  
  keep usubjid studyid trt01pn trt01p aval cnsr ittfl saffl sex ecog;
run;

* ── ITT population ──;
data itt;
  set adtte;
  where ittfl = "Y";
run;

* ── Stratified log-rank test using PROC LIFETEST ──;
* Note: STRATA statement defines stratification factors;
*       GROUP=trt01pn specifies the treatment comparison;
*       TEST=LOGRANK (default) performs the log-rank test;
ods output HomTests=logrank_result;
proc lifetest data=itt;
  time aval * cnsr(1);
  strata sex ecog / group=trt01pn test=logrank;
run;

* ── Extract results ──;
data _null_;
  set logrank_result;
  
  chi_sq = put(ChiSq, 8.4);
  p_val  = put(ProbChiSq, 10.6);
  df_val = put(DF, 2.0);
  
  put "──────────────────────────────────────────────";
  put "Method: Stratified log-rank test (SAS)";
  put "Strata: SEX, ECOG";
  put "Chi-square: " chi_sq;
  put "DF:         " df_val;
  put "p-value:    " p_val;
  put "──────────────────────────────────────────────";
  
  call symputx('chisq', chi_sq);
  call symputx('pvalue', p_val);
  call symputx('df', df_val);
run;

* ── Event counts ──;
proc sql;
  select count(*) into :n_total from itt;
  select sum(1 - cnsr) into :n_events from itt;
quit;

proc sql;
  create table strata_counts as
  select sex, ecog, 
         count(*) as n,
         sum(1 - cnsr) as events
  from itt
  group by sex, ecog;
quit;

title "TC-003: Stratified Log-Rank Test Results (SAS)";
title2 "ITT Population | Strata: SEX, ECOG";
proc print data=logrank_result;
run;

title2 "Strata Details";
proc print data=strata_counts;
run;
title;
