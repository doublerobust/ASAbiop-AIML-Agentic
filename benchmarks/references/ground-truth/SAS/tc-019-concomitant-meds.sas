/* ------------------------------------------------------------------ *
 * TC-019 Ground Truth: Concomitant Medications Summary Table (SAS)   *
 * Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark              *
 *                                                                    *
 * Summarizes concomitant medications by ATC class and preferred name: *
 *   - Number of subjects taking each medication (n, %)                *
 *   - Sorted by ATC class, then descending frequency                  *
 *   - Summary rows: Any CM, subjects with >=1 CM                      *
 *                                                                    *
 * ⚠️ Reference implementation only — not run or verified (no SAS license)*
 * Ground truth established via R + Python only                         *
 *                                                                    *
 * Usage: sas tc-019-concomitant-meds.sas -set seed 42 -set n 200     *
 *        -set outpath .                                              *
 * ------------------------------------------------------------------ */

options nosource nosource2 nomprint nomlogic nonotes;
%let seed = 42;
%let n = 200;
%let outpath = .;

/* ─────────────────────────────────────────────────────
   Synthetic ADCM Dataset Generation
   ───────────────────────────────────────────────────── */
data adcm;
    call streaminit(&seed);
    array atc_codes{8} $3 _temporary_ ("J01" "N02" "C03" "A02" "N05" "C07" "B01" "M01");
    array atc_names{8} $40 _temporary_ (
        "Antibacterials for systemic use"
        "Analgesics"
        "Diuretics"
        "Drugs for acid related disorders"
        "Psycholeptics"
        "Beta blocking agents"
        "Antithrombotic agents"
        "Antiinflammatory/antirheumatic products"
    );
    /* Medications per ATC class (max 3 per class) */
    array med_j01{3} $20 _temporary_ ("Amoxicillin" "Ciprofloxacin" "Azithromycin");
    array med_n02{3} $20 _temporary_ ("Paracetamol" "Ibuprofen" "Tramadol");
    array med_c03{2} $20 _temporary_ ("Furosemide" "Hydrochlorothiazide");
    array med_a02{3} $20 _temporary_ ("Omeprazole" "Pantoprazole" "Ranitidine");
    array med_n05{3} $20 _temporary_ ("Diazepam" "Lorazepam" "Zolpidem");
    array med_c07{3} $20 _temporary_ ("Metoprolol" "Atenolol" "Bisoprolol");
    array med_b01{3} $20 _temporary_ ("Warfarin" "Heparin" "Apixaban");
    array med_m01{3} $20 _temporary_ ("Naproxen" "Celecoxib" "Diclofenac");

    /* Treatment assignment matching ADSL */
    do i = 1 to &n;
        trt01pn = rand("bernoulli", 0.5);
        /* Each subject takes 0-5 concomitant medications */
        /* n_meds: 0(5%) 1(15%) 2(25%) 3(25%) 4(20%) 5(10%) */
        r = rand("uniform");
        if r < 0.05 then n_meds = 0;
        else if r < 0.20 then n_meds = 1;
        else if r < 0.45 then n_meds = 2;
        else if r < 0.70 then n_meds = 3;
        else if r < 0.90 then n_meds = 4;
        else n_meds = 5;

        if n_meds > 0 then do j = 1 to min(n_meds, 8);
            cls_idx = ceil(rand("uniform") * 8);
            atcclass = atc_codes{cls_idx};
            atcclas_name = atc_names{cls_idx};
            /* Select medication within class */
            select(cls_idx);
                when(1) med_idx = ceil(rand("uniform") * dim(med_j01));
                when(2) med_idx = ceil(rand("uniform") * dim(med_n02));
                when(3) med_idx = ceil(rand("uniform") * dim(med_c03));
                when(4) med_idx = ceil(rand("uniform") * dim(med_a02));
                when(5) med_idx = ceil(rand("uniform") * dim(med_n05));
                when(6) med_idx = ceil(rand("uniform") * dim(med_c07));
                when(7) med_idx = ceil(rand("uniform") * dim(med_b01));
                when(8) med_idx = ceil(rand("uniform") * dim(med_m01));
                otherwise med_idx = 1;
            end;
            select(cls_idx);
                when(1) cmdecod = med_j01{med_idx};
                when(2) cmdecod = med_n02{med_idx};
                when(3) cmdecod = med_c03{med_idx};
                when(4) cmdecod = med_a02{med_idx};
                when(5) cmdecod = med_n05{med_idx};
                when(6) cmdecod = med_c07{med_idx};
                when(7) cmdecod = med_b01{med_idx};
                when(8) cmdecod = med_m01{med_idx};
                otherwise cmdecod = "Unknown";
            end;
            usubjid = cats("SUBJ-", put(i, z4.));
            cmindc = "Treatment";
            output;
        end;
    end;
    drop i j r n_meds cls_idx med_idx;
run;

/* Build ADSL for N denominators */
data adsl;
    call streaminit(&seed);
    do i = 1 to &n;
        usubjid = cats("SUBJ-", put(i, z4.));
        trt01pn = rand("bernoulli", 0.5);
        saffl = "Y";
        ittfl = "Y";
        output;
    end;
    drop i;
run;

/* ─────────────────────────────────────────────────────
   Concomitant Medications Summary
   ───────────────────────────────────────────────────── */

/* Per-arm safety N */
proc sql noprint;
    create table arm_n as
    select trt01pn, count(*) as n_total
    from adsl
    where saffl = "Y"
    group by trt01pn;
quit;

/* Summary: Any CM */
proc sql noprint;
    create table any_cm as
    select a.trt01pn,
           count(distinct a.usubjid) as n_subjects_with_cm
    from adcm a
    inner join adsl s on a.usubjid = s.usubjid
    where s.saffl = "Y"
    group by a.trt01pn;
quit;

/* ATC class-level summary */
proc sql noprint;
    create table atc_summary as
    select a.atcclass,
           a.atcclas_name,
           a.trt01pn,
           count(distinct a.usubjid) as n_subjects
    from adcm a
    inner join adsl s on a.usubjid = s.usubjid
    where s.saffl = "Y"
    group by a.atcclass, a.atcclas_name, a.trt01pn
    order by a.atcclass, a.trt01pn;
quit;

/* Medication-level summary within ATC class */
proc sql noprint;
    create table med_summary as
    select a.atcclass,
           a.cmdecod,
           a.trt01pn,
           count(distinct a.usubjid) as n_subjects
    from adcm a
    inner join adsl s on a.usubjid = s.usubjid
    where s.saffl = "Y"
    group by a.atcclass, a.cmdecod, a.trt01pn
    order by a.atcclass, n_subjects desc, a.trt01pn;
quit;

/* ─────────────────────────────────────────────────────
   JSON Output
   ───────────────────────────────────────────────────── */
data _null_;
    file "&outpath/tc-019-results-sas.json";
    length line $2000;
    /* Header */
    put '{"test_case": "TC-019",';
    put '  "description": "Concomitant Medications Summary Table",';
    put '  "metadata": {';
    put '    "seed": &seed,';
    put '    "n_subjects": &n,';
    put '    "population": "SAFETY",';
    put '    "population_flag": "SAFFL"';
    put '  },';

    /* Arm N */
    put '  "arm_n": [';
    set arm_n end=eof;
    pct = n_total / &n * 100;
    line = catt('    {"trt01pn": ', trt01pn, ', "n_total": ', n_total, ', "pct": ', round(pct, 0.1), '}');
    if _n_ < 2 then put line ',';
    else put line;
    if eof then put '  ],';

    /* Any CM summary */
    put '  "summary_rows": [';
    set any_cm end=eof;
    line = catt('    {"label": "Any CM", "trt01pn": ', trt01pn,
                ', "n_subjects": ', n_subjects_with_cm, '}');
    if _n_ < 2 then put line ',';
    else put line;
    if eof then put '  ],';

    /* ATC class detail */
    put '  "atc_class_rows": [';
    set atc_summary end=eof;
    line = catt('    {"atcclass": "', atcclass, '", "atcclas_name": "', atcclas_name,
                '", "trt01pn": ', trt01pn, ', "n_subjects": ', n_subjects, '}');
    if not eof then put line ',';
    else put line;
    if eof then put '  ],';

    /* Medication detail */
    put '  "medication_rows": [';
    set med_summary end=eof;
    line = catt('    {"atcclass": "', atcclass, '", "cmdecod": "', cmdecod,
                '", "trt01pn": ', trt01pn, ', "n_subjects": ', n_subjects, '}');
    if not eof then put line ',';
    else put line;
    if eof then put '  ]';
    put '}';
run;
