/* TC-012 Ground Truth: Forest Plot Data — Subgroup Hazard Ratios (SAS)
   Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark

   ⚠️  REFERENCE IMPLEMENTATION ONLY — NOT RUN OR VERIFIED
   No SAS license available to execute this code.
   Ground truth established via R (survival::coxph) and Python (lifelines) only.

   Primary: PROC PHREG for Cox PH models, subgroup analysis via BY processing

   Usage: sas tc-012-forest-hr.sas -set seed 42 -set n 300 -set outpath .
*/

%let seed    = 42;
%let n       = 300;
%let outpath = .;

* ── Generate synthetic survival data ──;
data adtte;
  call streaminit(&seed.);
  length trt01a $13 usubjid $12 agegr1 $4 sex $6 ecoggr1 $3 region1 $15 priortrt $3;
  
  do i = 1 to &n.;
    if i <= &n. / 2 then do;
      trt01a = "Experimental";
      trt01pn = 1;
    end;
    else do;
      trt01a = "Control";
      trt01pn = 0;
    end;
    
    usubjid = cats("SUBJ-", substr(trt01a, 1, 1), "-", put(i, z4.));
    
    agegr1 = ifc(rand("UNIFORM") < 0.5, "<65", ">=65");
    sex = ifc(rand("UNIFORM") < 0.5, "Male", "Female");
    ecoggr1 = ifc(rand("UNIFORM") < 0.6, "0", "1+");
    region1 = choosec(ceil(3 * rand("UNIFORM")), "North America", "Europe", "Asia");
    priortrt = ifc(rand("UNIFORM") < 0.4, "Yes", "No");
    
    * Hazard: Experimental has HR=0.65, adjustments for age/ecog/prior;
    base_lambda = 0.05;
    if trt01pn = 1 then base_lambda = base_lambda * 0.65;
    if agegr1 = ">=65" then base_lambda = base_lambda * 1.2;
    if ecoggr1 = "1+" then base_lambda = base_lambda * 1.4;
    if priortrt = "Yes" then base_lambda = base_lambda * 0.9;
    
    tte = rand("EXPONENTIAL") / base_lambda;
    censor_time = 18 + 6 * rand("UNIFORM");
    
    if tte <= censor_time then do;
      aval = tte;
      cnsr = 0;
    end;
    else do;
      aval = censor_time;
      cnsr = 1;
    end;
    
    aval = round(aval, 0.01);
    output;
  end;
  
  keep usubjid trt01a trt01pn aval cnsr agegr1 sex ecoggr1 region1 priortrt;
run;

* ── Overall Cox PH model ──;
ods output ParameterEstimates=overall_pe HazardRatios=overall_hr;
proc phreg data=adtte;
  class trt01a (ref="Control") / param=ref;
  model aval * cnsr(1) = trt01a / ties=efron;
  hazardratio trt01a / diff=ref cl=wald;
run;

* ── Extract overall HR ──;
data _null_;
  set overall_hr;
  where Description = "Experimental vs Control";
  
  call symputx('overall_hr', put(HazardRatio, 6.3));
  call symputx('overall_lower', put(LowerCL, 6.3));
  call symputx('overall_upper', put(UpperCL, 6.3));
run;

* ── Subgroup analysis: create subgroup datasets and run BY processing ──;
* Create a long-format dataset with subgroup indicators;
data subgroups;
  set adtte;
  
  * Age <65;
  if agegr1 = "<65" then do;
    subgroup = "Age <65"; variable = "AGEGR1"; value = "<65"; output;
  end;
  if agegr1 = ">=65" then do;
    subgroup = "Age >=65"; variable = "AGEGR1"; value = ">=65"; output;
  end;
  
  * Sex;
  if sex = "Male" then do;
    subgroup = "Male"; variable = "SEX"; value = "Male"; output;
  end;
  if sex = "Female" then do;
    subgroup = "Female"; variable = "SEX"; value = "Female"; output;
  end;
  
  * ECOG;
  if ecoggr1 = "0" then do;
    subgroup = "ECOG PS 0"; variable = "ECOGGR1"; value = "0"; output;
  end;
  if ecoggr1 = "1+" then do;
    subgroup = "ECOG PS 1+"; variable = "ECOGGR1"; value = "1+"; output;
  end;
  
  * Region;
  if region1 = "North America" then do;
    subgroup = "North America"; variable = "REGION"; value = "North America"; output;
  end;
  if region1 = "Europe" then do;
    subgroup = "Europe"; variable = "REGION"; value = "Europe"; output;
  end;
  if region1 = "Asia" then do;
    subgroup = "Asia"; variable = "REGION"; value = "Asia"; output;
  end;
  
  * Prior therapy;
  if priortrt = "Yes" then do;
    subgroup = "Prior therapy: Yes"; variable = "PRIORTRT"; value = "Yes"; output;
  end;
  if priortrt = "No" then do;
    subgroup = "Prior therapy: No"; variable = "PRIORTRT"; value = "No"; output;
  end;
  
  keep usubjid trt01a trt01pn aval cnsr subgroup variable value;
run;

* Sort by subgroup for BY processing;
proc sort data=subgroups;
  by subgroup;
run;

* Run Cox PH within each subgroup;
ods output ParameterEstimates=sub_pe HazardRatios=sub_hr;
proc phreg data=subgroups;
  by subgroup;
  class trt01a (ref="Control") / param=ref;
  model aval * cnsr(1) = trt01a / ties=efron;
  hazardratio trt01a / diff=ref cl=wald;
run;

* ── Interaction p-values ──;
* For each variable, fit model with interaction term;
%macro interaction_pval(var);
  ods output ParameterEstimates=int_pe_&var.;
  proc phreg data=adtte;
    class trt01a (ref="Control") &var. / param=ref;
    model aval * cnsr(1) = trt01a &var. trt01a * &var. / ties=efron;
  run;
%mend;

%interaction_pval(agegr1);
%interaction_pval(sex);
%interaction_pval(ecoggr1);
%interaction_pval(region1);
%interaction_pval(priortrt);

* ── Event counts ──;
proc sql;
  select count(*) into :n_total from adtte;
  select sum(1 - cnsr) into :n_events from adtte;
  select count(*) into :n_exp from adtte where trt01a = "Experimental";
  select count(*) into :n_ctl from adtte where trt01a = "Control";
  select sum(1 - cnsr) into :evt_exp from adtte where trt01a = "Experimental";
  select sum(1 - cnsr) into :evt_ctl from adtte where trt01a = "Control";
quit;

* ── Output ──;
data _null_;
  file "&outpath./tc-012-output.json";
  put '{"test_case_id": "TC-012",';
  put '"language": "SAS",';
  put '"title": "Forest Plot — Subgroup Hazard Ratios for PFS",';
  put '"overall": {';
  put '  "hr": ' "&overall_hr.,";
  put '  "ci_lower": ' "&overall_lower.,";
  put '  "ci_upper": ' "&overall_upper.,";
  put '  "n_experimental": ' "&n_exp.,";
  put '  "n_control": ' "&n_ctl.,";
  put '  "events_experimental": ' "&evt_exp.,";
  put '  "events_control": ' "&evt_ctl.";
  put '},';
  put '"method": "Cox PH (PROC PHREG)",';
  put '"ci_method": "Wald (log-scale)"';
  put '}';
run;

title "TC-012: Forest Plot Subgroup HR (SAS)";
title2 "Overall: HR=&overall_hr (95% CI: &overall_lower–&overall_upper)";
proc print data=overall_hr noobs;
  var Description HazardRatio LowerCL UpperCL;
  label Description="Comparison" HazardRatio="HR" LowerCL="Lower" UpperCL="Upper";
run;
title;

title2 "Subgroup Results";
proc print data=sub_hr noobs;
  by subgroup;
  var Description HazardRatio LowerCL UpperCL;
  label Description="Comparison" HazardRatio="HR" LowerCL="Lower" UpperCL="Upper";
run;
title;
