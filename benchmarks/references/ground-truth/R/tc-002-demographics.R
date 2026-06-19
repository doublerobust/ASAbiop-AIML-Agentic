#!/usr/bin/env Rscript
# TC-002 Ground Truth: Baseline Demographics Table
# Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark
#
# Cross-validated against: SAS PROC FREQ + PROC MEANS, Python pandas + gtsummary
# Dependencies: dplyr, jsonlite, Tplyr (or tableone)
# Usage: Rscript tc-002-demographics.R --seed 42 --n 400 --output results.json

library(dplyr)
library(jsonlite)

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
    data = get_arg("--data", NA),
    output = get_arg("--output", NA)
  )
}

# ─────────────────────────────────────────────────────
# TC-002 Core Computation
# ─────────────────────────────────────────────────────

compute_demographics <- function(adsl, population = "SAFETY", seed = NA) {

  # Apply population filter
  if (population == "SAFETY") {
    data <- adsl %>% filter(SAFFL == "Y")
  } else if (population == "ITT") {
    data <- adsl %>% filter(ITTFL == "Y")
  } else {
    data <- adsl
  }

  if (nrow(data) == 0) {
    stop("No subjects in the specified population")
  }

  n_total <- nrow(data)

  # ── Continuous: AGE ──
  age_stats <- data %>%
    group_by(TRT01PN, TRT01P) %>%
    summarise(
      n = n(),
      mean = mean(AGE, na.rm = TRUE),
      sd = sd(AGE, na.rm = TRUE),
      median = median(AGE, na.rm = TRUE),
      min = min(AGE, na.rm = TRUE),
      max = max(AGE, na.rm = TRUE),
      .groups = "drop"
    )

  # ── Categorical: SEX, RACE, REGION1, ECOG ──
  compute_freq <- function(data, var, var_name) {
    data %>%
      group_by(TRT01PN, TRT01P, !!sym(var)) %>%
      summarise(n = n(), .groups = "drop") %>%
      group_by(TRT01PN, TRT01P) %>%
      mutate(pct = round(100 * n / sum(n), 1)) %>%
      ungroup() %>%
      mutate(variable = var_name) %>%
      rename(level = !!sym(var)) %>%
      # BUGFIX: coerce level to character so bind_rows() can combine numeric
      # (ECOG) and character (SEX/RACE/REGION) categorical levels without a
      # vctrs type error. This previously crashed TC-002 in R entirely.
      mutate(level = as.character(level))
  }

  sex_tbl   <- compute_freq(data, "SEX", "Sex")
  race_tbl  <- compute_freq(data, "RACE", "Race")
  region_tbl <- compute_freq(data, "REGION1", "Region")
  ecog_tbl  <- compute_freq(data, "ECOG", "ECOG")

  cat_tbl <- bind_rows(sex_tbl, race_tbl, region_tbl, ecog_tbl)

  # ── Overall totals ──
  total_age <- data %>%
    summarise(
      n = n(),
      mean = mean(AGE, na.rm = TRUE),
      sd = sd(AGE, na.rm = TRUE),
      median = median(AGE, na.rm = TRUE),
      min = min(AGE, na.rm = TRUE),
      max = max(AGE, na.rm = TRUE)
    )

  # ── Build result ──
  result <- list(
    test_case_id = "TC-002",
    variant_id = if (is.na(seed)) NA else paste0("v", seed),
    language = "R",
    package = "dplyr",
    package_version = as.character(packageVersion("dplyr")),
    population = population,
    n_total = n_total,
    age_by_arm = as.data.frame(age_stats) %>%
      mutate(across(where(is.numeric), ~ round(., 2))),
    categorical_by_arm = as.data.frame(cat_tbl) %>%
      mutate(across(where(is.numeric), ~ round(., 2))),
    total_age = as.data.frame(total_age) %>%
      mutate(across(where(is.numeric), ~ round(., 2))),
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

  cat(sprintf("TC-002: Baseline Demographics (R) — seed=%d, n=%d\n", seed, n))

  # Obtain ADSL: shared CSV (cross-language) or in-language generation (smoke)
  adsl <- get_adsl(data_path = opts$data, seed = seed, n_subjects = n, n_arms = 2)
  cat(sprintf("%s ADSL with %d subjects\n",
              if (!is.na(opts$data)) "Loaded shared" else "Generated", nrow(adsl)))

  # Compute demographics
  result <- compute_demographics(adsl, population = "SAFETY", seed = seed)

  # Print summary
  cat("\n──────────────────────────────────────────────\n")
  cat(sprintf("Population: %s (N=%d)\n", result$population, result$n_total))

  cat("\n— Age by Arm —\n")
  print(result$age_by_arm)

  cat("\n— Sex by Arm —\n")
  print(result$categorical_by_arm %>% filter(variable == "Sex"))

  cat("\n— Race by Arm —\n")
  print(result$categorical_by_arm %>% filter(variable == "Race"))

  cat("\n— Region by Arm —\n")
  print(result$categorical_by_arm %>% filter(variable == "Region"))

  cat("\n— ECOG by Arm —\n")
  print(result$categorical_by_arm %>% filter(variable == "ECOG"))

  cat("──────────────────────────────────────────────\n")

  # Structured JSON output
  print_output(result)

  if (!is.na(opts$output)) {
    write_output(result, opts$output)
  }
}
