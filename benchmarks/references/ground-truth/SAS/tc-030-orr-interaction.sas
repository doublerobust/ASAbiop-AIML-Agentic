/* TC-030: ORR by Subgroup with Interaction Test — SAS
 *
 * Extends TC-020 by adding:
 *   - Logistic regression with treatment × subgroup interaction (Wald test)
 *   - Clopper-Pearson exact confidence intervals
 *   - Breslow-Day test for homogeneity of odds ratios
 *
 * Output: Subgroup-level ORR (N, %, Clopper-Pearson CI) per arm,
 *         logistic interaction p-value, Breslow-Day p-value
 *
 * Usage: sas tc-030-orr-interaction.sas -set seed 42 -set n 200
 */

options nosource2 linesize=120;
%let seed = %sysget(seed);
%if &seed = %then %let seed = 42;
%let n = %sysget(n);
%if &n = %then %let n = 200;

/* --- Generate tumor response data --- */
data adrs;
  call streaminit(&seed);
  length USUBJID $10 TRT01A $12 SEX $6 AGEGR1 $5 BOR $2;
  do i = 1 to &n;
    trt = rand("bernoulli", 0.5);
    sex = ifc(rand("uniform") < 0.55, "Male", "Female");
    age = round(rand("normal", 58, 12));
    agegr1 = ifc(age < 65, "<65", ">=65");
    ecog = ifc(rand("uniform") < 0.6, 0, 1);

    /* Response probability */
    if trt = 1 then do;
      if ecog = 0 then orr_prob = 0.45;
      else orr_prob = 0.30;
    end;
    else do;
      if ecog = 0 then orr_prob = 0.25;
      else orr_prob = 0.15;
    end;

    is_resp = rand("bernoulli", orr_prob);
    if is_resp = 1 then do;
      if rand("uniform") < 0.3 then bor = "CR";
      else bor = "PR";
    end;
    else do;
      if rand("uniform") < 0.4 then bor = "SD";
      else bor = "PD";
    end;

    aval = ifc(bor in ("CR", "PR"), 1, 0);
    USUBJID = cats("SUBJ-", put(i, z4.));
    TRT01PN = trt;
    TRT01A = ifc(trt = 0, "Control", "Experimental");
    output;
  end;
  keep USUBJID TRT01PN TRT01A SEX AGEGR1 ECOG BOR AVAL;
run;

/* --- Overall ORR by arm --- */
proc means data=adrs n sum mean;
  class TRT01PN;
  var AVAL;
  output out=overall_orr n=n_total sum=responders mean=orr_pct;
run;

/* --- Subgroup-level ORR --- */
/* SEX */
proc freq data=adrs;
  tables TRT01PN * AVAL / binomial (level=second);
  by SEX;
  output out=orr_sex;
run;

/* AGEGR1 */
proc freq data=adrs;
  tables TRT01PN * AVAL / binomial (level=second);
  by AGEGR1;
  output out=orr_agegr1;
run;

/* ECOG */
proc freq data=adrs;
  tables TRT01PN * AVAL / binomial (level=second);
  by ECOG;
  output out=orr_ecog;
run;

/* --- Logistic regression with interaction (SEX) --- */
data adrs_sex;
  set adrs;
  sg_num = ifc(SEX = "Male", 0, 1);
  trt_num = TRT01PN;
  interaction = trt_num * sg_num;
run;

proc logistic data=adrs_sex;
  model AVAL(event="1") = trt_num sg_num interaction / cl=wald;
  output out=logit_sex_out;
run;

/* --- Logistic regression with interaction (AGEGR1) --- */
data adrs_age;
  set adrs;
  sg_num = ifc(AGEGR1 = "<65", 0, 1);
  trt_num = TRT01PN;
  interaction = trt_num * sg_num;
run;

proc logistic data=adrs_age;
  model AVAL(event="1") = trt_num sg_num interaction / cl=wald;
  output out=logit_age_out;
run;

/* --- Logistic regression with interaction (ECOG) --- */
data adrs_ecog;
  set adrs;
  sg_num = ECOG;
  trt_num = TRT01PN;
  interaction = trt_num * sg_num;
run;

proc logistic data=adrs_ecog;
  model AVAL(event="1") = trt_num sg_num interaction / cl=wald;
  output out=logit_ecog_out;
run;

/* --- CMH test for each subgroup (Breslow-Day) --- */
proc freq data=adrs;
  tables SEX * TRT01PN * AVAL / cmh;
  output out=cmh_sex;
run;

proc freq data=adrs;
  tables AGEGR1 * TRT01PN * AVAL / cmh;
  output out=cmh_agegr1;
run;

proc freq data=adrs;
  tables ECOG * TRT01PN * AVAL / cmh;
  output out=cmh_ecog;
run;

/* --- Print results --- */
title "TC-030: ORR by Subgroup with Interaction Test";
proc print data=overall_orr;
run;

proc print data=orr_sex;
run;

proc print data=logit_sex_out (obs=5);
run;

title;
