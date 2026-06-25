#!/usr/bin/env Rscript
#' TC-011: Adverse Event Summary Table by SOC and Preferred Term
#' 
#' Generates a safety summary table with:
#' - Rows: System Organ Class (SOC) → Preferred Term (PT) hierarchy
#' - Columns: Treatment arms (Experimental vs Control)
#' - Cells: n (%) for each AE term, sorted by descending frequency
#' - Overall AEs, Serious AEs, and AEs leading to discontinuation
#'
#' Usage:
#'   Rscript tc-011-ae-summary.R --seed 42 --n 200 --output tc-011-output.json

suppressPackageStartupMessages({
  library(jsonlite)
  library(dplyr)
  library(tidyr)
})

# --- Argument parsing ---
args <- commandArgs(trailingOnly = TRUE)
seed <- 42
n_subjects <- 200
output_file <- "tc-011-output.json"
data_csv <- ""

i <- 1
while (i <= length(args)) {
  if (args[i] == "--seed") { seed <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--n") { n_subjects <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--output") { output_file <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--data") { data_csv <- args[i + 1]; i <- i + 2 }
  else { i <- i + 1 }
}

set.seed(seed)

# --- Data generation or loading ---
n_arm <- n_subjects / 2
arms <- rep(c("Experimental", "Control"), each = n_arm)
subjid <- paste0("SUBJ-", sprintf("%04d", 1:n_subjects))

if (data_csv != "") {
  # Load shared ADAE dataset from CSV
  adae <- read.csv(data_csv, stringsAsFactors = FALSE)
} else {
  # Generate ADSL-like subject data
  adsl <- data.frame(
    USUBJID = subjid,
    TRT01A = arms,
    SAFFL = "Y",
    stringsAsFactors = FALSE
  )

  # Define SOC/PT hierarchy with realistic frequencies
  ae_catalog <- list(
    "Gastrointestinal disorders" = c(
      "Nausea", "Diarrhoea", "Vomiting", "Abdominal pain", "Constipation"
    ),
    "General disorders and administration site conditions" = c(
      "Fatigue", "Pyrexia", "Oedema peripheral", "Asthenia"
    ),
    "Nervous system disorders" = c(
      "Headache", "Dizziness", "Neuropathy peripheral", "Dysgeusia"
    ),
    "Skin and subcutaneous tissue disorders" = c(
      "Rash", "Pruritus", "Alopecia", "Dry skin"
    ),
    "Investigations" = c(
      "ALT increased", "AST increased", "Blood creatinine increased", "Weight decreased"
    ),
    "Respiratory, thoracic and mediastinal disorders" = c(
      "Cough", "Dyspnoea", "Epistaxis"
    ),
    "Musculoskeletal and connective tissue disorders" = c(
      "Arthralgia", "Myalgia", "Back pain"
    ),
    "Infections and infestations" = c(
      "Upper respiratory tract infection", "Urinary tract infection", "Nasopharyngitis"
    )
  )

  # Generate AE rates (higher in experimental arm)
  generate_aes <- function(subjids, arm, ae_catalog, seed_offset) {
    set.seed(seed + seed_offset)
    records <- list()

    rate_multiplier <- if (arm == "Experimental") 1.3 else 1.0

    for (soc in names(ae_catalog)) {
      for (pt in ae_catalog[[soc]]) {
        base_rate <- runif(1, 0.02, 0.25)
        adj_rate <- min(base_rate * rate_multiplier, 0.95)

        n_events <- rbinom(1, length(subjids), adj_rate)
        if (n_events > 0) {
          affected <- sample(subjids, n_events)
          for (s in affected) {
            records[[length(records) + 1]] <- list(
              USUBJID = s,
              TRT01A = arm,
              AEBODSYS = soc,
              AEDECOD = pt,
              AESER = sample(c("Y", "N"), 1, prob = c(0.1, 0.9)),
              AEACN = sample(c("DOSE NOT CHANGED", "DOSE REDUCED", "DRUG WITHDRAWN"), 1, prob = c(0.7, 0.2, 0.1))
            )
          }
        }
      }
    }

    if (length(records) == 0) return(data.frame())
    do.call(rbind, lapply(records, as.data.frame, stringsAsFactors = FALSE))
  }

  adae_exp <- generate_aes(subjid[arms == "Experimental"], "Experimental", ae_catalog, 100)
  adae_ctl <- generate_aes(subjid[arms == "Control"], "Control", ae_catalog, 200)
  adae <- rbind(adae_exp, adae_ctl)
}

# --- Compute AE summary ---
n_exp <- sum(arms == "Experimental")
n_ctl <- sum(arms == "Control")

# Helper: compute n(%) for a set of subjects
fmt_n_pct <- function(n, total) {
  pct <- round(100 * n / total, 1)
  paste0(n, " (", pct, "%)")
}

# Any AE
any_exp <- length(unique(adae$USUBJID[adae$TRT01A %in% "Experimental"]))
any_ctl <- length(unique(adae$USUBJID[adae$TRT01A %in% "Control"]))

# Serious AEs
ser_exp <- length(unique(adae$USUBJID[adae$AESER == "Y" & adae$TRT01A %in% "Experimental"]))
ser_ctl <- length(unique(adae$USUBJID[adae$AESER == "Y" & adae$TRT01A %in% "Control"]))

# AEs leading to discontinuation
disc_exp <- length(unique(adae$USUBJID[adae$AEACN == "DRUG WITHDRAWN" & adae$TRT01A %in% "Experimental"]))
disc_ctl <- length(unique(adae$USUBJID[adae$AEACN == "DRUG WITHDRAWN" & adae$TRT01A %in% "Control"]))

# By SOC and PT
# NOTE: a previous broken `ae_summary` block referenced undefined variables
# (n_exp_total / n_ctl_total) inside mutate() and crashed the script; it was
# also dead code (never used downstream). Removed. The PT- and SOC-level
# tables below are the authoritative aggregations used to build the output.
ae_by_pt <- adae %>%
  group_by(AEBODSYS, AEDECOD, TRT01A) %>%
  summarise(n = n_distinct(USUBJID), .groups = "drop") %>%
  pivot_wider(names_from = TRT01A, values_from = n, values_fill = 0)

# SOC-level aggregation
ae_by_soc <- adae %>%
  group_by(AEBODSYS, TRT01A) %>%
  summarise(n = n_distinct(USUBJID), .groups = "drop") %>%
  pivot_wider(names_from = TRT01A, values_from = n, values_fill = 0)

# --- Build output ---
build_output <- function() {
  # Summary rows
  summary_rows <- list(
    list(
      category = "summary",
      soc = "Any adverse event",
      pt = NA,
      n_experimental = any_exp,
      pct_experimental = round(100 * any_exp / n_exp, 1),
      n_control = any_ctl,
      pct_control = round(100 * any_ctl / n_ctl, 1)
    ),
    list(
      category = "summary",
      soc = "Serious adverse events",
      pt = NA,
      n_experimental = ser_exp,
      pct_experimental = round(100 * ser_exp / n_exp, 1),
      n_control = ser_ctl,
      pct_control = round(100 * ser_ctl / n_ctl, 1)
    ),
    list(
      category = "summary",
      soc = "Adverse events leading to discontinuation",
      pt = NA,
      n_experimental = disc_exp,
      pct_experimental = round(100 * disc_exp / n_exp, 1),
      n_control = disc_ctl,
      pct_control = round(100 * disc_ctl / n_ctl, 1)
    )
  )
  
  # SOC/PT rows sorted by descending frequency
  detail_rows <- list()
  for (soc_name in unique(ae_by_pt$AEBODSYS)) {
    soc_data <- ae_by_soc %>% filter(AEBODSYS == soc_name)
    soc_exp <- if ("Experimental" %in% names(soc_data)) soc_data$Experimental else 0
    soc_ctl <- if ("Control" %in% names(soc_data)) soc_data$Control else 0
    
    detail_rows[[length(detail_rows) + 1]] <- list(
      category = "soc",
      soc = soc_name,
      pt = NA,
      n_experimental = soc_exp,
      pct_experimental = round(100 * soc_exp / n_exp, 1),
      n_control = soc_ctl,
      pct_control = round(100 * soc_ctl / n_ctl, 1)
    )
    
    pt_data <- ae_by_pt %>% filter(AEBODSYS == soc_name) %>% 
      arrange(desc(pmax(if ("Experimental" %in% names(.)) Experimental else 0, 
                        if ("Control" %in% names(.)) Control else 0)))
    
    for (j in seq_len(nrow(pt_data))) {
      pt_exp <- if ("Experimental" %in% names(pt_data)) pt_data$Experimental[j] else 0
      pt_ctl <- if ("Control" %in% names(pt_data)) pt_data$Control[j] else 0
      
      detail_rows[[length(detail_rows) + 1]] <- list(
        category = "pt",
        soc = soc_name,
        pt = pt_data$AEDECOD[j],
        n_experimental = pt_exp,
        pct_experimental = round(100 * pt_exp / n_exp, 1),
        n_control = pt_ctl,
        pct_control = round(100 * pt_ctl / n_ctl, 1)
      )
    }
  }
  
  list(
    test_case_id = "TC-011",
    title = "Adverse Event Summary Table by SOC and PT",
    parameters = list(seed = seed, n_subjects = n_subjects),
    population = list(
      description = "Safety population (SAFFL = 'Y')",
      n_experimental = n_exp,
      n_control = n_ctl
    ),
    summary = summary_rows,
    ae_table = c(summary_rows, detail_rows),
    metadata = list(
      language = "R",
      packages = c("dplyr", "tidyr", "jsonlite")
    )
  )
}

output <- build_output()
write_json(output, output_file, auto_unbox = TRUE, pretty = TRUE)
cat("TC-011 output written to:", output_file, "\n")
