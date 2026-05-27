#!/usr/bin/env Rscript
# TC-003 Ground Truth: Stratified Log-Rank Test
# Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark
#
# Cross-validated against: SAS PROC LIFETEST STRATA, Python lifelines
# Dependencies: survival (>= 3.5), jsonlite, dplyr
# Usage: Rscript tc-003-stratified-logrank.R --seed 42 --n 400 --output results.json

library(survival)
library(jsonlite)
library(dplyr)

# Source common utilities
source("common/data-generation.R")

# ─────────────────────────────────────────────────────
# Command-line argument parsing
# ─────────────────────────────────────────────────────

parse_args <- function() {
  args <- commandArgs(trailingOnly = TRUE)

  get_arg <- function(flag, default) {
    idx <- which(args == flag)
    if (length(idx) > 0 && idx < length(args)) {
      return(args[idx + 1])
    }
    return(default)
  }

  list(
    seed = as.integer(get_arg("--seed", "42")),
    n = as.integer(get_arg("--n", "400")),
    strata_vars = get_arg("--strata", "SEX,ECOG"),
    output = get_arg("--output", NA)
  )
}

# ─────────────────────────────────────────────────────
# TC-003 Core Computation
# ─────────────────────────────────────────────────────

compute_stratified_logrank <- function(adtte,
                                       strata_vars = c("SEX", "ECOG"),
                                       population = "ITT") {

  # Apply population filter
  if (population == "ITT") {
    data <- adtte %>% filter(ITTFL == "Y")
  } else {
    data <- adtte
  }

  if (nrow(data) == 0) {
    stop("No subjects in the specified population")
  }

  # Check both arms exist
  arms_present <- unique(data$TRT01PN)
  if (length(arms_present) < 2) {
    stop(sprintf("Need 2 arms for comparison; found: %s",
                 paste(arms_present, collapse = ", ")))
  }

  # Build stratum interaction term
  stratum_formula <- paste("strata(", paste(strata_vars, collapse = ", "), ")")

  # Perform stratified log-rank test
  formula_str <- sprintf("Surv(AVAL, 1 - CNSR) ~ TRT01PN + %s", stratum_formula)
  formula_obj <- as.formula(formula_str)

  fit <- survdiff(formula_obj, data = data)

  # Extract results
  chi_square <- fit$chisq
  df <- length(fit$n) - 1  # Usually 1 for two-arm comparison

  # Count non-empty strata
  strata_counts <- fit$n
  n_strata <- length(strata_counts)
  strata_with_events <- sum(strata_counts > 0)

  # p-value (two-sided)
  p_value <- 1 - pchisq(chi_square, df)

  result <- list(
    test_case_id = "TC-003",
    variant_id = paste0("v", seed),
    language = "R",
    package = "survival",
    package_version = as.character(packageVersion("survival")),
    chi_square = round(chi_square, 4),
    df = df,
    p_value = round(p_value, 6),
    n_total = nrow(data),
    n_events = sum(1 - data$CNSR),
    strata_variables = strata_vars,
    n_strata_total = n_strata,
    n_strata_with_events = strata_with_events,
    stratification_method = "equal_weight_per_stratum",
    seed = seed
  )

  return(result)
}

# ─────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────

if (sys.nframe() == 0) {
  opts <- parse_args()
  seed <- opts$seed
  n <- opts$n
  strata_vars <- strsplit(opts$strata_vars, ",")[[1]]

  cat(sprintf("TC-003: Stratified Log-Rank Test (R) — seed=%d, n=%d\n", seed, n))
  cat(sprintf("Strata: %s\n", paste(strata_vars, collapse = ", ")))

  # Generate synthetic ADTTE (2 arms by default)
  adtte <- generate_adtte(seed = seed, n_subjects = n, n_arms = 2, hr = 0.75)
  cat(sprintf("Generated ADTTE with %d subjects\n", nrow(adtte)))

  # Compute stratified log-rank
  result <- compute_stratified_logrank(adtte,
                                        strata_vars = strata_vars)

  # Print result
  cat("\n──────────────────────────────────────────────\n")
  cat("Method: Stratified log-rank test\n")
  cat(sprintf("Stratification: %s\n",
              paste(result$strata_variables, collapse = ", ")))
  cat(sprintf("Chi-square:     %.4f\n", result$chi_square))
  cat(sprintf("DF:             %d\n", result$df))
  cat(sprintf("p-value:        %.6f\n", result$p_value))
  cat(sprintf("Total N:        %d (%d events)\n", result$n_total, result$n_events))
  cat(sprintf("Strata:         %d total, %d with events\n",
              result$n_strata_total, result$n_strata_with_events))
  cat(sprintf("Method:         %s\n", result$stratification_method))
  cat(sprintf("R survival v%s\n", result$package_version))
  cat("──────────────────────────────────────────────\n")

  # Structured JSON output
  print_output(result)

  if (!is.na(opts$output)) {
    write_output(result, opts$output)
  }
}
