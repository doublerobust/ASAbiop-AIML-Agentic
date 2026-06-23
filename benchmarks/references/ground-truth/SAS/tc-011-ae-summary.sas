/* TC-011 Ground Truth: Adverse Event Summary Table by SOC and PT (SAS)
   Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark

   ⚠️  REFERENCE IMPLEMENTATION ONLY — NOT RUN OR VERIFIED
   No SAS license available to execute this code.
   Ground truth established via R (dplyr) and Python (pandas) only.

   Primary: PROC FREQ for AE counts by SOC/PT, PROC SQL for summary

   Usage: sas tc-011-ae-summary.sas -set seed 42 -set n 200 -set outpath .
*/

%let seed    = 42;
%let n       = 200;
%let outpath = .;

* ── Generate synthetic ADSL ──;
data adsl;
  call streaminit(&seed.);
  length trt01a $13 usubjid $9 saffl $1;
  
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
    saffl = "Y";
    output;
  end;
  keep usubjid trt01a trt01pn saffl;
run;

* ── Generate ADAE from SOC/PT catalog ──;
* In practice, this would be a pre-generated ADAE dataset;
* Here we create a self-contained illustration;
data adae;
  call streaminit(&seed. + 100);
  length aebodsys $60 aedecod $40 aeser $1 aeacn $20 trt01a $13 usubjid $9;
  
  * AE catalog arrays;
  array soc_list{8} $60 (
    "Gastrointestinal disorders",
    "General disorders and administration site conditions",
    "Nervous system disorders",
    "Skin and subcutaneous tissue disorders",
    "Investigations",
    "Respiratory, thoracic and mediastinal disorders",
    "Musculoskeletal and connective tissue disorders",
    "Infections and infestations"
  );
  
  * Generate AEs for experimental arm;
  do subj = 1 to &n. / 2;
    usubjid = cats("SUBJ-", put(subj, z4.));
    trt01a = "Experimental";
    trt01pn = 1;
    
    do s = 1 to 8;
      * Base rate per SOC (2%–25%);
      base_rate = 0.02 + 0.23 * rand("UNIFORM");
      adj_rate = min(base_rate * 1.3, 0.95);
      
      * Determine number of subjects affected in this SOC;
      n_aff = rand("BINOMIAL", adj_rate, 1);
      if n_aff > 0 then do;
        * Pick a PT within this SOC (simplified — one PT per subject per SOC);
        pt_idx = ceil(4 * rand("UNIFORM"));
        
        * Select PT based on SOC;
        aedecod = choosec(s,
          choosec(min(pt_idx, 5), "Nausea", "Diarrhoea", "Vomiting", "Abdominal pain", "Constipation"),
          choosec(min(pt_idx, 4), "Fatigue", "Pyrexia", "Oedema peripheral", "Asthenia"),
          choosec(min(pt_idx, 4), "Headache", "Dizziness", "Neuropathy peripheral", "Dysgeusia"),
          choosec(min(pt_idx, 4), "Rash", "Pruritus", "Alopecia", "Dry skin"),
          choosec(min(pt_idx, 4), "ALT increased", "AST increased", "Blood creatinine increased", "Weight decreased"),
          choosec(min(pt_idx, 3), "Cough", "Dyspnoea", "Epistaxis"),
          choosec(min(pt_idx, 3), "Arthralgia", "Myalgia", "Back pain"),
          choosec(min(pt_idx, 3), "Upper respiratory tract infection", "Urinary tract infection", "Nasopharyngitis")
        );
        
        aebodsys = soc_list{s};
        aeser = ifc(rand("UNIFORM") < 0.1, "Y", "N");
        aeacn = choosec(ceil(3 * rand("UNIFORM")), "DOSE NOT CHANGED", "DOSE REDUCED", "DRUG WITHDRAWN");
        
        output;
      end;
    end;
  end;
  
  * Generate AEs for control arm;
  do subj = &n. / 2 + 1 to &n.;
    usubjid = cats("SUBJ-", put(subj, z4.));
    trt01a = "Control";
    trt01pn = 0;
    
    do s = 1 to 8;
      base_rate = 0.02 + 0.23 * rand("UNIFORM");
      
      n_aff = rand("BINOMIAL", base_rate, 1);
      if n_aff > 0 then do;
        pt_idx = ceil(4 * rand("UNIFORM"));
        aedecod = choosec(s,
          choosec(min(pt_idx, 5), "Nausea", "Diarrhoea", "Vomiting", "Abdominal pain", "Constipation"),
          choosec(min(pt_idx, 4), "Fatigue", "Pyrexia", "Oedema peripheral", "Asthenia"),
          choosec(min(pt_idx, 4), "Headache", "Dizziness", "Neuropathy peripheral", "Dysgeusia"),
          choosec(min(pt_idx, 4), "Rash", "Pruritus", "Alopecia", "Dry skin"),
          choosec(min(pt_idx, 4), "ALT increased", "AST increased", "Blood creatinine increased", "Weight decreased"),
          choosec(min(pt_idx, 3), "Cough", "Dyspnoea", "Epistaxis"),
          choosec(min(pt_idx, 3), "Arthralgia", "Myalgia", "Back pain"),
          choosec(min(pt_idx, 3), "Upper respiratory tract infection", "Urinary tract infection", "Nasopharyngitis")
        );
        aebodsys = soc_list{s};
        aeser = ifc(rand("UNIFORM") < 0.1, "Y", "N");
        aeacn = choosec(ceil(3 * rand("UNIFORM")), "DOSE NOT CHANGED", "DOSE REDUCED", "DRUG WITHDRAWN");
        output;
      end;
    end;
  end;
  
  keep usubjid trt01a trt01pn aebodsys aedecod aeser aeacn;
run;

* ── Safety population N ──;
proc sql;
  select count(*) into :n_exp from adsl where trt01a = "Experimental";
  select count(*) into :n_ctl from adsl where trt01a = "Control";
quit;

* ── Any AE (subjects with ≥1 AE) ──;
proc sql;
  create table any_ae as
  select trt01a, count(distinct usubjid) as n_subjects
  from adae
  group by trt01a;
quit;

* ── Serious AEs ──;
proc sql;
  create table ser_ae as
  select trt01a, count(distinct usubjid) as n_subjects
  from adae
  where aeser = "Y"
  group by trt01a;
quit;

* ── AEs leading to discontinuation ──;
proc sql;
  create table disc_ae as
  select trt01a, count(distinct usubjid) as n_subjects
  from adae
  where aeacn = "DRUG WITHDRAWN"
  group by trt01a;
quit;

* ── AE by SOC and PT ──;
proc sql;
  create table ae_soc_pt as
  select aebodsys, aedecod, trt01a,
         count(distinct usubjid) as n_subjects
  from adae
  group by aebodsys, aedecod, trt01a;
quit;

* ── AE by SOC (any PT) ──;
proc sql;
  create table ae_soc as
  select aebodsys, trt01a,
         count(distinct usubjid) as n_subjects
  from adae
  group by aebodsys, trt01a;
quit;

* ── Pivot SOC counts by treatment ──;
proc transpose data=ae_soc out=ae_soc_wide prefix=trt_;
  by aebodsys;
  id trt01a;
  var n_subjects;
run;

* ── Pivot PT counts by treatment ──;
proc transpose data=ae_soc_pt out=ae_pt_wide prefix=trt_;
  by aebodsys aedecod;
  id trt01a;
  var n_subjects;
run;

* ── Sort SOC by total frequency (descending) ──;
data ae_soc_wide2;
  set ae_soc_wide;
  total = sum(trt_Experimental, trt_Control, 0);
  call sortx(aebodsys, total, 'D');
run;

proc sort data=ae_soc_wide2;
  by descending total aebodsys;
run;

* ── Output JSON ──;
data _null_;
  file "&outpath./tc-011-output.json";
  put '{"test_case_id": "TC-011",';
  put '"language": "SAS",';
  put '"title": "Adverse Event Summary Table by SOC and PT",';
  put '"population": {"n_experimental": ' "&n_exp., " '"n_control": ' "&n_ctl."},';
  
  * Any AE;
  select * from any_ae where trt01a = "Experimental" into :any_exp;
  select * from any_ae where trt01a = "Control" into :any_ctl;
  put '"any_ae": {"experimental": ' "&any_exp., " '"control": ' "&any_ctl."},';
  
  * Serious AE;
  select * from ser_ae where trt01a = "Experimental" into :ser_exp;
  select * from ser_ae where trt01a = "Control" into :ser_ctl;
  put '"serious_ae": {"experimental": ' "&ser_exp., " '"control": ' "&ser_ctl."},';
  
  * Discontinuation;
  select * from disc_ae where trt01a = "Experimental" into :disc_exp;
  select * from disc_ae where trt01a = "Control" into :disc_ctl;
  put '"disc_ae": {"experimental": ' "&disc_exp., " '"control": ' "&disc_ctl."}";
  put '}';
run;

title "TC-011: AE Summary Table by SOC and PT (SAS)";
title2 "Safety Population | N_exp=&n_exp N_ctl=&n_ctl";
proc print data=ae_soc_wide2 noobs;
  var aebodsys trt_Experimental trt_Control total;
  label aebodsys="SOC" trt_Experimental="Exp n" trt_Control="Ctl n" total="Total";
run;
title;
