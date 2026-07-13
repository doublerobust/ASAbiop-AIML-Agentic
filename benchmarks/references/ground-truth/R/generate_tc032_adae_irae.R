#!/usr/bin/env Rscript
#' Generate shared ADAE dataset for TC-032 cross-language verification.
#'
#' Creates a shared ADAE dataset with AEFLAG='IMMUNE' field for immune-related
#' AE classification. Both R and Python scripts read the same CSV to ensure
#' identical inputs for cross-language comparison.
#'
#' Usage:
#'   Rscript generate_tc032_adae_irae.R --seed 42 --n 200 --output ../shared/adae_irae.csv

suppressPackageStartupMessages({
  library(jsonlite)
  library(dplyr)
})

args <- commandArgs(trailingOnly = TRUE)
seed <- 42
n_subjects <- 200
output_file <- "adae_irae.csv"

i <- 1
while (i <= length(args)) {
  if (args[i] == "--seed") { seed <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--n") { n_subjects <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--output") { output_file <- args[i + 1]; i <- i + 2 }
  else { i <- i + 1 }
}

set.seed(seed)

n_arm <- n_subjects %/% 2
subjid <- paste0("SUBJ-", sprintf("%04d", 1:n_subjects))
arms <- rep(c("Experimental", "Control"), each = n_arm)

irae_categories <- list(
  "Endocrine disorders" = list(
    soc = "Endocrine disorders",
    pts = c("Hypothyroidism", "Hyperthyroidism", "Thyroiditis",
            "Adrenal insufficiency", "Hypophysitis", "Type 1 diabetes mellitus",
            "Autoimmune diabetes")
  ),
  "Dermatologic disorders" = list(
    soc = "Skin and subcutaneous tissue disorders",
    pts = c("Rash maculo-papular", "Vitiligo", "Pruritus",
            "Alopecia", "Psoriasis", "Dermatitis bullous",
            "Erythema multiforme")
  ),
  "Hepatic disorders" = list(
    soc = "Hepatobiliary disorders",
    pts = c("Hepatitis", "Autoimmune hepatitis", "Hepatotoxicity",
            "Blood bilirubin increased", "Liver function test abnormal")
  ),
  "Gastrointestinal disorders" = list(
    soc = "Gastrointestinal disorders",
    pts = c("Colitis", "Diarrhoea", "Enterocolitis",
            "Gastritis", "Pancreatitis")
  ),
  "Pulmonary disorders" = list(
    soc = "Respiratory, thoracic and mediastinal disorders",
    pts = c("Pneumonitis", "Interstitial lung disease", "Pleural effusion",
            "Cough", "Dyspnoea")
  ),
  "Other immune-related" = list(
    soc = "Musculoskeletal and connective tissue disorders",
    pts = c("Arthritis", "Myositis", "Nephritis",
            "Autoimmune nephritis", "Anaemia", "Neutropenia",
            "Guillain-Barre syndrome", "Myasthenia gravis",
            "Encephalitis", "Meningitis aseptic")
  )
)

severity_grades <- c(1, 2, 3, 4, 5)
irae_severity_weights <- c(0.35, 0.30, 0.20, 0.10, 0.05)

generate_irae_records <- function(subjids, arm, seed_offset) {
  set.seed(seed + seed_offset)
  records <- list()
  rate_mult <- if (arm == "Experimental") 1.5 else 0.6

  for (cat_name in names(irae_categories)) {
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

          records[[length(records) + 1]] <- data.frame(
            USUBJID = s,
            TRT01A = arm,
            AEBODSYS = cat_info$soc,
            AEDECOD = pt,
            AESEV = as.character(severity),
            AESER = aeser,
            AEACN = aeacn,
            AEFLAG = "IMMUNE",
            ASTDT = ttonset,
            stringsAsFactors = FALSE
          )
        }
      }
    }
  }

  if (length(records) == 0) return(data.frame())
  do.call(rbind, records)
}

# Also generate some non-immune AEs (noise) to test filtering
generate_non_irae_records <- function(subjids, arm, seed_offset) {
  set.seed(seed + seed_offset)
  records <- list()
  rate_mult <- if (arm == "Experimental") 1.2 else 1.0

  noise_pts <- c("Headache", "Back pain", "Insomnia", "Mouth ulceration",
                 "Peripheral neuropathy", "Tinnitus", "Dry eye")

  for (pt in noise_pts) {
    base_rate <- runif(1, 0.02, 0.10)
    adj_rate <- min(base_rate * rate_mult, 0.80)
    n_events <- rbinom(1, length(subjids), adj_rate)
    if (n_events > 0) {
      affected <- sample(subjids, n_events)
      for (s in affected) {
        severity <- sample(severity_grades, 1, prob = c(0.50, 0.30, 0.15, 0.04, 0.01))
        records[[length(records) + 1]] <- data.frame(
          USUBJID = s,
          TRT01A = arm,
          AEBODSYS = "Various",
          AEDECOD = pt,
          AESEV = as.character(severity),
          AESER = if (severity >= 4) "Y" else "N",
          AEACN = "DOSE NOT CHANGED",
          AEFLAG = "NON-IMMUNE",
          ASTDT = sample(1:365, 1),
          stringsAsFactors = FALSE
        )
      }
    }
  }
  if (length(records) == 0) return(data.frame())
  do.call(rbind, records)
}

subj_exp <- subjid[arms == "Experimental"]
subj_ctl <- subjid[arms == "Control"]

adae_irae_exp <- generate_irae_records(subj_exp, "Experimental", 1100)
adae_irae_ctl <- generate_irae_records(subj_ctl, "Control", 1200)
adae_noise_exp <- generate_non_irae_records(subj_exp, "Experimental", 2100)
adae_noise_ctl <- generate_non_irae_records(subj_ctl, "Control", 2200)

adae <- rbind(adae_irae_exp, adae_irae_ctl, adae_noise_exp, adae_noise_ctl)

write.csv(adae, output_file, row.names = FALSE)

cat("Shared ADAE (irAE) dataset written to:", output_file, "\n")
cat("  Total records:", nrow(adae), "\n")
cat("  irAE records:", sum(adae$AEFLAG == "IMMUNE"), "\n")
cat("  Non-irAE records:", sum(adae$AEFLAG == "NON-IMMUNE"), "\n")
cat("  Subjects:", n_subjects, "(Exp =", length(subj_exp), ", Ctrl =", length(subj_ctl), ")\n")
