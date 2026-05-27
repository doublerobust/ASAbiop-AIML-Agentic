#!/usr/bin/env Rscript
# TC-001 Ground Truth: Kaplan-Meier Median PFS Estimation
# Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark
#
# Cross-validated against: SAS PROC LIFETEST, Python lifelines
# Dependencies: survival (>= 3.5), jsonlite, dplyr
# Usage: Rscript tc-001-km-median.R --seed 42 --n 200 --output results.json

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
    n = as.integer(get_arg("--n", "200")),
    arm = as.integer(get_arg("--arm", "1")),
    conf_type = get_arg("--conf-type", "log-log"),
    output = get_arg("--output", NA)
  )
}

# ─────────────────────────────────────────────────────
# TC-001 Core Computation
# ─────────────────────────────────────────────────────

compute_km_median <- function(adtte,
                              arm = 1,
                              population = "ITT",
                              conf_type = "log-log") {

  # Apply population filter
  if (population == "ITT") {
    data <- adtte %>% filter(ITTFL == "Y", TRT01PN == arm)
  } else {
    data <- adtte %>% filter(TRT01PN == arm)
  }

  if (nrow(data) == 0) {
    stop(sprintf("No subjects in arm %d for population %s", arm, population))
  }

  # Time-to-event: AVAL (months), CNSR (0=event, 1=censored)
  fit <- survfit(Surv(AVAL, 1 - CNSR) ~ 1,
                 data = data,
                 conf.type = conf_type)

  # Extract median and 95% CI
  median_pfs <- fit$median
  ci_lower   <- fit$lower
  ci_upper   <- fit$upper
  n_events   <- fit$nevent
  n_total    <- fit$n

  # Handle non-estimable cases
  if (is.na(median_pfs)) {
    result <- list(
      test_case_id = "TC-001",
      variant_id = paste0("v", seed),
      language = "R",
      package = "survival",
      package_version = as.character(packageVersion("survival")),
      median_pfs = NA,
      ci_lower = NA,
      ci_upper = NA,
      n_events = n_events,
      n_total = n_total,
      ci_method = conf_type,
      estimable = FALSE,
      seed = seed
    )
    return(result)
  }

  result <- list(
    test_case_id = "TC-001",
    variant_id = paste0("v", seed),
    language = "R",
    package = "survival",
    package_version = as.character(packageVersion("survival")),
    median_pfs = round(as.numeric(median_pfs), 4),
    ci_lower = round(as.numeric(ci_lower), 4),
    ci_upper = if (is.na(ci_upper)) NA else round(as.numeric(ci_upper), 4),
    n_events = n_events,
    n_total = n_total,
    ci_method = conf_type,
    estimable = TRUE,
    seed = seed
  )

  return(result)
}

# ─────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────

if (sys.nframe() == 0) {  # Only runs when script is executed directly
  opts <- parse_args()
  seed <- opts$seed
  n <- opts$n

  cat(sprintf("TC-001: KM Median PFS (R) — seed=%d, n=%d, arm=%d\n",
              seed, n, opts$arm))

  # Generate synthetic ADTTE
  adtte <- generate_adtte(seed = seed, n_subjects = n, n_arms = 2)

  cat(sprintf("Generated ADTTE with %d subjects\n", nrow(adtte)))

  # Compute KM median
  result <- compute_km_median(adtte,
                               arm = opts$arm,
                               conf_type = opts$conf_type)

  # Print for machine parsing
  cat("\n──────────────────────────────────────────────\n")
  if (result$estimable) {
    cat(sprintf("Median PFS:     %.1f months\n", result$median_pfs))
    cat(sprintf("95%% CI:         (%.1f, %.1f)\n", result$ci_lower, result$ci_upper))
  } else {
    cat("Median PFS:     Not estimable (survival never crosses 0.5)\n")
  }
  cat(sprintf("Events:         %d / %d (%.1f%%)\n",
              result$n_events, result$n_total,
              100 * result$n_events / result$n_total))
  cat(sprintf("CI method:      %s\n", result$ci_method))
  cat(sprintf("R survival v%s\n", result$package_version))
  cat("──────────────────────────────────────────────\n")

  # Structured JSON output
  print_output(result)

  # Write to file if --output specified
  if (!is.na(opts$output)) {
    write_output(result, opts$output)
  }
}
