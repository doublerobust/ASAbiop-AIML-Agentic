/* TC-014 Ground Truth: Listing of Key Protocol Deviations (SAS)
   Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark

   ⚠️  REFERENCE IMPLEMENTATION ONLY — NOT RUN OR VERIFIED
   No SAS license available to execute this code.
   Ground truth established via R and Python only.

   Primary: DATA step for PD generation, PROC SORT, PROC FREQ for summary

   Usage: sas tc-014-pd-listing.sas -set seed 42 -set n 200 -set outpath .
*/

%let seed    = 42;
%let n       = 200;
%let outpath = .;

* ── Generate protocol deviations ──;
data protocols;
  call streaminit(&seed.);
  length trt01a $13 usubjid $9 pd_cat $25 pd_code $12 pddesc $80 severity $8 pddtc $10;
  
  * PD catalog arrays;
  array pd_cats{6} $25 (
    "Eligibility",
    "Visit Window",
    "Prohibited Medication",
    "Dose Modification",
    "Consent",
    "Endpoint Deviation"
  );
  
  array n_codes{6} (3 3 2 3 2 2);
  
  study_start = '15JAN2025'd;
  
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
    
    * ~30% of subjects have PDs;
    if rand("UNIFORM") < 0.30 then do;
      n_pds = ceil(3 * rand("UNIFORM"));
      if n_pds > 3 then n_pds = 3;
      
      do j = 1 to n_pds;
        * Random category;
        cat_idx = ceil(6 * rand("UNIFORM"));
        pd_cat = pd_cats{cat_idx};
        
        * Random code within category;
        code_idx = ceil(n_codes{cat_idx} * rand("UNIFORM"));
        
        * Assign code and description;
        if pd_cat = "Eligibility" then do;
          if code_idx = 1 then do; pd_code = "ELIG-01"; pddesc = "Inclusion criterion not met: baseline lab value outside range"; end;
          else if code_idx = 2 then do; pd_code = "ELIG-02"; pddesc = "Exclusion criterion violated: prior therapy within washout period"; end;
          else do; pd_code = "ELIG-03"; pddesc = "Informed consent obtained after first dose"; end;
        end;
        else if pd_cat = "Visit Window" then do;
          if code_idx = 1 then do; pd_code = "VISIT-01"; pddesc = "Visit conducted outside protocol-specified window (+7 days)"; end;
          else if code_idx = 2 then do; pd_code = "VISIT-02"; pddesc = "Missing required assessment at scheduled visit"; end;
          else do; pd_code = "VISIT-03"; pddesc = "Visit conducted >14 days outside window"; end;
        end;
        else if pd_cat = "Prohibited Medication" then do;
          if code_idx = 1 then do; pd_code = "PROHIB-01"; pddesc = "Concomitant medication prohibited per protocol"; end;
          else do; pd_code = "PROHIB-02"; pddesc = "Prior medication washout period not completed"; end;
        end;
        else if pd_cat = "Dose Modification" then do;
          if code_idx = 1 then do; pd_code = "DOSE-01"; pddesc = "Dose modification not per protocol algorithm"; end;
          else if code_idx = 2 then do; pd_code = "DOSE-02"; pddesc = "Treatment delay >7 days without protocol authorization"; end;
          else do; pd_code = "DOSE-03"; pddesc = "Dose administered outside +/-10% of protocol-specified dose"; end;
        end;
        else if pd_cat = "Consent" then do;
          if code_idx = 1 then do; pd_code = "CONSENT-01"; pddesc = "Informed consent form version not current"; end;
          else do; pd_code = "CONSENT-02"; pddesc = "Consent re-consent not obtained after protocol amendment"; end;
        end;
        else do;
          if code_idx = 1 then do; pd_code = "ENDPT-01"; pddesc = "Primary endpoint assessment not performed per schedule"; end;
          else do; pd_code = "ENDPT-02"; pddesc = "Imaging assessment not reviewed by independent radiologist"; end;
        end;
        
        * Study day and date;
        pddy = ceil(365 * rand("UNIFORM"));
        pddtc = put(study_start + pddy, yymmdd10.);
        
        * Severity;
        sev_prob = rand("UNIFORM");
        if sev_prob < 0.15 then severity = "Critical";
        else if sev_prob < 0.50 then severity = "Major";
        else severity = "Minor";
        
        output;
      end;
    end;
  end;
  
  keep usubjid trt01a trt01pn pd_cat pd_code pddesc pddy pddtc severity;
run;

* ── Sort listing by TRT01A, USUBJID, PDDY ──;
proc sort data=protocols out=pd_listing;
  by trt01a usubjid pddy;
run;

* ── Summary by category and treatment ──;
proc freq data=pd_listing;
  tables trt01a * pd_cat / norow nocol nopercent out=cat_counts;
run;

* ── Summary by severity and treatment ──;
proc freq data=pd_listing;
  tables trt01a * severity / norow nocol nopercent out=sev_counts;
run;

* ── Subjects with PDs by treatment ──;
proc sql;
  create table subj_summary as
  select
    trt01a,
    count(distinct usubjid) as n_subjects_with_pd,
    count(*) as n_total_deviations
  from pd_listing
  group by trt01a;
quit;

* ── Overall summary ──;
proc sql;
  select count(distinct usubjid) into :n_subj_pd from pd_listing;
  select count(*) into :n_total_pd from pd_listing;
quit;

* ── Output JSON ──;
data _null_;
  file "&outpath./tc-014-output.json";
  put '{"test_case_id": "TC-014",';
  put '"language": "SAS",';
  put '"title": "Listing of Key Protocol Deviations",';
  put '"n_subjects_with_pd": ' "&n_subj_pd.,";
  put '"n_total_deviations": ' "&n_total_pd.,";
  put '"sorting": "TRT01A, USUBJID, PDDY"';
  put '}';
run;

title "TC-014: Protocol Deviations Listing (SAS)";
title2 "Subjects with PD: &n_subj_pd | Total deviations: &n_total_pd";
proc print data=subj_summary noobs;
  var trt01a n_subjects_with_pd n_total_deviations;
  label trt01a="Arm" n_subjects_with_pd="Subjects w/ PD" n_total_deviations="Total PDs";
run;
title;

title2 "By Category and Severity";
proc print data=cat_counts noobs;
  var trt01a pd_cat count;
  label trt01a="Arm" pd_cat="Category" count="N";
run;
title;
