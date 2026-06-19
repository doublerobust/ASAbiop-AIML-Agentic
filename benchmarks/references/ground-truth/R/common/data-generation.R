#!/usr/bin/env Rscript
# data-generation.R — Synthetic CDISC-compliant clinical trial data
# Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark
# Common utilities used by all ground truth reference implementations
#
# Dependencies: dplyr, jsonlite (base R rexp/sample used for generation)
# Install: install.packages(c("dplyr", "jsonlite"))
#
# NOTE ON CROSS-LANGUAGE VERIFICATION:
#   R's RNG (Mersenne-Twister via set.seed) and Python's RNG (numpy PCG64)
#   produce DIFFERENT random streams for the same seed. Generating data
#   independently in each language therefore yields DIFFERENT datasets, and
#   the ground-truth statistics CANNOT be expected to match across languages.
#
#   To verify that R/SAS/Python compute the SAME statistic on the SAME data,
#   generate the data once and share it as a CSV (see write_shared_data() and
#   the --data flag in each TC script). Independent generation is retained
#   only for single-language smoke tests, not for cross-language comparison.

library(dplyr)
library(jsonlite)

# ─────────────────────────────────────────────────────
# 1. TC-001 / TC-003: Synthetic ADTTE Dataset
# ─────────────────────────────────────────────────────

#' Generate synthetic ADTTE dataset for survival test cases
#'
#' @param seed Random seed for reproducibility
#' @param n_subjects Total number of subjects (default: 200)
#' @param n_arms Number of treatment arms (1 or 2; default: 2)
#' @param median_pfs_control Median PFS in control arm (months, default: 6)
#' @param hr Hazard ratio for treatment vs. control (default: 0.75)
#' @param censoring_rate Overall censoring rate (default: 0.30)
#' @param p_itt Proportion ITT population (default: 0.95)
#'
#' @return data.frame in ADTTE-like format
generate_adtte <- function(seed = 42,
                           n_subjects = 200,
                           n_arms = 2,
                           median_pfs_control = 6.0,
                           hr = 0.75,
                           censoring_rate = 0.30,
                           p_itt = 0.95) {

  set.seed(seed)

  # Base hazard (exponential, rate = log(2)/median)
  base_rate <- log(2) / median_pfs_control

  # Treatment assignment
  trt <- sample(0:(n_arms - 1), n_subjects, replace = TRUE)

  # Hazard multiplier by arm
  hazard_mult <- ifelse(trt == 0, 1.0, hr)

  # Generate survival times from exponential
  aval <- rexp(n_subjects, rate = base_rate * hazard_mult)

  # Generate independent censoring times
  cens_time <- rexp(n_subjects, rate = base_rate * censoring_rate / (1 - censoring_rate))

  # Observed time = min(event, censoring)
  observed_time <- pmin(aval, cens_time)
  cnsr <- ifelse(aval <= cens_time, 0, 1)  # 0 = event, 1 = censored

  # Stratification factors
  sex <- sample(c("Male", "Female"), n_subjects, replace = TRUE, prob = c(0.5, 0.5))
  ecog <- sample(0:1, n_subjects, replace = TRUE, prob = c(0.6, 0.4))

  # ITT flag (some patients excluded from ITT)
  ittfl <- ifelse(runif(n_subjects) < p_itt, "Y", "N")

  # ECOG must be consistent with ADSL strata levels {0,1}; kept as-is
  # Build ADTTE-like data frame
  data.frame(
    USUBJID = sprintf("SUBJ-%04d", 1:n_subjects),
    STUDYID = "BENCHMARK-001",
    TRT01PN = trt,
    TRT01P = ifelse(trt == 0, "Placebo", "Active"),
    AVAL = round(observed_time, 2),
    CNSR = cnsr,
    PARAMCD = "PFS",
    PARAM = "Progression-Free Survival",
    ITTFL = ittfl,
    SAFFL = ifelse(runif(n_subjects) < 0.98, "Y", "N"),
    SEX = sex,
    ECOG = ecog,
    stringsAsFactors = FALSE
  )
}

# ─────────────────────────────────────────────────────
# 2. TC-002: Synthetic ADSL Dataset
# ─────────────────────────────────────────────────────

#' Generate synthetic ADSL dataset for demographics test cases
#'
#' @param seed Random seed
#' @param n_subjects Number of subjects (default: 400)
#' @param n_arms Number of treatment arms (default: 2)
#'
#' @return data.frame in ADSL-like format
generate_adsl <- function(seed = 42, n_subjects = 400, n_arms = 2) {
  set.seed(seed)

  trt <- sample(0:(n_arms - 1), n_subjects, replace = TRUE)

  age <- round(rnorm(n_subjects, mean = 58, sd = 12))

  data.frame(
    USUBJID = sprintf("SUBJ-%04d", 1:n_subjects),
    STUDYID = "BENCHMARK-001",
    TRT01PN = trt,
    TRT01P = ifelse(trt == 0, "Placebo", "Active"),
    AGE = age,
    # AGEGR1 derived deterministically from AGE (CDISC convention), not random
    AGEGR1 = ifelse(age < 65, "<65", ">=65"),
    SEX = sample(c("M", "F"), n_subjects, replace = TRUE, prob = c(0.55, 0.45)),
    RACE = sample(c("White", "Black", "Asian", "Other"),
                  n_subjects, replace = TRUE,
                  prob = c(0.60, 0.15, 0.20, 0.05)),
    REGION1 = sample(c("North America", "Europe", "Asia", "Rest of World"),
                     n_subjects, replace = TRUE,
                     prob = c(0.35, 0.30, 0.20, 0.15)),
    ECOG = sample(0:2, n_subjects, replace = TRUE, prob = c(0.4, 0.4, 0.2)),
    SAFFL = ifelse(runif(n_subjects) < 0.98, "Y", "N"),
    ITTFL = ifelse(runif(n_subjects) < 0.95, "Y", "N"),
    stringsAsFactors = FALSE
  )
}

# ─────────────────────────────────────────────────────
# 3. Output Helpers — Structured JSON Output
# ─────────────────────────────────────────────────────

#' Write structured output to JSON file
#'
#' @param result Named list with benchmark results
#' @param filepath Path to output JSON file
write_output <- function(result, filepath) {
  output <- jsonlite::toJSON(result, auto_unbox = TRUE, pretty = TRUE)
  writeLines(output, filepath)
  cat(sprintf("Wrote output to: %s\n", filepath))
  invisible(result)
}

#' Print result in structured format for automated parsing
print_output <- function(result) {
  cat("\n=== BENCHMARK OUTPUT ===\n")
  cat(jsonlite::toJSON(result, auto_unbox = TRUE, pretty = TRUE))
  cat("\n=== END OUTPUT ===\n")
}

# ─────────────────────────────────────────────────────
# 4. Shared-Data Helpers (for TRUE cross-language verification)
# ─────────────────────────────────────────────────────

#' Write a generated dataset to CSV so SAS/Python can read the SAME data
write_shared_data <- function(df, filepath) {
  utils::write.csv(df, filepath, row.names = FALSE, na = "")
  cat(sprintf("Wrote shared dataset to: %s\n", filepath))
  invisible(df)
}

#' Read a shared dataset from CSV (preferred path for cross-language runs)
read_shared_data <- function(filepath) {
  utils::read.csv(filepath, stringsAsFactors = FALSE)
}

#' Obtain analysis data: read shared CSV if provided, else generate in-language.
#' Cross-language verification REQUIRES a shared CSV; in-language generation is
#' for single-language smoke tests only.
get_adtte <- function(data_path = NA, seed = 42, n_subjects = 200, ...) {
  if (!is.na(data_path) && nzchar(data_path)) return(read_shared_data(data_path))
  generate_adtte(seed = seed, n_subjects = n_subjects, ...)
}

get_adsl <- function(data_path = NA, seed = 42, n_subjects = 400, ...) {
  if (!is.na(data_path) && nzchar(data_path)) return(read_shared_data(data_path))
  generate_adsl(seed = seed, n_subjects = n_subjects, ...)
}
