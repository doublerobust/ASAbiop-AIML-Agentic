#!/usr/bin/env Rscript
# TC-024 Ground Truth: Overall Survival (OS) — KM Median
# Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark
#
# OS is defined as the time from randomization to death from any cause.
# Unlike PFS (TC-001), the event is death only (not progression).
# Subjects who are alive at data cutoff are censored.
#
# This tests:
#   1. Correct identification of OS endpoint (death event, not progression)
#   2. KM median estimation with death-only event
#   3. Log-rank test for treatment comparison
#   4. Hazard ratio from Cox PH model
#
# Dependencies: survival (>= 3.5), jsonlite, dplyr
# Usage: Rscript tc-024-os.R --seed 42 --n 200 --output results.json

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
# Generate OS-specific ADTTE data
# ─────────────────────────────────────────────────────
# OS dataset: time from randomization to death (any cause).
# Progression is NOT an event for OS — only death.
# Censoring: alive at data cutoff.

generate_os_adtte <- function(seed = 42, n_subjects = 200, hr = 0.75) {
  set.seed(seed)
  base_rate <- log(2) / 14.0  # median OS control = 14 months (longer than PFS)
  trt <- sample(0:1, n_subjects, replace = TRUE)
  hazard_mult <- ifelse(trt == 0, 1.0, hr)

  # Time to death (exponential)
  death_time <- rexp(n_subjects, rate = base_rate * hazard_mult)

  # Censoring (lost to follow-up, study end)
  cens_time <- rexp(n_subjects, rate = base_rate * 0.2)

  # Observed time
  observed_time <- pmin(death_time, cens_time)
  cnsr <- ifelse(death_time <= cens_time, 0, 1)  # 0 = event (death), 1 = censored

  # Stratification factors
  sex <- sample(c("M", "F"), n_subjects, replace = TRUE, prob = c(0.55, 0.45))
  ecog <- sample(0:1, n_subjects, replace = TRUE, prob = c(0.6, 0.4))
  age <- round(rnorm(n_subjects, mean = 58, sd = 12))
  agegr1 <- ifelse(age < 65, "<65", ">=65")

  data.frame(
    USUBJID = sprintf("SUBJ-%04d", 1:n_subjects),
    STUDYID = "BENCHMARK-001",
    TRT01PN = trt,
    TRT01P = ifelse(trt == 0, "Placebo", "Active"),
    AVAL = round(observed_time, 2),
    CNSR = cnsr,
    PARAMCD = "OS",
    PARAM = "Overall Survival",
    ITTFL = ifelse(runif(n_subjects) < 0.95, "Y", "N"),
    SAFFL = ifelse(runif(n_subjects) < 0.98, "Y", "N"),
    SEX = sex,
    ECOG = ecog,
    AGEGR1 = agegr1,
    stringsAsFactors = FALSE
  )
}

# ─────────────────────────────────────────────────────
# TC-024 Core Computation
# ─────────────────────────────────────────────────────

compute_os_median <- function(adtte, arm = 1, population = "ITT",
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

  # KM fit
  fit <- survfit(Surv(AVAL, 1 - CNSR) ~ 1, data = data, conf.type = conf_type)

  tab <- summary(fit)$table
  median_os <- unname(tab["median"])
  ci_lower   <- unname(tab["0.95LCL"])
  ci_upper   <- unname(tab["0.95UCL"])
  n_events   <- unname(tab["events"])
  n_total    <- unname(tab["records"])

  # Event rate
  event_rate <- round(n_events / n_total, 4)

  # Log-rank test (treatment comparison)
  data_lr <- adtte %>% filter(ITTFL == "Y")
  lr_fit <- survdiff(Surv(AVAL, 1 - CNSR) ~ TRT01PN, data = data_lr)
  lr_chisq <- lr_fit$chisq
  lr_p <- round(1 - pchisq(lr_chisq, df = 1), 6)

  # Cox PH model for HR
  cox_fit <- coxph(Surv(AVAL, 1 - CNSR) ~ TRT01PN, data = data_lr)
  hr <- exp(coef(cox_fit)["TRT01PN"])
  hr_ci_lower <- exp(confint(cox_fit)["TRT01PN", 1])
  hr_ci_upper <- exp(confint(cox_fit)["TRT01PN", 2])

  list(
    median_os = round(median_os, 2),
    median_ci_lower = round(ci_lower, 2),
    median_ci_upper = round(ci_upper, 2),
    n_events = as.integer(n_events),
    n_total = as.integer(n_total),
    event_rate = event_rate,
    logrank_chisq = round(lr_chisq, 4),
    logrank_p = lr_p,
    hazard_ratio = round(hr, 4),
    hr_ci_lower = round(hr_ci_lower, 4),
    hr_ci_upper = round(hr_ci_upper, 4),
    arm = arm,
    population = population
  )
}

# ─────────────────────────────────────────────────────
# ARS Output Envelope (ARS v1.0 compatible)
# ─────────────────────────────────────────────────────

write_ars_output <- function(results, filepath) {
  ars <- list(
    reportingEvent = list(
      id = "TC-024-OS",
      name = "Overall Survival KM Median",
      version = "1.0"
    ),
    analysisResults = list(
      list(
        id = "TC-024-OS-001",
        analysisId = "OS-KM-MEDIAN",
        method = "KaplanMeier",
        purpose = "Estimate median overall survival",
        results = results
      )
    ),
    referencingMetadata = list(
      dataset = "ADTTE",
      paramcd = "OS",
      population = "ITT"
    )
  )
  writeLines(jsonlite::toJSON(ars, auto_unbox = TRUE, pretty = TRUE), filepath)
  cat(sprintf("Wrote ARS output to: %s\n", filepath))
}

# ─────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────

main <- function() {
  args <- parse_args()

  # Get data
  if (!is.na(args$data) && nzchar(args$data)) {
    adtte <- read_shared_data(args$data)
  } else {
    adtte <- generate_os_adtte(seed = args$seed, n_subjects = args$n)
  }

  # Compute for both arms
  results_arm0 <- compute_os_median(adtte, arm = 0, population = "ITT",
                                     conf_type = args$conf_type)
  results_arm1 <- compute_os_median(adtte, arm = 1, population = "ITT",
                                     conf_type = args$conf_type)

  # Subgroup analysis: by SEX, AGEGR1, ECOG
  subgroups <- list()
  for (var in c("SEX", "AGEGR1", "ECOG")) {
    data_itt <- adtte %>% filter(ITTFL == "Y")
    levels <- sort(unique(data_itt[[var]]))
    for (lvl in levels) {
      data_sub <- data_itt %>% filter(!!sym(var) == lvl)
      if (nrow(data_sub) > 0) {
        fit_sub <- survfit(Surv(AVAL, 1 - CNSR) ~ TRT01PN, data = data_sub)
        cox_sub <- tryCatch(
          coxph(Surv(AVAL, 1 - CNSR) ~ TRT01PN, data = data_sub),
          error = function(e) NULL
        )
        tab_sub <- summary(fit_sub)$table
        subgroups[[length(subgroups) + 1]] <- list(
          variable = var,
          level = as.character(lvl),
          median_exp = round(unname(summary(fit_sub)$table["1", "median"]), 2),
          median_ctrl = round(unname(summary(fit_sub)$table["0", "median"]), 2),
          n_exp = as.integer(summary(fit_sub)$table["1", "records"]),
          n_ctrl = as.integer(summary(fit_sub)$table["0", "records"]),
          hr = if (!is.null(cox_sub)) round(exp(coef(cox_sub)["TRT01PN"]), 4) else NA
        )
      }
    }
  }

  # BOR summary (for cross-TFL consistency with TC-020/023)
  data_itt <- adtte %>% filter(ITTFL == "Y")
  bor_dist <- data_itt %>%
    group_by(TRT01PN, CNSR) %>%
    summarise(n = n(), .groups = "drop") %>%
    arrange(TRT01PN, CNSR)

  result <- list(
    test_case_id = "TC-024",
    endpoint = "Overall Survival",
    population = "ITT",
    arm_control = results_arm0,
    arm_experimental = results_arm1,
    subgroups = subgroups,
    censoring_summary = list(
      n_censored = as.integer(sum(data_itt$CNSR)),
      n_events = as.integer(sum(1 - data_itt$CNSR)),
      censoring_rate = round(sum(data_itt$CNSR) / nrow(data_itt), 4)
    ),
    language = "R",
    version = "1.0"
  )

  if (!is.na(args$output) && nzchar(args$output)) {
    write_output(result, args$output)
  } else {
    print_output(result)
  }

  # ARS output
  if (!is.na(args$ars_output) && nzchar(args$ars_output)) {
    write_ars_output(result, args$ars_output)
  }
}

main()
