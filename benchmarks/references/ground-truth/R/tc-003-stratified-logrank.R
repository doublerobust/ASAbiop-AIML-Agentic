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
    data = get_arg("--data", NA),
    ars_output = get_arg("--ars-output", NA),
    output = get_arg("--output", NA)
  )
}

# ─────────────────────────────────────────────────────
# TC-003 Core Computation
# ─────────────────────────────────────────────────────

compute_stratified_logrank <- function(adtte,
                                       strata_vars = c("SEX", "ECOG"),
                                       population = "ITT",
                                       seed = NA) {

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

  # ---------------------------------------------------------------------
  # Degrees of freedom = (number of comparison GROUPS) - 1.
  # BUGFIX: when strata() is in the formula, fit$n is indexed by the GROUP
  # variable (TRT01PN), so length(fit$n) equals the number of arms, not the
  # number of strata. For a two-arm comparison df = 1. Derive df from the
  # number of distinct treatment groups directly so it is unambiguous.
  # ---------------------------------------------------------------------
  n_groups <- length(unique(data$TRT01PN))
  df <- n_groups - 1

  # ---------------------------------------------------------------------
  # Count strata CORRECTLY from the cross-classification of strata_vars.
  # BUGFIX: the previous code used length(fit$n) (= number of arms) and
  # sum(fit$n > 0) (= arms with subjects) and mislabeled them as strata
  # counts. With SEX(2) x ECOG(2) the true total is 4 strata, not 2.
  # A stratum 'has events' only if it contains >= 1 observed event.
  # ---------------------------------------------------------------------
  strata_key <- interaction(data[strata_vars], drop = TRUE)
  n_strata <- nlevels(strata_key)
  events_per_stratum <- tapply(1 - data$CNSR, strata_key, sum)
  strata_with_events <- sum(events_per_stratum > 0, na.rm = TRUE)

  # p-value (two-sided, chi-square with df)
  p_value <- pchisq(chi_square, df, lower.tail = FALSE)

  variant <- if (is.na(seed)) NA else paste0("v", seed)

  result <- list(
    test_case_id = "TC-003",
    variant_id = variant,
    language = "R",
    package = "survival",
    package_version = as.character(packageVersion("survival")),
    chi_square = round(chi_square, 4),
    df = df,
    p_value = round(p_value, 6),
    n_total = nrow(data),
    n_events = as.integer(sum(1 - data$CNSR)),
    strata_variables = strata_vars,
    n_strata_total = as.integer(n_strata),
    n_strata_with_events = as.integer(strata_with_events),
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

  # Obtain ADTTE: shared CSV (cross-language) or in-language generation (smoke)
  adtte <- get_adtte(data_path = opts$data, seed = seed, n_subjects = n, n_arms = 2, hr = 0.75)
  cat(sprintf("%s ADTTE with %d subjects\n",
              if (!is.na(opts$data)) "Loaded shared" else "Generated", nrow(adtte)))

  # Compute stratified log-rank
  result <- compute_stratified_logrank(adtte,
                                        strata_vars = strata_vars,
                                        seed = seed)

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

  # ─────────────────────────────────────────────────────
  # ARS-compatible output envelope (CDISC ARS v1.0)
  # Phase 3: extends ARS coverage to stratified log-rank test
  # ─────────────────────────────────────────────────────
  if (!is.na(opts$ars_output)) {
    ars_envelope <- list(
      ars_version = "1.0",
      analysisResult = list(
        id = "TC-003",
        version = "1.0",
        analysisReason = "Treatment comparison via stratified log-rank test",
        analysisMethod = list(
          name = "Stratified Log-Rank Test",
          codeTemplate = "survival::survdiff(Surv(AVAL, 1-CNSR) ~ TRT01PN + strata(SEX, ECOG))",
          parameters = list(
            strata_variables = strata_vars,
            tie_method = "exact",
            weight_method = "equal_weight_per_stratum"
          )
        ),
        analysisVariables = list(
          list(name = "AVAL", dataset = "ADTTE", role = "analysis time"),
          list(name = "CNSR", dataset = "ADTTE", role = "censoring"),
          list(name = "TRT01PN", dataset = "ADTTE", role = "treatment"),
          list(name = "SEX", dataset = "ADTTE", role = "stratification"),
          list(name = "ECOG", dataset = "ADTTE", role = "stratification")
        ),
        analysisPopulation = list(
          name = "ITT",
          filter = "ITTFL = 'Y'"
        ),
        analysisDataset = "ADTTE",
        resultGroups = list(
          list(id = "Experimental",
               n = as.integer(sum(adtte$TRT01PN == 1 & adtte$ITTFL == "Y")),
               events = as.integer(sum(adtte$TRT01PN == 1 & adtte$ITTFL == "Y" & adtte$CNSR == 0))),
          list(id = "Control",
               n = as.integer(sum(adtte$TRT01PN == 0 & adtte$ITTFL == "Y")),
               events = as.integer(sum(adtte$TRT01PN == 0 & adtte$ITTFL == "Y" & adtte$CNSR == 0)))
        ),
        documentation = "Stratified log-rank test comparing PFS between arms, stratified by SEX and ECOG",
        analysisResultsData = list(
          statistics = list(
            list(name = "chi_square", value = result$chi_square, unit = "chi-square statistic"),
            list(name = "df", value = result$df, unit = "degrees of freedom"),
            list(name = "p_value", value = result$p_value, unit = "two-sided p-value"),
            list(name = "n_total", value = as.integer(result$n_total)),
            list(name = "n_events", value = as.integer(result$n_events)),
            list(name = "n_strata_total", value = as.integer(result$n_strata_total)),
            list(name = "n_strata_with_events", value = as.integer(result$n_strata_with_events))
          )
        )
      )
    )

    ars_json <- jsonlite::toJSON(ars_envelope, auto_unbox = TRUE, pretty = TRUE)
    writeLines(ars_json, opts$ars_output)
    cat(sprintf("Wrote ARS-compatible output to: %s\n", opts$ars_output))
  }
}
