#!/usr/bin/env Rscript
# TC-021 Ground Truth: Time-to-Progression (TTP) — KM Median
# Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark
#
# Key difference from TC-001 (PFS):
#   PFS: event = disease progression OR death (whichever comes first)
#   TTP: event = disease progression only; death is censored
#
# This tests whether the agent correctly handles censoring rules —
# a common source of programming errors in oncology trials.
#
# Dependencies: survival (>= 3.5), jsonlite, dplyr
# Usage: Rscript tc-021-ttp.R --seed 42 --n 200 --output results.json

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
    if (length(idx) > 0 && idx < length(args)) return(args[idx + 1])
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
# Generate TTP-specific ADTTE data
# ─────────────────────────────────────────────────────
# TTP dataset includes both progression and death events.
# For TTP analysis: event = progression only, death = censored.
# We store EVNTTYPE to distinguish: "PROG" vs "DEATH"

generate_ttp_adtte <- function(seed = 42, n_subjects = 200, hr = 0.75) {
  set.seed(seed)
  base_rate <- log(2) / 6.0  # median PFS control = 6 months
  trt <- sample(0:1, n_subjects, replace = TRUE)
  hazard_mult <- ifelse(trt == 0, 1.0, hr)

  # Generate progression times
  prog_time <- rexp(n_subjects, rate = base_rate * hazard_mult)
  # Generate death times (independent, may occur before or after progression)
  death_time <- rexp(n_subjects, rate = base_rate * 0.3 * hazard_mult)
  # Censoring times
  cens_time <- rexp(n_subjects, rate = base_rate * 0.3 / 0.7)

  # PFS time = min(progression, death, censoring)
  # TTP time = min(progression, censoring) — death is censored

  # For TTP analysis:
  # If progression occurs first → event (CNSR = 0, EVNTTYPE = "PROG")
  # If death occurs before progression → censored at death time (CNSR = 1)
  # If censoring occurs first → censored (CNSR = 1)

  ttp_time <- pmin(prog_time, cens_time)
  ttp_cnsr <- ifelse(prog_time <= cens_time, 0, 1)

  # But if death occurs before progression and before censoring:
  # TTP is censored at death time (not at censoring time)
  death_before_prog <- death_time < prog_time & death_time < cens_time
  ttp_time <- ifelse(death_before_prog, death_time, ttp_time)
  ttp_cnsr <- ifelse(death_before_prog, 1, ttp_cnsr)

  # For reference: PFS event = progression OR death
  pfs_time <- pmin(prog_time, death_time, cens_time)
  pfs_cnsr <- ifelse(prog_time <= cens_time | death_time <= cens_time, 0, 1)
  pfs_cnsr <- ifelse(pfs_time == cens_time & prog_time > cens_time & death_time > cens_time, 1, pfs_cnsr)

  sex <- sample(c("Male", "Female"), n_subjects, replace = TRUE, prob = c(0.5, 0.5))
  ecog <- sample(0:1, n_subjects, replace = TRUE, prob = c(0.6, 0.4))
  ittfl <- ifelse(runif(n_subjects) < 0.95, "Y", "N")

  data.frame(
    USUBJID = sprintf("SUBJ-%04d", 1:n_subjects),
    STUDYID = "BENCHMARK-001",
    TRT01PN = trt,
    TRT01P = ifelse(trt == 0, "Placebo", "Active"),
    AVAL = round(ttp_time, 2),
    CNSR = ttp_cnsr,
    PARAMCD = "TTP",
    PARAM = "Time to Progression",
    ITTFL = ittfl,
    SAFFL = ifelse(runif(n_subjects) < 0.98, "Y", "N"),
    SEX = sex,
    ECOG = ecog,
    # Store PFS equivalents for cross-TFL validation
    PFS_AVAL = round(pfs_time, 2),
    PFS_CNSR = pfs_cnsr,
    stringsAsFactors = FALSE
  )
}

# ─────────────────────────────────────────────────────
# TC-021 Core Computation
# ─────────────────────────────────────────────────────

compute_ttp_median <- function(adtte,
                                arm = 1,
                                population = "ITT",
                                conf_type = "log-log",
                                seed = NA) {

  if (population == "ITT") {
    data <- adtte %>% filter(ITTFL == "Y", TRT01PN == arm)
  } else {
    data <- adtte %>% filter(TRT01PN == arm)
  }

  if (nrow(data) == 0) {
    stop(sprintf("No subjects in arm %d for population %s", arm, population))
  }

  # KM estimation for TTP (death already censored in data)
  fit <- survfit(Surv(AVAL, 1 - CNSR) ~ 1,
                 data = data,
                 conf.type = conf_type)

  tab <- summary(fit)$table
  median_ttp <- unname(tab["median"])
  ci_lower   <- unname(tab["0.95LCL"])
  ci_upper   <- unname(tab["0.95UCL"])
  n_events   <- unname(tab["events"])
  n_total    <- unname(tab["records"])

  variant <- if (is.na(seed)) NA else paste0("v", seed)

  if (length(median_ttp) == 0 || is.na(median_ttp)) {
    result <- list(
      test_case_id = "TC-021",
      variant_id = variant,
      language = "R",
      package = "survival",
      package_version = as.character(packageVersion("survival")),
      median_ttp = NA,
      ci_lower = if (is.na(ci_lower)) NA else round(as.numeric(ci_lower), 4),
      ci_upper = NA,
      n_events = as.integer(n_events),
      n_total = as.integer(n_total),
      ci_method = conf_type,
      endpoint = "TTP",
      censoring_rule = "death censored (progression only)",
      estimable = FALSE,
      seed = seed
    )
    return(result)
  }

  result <- list(
    test_case_id = "TC-021",
    variant_id = variant,
    language = "R",
    package = "survival",
    package_version = as.character(packageVersion("survival")),
    median_ttp = round(as.numeric(median_ttp), 4),
    ci_lower = if (is.na(ci_lower)) NA else round(as.numeric(ci_lower), 4),
    ci_upper = if (is.na(ci_upper)) NA else round(as.numeric(ci_upper), 4),
    n_events = as.integer(n_events),
    n_total = as.integer(n_total),
    ci_method = conf_type,
    endpoint = "TTP",
    censoring_rule = "death censored (progression only)",
    estimable = TRUE,
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

  cat(sprintf("TC-021: Time-to-Progression KM Median (R) — seed=%d, n=%d, arm=%d\n",
              seed, n, opts$arm))

  # Obtain data: shared CSV or generate TTP-specific ADTTE
  if (!is.na(opts$data)) {
    adtte <- read_shared_data(opts$data)
    cat(sprintf("Loaded shared ADTTE with %d subjects\n", nrow(adtte)))
  } else {
    adtte <- generate_ttp_adtte(seed = seed, n_subjects = n)
    cat(sprintf("Generated TTP ADTTE with %d subjects\n", nrow(adtte)))
  }

  result <- compute_ttp_median(adtte,
                                arm = opts$arm,
                                conf_type = opts$conf_type,
                                seed = seed)

  cat("\n──────────────────────────────────────────────\n")
  cat(sprintf("Endpoint:       %s\n", result$endpoint))
  cat(sprintf("Censoring rule: %s\n", result$censoring_rule))
  if (result$estimable) {
    cat(sprintf("Median TTP:     %.1f months\n", result$median_ttp))
    cat(sprintf("95%% CI:         (%.1f, %.1f)\n", result$ci_lower, result$ci_upper))
  } else {
    cat("Median TTP:     Not estimable\n")
  }
  cat(sprintf("N events:      %d / %d\n", result$n_events, result$n_total))
  cat(sprintf("R survival v%s\n", result$package_version))
  cat("──────────────────────────────────────────────\n")

  print_output(result)

  if (!is.na(opts$output)) {
    write_output(result, opts$output)
  }

  # ARS-compatible output envelope (CDISC ARS v1.0)
  if (!is.na(opts$ars_output)) {
    ars_envelope <- list(
      ars_version = "1.0",
      analysisResult = list(
        id = "TC-021",
        version = "1.0",
        analysisReason = "Secondary efficacy endpoint: time to disease progression",
        analysisMethod = list(
          name = "Kaplan-Meier",
          codeTemplate = "survival::survfit(Surv(AVAL, 1-CNSR) ~ 1)",
          parameters = list(
            conf_type = result$ci_method,
            tie_method = "efron",
            censoring_rule = "death censored"
          )
        ),
        analysisVariables = list(
          list(name = "AVAL", dataset = "ADTTE", role = "analysis time"),
          list(name = "CNSR", dataset = "ADTTE", role = "censoring (death = censored)"),
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
        documentation = "KM median TTP estimation; death treated as censoring (progression-only events)",
        analysisResultsData = list(
          statistics = list(
            list(name = "median_ttp", value = result$median_ttp, unit = "months"),
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
