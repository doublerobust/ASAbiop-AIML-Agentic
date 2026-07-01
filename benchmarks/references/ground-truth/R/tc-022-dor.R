#!/usr/bin/env Rscript
# TC-022 Ground Truth: Duration of Response (DOR) — KM Median
# Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark
#
# DOR is defined as the time from first documented response (CR or PR)
# to disease progression or death, among subjects who achieved a response.
#
# Key differences from TC-001 (PFS) and TC-021 (TTP):
#   PFS (TC-001): All subjects, event = progression OR death
#   TTP (TC-021): All subjects, event = progression only (death censored)
#   DOR (TC-022): Responders only, event = progression OR death
#                 Left-truncated: entry time = time to first response
#
# This tests:
#   1. Correct subsetting to responder population (CR + PR)
#   2. KM estimation on a selected subset (not full ITT)
#   3. Handling of left truncation (response occurs after randomization)
#
# Dependencies: survival (>= 3.5), jsonlite, dplyr
# Usage: Rscript tc-022-dor.R --seed 42 --n 200 --output results.json

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
# Generate DOR-specific ADTTE data
# ─────────────────────────────────────────────────────
# DOR dataset: among responders (CR/PR), time from first response to
# progression or death. Includes left truncation (entry = time to response).

generate_dor_adtte <- function(seed = 42, n_subjects = 200, hr = 0.75) {
  set.seed(seed)
  base_rate <- log(2) / 6.0  # median PFS control = 6 months
  trt <- sample(0:1, n_subjects, replace = TRUE)
  hazard_mult <- ifelse(trt == 0, 1.0, hr)

  # Generate time to first response (CR or PR)
  # Response probability depends on treatment
  orr_prob <- ifelse(trt == 1, 0.40, 0.20)
  is_responder <- rbinom(n_subjects, 1, orr_prob)

  # Time to response (among responders): exponential with mean ~2 months
  time_to_response <- ifelse(is_responder == 1,
                              rexp(n_subjects, rate = 1.0 / 2.0),
                              NA)

  # Time to progression or death (from randomization)
  prog_time <- rexp(n_subjects, rate = base_rate * hazard_mult)
  death_time <- rexp(n_subjects, rate = base_rate * 0.3 * hazard_mult)
  cens_time <- rexp(n_subjects, rate = base_rate * 0.3 / 0.7)

  # For responders: DOR = time from response to event (prog/death) or censoring
  # Event time from randomization
  event_time_from_rand <- pmin(prog_time, death_time)
  cens_from_rand <- cens_time

  # DOR time = event_time - time_to_response (if event after response)
  # If event before response → not applicable (shouldn't happen if response occurred)
  # If censoring before event → censored

  # Only responders have valid DOR
  has_event_after_response <- is_responder == 1 & event_time_from_rand > time_to_response
  has_cens_before_event <- is_responder == 1 & cens_from_rand < event_time_from_rand & cens_from_rand > time_to_response

  # DOR duration
  dor_time <- ifelse(has_event_after_response,
                     event_time_from_rand - time_to_response,
                     NA)
  # If censoring occurs before event but after response
  dor_time <- ifelse(has_cens_before_event,
                     cens_from_rand - time_to_response,
                     dor_time)
  # Censoring indicator: 0 = event, 1 = censored
  dor_cnsr <- ifelse(has_event_after_response & !has_cens_before_event, 0, 1)
  dor_cnsr <- ifelse(has_cens_before_event, 1, dor_cnsr)

  # For non-responders: NA
  dor_time <- ifelse(is_responder == 0, NA, dor_time)
  dor_cnsr <- ifelse(is_responder == 0, NA, dor_cnsr)

  # Response type
  is_cr <- ifelse(is_responder == 1, rbinom(n_subjects, 1, 0.3), 0)
  bor <- ifelse(is_cr == 1, "CR",
                ifelse(is_responder == 1, "PR",
                       sample(c("SD", "PD"), n_subjects, replace = TRUE, prob = c(0.4, 0.6))))

  sex <- sample(c("Male", "Female"), n_subjects, replace = TRUE, prob = c(0.5, 0.5))
  ecog <- sample(0:1, n_subjects, replace = TRUE, prob = c(0.6, 0.4))
  ittfl <- ifelse(runif(n_subjects) < 0.95, "Y", "N")

  data.frame(
    USUBJID = sprintf("SUBJ-%04d", 1:n_subjects),
    STUDYID = "BENCHMARK-001",
    TRT01PN = trt,
    TRT01P = ifelse(trt == 0, "Placebo", "Active"),
    AVAL = round(dor_time, 2),
    CNSR = dor_cnsr,
    PARAMCD = "DOR",
    PARAM = "Duration of Response",
    ITTFL = ittfl,
    SAFFL = ifelse(runif(n_subjects) < 0.98, "Y", "N"),
    SEX = sex,
    ECOG = ecog,
    BOR = bor,
    IS_RESPONDER = is_responder,
    TIME_TO_RESPONSE = round(time_to_response, 2),
    stringsAsFactors = FALSE
  )
}

# ─────────────────────────────────────────────────────
# TC-022 Core Computation
# ─────────────────────────────────────────────────────

compute_dor_median <- function(adtte,
                                arm = 1,
                                population = "ITT",
                                conf_type = "log-log",
                                seed = NA) {

  if (population == "ITT") {
    data <- adtte %>% filter(ITTFL == "Y", TRT01PN == arm)
  } else {
    data <- adtte %>% filter(TRT01PN == arm)
  }

  # Filter to responders only
  data <- data %>% filter(IS_RESPONDER == 1, !is.na(AVAL), AVAL > 0)

  if (nrow(data) == 0) {
    # No responders → DOR not estimable
    return(list(
      test_case_id = "TC-022",
      variant_id = if (is.na(seed)) NA else paste0("v", seed),
      language = "R",
      package = "survival",
      package_version = as.character(packageVersion("survival")),
      median_dor = NA,
      ci_lower = NA,
      ci_upper = NA,
      n_responders = 0L,
      n_events = 0L,
      n_total = as.integer(nrow(adtte %>% filter(ITTFL == "Y", TRT01PN == arm))),
      ci_method = conf_type,
      endpoint = "DOR",
      population = "responders (CR+PR)",
      censoring_rule = "event = progression or death",
      estimable = FALSE,
      seed = seed
    ))
  }

  n_total_in_arm <- nrow(adtte %>% filter(ITTFL == "Y", TRT01PN == arm))

  # KM estimation for DOR (no left truncation in this simplified version;
  # DOR time is already computed as time from response to event)
  fit <- survfit(Surv(AVAL, 1 - CNSR) ~ 1,
                 data = data,
                 conf.type = conf_type)

  tab <- summary(fit)$table
  median_dor <- unname(tab["median"])
  ci_lower   <- unname(tab["0.95LCL"])
  ci_upper   <- unname(tab["0.95UCL"])
  n_events   <- unname(tab["events"])
  n_responders <- nrow(data)

  variant <- if (is.na(seed)) NA else paste0("v", seed)

  if (length(median_dor) == 0 || is.na(median_dor)) {
    result <- list(
      test_case_id = "TC-022",
      variant_id = variant,
      language = "R",
      package = "survival",
      package_version = as.character(packageVersion("survival")),
      median_dor = NA,
      ci_lower = NA,
      ci_upper = NA,
      n_responders = as.integer(n_responders),
      n_events = as.integer(n_events),
      n_total = as.integer(n_total_in_arm),
      ci_method = conf_type,
      endpoint = "DOR",
      population = "responders (CR+PR)",
      censoring_rule = "event = progression or death",
      estimable = FALSE,
      seed = seed
    )
    return(result)
  }

  result <- list(
    test_case_id = "TC-022",
    variant_id = variant,
    language = "R",
    package = "survival",
    package_version = as.character(packageVersion("survival")),
    median_dor = round(as.numeric(median_dor), 4),
    ci_lower = if (is.na(ci_lower)) NA else round(as.numeric(ci_lower), 4),
    ci_upper = if (is.na(ci_upper)) NA else round(as.numeric(ci_upper), 4),
    n_responders = as.integer(n_responders),
    n_events = as.integer(n_events),
    n_total = as.integer(n_total_in_arm),
    ci_method = conf_type,
    endpoint = "DOR",
    population = "responders (CR+PR)",
    censoring_rule = "event = progression or death",
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

  cat(sprintf("TC-022: Duration of Response KM Median (R) — seed=%d, n=%d, arm=%d\n",
              seed, n, opts$arm))

  # Obtain data: shared CSV or generate DOR-specific ADTTE
  if (!is.na(opts$data)) {
    adtte <- read_shared_data(opts$data)
    cat(sprintf("Loaded shared ADTTE with %d subjects\n", nrow(adtte)))
  } else {
    adtte <- generate_dor_adtte(seed = seed, n_subjects = n)
    cat(sprintf("Generated DOR ADTTE with %d subjects\n", nrow(adtte)))
  }

  result <- compute_dor_median(adtte,
                                arm = opts$arm,
                                conf_type = opts$conf_type,
                                seed = seed)

  cat("\n──────────────────────────────────────────────\n")
  cat(sprintf("Endpoint:       %s\n", result$endpoint))
  cat(sprintf("Population:     %s\n", result$population))
  cat(sprintf("Censoring rule: %s\n", result$censoring_rule))
  if (result$estimable) {
    cat(sprintf("Median DOR:     %.1f months\n", result$median_dor))
    cat(sprintf("95%% CI:         (%.1f, %.1f)\n", result$ci_lower, result$ci_upper))
  } else {
    cat("Median DOR:     Not estimable\n")
  }
  cat(sprintf("N responders:  %d / %d\n", result$n_responders, result$n_total))
  cat(sprintf("N events:      %d\n", result$n_events))
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
        id = "TC-022",
        version = "1.0",
        analysisReason = "Secondary efficacy endpoint: duration of response among responders",
        analysisMethod = list(
          name = "Kaplan-Meier",
          codeTemplate = "survival::survfit(Surv(AVAL, 1-CNSR) ~ 1)",
          parameters = list(
            conf_type = result$ci_method,
            tie_method = "efron",
            population = "responders (CR+PR)",
            event_definition = "progression or death"
          )
        ),
        analysisVariables = list(
          list(name = "AVAL", dataset = "ADTTE", role = "analysis time (from response)"),
          list(name = "CNSR", dataset = "ADTTE", role = "censoring"),
          list(name = "BOR", dataset = "ADRS", role = "best overall response"),
          list(name = "TRT01A", dataset = "ADSL", role = "treatment")
        ),
        analysisPopulation = list(
          name = "Responders",
          filter = "IS_RESPONDER = 1 AND ITTFL = 'Y'"
        ),
        analysisDataset = "ADTTE",
        resultGroups = list(
          list(id = ifelse(opts$arm == 1, "Experimental", "Control"),
               n = result$n_responders,
               events = result$n_events)
        ),
        documentation = "KM median DOR estimation among responders (CR+PR); event = progression or death",
        analysisResultsData = list(
          statistics = list(
            list(name = "median_dor", value = result$median_dor, unit = "months"),
            list(name = "ci_lower", value = result$ci_lower),
            list(name = "ci_upper", value = result$ci_upper),
            list(name = "n_responders", value = as.integer(result$n_responders)),
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
