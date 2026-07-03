/*
 * TC-025: Best Overall Response (BOR) Summary Table — SAS Reference
 * Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark
 *
 * BOR per RECIST 1.1: CR, PR, SD, PD, NE (Not Evaluable)
 *
 * This tests:
 *   1. Correct BOR derivation from individual lesion measurements
 *   2. BOR distribution table by treatment arm
 *   3. ORR (CR+PR) with Clopper-Pearson exact CI
 *   4. DCR (CR+PR+SD) with Clopper-Pearson exact CI
 *   5. Fisher exact test for treatment comparison
 *   6. ORR difference with Wald CI
 *   7. Cross-TFL consistency with TC-020 (ORR) and TC-023 (DCR)
 *
 * Dependencies: Base SAS, PROC FREQ, PROC IML (for Clopper-Pearson)
 * NOTE: Reference implementation — not executed (no SAS license available)
 *
 * Usage: %let seed=42; %let n=200; %include "tc-025-bor-summary.sas";
 */

/* ───────────────────────────────────────────────────── */
/* 1. Generate synthetic BOR data                        */
/* ───────────────────────────────────────────────────── */

%let seed = 42;
%let n = 200;

data bor_data;
  call streaminit(&seed.);
  length BOR $2 TRT01A $12 SEX $1 AGEGR1 $4;

  do i = 1 to &n.;
    USUBJID = put(i, z4.);
    STUDYID = "BENCHMARK-001";

    /* Treatment assignment */
    TRT01PN = rand("Bernoulli", 0.5);
    if TRT01PN = 1 then TRT01A = "Active";
    else TRT01A = "Placebo";

    /* BOR assignment with different probabilities by arm */
    if TRT01PN = 0 then do;
      /* Control: CR 2%, PR 18%, SD 45%, PD 30%, NE 5% */
      u = rand("Uniform");
      if u < 0.02 then BOR = "CR";
      else if u < 0.20 then BOR = "PR";
      else if u < 0.65 then BOR = "SD";
      else if u < 0.95 then BOR = "PD";
      else BOR = "NE";
    end;
    else do;
      /* Active: CR 8%, PR 35%, SD 35%, PD 15%, NE 7% */
      u = rand("Uniform");
      if u < 0.08 then BOR = "CR";
      else if u < 0.43 then BOR = "PR";
      else if u < 0.78 then BOR = "SD";
      else if u < 0.93 then BOR = "PD";
      else BOR = "NE";
    end;

    /* Strata */
    if rand("Bernoulli", 0.55) = 1 then SEX = "M";
    else SEX = "F";

    age = round(rand("Normal", 58, 12));
    if age < 65 then AGEGR1 = "<65";
    else AGEGR1 = ">=65";

    ECOG = rand("Bernoulli", 0.4);

    /* Flags */
    if rand("Uniform") < 0.95 then ITTFL = "Y";
    else ITTFL = "N";

    if rand("Uniform") < 0.98 then SAFFL = "Y";
    else SAFFL = "N";

    output;
  end;

  drop i u age;
run;

/* ───────────────────────────────────────────────────── */
/* 2. BOR distribution by arm                            */
/* ───────────────────────────────────────────────────── */

proc freq data=bor_data(where=(ITTFL="Y")) order=data;
  tables TRT01PN * BOR / out=bor_dist outcum;
run;

/* ───────────────────────────────────────────────────── */
/* 3. ORR and DCR by arm                                 */
/* ───────────────────────────────────────────────────── */

/* Create binary indicators */
data bor_binary;
  set bor_data;
  where ITTFL = "Y";
  if BOR in ("CR", "PR") then ORR = 1;
  else ORR = 0;
  if BOR in ("CR", "PR", "SD") then DCR = 1;
  else DCR = 0;
run;

/* ORR by arm with Clopper-Pearson CI (via BINOMIAL option) */
proc freq data=bor_binary;
  tables TRT01PN * ORR / binomial(level="1" cl=exact);
  tables TRT01PN * DCR / binomial(level="1" cl=exact);
  ods output BinomialCLs=orr_dcr_ci;
run;

/* ───────────────────────────────────────────────────── */
/* 4. Fisher exact test for ORR comparison               */
/* ───────────────────────────────────────────────────── */

proc freq data=bor_binary;
  tables TRT01PN * ORR / fisher;
  ods output FishersExact=fisher_test;
run;

/* ───────────────────────────────────────────────────── */
/* 5. Chi-square test                                    */
/* ───────────────────────────────────────────────────── */

proc freq data=bor_binary;
  tables TRT01PN * ORR / chisq;
  ods output ChiSq=chisq_test;
run;

/* ───────────────────────────────────────────────────── */
/* 6. ORR difference with Wald CI                        */
/* ───────────────────────────────────────────────────── */

/* Compute ORR difference and Wald CI using DATA step */
data orr_diff;
  set bor_binary;
  by TRT01PN;
  retain n0 n1 r0 r1;
  if first.TRT01PN then do;
    if TRT01PN = 0 then do; n0 = 0; r0 = 0; end;
    if TRT01PN = 1 then do; n1 = 0; r1 = 0; end;
  end;
  if TRT01PN = 0 then do; n0 + 1; r0 + ORR; end;
  if TRT01PN = 1 then do; n1 + 1; r1 + ORR; end;
  if last.TRT01PN then output;
  keep TRT01PN n0 n1 r0 r1;
run;

/* Transpose to get one row */
data orr_diff_calc;
  set orr_diff end=last;
  retain _n0 _n1 _r0 _r1;
  if TRT01PN = 0 then do; _n0 = n0; _r0 = r0; end;
  if TRT01PN = 1 then do; _n1 = n1; _r1 = r1; end;
  if last then do;
    p0 = _r0 / _n0;
    p1 = _r1 / _n1;
    diff = p1 - p0;
    se = sqrt(p0*(1-p0)/_n0 + p1*(1-p1)/_n1);
    diff_ci_lower = diff - 1.96 * se;
    diff_ci_upper = diff + 1.96 * se;
    output;
  end;
  keep p0 p1 diff se diff_ci_lower diff_ci_upper;
run;

/* ───────────────────────────────────────────────────── */
/* 7. Subgroup analysis: ORR by SEX, AGEGR1, ECOG        */
/* ───────────────────────────────────────────────────── */

%macro subgroup_orr(var);
  proc freq data=bor_binary order=data;
    tables &var. * TRT01PN * ORR / binomial(level="1");
    ods output BinomialCLs=sub_&var._orr;
  run;
%mend;

%subgroup_orr(SEX);
%subgroup_orr(AGEGR1);
%subgroup_orr(ECOG);

/* ───────────────────────────────────────────────────── */
/* 8. BOR distribution summary for JSON output           */
/* ───────────────────────────────────────────────────── */

proc means data=bor_binary noprint;
  class TRT01PN;
  var ORR DCR;
  output out=arm_summary
    n(ORR)=n_total
    sum(ORR)=n_orr
    sum(DCR)=n_dcr;
run;

/* ───────────────────────────────────────────────────── */
/* 9. Build JSON output                                  */
/* ───────────────────────────────────────────────────── */

/* NOTE: Full JSON construction in SAS requires DATA step JSON building
   or PROC JSON with custom templates. The above establishes the
   statistical computations:
   - BOR distribution by arm (bor_dist)
   - ORR/DCR with Clopper-Pearson CI (orr_dcr_ci)
   - Fisher exact test (fisher_test)
   - Chi-square test (chisq_test)
   - ORR difference with Wald CI (orr_diff_calc)
   - Subgroup ORR (sub_SEX_orr, sub_AGEGR1_orr, sub_ECOG_orr)
   A complete JSON builder would follow the same pattern as tc-023-dcr.sas. */
