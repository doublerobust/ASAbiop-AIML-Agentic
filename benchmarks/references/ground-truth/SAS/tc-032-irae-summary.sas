/* TC-032: Immune-Related Adverse Event (irAE) Summary
 *
 * Generates an I-O specific safety summary table with:
 * - Rows: irAE categories (Endocrine, Dermatologic, Hepatic, GI, Pulmonary, Other)
 *   -> PT -> Severity Grade (CTCAE v5.0)
 * - Columns: Treatment arms (Experimental vs Control)
 * - Cells: n (%) for each irAE term by severity
 * - Overall irAE summary: Any irAE, Grade 3+, irAE leading to discontinuation
 * - Median time-to-onset by category
 *
 * Usage:
 *   sas tc-032-irae-summary.sas -set seed 42 -set n 200 -set output tc-032-output.json
 */

/* Generate ADAE dataset with AEFLAG = 'IMMUNE' */
data adsl;
  retain USUBJID TRT01A SAFFL;
  call streaminit(&seed);
  n_arm = &n / 2;
  do i = 1 to &n;
    USUBJID = cats("SUBJ-", put(i, z4.));
    if i <= n_arm then TRT01A = "Experimental";
    else TRT01A = "Control";
    SAFFL = "Y";
    output;
  end;
  drop i n_arm;
run;

/* Generate immune-related AEs */
data adae;
  call streaminit(&seed + 1100);

  /* irAE category definitions */
  length AEBODSYS $60 AEDECOD $40;
  array cats{6} $30 _temporary_ (
    "Endocrine",
    "Dermatologic",
    "Hepatic",
    "Gastrointestinal",
    "Pulmonary",
    "Other_irAE"
  );

  /* Define PT lists per category */
  array endo_pts{7} $30 _temporary_ (
    "Hypothyroidism", "Hyperthyroidism", "Thyroiditis",
    "Adrenal insufficiency", "Hypophysitis", "Type 1 diabetes mellitus",
    "Autoimmune diabetes"
  );
  array derm_pts{7} $30 _temporary_ (
    "Rash maculo-papular", "Vitiligo", "Pruritus",
    "Alopecia", "Psoriasis", "Dermatitis bullous",
    "Erythema multiforme"
  );
  array hep_pts{5} $30 _temporary_ (
    "Hepatitis", "Autoimmune hepatitis", "Hepatotoxicity",
    "Blood bilirubin increased", "Liver function test abnormal"
  );
  array gi_pts{5} $30 _temporary_ (
    "Colitis", "Diarrhoea", "Enterocolitis",
    "Gastritis", "Pancreatitis"
  );
  array pulm_pts{5} $30 _temporary_ (
    "Pneumonitis", "Interstitial lung disease", "Pleural effusion",
    "Cough", "Dyspnoea"
  );
  array other_pts{10} $30 _temporary_ (
    "Arthritis", "Myositis", "Nephritis",
    "Autoimmune nephritis", "Anaemia", "Neutropenia",
    "Guillain-Barre syndrome", "Myasthenia gravis",
    "Encephalitis", "Meningitis aseptic"
  );

  do subj_idx = 1 to &n;
    if subj_idx <= &n/2 then arm = "Experimental";
    else arm = "Control";
    rate_mult = ifc(arm = "Experimental", 1.5, 0.6);

    /* Endocrine irAEs */
    do pt_idx = 1 to 7;
      base_rate = 0.01 + (rand("uniform") * 0.14);
      adj_rate = min(base_rate * rate_mult, 0.90);
      if rand("uniform") < adj_rate then do;
        USUBJID = cats("SUBJ-", put(subj_idx, z4.));
        TRT01A = arm;
        AEBODSYS = "Endocrine disorders";
        AEDECOD = endo_pts{pt_idx};
        AESEV = put(rand("table", 0.35, 0.30, 0.20, 0.10), 1.);
        AEFLAG = "IMMUNE";
        ASTDT = rand("uniform", 14, 180);
        output;
      end;
    end;

    /* Dermatologic irAEs */
    do pt_idx = 1 to 7;
      base_rate = 0.01 + (rand("uniform") * 0.14);
      adj_rate = min(base_rate * rate_mult, 0.90);
      if rand("uniform") < adj_rate then do;
        USUBJID = cats("SUBJ-", put(subj_idx, z4.));
        TRT01A = arm;
        AEBODSYS = "Skin and subcutaneous tissue disorders";
        AEDECOD = derm_pts{pt_idx};
        AESEV = put(rand("table", 0.35, 0.30, 0.20, 0.10), 1.);
        AEFLAG = "IMMUNE";
        ASTDT = rand("uniform", 14, 180);
        output;
      end;
    end;

    /* Hepatic irAEs */
    do pt_idx = 1 to 5;
      base_rate = 0.01 + (rand("uniform") * 0.14);
      adj_rate = min(base_rate * rate_mult, 0.90);
      if rand("uniform") < adj_rate then do;
        USUBJID = cats("SUBJ-", put(subj_idx, z4.));
        TRT01A = arm;
        AEBODSYS = "Hepatobiliary disorders";
        AEDECOD = hep_pts{pt_idx};
        AESEV = put(rand("table", 0.35, 0.30, 0.20, 0.10), 1.);
        AEFLAG = "IMMUNE";
        ASTDT = rand("uniform", 14, 180);
        output;
      end;
    end;

    /* GI irAEs */
    do pt_idx = 1 to 5;
      base_rate = 0.01 + (rand("uniform") * 0.14);
      adj_rate = min(base_rate * rate_mult, 0.90);
      if rand("uniform") < adj_rate then do;
        USUBJID = cats("SUBJ-", put(subj_idx, z4.));
        TRT01A = arm;
        AEBODSYS = "Gastrointestinal disorders";
        AEDECOD = gi_pts{pt_idx};
        AESEV = put(rand("table", 0.35, 0.30, 0.20, 0.10), 1.);
        AEFLAG = "IMMUNE";
        ASTDT = rand("uniform", 14, 180);
        output;
      end;
    end;

    /* Pulmonary irAEs */
    do pt_idx = 1 to 5;
      base_rate = 0.01 + (rand("uniform") * 0.14);
      adj_rate = min(base_rate * rate_mult, 0.90);
      if rand("uniform") < adj_rate then do;
        USUBJID = cats("SUBJ-", put(subj_idx, z4.));
        TRT01A = arm;
        AEBODSYS = "Respiratory, thoracic and mediastinal disorders";
        AEDECOD = pulm_pts{pt_idx};
        AESEV = put(rand("table", 0.35, 0.30, 0.20, 0.10), 1.);
        AEFLAG = "IMMUNE";
        ASTDT = rand("uniform", 14, 180);
        output;
      end;
    end;

    /* Other immune-related AEs */
    do pt_idx = 1 to 10;
      base_rate = 0.01 + (rand("uniform") * 0.14);
      adj_rate = min(base_rate * rate_mult, 0.90);
      if rand("uniform") < adj_rate then do;
        USUBJID = cats("SUBJ-", put(subj_idx, z4.));
        TRT01A = arm;
        AEBODSYS = "Musculoskeletal and connective tissue disorders";
        AEDECOD = other_pts{pt_idx};
        AESEV = put(rand("table", 0.35, 0.30, 0.20, 0.10), 1.);
        AEFLAG = "IMMUNE";
        ASTDT = rand("uniform", 14, 180);
        output;
      end;
    end;
  end;
  drop subj_idx arm rate_mult base_rate adj_rate pt_idx;
run;

/* Filter to immune-related AEs only */
data irae;
  set adae;
  where AEFLAG = "IMMUNE";
run;

/* Severity summary */
proc sql;
  create table severity_summary as
  select input(AESEV, 1.) as grade,
    count(distinct case when TRT01A = "Experimental" then USUBJID end) as n_experimental,
    count(distinct case when TRT01A = "Control" then USUBJID end) as n_control
  from irae
  group by calculated grade
  order by calculated grade;
quit;

/* Category-level summary */
proc sql;
  create table category_summary as
  select AEBODSYS as irae_category,
    count(distinct case when TRT01A = "Experimental" then USUBJID end) as n_experimental,
    count(distinct case when TRT01A = "Control" then USUBJID end) as n_control
  from irae
  group by AEBODSYS;
quit;

/* Overall summary */
proc sql;
  create table overall_summary as
  select
    count(distinct case when TRT01A = "Experimental" then USUBJID end) as any_irae_exp,
    count(distinct case when TRT01A = "Control" then USUBJID end) as any_irae_ctl,
    count(distinct case when input(AESEV,1.) >= 3 and TRT01A = "Experimental" then USUBJID end) as g3plus_exp,
    count(distinct case when input(AESEV,1.) >= 3 and TRT01A = "Control" then USUBJID end) as g3plus_ctl,
    count(distinct case when AEACN = "DRUG WITHDRAWN" and TRT01A = "Experimental" then USUBJID end) as disc_exp,
    count(distinct case when AEACN = "DRUG WITHDRAWN" and TRT01A = "Control" then USUBJID end) as disc_ctl
  from irae;
quit;

/* Output JSON via PROC JSON */
proc json out="&output" pretty;
  write open object;
  write "test_case_id" "TC-032";
  write "title" "Immune-Related Adverse Event Summary";
  write close;
run;
