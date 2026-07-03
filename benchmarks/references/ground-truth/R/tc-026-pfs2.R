#!/usr/bin/env Rscript
# TC-026 Ground Truth: Time to Second Progression (PFS2) — KM Median
# Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark
#
# PFS2 is defined as the time from randomization to the second disease
# progression or death, whichever comes first. Unlike PFS (TC-001) which
# captures time to first progression/death, PFS2 captures the total
# duration of disease control including post-progression benefit.
#
# This tests:
#   1. Correct identification of PFS2 endpoint (second progression, not first)
#   2. Handling of subjects without first progression (cannot have PFS2 event)
#   3. KM median estimation with complex censoring
#   4. Log-rank test and Cox PH HR
#   5. Subgroup analysis (SEX, AGEGR1, ECOG)
#
# Dependencies: survival (>= 3.5), jsonlite, dplyr
# Usage: Rscript tc-026-pfs2.R --seed 42 --n 200 --output results.json

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
# Generate PFS2-specific ADTTE data
# ─────────────────────────────────────────────────────
# PFS2 dataset: time from randomization to second progression or death.
# Subjects who do not have a first progression cannot have a PFS2 event.
# PFS2 time >= PFS time for all subjects (by construction).

generate_pfs2_adtte <- function(seed = 42, n_subjects = 200, hr = 0.65) {
  set.seed(seed)
  base_rate <- log(2) / 9.0  # median PFS2 control = 9 months (longer than PFS)
  trt <- sample(0:1, n_subjects, replace = TRUE)
  hazard_mult <- ifelse(trt == 0, 1.0, hr)

  # Time to first progression
  prog1_time <- rexp(n_subjects, rate = base_rate * 1.5 * hazard_mult)

  # Time to second progression (only for those who had first progression)
  # Additional time from first to second progression
  prog2_gap <- rexp(n_subjects, rate = base_rate * 0.8 * hazard_mult)

  # Time to death
  death_time <- rexp(n_subjects, rate = base_rate * 0.4 * hazard_mult)

  # PFS2 event time: second progression or death, whichever comes first
  # Subject must have first progression to be eligible for second progression
  prog2_time <- prog1_time + prog2_gap  # absolute time of second progression

  # PFS2 observed time: min(prog2_time, death_time) for those with first progression
  # For those without first progression (censored before first), PFS2 is censored
  cens_time <- rexp(n_subjects, rate = base_rate * 0.15)

  # Determine observed time and event
  observed_time <- numeric(n_subjects)
  cnsr <- integer(n_subjects)

  for (i in 1:n_subjects) {
    if (prog1_time[i] > cens_time[i]) {
      # No first progression observed (censored before first progression)
      observed_time[i] <- cens_time[i]
      cnsr[i] <- 1  # censored
    } else {
      # First progression observed; now check second progression vs death vs censoring
      t2 <- min(prog2_time[i], death_time[i])
      if (t2 <= cens_time[i]) {
        observed_time[i] <- t2
        cnsr[i] <- 0  # event (second progression or death)
      } else {
        observed_time[i] <- cens_time[i]
        cnsr[i] <- 1  # censored
      }
    }
  }

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
    PARAMCD = "PFS2",
    PARAM = "Progression-Free Survival 2",
    ITTFL = ifelse(runif(n_subjects) < 0.95, "Y", "N"),
    SAFFL = ifelse(runif(n_subjects) < 0.98, "Y", "N"),
    SEX = sex,
    ECOG = ecog,
    AGEGR1 = agegr1,
    stringsAsFactors = FALSE
  )
}

# ─────────────────────────────────────────────────────
# TC-026 Core Computation
# ─────────────────────────────────────────────────────

compute_pfs2_median <- function(adtte, arm = 1, population = "ITT",
                                 conf_type = "log-log") {
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
  median_pfs2 <- unname(tab["median"])
  ci_lower <- unname(tab["0.95LCL"])
  ci_upper <- unname(tab["0.95UCL"])
  n_events <- unname(tab["events"])
  n_total <- unname(tab["records"])

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
    median_pfs2 = round(median_pfs2, 2),
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
      id = "TC-026-PFS2",
      name = "PFS2 KM Median",
      version = "1.0"
    ),
    analysisResults = list(
      list(
        id = "TC-026-PFS2-001",
        analysisId = "PFS2-KM-MEDIAN",
        method = "KaplanMeier",
        purpose = "Estimate median progression-free survival 2",
        results = results
      )
    ),
    referencingMetadata = list(
      dataset = "ADTTE",
      paramcd = "PFS2",
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

  if (!is.na(args$data) && nzchar(args$data)) {
    adtte <- read_shared_data(args$data)
  } else {
    adtte <- generate_pfs2_adtte(seed = args$seed, n_subjects = args$n)
  }

  results_arm0 <- compute_pfs2_median(adtte, arm = 0, population = "ITT",
                                       conf_type = args$conf_type)
  results_arm1 <- compute_pfs2_median(adtte, arm = 1, population = "ITT",
                                       conf_type = args$conf_type)

  # Subgroup analysis
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
        row_names <- rownames(tab_sub)
        exp_row <- grep("=1$", row_names, value = TRUE)[1]
        ctrl_row <- grep("=0$", row_names, value = TRUE)[1]
        subgroups[[length(subgroups) + 1]] <- list(
          variable = var,
          level = as.character(lvl),
          median_exp = if (!is.na(exp_row)) round(unname(tab_sub[exp_row, "median"]), 2) else NA,
          median_ctrl = if (!is.na(ctrl_row)) round(unname(tab_sub[ctrl_row, "median"]), 2) else NA,
          n_exp = if (!is.na(exp_row)) as.integer(tab_sub[exp_row, "records"]) else NA,
          n_ctrl = if (!is.na(ctrl_row)) as.integer(tab_sub[ctrl_row, "records"]) else NA,
          hr = if (!is.null(cox_sub)) round(exp(coef(cox_sub)["TRT01PN"]), 4) else NA
        )
      }
    }
  }

  data_itt <- adtte %>% filter(ITTFL == "Y")

  result <- list(
    test_case_id = "TC-026",
    endpoint = "Progression-Free Survival 2",
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

  if (!is.na(args$ars_output) && nzchar(args$ars_output)) {
    write_ars_output(result, args$ars_output)
  }
}

main()
