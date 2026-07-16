/* TC-035 Ground Truth: ORR/DCR/DOR Composite Efficacy Table (Level 2)
 * Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark
 *
 * Level 2 multi-TC integration: ORR + DCR + DOR in a single table.
 *
 * Components:
 *   1. ORR: CR+PR rate, Clopper-Pearson CI (PROC FREQ)
 *   2. DCR: CR+PR+SD rate, Wilson CI (PROC FREQ)
 *   3. DOR: KM median among responders (PROC LIFETEST)
 *
 * Cross-TFL consistency:
 *   - ORR responders == DOR population
 *   - DCR >= ORR
 *   - BOR distribution sums to N per arm
 *
 * Usage: Run with shared composite efficacy dataset.
 *        %let seed=42; %let n=200;
 */

/* ─────────────────────────────────────────────────────
   Generate composite efficacy data (inline for SAS)
   ───────────────────────────────────────────────────── */

%let seed = 42;
%let n = 200;
%let base_rate = %sysfunc(log(2)/6.0);

data composite_efficacy;
  call streaminit(&seed);
  length USUBJID $10 STUDYID $12 TRT01A $12 SEX $6 AGEGR1 $4 BOR $2 ITTFL $1 SAFFL $1;
  array _seeds[100] _temporary_;

  base_rate = &base_rate;

  do i = 1 to &n;
    USUBJID = cats("SUBJ-", put(i, z4.));
    STUDYID = "BENCHMARK-001";

    /* Treatment assignment */
    trt = rand("BERNOULLI", 0.5);
    TRT01PN = trt;
    TRT01A = ifc(trt = 0, "Control", "Experimental");
    hazard_mult = ifc(trt = 0, 1.0, 0.75);

    /* Demographics */
    sex_rand = rand("UNIFORM");
    SEX = ifc(sex_rand < 0.55, "Male", "Female");
    age = round(rand("NORMAL", 58, 12));
    AGEGR1 = ifc(age < 65, "<65", ">=65");
    ecog_rand = rand("UNIFORM");
    ECOG = ifc(ecog_rand < 0.6, 0, 1);

    /* Response probability (same as TC-020/TC-023) */
    if trt = 1 then do;
      if ECOG = 0 then orr_prob = 0.45;
      else orr_prob = 0.30;
    end;
    else do;
      if ECOG = 0 then orr_prob = 0.25;
      else orr_prob = 0.15;
    end;

    is_responder = rand("BERNOULLI", orr_prob);

    /* BOR: ~30% of responders are CR */
    if is_responder = 1 then do;
      cr_rand = rand("UNIFORM");
      if cr_rand < 0.3 then BOR = "CR";
      else BOR = "PR";
    end;
    else do;
      sd_rand = rand("UNIFORM");
      if sd_rand < 0.4 then BOR = "SD";
      else BOR = "PD";
    end;

    /* ITTFL/SAFFL */
    itt_rand = rand("UNIFORM");
    ITTFL = ifc(itt_rand < 0.95, "Y", "N");
    saf_rand = rand("UNIFORM");
    SAFFL = ifc(saf_rand < 0.98, "Y", "N");

    /* AVAL_ORR / AVAL_DCR */
    if BOR in ("CR", "PR") then AVAL_ORR = 1; else AVAL_ORR = 0;
    if BOR in ("CR", "PR", "SD") then AVAL_DCR = 1; else AVAL_DCR = 0;
    IS_RESPONDER = is_responder;

    /* DOR time-to-event for responders */
    if is_responder = 1 then do;
      time_to_response = rand("EXPONENTIAL", 2.0);
      prog_time = rand("EXPONENTIAL", 1.0 / (base_rate * hazard_mult));
      death_time = rand("EXPONENTIAL", 1.0 / (base_rate * 0.3 * hazard_mult));
      cens_time = rand("EXPONENTIAL", 1.0 / (base_rate * 0.3 / 0.7));
      event_time = min(prog_time, death_time);

      if event_time > time_to_response then do;
        if cens_time < event_time and cens_time > time_to_response then do;
          AVAL_DOR = round(cens_time - time_to_response, 0.01);
          CNSR_DOR = 1;
        end;
        else do;
          AVAL_DOR = round(event_time - time_to_response, 0.01);
          CNSR_DOR = 0;
        end;
      end;
      else do;
        AVAL_DOR = .;
        CNSR_DOR = .;
      end;
      TIME_TO_RESPONSE = round(time_to_response, 0.01);
    end;
    else do;
      AVAL_DOR = .;
      CNSR_DOR = .;
      TIME_TO_RESPONSE = .;
    end;

    output;
  end;
  drop i base_rate trt sex_rand age ecog_rand orr_prob is_responder cr_rand
       sd_rand itt_rand saf_rand hazard_mult prog_time death_time cens_time
       event_time time_to_response;
run;

/* ─────────────────────────────────────────────────────
   1. ORR by arm (Clopper-Pearson CI)
   ───────────────────────────────────────────────────── */

proc freq data=composite_efficacy;
  where ITTFL = "Y";
  tables TRT01A * BOR / binomial(level="CR" "PR" clique);
  tables TRT01A * AVAL_ORR / binomial(cl=exact);
  output out=orr_results binomial;
run;

/* ─────────────────────────────────────────────────────
   2. DCR by arm (Wilson CI)
   ───────────────────────────────────────────────────── */

proc freq data=composite_efficacy;
  where ITTFL = "Y";
  tables TRT01A * AVAL_DCR / binomial(cl=wilson);
  output out=dcr_results binomial;
run;

/* ─────────────────────────────────────────────────────
   3. DOR KM median among responders (PROC LIFETEST)
   ───────────────────────────────────────────────────── */

/* Experimental arm responders */
proc lifetest data=composite_efficacy method=km conhaz=normal
  outsurv=dor_surv_exp;
  where TRT01PN = 1 and ITTFL = "Y" and IS_RESPONDER = 1
    and AVAL_DOR is not missing and AVAL_DOR > 0;
  time AVAL_DOR * CNSR_DOR(1);
run;

/* Control arm responders */
proc lifetest data=composite_efficacy method=km conhaz=normal
  outsurv=dor_surv_ctrl;
  where TRT01PN = 0 and ITTFL = "Y" and IS_RESPONDER = 1
    and AVAL_DOR is not missing and AVAL_DOR > 0;
  time AVAL_DOR * CNSR_DOR(1);
run;

/* ─────────────────────────────────────────────────────
   4. BOR distribution by arm
   ───────────────────────────────────────────────────── */

proc freq data=composite_efficacy;
  where ITTFL = "Y";
  tables TRT01A * BOR / out=bor_dist outcum;
run;

/* ─────────────────────────────────────────────────────
   5. Cross-TFL consistency checks
   ───────────────────────────────────────────────────── */

/* Check: DCR >= ORR (disease_controlled >= responders per arm) */
/* Check: ORR responders == DOR population */
/* Check: BOR distribution sums to N per arm */
/* Check: CR+PR counts match ORR responders */

/* These checks are performed via PROC SQL joins and DATA step comparisons */

proc sql;
  create table consistency_check as
  select
    a.TRT01A,
    sum(a.AVAL_ORR) as orr_responders,
    sum(a.AVAL_DCR) as dcr_controlled,
    sum(case when a.IS_RESPONDER = 1 and a.AVAL_DOR is not missing and a.AVAL_DOR > 0
             then 1 else 0 end) as dor_responders,
    count(*) as n_total,
    sum(case when a.BOR = "CR" then 1 else 0 end) as n_cr,
    sum(case when a.BOR = "PR" then 1 else 0 end) as n_pr,
    sum(case when a.BOR = "SD" then 1 else 0 end) as n_sd,
    sum(case when a.BOR = "PD" then 1 else 0 end) as n_pd,
    calculated dcr_controlled >= calculated orr_responders as check_dcr_ge_orr,
    calculated orr_responders = calculated dor_responders as check_orr_matches_dor,
    (calculated n_cr + calculated n_pr + calculated n_sd + calculated n_pd) = calculated n_total as check_bor_sums,
    (calculated n_cr + calculated n_pr) = calculated orr_responders as check_cr_pr_matches_orr
  from composite_efficacy as a
  where a.ITTFL = "Y"
  group by a.TRT01A;
quit;

/* ─────────────────────────────────────────────────────
   Output: Build composite table for export
   ───────────────────────────────────────────────────── */

/* Export ORR results */
proc print data=orr_results;
  title "TC-035: ORR by Arm (Clopper-Pearson CI)";
run;

/* Export DCR results */
proc print data=dcr_results;
  title "TC-035: DCR by Arm (Wilson CI)";
run;

/* Export DOR median survival times */
proc print data=dor_surv_exp;
  where CENSOR = 0;
  title "TC-035: DOR KM Survival — Experimental";
run;

proc print data=dor_surv_ctrl;
  where CENSOR = 0;
  title "TC-035: DOR KM Survival — Control";
run;

/* Export BOR distribution */
proc print data=bor_dist;
  title "TC-035: BOR Distribution by Arm";
run;

/* Export consistency checks */
proc print data=consistency_check;
  title "TC-035: Cross-TFL Consistency Checks";
run;

title;
