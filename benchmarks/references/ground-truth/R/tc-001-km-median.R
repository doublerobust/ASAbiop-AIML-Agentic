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
    data = get_arg("--data", NA),
    output = get_arg("--output", NA),
    ars_output = get_arg("--ars-output", NA)
  )
}

# ─────────────────────────────────────────────────────
# TC-001 Core Computation
# ─────────────────────────────────────────────────────

compute_km_median <- function(adtte,
                              arm = 1,
                              population = "ITT",
                              conf_type = "log-log",
                              seed = NA) {

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

  # ---------------------------------------------------------------------
  # Extract median and 95% CI CORRECTLY.
  # BUGFIX: fit$median is NOT a reliable scalar on modern survfit objects
  # (it can be length-zero/NULL), and fit$lower / fit$upper are VECTORS of
  # the pointwise CI at every event time — NOT the CI of the median. The
  # quantile-based median and its CI come from summary(fit)$table.
  # ---------------------------------------------------------------------
  tab <- summary(fit)$table
  median_pfs <- unname(tab["median"])
  ci_lower   <- unname(tab["0.95LCL"])
  ci_upper   <- unname(tab["0.95UCL"])
  n_events   <- unname(tab["events"])
  n_total    <- unname(tab["records"])

  variant <- if (is.na(seed)) NA else paste0("v", seed)

  # Handle non-estimable cases (median NA when survival never reaches 0.5)
  if (length(median_pfs) == 0 || is.na(median_pfs)) {
    result <- list(
      test_case_id = "TC-001",
      variant_id = variant,
      language = "R",
      package = "survival",
      package_version = as.character(packageVersion("survival")),
      median_pfs = NA,
      ci_lower = if (is.na(ci_lower)) NA else round(as.numeric(ci_lower), 4),
      ci_upper = NA,
      n_events = as.integer(n_events),
      n_total = as.integer(n_total),
      ci_method = conf_type,
      estimable = FALSE,
      seed = seed
    )
    return(result)
  }

  result <- list(
    test_case_id = "TC-001",
    variant_id = variant,
    language = "R",
    package = "survival",
    package_version = as.character(packageVersion("survival")),
    median_pfs = round(as.numeric(median_pfs), 4),
    ci_lower = if (is.na(ci_lower)) NA else round(as.numeric(ci_lower), 4),
    ci_upper = if (is.na(ci_upper)) NA else round(as.numeric(ci_upper), 4),
    n_events = as.integer(n_events),
    n_total = as.integer(n_total),
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

  # Obtain ADTTE: shared CSV (cross-language) or in-language generation (smoke)
  adtte <- get_adtte(data_path = opts$data, seed = seed, n_subjects = n, n_arms = 2)

  cat(sprintf("%s ADTTE with %d subjects\n",
              if (!is.na(opts$data)) "Loaded shared" else "Generated", nrow(adtte)))

  # Compute KM median
  result <- compute_km_median(adtte,
                               arm = opts$arm,
                               conf_type = opts$conf_type,
                               seed = seed)

  # Print for machine parsing
  cat("\n──────────────────────────────────────────────\n")
  if (result$estimable) {
    cat(sprintf("Median PFS:     %.1f months\n", result$median_pfs))
    ci_lo <- if (is.na(result$ci_lower)) "NE" else sprintf("%.1f", result$ci_lower)
    ci_hi <- if (is.na(result$ci_upper)) "NE" else sprintf("%.1f", result$ci_upper)
    cat(sprintf("95%% CI:         (%s, %s)\n", ci_lo, ci_hi))
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

  # ─────────────────────────────────────────────────────
  # ARS-compatible output envelope (CDISC ARS v1.0)
  # Phase 2 proof-of-concept: wraps benchmark output in ARS structure
  # ─────────────────────────────────────────────────────
  if (!is.na(opts$ars_output)) {
    ars_envelope <- list(
      ars_version = "1.0",
      analysisResult = list(
        id = "TC-001",
        version = "1.0",
        analysisReason = "Primary efficacy endpoint estimation",
        analysisMethod = list(
          name = "Kaplan-Meier",
          codeTemplate = "survival::survfit(Surv(AVAL, 1 - CNSR) ~ 1)",
          parameters = list(
            conf_type = result$ci_method,
            tie_method = "efron"
          )
        ),
        analysisVariables = list(
          list(name = "AVAL", dataset = "ADTTE", role = "analysis time"),
          list(name = "CNSR", dataset = "ADTTE", role = "censoring"),
          list(name = "TRT01A", dataset = "ADSL", role = "treatment")
        ),
        analysisPopulation = list(
          name = "ITT",
          filter = "ITTFL = 'Y'"
        ),
        analysisDataset = "ADTTE",
        resultGroups = list(
          list(id = ifelse(opts$arm == 1, "Experimental", "Control"),
               n = result$n_total,
               events = result$n_events)
        ),
        documentation = "KM median PFS estimation with 95% CI (Brookmeyer-Crowley log-log)",
        analysisResultsData = list(
          statistics = list(
            list(name = "median_pfs", value = result$median_pfs, unit = "months"),
            list(name = "ci_lower", value = result$ci_lower),
            list(name = "ci_upper", value = result$ci_upper),
            list(name = "n_events", value = as.integer(result$n_events)),
            list(name = "n_total", value = as.integer(result$n_total)),
            list(name = "estimable", value = result$estimable)
          )
        )
      )
    )

    ars_json <- jsonlite::toJSON(ars_envelope, auto_unbox = TRUE, pretty = TRUE)
    writeLines(ars_json, opts$ars_output)
    cat(sprintf("Wrote ARS-compatible output to: %s\n", opts$ars_output))
  }
}
