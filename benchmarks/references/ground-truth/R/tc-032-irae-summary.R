#!/usr/bin/env Rscript
#' TC-032: Immune-Related Adverse Event (irAE) Summary
#'
#' Generates an I-O specific safety summary table with:
#' - Rows: irAE categories (Endocrine, Dermatologic, Hepatic, GI, Pulmonary, Other)
#'   → Preferred Term (PT) → Severity Grade (CTCAE v5.0)
#' - Columns: Treatment arms (Experimental vs Control)
#' - Cells: n (%) for each irAE term by severity
#' - Overall irAE summary: Any irAE, Grade 3+, irAE leading to discontinuation
#' - Median time-to-onset by category
#'
#' Usage:
#'   Rscript tc-032-irae-summary.R --seed 42 --n 200 --output tc-032-output.json

suppressPackageStartupMessages({
  library(jsonlite)
  library(dplyr)
  library(tidyr)
})

# --- Argument parsing ---
args <- commandArgs(trailingOnly = TRUE)
seed <- 42
n_subjects <- 200
output_file <- "tc-032-output.json"
data_csv <- ""
ars_output <- ""

i <- 1
while (i <= length(args)) {
  if (args[i] == "--seed") { seed <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--n") { n_subjects <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--output") { output_file <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--data") { data_csv <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--ars-output") { ars_output <- args[i + 1]; i <- i + 2 }
  else { i <- i + 1 }
}

set.seed(seed)

# --- irAE category definitions ---
irae_categories <- list(
  "Endocrine disorders" = list(
    soc_list = "Endocrine disorders",
    pts = c("Hypothyroidism", "Hyperthyroidism", "Thyroiditis",
            "Adrenal insufficiency", "Hypophysitis", "Type 1 diabetes mellitus",
            "Autoimmune diabetes")
  ),
  "Dermatologic disorders" = list(
    soc_list = "Skin and subcutaneous tissue disorders",
    pts = c("Rash maculo-papular", "Vitiligo", "Pruritus",
            "Alopecia", "Psoriasis", "Dermatitis bullous",
            "Erythema multiforme")
  ),
  "Hepatic disorders" = list(
    soc_list = "Hepatobiliary disorders",
    pts = c("Hepatitis", "Autoimmune hepatitis", "Hepatotoxicity",
            "Blood bilirubin increased", "Liver function test abnormal")
  ),
  "Gastrointestinal disorders" = list(
    soc_list = "Gastrointestinal disorders",
    pts = c("Colitis", "Diarrhoea", "Enterocolitis",
            "Gastritis", "Pancreatitis")
  ),
  "Pulmonary disorders" = list(
    soc_list = "Respiratory, thoracic and mediastinal disorders",
    pts = c("Pneumonitis", "Interstitial lung disease", "Pleural effusion",
            "Cough", "Dyspnoea")
  ),
  "Other immune-related" = list(
    soc_list = "Musculoskeletal and connective tissue disorders",
    pts = c("Arthritis", "Myositis", "Nephritis",
            "Autoimmune nephritis", "Anaemia", "Neutropenia",
            "Guillain-Barre syndrome", "Myasthenia gravis",
            "Encephalitis", "Meningitis aseptic")
  )
)

category_order <- names(irae_categories)

# CTCAE v5.0 severity grades
severity_grades <- c(1, 2, 3, 4, 5)
# irAEs tend to be more evenly distributed than general AEs
irae_severity_weights <- c(0.35, 0.30, 0.20, 0.10, 0.05)

# --- Data generation or loading ---
n_arm <- n_subjects %/% 2
arms <- rep(c("Experimental", "Control"), each = n_arm)
subjid <- paste0("SUBJ-", sprintf("%04d", 1:n_subjects))

if (data_csv != "") {
  adae <- read.csv(data_csv, stringsAsFactors = FALSE)
  n_arm <- length(unique(adae$USUBJID[adae$TRT01A == "Experimental"]))
  n_arm_ctl <- length(unique(adae$USUBJID[adae$TRT01A == "Control"]))
  n_subjects <- n_arm + n_arm_ctl
} else {
  generate_irae_records <- function(subjids, arm, seed_offset) {
    set.seed(seed + seed_offset)
    records <- list()
    rate_mult <- if (arm == "Experimental") 1.5 else 0.6

    for (cat_name in category_order) {
      cat_info <- irae_categories[[cat_name]]
      for (pt in cat_info$pts) {
        base_rate <- runif(1, 0.01, 0.15)
        adj_rate <- min(base_rate * rate_mult, 0.90)
        n_events <- rbinom(1, length(subjids), adj_rate)

        if (n_events > 0) {
          affected <- sample(subjids, n_events)
          for (s in affected) {
            severity <- sample(severity_grades, 1, prob = irae_severity_weights)
            if (severity >= 3) {
              aeacn <- sample(
                c("DOSE NOT CHANGED", "DOSE REDUCED", "DRUG WITHDRAWN",
                  "DRUG INTERRUPTED", "CORTICOSTEROID THERAPY"),
                1, prob = c(0.20, 0.15, 0.20, 0.25, 0.20)
              )
            } else {
              aeacn <- sample(
                c("DOSE NOT CHANGED", "DOSE REDUCED", "DRUG WITHDRAWN",
                  "DRUG INTERRUPTED", "CORTICOSTEROID THERAPY"),
                1, prob = c(0.55, 0.10, 0.05, 0.10, 0.20)
              )
            }
            aeser <- if (severity >= 4) "Y" else sample(c("Y", "N"), 1, prob = c(0.08, 0.92))
            ttonset <- sample(14:180, 1)

            records[[length(records) + 1]] <- list(
              USUBJID = s,
              TRT01A = arm,
              AEBODSYS = cat_info$soc_list,
              AEDECOD = pt,
              AESEV = as.character(severity),
              AESER = aeser,
              AEACN = aeacn,
              AEFLAG = "IMMUNE",
              ASTDT = ttonset
            )
          }
        }
      }
    }

    if (length(records) == 0) return(data.frame())
    do.call(rbind, lapply(records, as.data.frame, stringsAsFactors = FALSE))
  }

  adae_exp <- generate_irae_records(subjid[arms == "Experimental"], "Experimental", 1100)
  adae_ctl <- generate_irae_records(subjid[arms == "Control"], "Control", 1200)
  adae <- rbind(adae_exp, adae_ctl)
}

# Filter to immune-related AEs only
irae_records <- adae[adae$AEFLAG == "IMMUNE", ]

# --- Classify irAEs by category ---
classify_irae <- function(pt) {
  for (cat_name in category_order) {
    if (pt %in% irae_categories[[cat_name]]$pts) return(cat_name)
  }
  return("Other immune-related")
}

irae_records$irae_category <- sapply(irae_records$AEDECOD, classify_irae)

# --- Compute irAE summary ---
n_exp <- n_arm
n_ctl <- n_subjects - n_arm
pct <- function(n, total) round(100 * n / total, 1)

# Overall irAE summary
any_irae_exp <- length(unique(irae_records$USUBJID[irae_records$TRT01A == "Experimental"]))
any_irae_ctl <- length(unique(irae_records$USUBJID[irae_records$TRT01A == "Control"]))
g3plus_exp <- length(unique(irae_records$USUBJID[irae_records$TRT01A == "Experimental" & as.integer(irae_records$AESEV) >= 3]))
g3plus_ctl <- length(unique(irae_records$USUBJID[irae_records$TRT01A == "Control" & as.integer(irae_records$AESEV) >= 3]))
disc_exp <- length(unique(irae_records$USUBJID[irae_records$TRT01A == "Experimental" & irae_records$AEACN == "DRUG WITHDRAWN"]))
disc_ctl <- length(unique(irae_records$USUBJID[irae_records$TRT01A == "Control" & irae_records$AEACN == "DRUG WITHDRAWN"]))
steroid_exp <- length(unique(irae_records$USUBJID[irae_records$TRT01A == "Experimental" & grepl("CORTICOSTEROID", irae_records$AEACN)]))
steroid_ctl <- length(unique(irae_records$USUBJID[irae_records$TRT01A == "Control" & grepl("CORTICOSTEROID", irae_records$AEACN)]))

summary_rows <- list(
  list(category = "Any immune-related AE",
       n_experimental = any_irae_exp,
       pct_experimental = if (n_exp > 0) pct(any_irae_exp, n_exp) else 0,
       n_control = any_irae_ctl,
       pct_control = if (n_ctl > 0) pct(any_irae_ctl, n_ctl) else 0),
  list(category = "Grade \u22653 immune-related AE",
       n_experimental = g3plus_exp,
       pct_experimental = if (n_exp > 0) pct(g3plus_exp, n_exp) else 0,
       n_control = g3plus_ctl,
       pct_control = if (n_ctl > 0) pct(g3plus_ctl, n_ctl) else 0),
  list(category = "irAE leading to discontinuation",
       n_experimental = disc_exp,
       pct_experimental = if (n_exp > 0) pct(disc_exp, n_exp) else 0,
       n_control = disc_ctl,
       pct_control = if (n_ctl > 0) pct(disc_ctl, n_ctl) else 0),
  list(category = "irAE requiring corticosteroids",
       n_experimental = steroid_exp,
       pct_experimental = if (n_exp > 0) pct(steroid_exp, n_exp) else 0,
       n_control = steroid_ctl,
       pct_control = if (n_ctl > 0) pct(steroid_ctl, n_ctl) else 0)
)

# --- Severity summary by grade ---
severity_summary <- lapply(severity_grades, function(g) {
  exp_n <- length(unique(irae_records$USUBJID[irae_records$AESEV == as.character(g) & irae_records$TRT01A == "Experimental"]))
  ctl_n <- length(unique(irae_records$USUBJID[irae_records$AESEV == as.character(g) & irae_records$TRT01A == "Control"]))
  list(
    grade = g,
    n_experimental = exp_n,
    pct_experimental = if (n_exp > 0) pct(exp_n, n_exp) else 0,
    n_control = ctl_n,
    pct_control = if (n_ctl > 0) pct(ctl_n, n_ctl) else 0
  )
})

# --- By category → PT → Severity ---
irae_table <- list()

for (cat_name in category_order) {
  cat_data <- irae_records[irae_records$irae_category == cat_name, ]

  cat_exp <- length(unique(cat_data$USUBJID[cat_data$TRT01A == "Experimental"]))
  cat_ctl <- length(unique(cat_data$USUBJID[cat_data$TRT01A == "Control"]))

  irae_table[[length(irae_table) + 1]] <- list(
    category = "category",
    irae_category = cat_name,
    pt = NA,
    severity = NA,
    n_experimental = cat_exp,
    pct_experimental = if (n_exp > 0) pct(cat_exp, n_exp) else 0,
    n_control = cat_ctl,
    pct_control = if (n_ctl > 0) pct(cat_ctl, n_ctl) else 0
  )

  # Category by severity
  for (g in severity_grades) {
    g_exp <- length(unique(cat_data$USUBJID[cat_data$AESEV == as.character(g) & cat_data$TRT01A == "Experimental"]))
    g_ctl <- length(unique(cat_data$USUBJID[cat_data$AESEV == as.character(g) & cat_data$TRT01A == "Control"]))
    irae_table[[length(irae_table) + 1]] <- list(
      category = "category_severity",
      irae_category = cat_name,
      pt = NA,
      severity = g,
      n_experimental = g_exp,
      pct_experimental = if (n_exp > 0) pct(g_exp, n_exp) else 0,
      n_control = g_ctl,
      pct_control = if (n_ctl > 0) pct(g_ctl, n_ctl) else 0
    )
  }

  # PTs within category, sorted by descending max frequency
  pt_data <- cat_data %>%
    group_by(AEDECOD) %>%
    summarise(total = n_distinct(USUBJID), .groups = "drop") %>%
    arrange(desc(total))

  for (pt in pt_data$AEDECOD) {
    pt_data_sub <- cat_data[cat_data$AEDECOD == pt, ]
    pt_exp <- length(unique(pt_data_sub$USUBJID[pt_data_sub$TRT01A == "Experimental"]))
    pt_ctl <- length(unique(pt_data_sub$USUBJID[pt_data_sub$TRT01A == "Control"]))

    irae_table[[length(irae_table) + 1]] <- list(
      category = "pt",
      irae_category = cat_name,
      pt = pt,
      severity = NA,
      n_experimental = pt_exp,
      pct_experimental = if (n_exp > 0) pct(pt_exp, n_exp) else 0,
      n_control = pt_ctl,
      pct_control = if (n_ctl > 0) pct(pt_ctl, n_ctl) else 0
    )

    # PT by severity
    for (g in severity_grades) {
      g_exp <- length(unique(pt_data_sub$USUBJID[pt_data_sub$AESEV == as.character(g) & pt_data_sub$TRT01A == "Experimental"]))
      g_ctl <- length(unique(pt_data_sub$USUBJID[pt_data_sub$AESEV == as.character(g) & pt_data_sub$TRT01A == "Control"]))
      irae_table[[length(irae_table) + 1]] <- list(
        category = "pt_severity",
        irae_category = cat_name,
        pt = pt,
        severity = g,
        n_experimental = g_exp,
        pct_experimental = if (n_exp > 0) pct(g_exp, n_exp) else 0,
        n_control = g_ctl,
        pct_control = if (n_ctl > 0) pct(g_ctl, n_ctl) else 0
      )
    }
  }
}

# --- Median time-to-onset by category ---
onset_summary <- list()
for (cat_name in category_order) {
  cat_data <- irae_records[irae_records$irae_category == cat_name, ]
  exp_onsets <- sort(as.integer(cat_data$ASTDT[cat_data$TRT01A == "Experimental"]))
  ctl_onsets <- sort(as.integer(cat_data$ASTDT[cat_data$TRT01A == "Control"]))

  median_val <- function(lst) {
    if (length(lst) == 0) return(NA)
    n <- length(lst)
    if (n %% 2 == 1) return(lst[(n + 1) / 2])
    else return(round((lst[n / 2] + lst[n / 2 + 1]) / 2, 1))
  }

  onset_summary[[length(onset_summary) + 1]] <- list(
    irae_category = cat_name,
    median_onset_experimental = median_val(exp_onsets),
    median_onset_control = median_val(ctl_onsets),
    n_experimental = length(exp_onsets),
    n_control = length(ctl_onsets)
  )
}

output <- list(
  test_case_id = "TC-032",
  title = "Immune-Related Adverse Event Summary",
  parameters = list(seed = seed, n_subjects = n_subjects),
  population = list(
    description = "Safety population (SAFFL = 'Y')",
    n_experimental = n_exp,
    n_control = n_ctl
  ),
  severity_grades = severity_grades,
  severity_summary = severity_summary,
  summary = summary_rows,
  irae_table = irae_table,
  onset_summary = onset_summary,
  metadata = list(
    language = "R",
    packages = c("jsonlite", "dplyr", "tidyr")
  )
)

write_json(output, output_file, auto_unbox = TRUE, pretty = TRUE)

cat("TC-032 output written to", output_file, "\n")
cat("  Subjects:", n_subjects, "(Exp =", n_exp, ", Ctrl =", n_ctl, ")\n")
cat("  irAE records:", nrow(irae_records), "\n")
cat("  Categories:", length(category_order), "\n")
cat("  Any irAE: Exp =", any_irae_exp, "(", round(100 * any_irae_exp / n_exp, 1), "%),",
    "Ctrl =", any_irae_ctl, "(", round(100 * any_irae_ctl / n_ctl, 1), "%)\n")
cat("  Grade \u22653: Exp =", g3plus_exp, ", Ctrl =", g3plus_ctl, "\n")

# --- ARS output (optional) ---
if (ars_output != "") {
  ars_envelope <- list(
    analysisResult = list(
      id = "TC-032",
      version = "1.0",
      analysisReason = "Safety: immune-related AE summary by category and severity",
      analysisMethod = list(
        name = "irAE summary by category and severity",
        codeTemplate = "tc-032-irae-summary.R",
        parameters = list(
          severity_grades = severity_grades,
          irae_categories = category_order,
          population = "SAFETY",
          irae_filter = "AEFLAG = 'IMMUNE'"
        )
      ),
      analysisVariables = list(
        list(name = "AEDECOD", dataset = "ADAE", role = "category"),
        list(name = "AESEV", dataset = "ADAE", role = "severity"),
        list(name = "AEFLAG", dataset = "ADAE", role = "immune_flag"),
        list(name = "TRT01A", dataset = "ADSL", role = "treatment"),
        list(name = "ASTDT", dataset = "ADAE", role = "onset_date")
      ),
      analysisPopulation = list(
        id = "SAFETY",
        filter = "SAFFL = 'Y' AND AEFLAG = 'IMMUNE'",
        n = n_subjects
      ),
      resultGroups = list(
        list(id = "Experimental", n = n_exp),
        list(id = "Control", n = n_ctl)
      ),
      analysisResultsData = list(
        statistics = c(
          lapply(severity_grades, function(g) {
            list(name = paste0("grade_", g, "_n_experimental"),
                 value = severity_summary[[g]]$n_experimental)
          }),
          lapply(severity_grades, function(g) {
            list(name = paste0("grade_", g, "_n_control"),
                 value = severity_summary[[g]]$n_control)
          }),
          list(
            list(name = "any_irae_n_experimental", value = any_irae_exp),
            list(name = "any_irae_n_control", value = any_irae_ctl),
            list(name = "g3plus_n_experimental", value = g3plus_exp),
            list(name = "g3plus_n_control", value = g3plus_ctl)
          )
        ),
        timeToOnset = lapply(onset_summary, function(o) {
          list(
            category = o$irae_category,
            median_experimental = o$median_onset_experimental,
            median_control = o$median_onset_control
          )
        })
      )
    )
  )
  write_json(ars_envelope, ars_output, auto_unbox = TRUE, pretty = TRUE)
  cat("ARS envelope written to", ars_output, "\n")
}
