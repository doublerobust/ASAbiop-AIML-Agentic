#!/usr/bin/env Rscript
# TC-027 Ground Truth: Duration of Stable Disease (DOSD) — KM Median
# Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark
#
# DOSD is defined as the time from first documentation of Stable Disease (SD)
# to disease progression or death, among subjects whose Best Overall Response
# is SD. This is a subset analysis on a non-trivial population (typically
# 30-45% of ITT).
#
# Key distinctions from other time-to-event TCs:
#   DOR (TC-022): Responders only (CR+PR), time from response to PD/death
#   DOSD (TC-027): SD subjects only, time from SD documentation to PD/death
#                  DOSD subjects and DOR subjects are disjoint (SD vs CR+PR)
#
# This tests:
#   1. Correct subset identification (BOR = SD only, not CR/PR/PD/NE)
#   2. Time-to-event analysis on a non-trivial subset
#   3. KM estimation with small-to-moderate sample sizes
#   4. Cross-TFL consistency: DOSD N = SD count from TC-025 BOR Summary
#   5. DOSD N <= DCR N (TC-023, since SD is a subset of DCR)
#
# Dependencies: survival (>= 3.5), jsonlite, dplyr
# Usage: Rscript tc-027-dosd.R --seed 42 --n 200 --output results.json

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
# Generate DOSD-specific ADTTE data
# ─────────────────────────────────────────────────────
# DOSD dataset: among subjects with BOR = SD, time from first SD documentation
# to disease progression or death.
#
# Data generation strategy:
# - Generate BOR categories consistent with TC-025 (BOR Summary)
# - For SD subjects: generate time to SD documentation, time from SD to event
# - Non-SD subjects have NA DOSD time

generate_dosd_adtte <- function(seed = 42, n_subjects = 200, hr = 0.80) {
  set.seed(seed)
  base_rate <- log(2) / 4.5  # median DOSD control = 4.5 months
  trt <- sample(0:1, n_subjects, replace = TRUE)
  hazard_mult <- ifelse(trt == 0, 1.0, hr)

  # BOR distribution consistent with TC-025
  # Control: CR 2%, PR 18%, SD 45%, PD 30%, NE 5%
  # Active: CR 8%, PR 35%, SD 35%, PD 15%, NE 7%
  bor <- sapply(trt, function(a) {
    if (a == 0) {
      sample(c("CR", "PR", "SD", "PD", "NE"),
             1, prob = c(0.02, 0.18, 0.45, 0.30, 0.05))
    } else {
      sample(c("CR", "PR", "SD", "PD", "NE"),
             1, prob = c(0.08, 0.35, 0.35, 0.15, 0.07))
    }
  })

  is_sd <- bor == "SD"

  # Time to SD documentation (from randomization): ~1-3 months
  time_to_sd <- ifelse(is_sd,
                        rexp(n_subjects, rate = 1.0 / 1.5),
                        NA)

  # Time from SD documentation to progression or death
  prog_time <- rexp(n_subjects, rate = base_rate * hazard_mult)
  death_time <- rexp(n_subjects, rate = base_rate * 0.3 * hazard_mult)
  cens_time <- rexp(n_subjects, rate = base_rate * 0.3 / 0.7)

  # Event time from randomization = time_to_sd + time from SD to event
  event_from_sd <- pmin(prog_time, death_time)

  # DOSD time = time from SD documentation to event or censoring
  # Only meaningful for SD subjects
  observed_dosd <- numeric(n_subjects)
  dosd_cnsr <- integer(n_subjects)

  for (i in 1:n_subjects) {
    if (!is_sd[i]) {
      observed_dosd[i] <- NA
      dosd_cnsr[i] <- NA
      next
    }

    # Absolute event time from randomization
    event_time_abs <- time_to_sd[i] + event_from_sd[i]

    if (cens_time[i] < event_time_abs && cens_time[i] > time_to_sd[i]) {
      # Censored after SD documentation but before event
      observed_dosd[i] <- cens_time[i] - time_to_sd[i]
      dosd_cnsr[i] <- 1
    } else if (cens_time[i] <= time_to_sd[i]) {
      # Censored before SD documentation — shouldn't happen for SD subjects
      # but handle gracefully: censored at last known time
      observed_dosd[i] <- cens_time[i] - time_to_sd[i]
      if (observed_dosd[i] < 0) observed_dosd[i] <- 0.01
      dosd_cnsr[i] <- 1
    } else {
      # Event observed
      observed_dosd[i] <- event_from_sd[i]
      dosd_cnsr[i] <- 0
    }
  }

  # Stratification factors
  sex <- sample(c("M", "F"), n_subjects, replace = TRUE, prob = c(0.55, 0.45))
  ecog <- sample(0:1, n_subjects, replace = TRUE, prob = c(0.6, 0.4))
  age <- round(rnorm(n_subjects, mean = 58, sd = 12))
  agegr1 <- ifelse(age < 65, "<65", ">=65")

  ittfl <- ifelse(runif(n_subjects) < 0.95, "Y", "N")
  saffl <- ifelse(runif(n_subjects) < 0.98, "Y", "N")

  data.frame(
    USUBJID = sprintf("SUBJ-%04d", 1:n_subjects),
    STUDYID = "BENCHMARK-001",
    TRT01PN = trt,
    TRT01P = ifelse(trt == 0, "Placebo", "Active"),
    AVAL = round(observed_dosd, 2),
    CNSR = dosd_cnsr,
    PARAMCD = "DOSD",
    PARAM = "Duration of Stable Disease",
    ITTFL = ittfl,
    SAFFL = saffl,
    SEX = sex,
    ECOG = ecog,
    AGEGR1 = agegr1,
    BOR = bor,
    IS_SD = as.integer(is_sd),
    TIME_TO_SD = round(time_to_sd, 2),
    stringsAsFactors = FALSE
  )
}

# ─────────────────────────────────────────────────────
# TC-027 Core Computation
# ─────────────────────────────────────────────────────

compute_dosd_median <- function(adtte, arm = 1, population = "ITT",
                                 conf_type = "log-log") {
  if (population == "ITT") {
    data <- adtte %>% filter(ITTFL == "Y", TRT01PN == arm)
  } else {
    data <- adtte %>% filter(TRT01PN == arm)
  }

  n_total_in_arm <- nrow(data)

  # Filter to SD subjects only
  data <- data %>% filter(IS_SD == 1, !is.na(AVAL), AVAL > 0)

  if (nrow(data) == 0) {
    # No SD subjects → DOSD not estimable
    return(list(
      median_dosd = NA,
      median_ci_lower = NA,
      median_ci_upper = NA,
      n_sd = 0L,
      n_events = 0L,
      n_total = as.integer(n_total_in_arm),
      event_rate = NA,
      hazard_ratio = NA,
      hr_ci_lower = NA,
      hr_ci_upper = NA,
      logrank_chisq = NA,
      logrank_p = NA,
      ci_method = conf_type,
      arm = arm,
      population = "ITT with BOR=SD",
      estimable = FALSE
    ))
  }

  # KM estimation for DOSD
  fit <- survfit(Surv(AVAL, 1 - CNSR) ~ 1,
                 data = data,
                 conf.type = conf_type)

  tab <- summary(fit)$table
  median_dosd <- unname(tab["median"])
  ci_lower <- unname(tab["0.95LCL"])
  ci_upper <- unname(tab["0.95UCL"])
  n_events <- unname(tab["events"])
  n_sd <- nrow(data)
  n_total <- unname(tab["records"])

  event_rate <- round(n_events / n_total, 4)

  # Log-rank test (treatment comparison among SD subjects)
  data_lr <- adtte %>% filter(ITTFL == "Y", IS_SD == 1, !is.na(AVAL), AVAL > 0)

  lr_p <- NA
  lr_chisq <- NA
  hr <- NA
  hr_ci_lower <- NA
  hr_ci_upper <- NA

  if (nrow(data_lr) > 0 && length(unique(data_lr$TRT01PN)) > 1) {
    lr_fit <- tryCatch(
      survdiff(Surv(AVAL, 1 - CNSR) ~ TRT01PN, data = data_lr),
      error = function(e) NULL
    )
    if (!is.null(lr_fit)) {
      lr_chisq <- unname(lr_fit$chisq)
      lr_p <- round(1 - pchisq(lr_chisq, df = 1), 6)
    }

    cox_fit <- tryCatch(
      coxph(Surv(AVAL, 1 - CNSR) ~ TRT01PN, data = data_lr),
      error = function(e) NULL
    )
    if (!is.null(cox_fit)) {
      hr <- round(exp(coef(cox_fit)["TRT01PN"]), 4)
      hr_ci <- exp(confint(cox_fit)["TRT01PN", ])
      hr_ci_lower <- round(hr_ci[1], 4)
      hr_ci_upper <- round(hr_ci[2], 4)
    }
  }

  if (length(median_dosd) == 0 || is.na(median_dosd)) {
    return(list(
      median_dosd = NA,
      median_ci_lower = NA,
      median_ci_upper = NA,
      n_sd = as.integer(n_sd),
      n_events = as.integer(n_events),
      n_total = as.integer(n_total),
      event_rate = event_rate,
      hazard_ratio = hr,
      hr_ci_lower = hr_ci_lower,
      hr_ci_upper = hr_ci_upper,
      logrank_chisq = lr_chisq,
      logrank_p = lr_p,
      ci_method = conf_type,
      arm = arm,
      population = "ITT with BOR=SD",
      estimable = FALSE
    ))
  }

  list(
    median_dosd = round(as.numeric(median_dosd), 2),
    median_ci_lower = round(as.numeric(ci_lower), 2),
    median_ci_upper = round(as.numeric(ci_upper), 2),
    n_sd = as.integer(n_sd),
    n_events = as.integer(n_events),
    n_total = as.integer(n_total),
    event_rate = event_rate,
    hazard_ratio = hr,
    hr_ci_lower = hr_ci_lower,
    hr_ci_upper = hr_ci_upper,
    logrank_chisq = if (is.null(lr_chisq)) NA else round(as.numeric(lr_chisq), 4),
    logrank_p = lr_p,
    ci_method = conf_type,
    arm = arm,
    population = "ITT with BOR=SD",
    estimable = TRUE
  )
}

# ─────────────────────────────────────────────────────
# ARS Output Envelope (ARS v1.0 compatible)
# ─────────────────────────────────────────────────────

write_ars_output <- function(results, filepath) {
  ars <- list(
    reportingEvent = list(
      id = "TC-027-DOSD",
      name = "DOSD KM Median",
      version = "1.0"
    ),
    analysisResults = list(
      list(
        id = "TC-027-DOSD-001",
        analysisId = "DOSD-KM-MEDIAN",
        method = "KaplanMeier",
        purpose = "Estimate median duration of stable disease among BOR=SD subjects",
        results = results
      )
    ),
    referencingMetadata = list(
      dataset = "ADTTE",
      paramcd = "DOSD",
      population = "ITT with BOR=SD"
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

  cat(sprintf("TC-027: Duration of Stable Disease KM Median (R) — seed=%d, n=%d\n",
              args$seed, args$n))

  if (!is.na(args$data) && nzchar(args$data)) {
    adtte <- read_shared_data(args$data)
    cat(sprintf("Loaded shared ADTTE with %d subjects\n", nrow(adtte)))
  } else {
    adtte <- generate_dosd_adtte(seed = args$seed, n_subjects = args$n)
    cat(sprintf("Generated DOSD ADTTE with %d subjects\n", nrow(adtte)))
  }

  results_arm0 <- compute_dosd_median(adtte, arm = 0, population = "ITT",
                                       conf_type = args$conf_type)
  results_arm1 <- compute_dosd_median(adtte, arm = 1, population = "ITT",
                                       conf_type = args$conf_type)

  # Subgroup analysis (among SD subjects)
  subgroups <- list()
  data_sd <- adtte %>% filter(ITTFL == "Y", IS_SD == 1, !is.na(AVAL), AVAL > 0)

  for (var in c("SEX", "AGEGR1", "ECOG")) {
    levels <- sort(unique(data_sd[[var]]))
    for (lvl in levels) {
      data_sub <- data_sd %>% filter(!!sym(var) == lvl)
      if (nrow(data_sub) < 5) next

      arm0_sub <- data_sub %>% filter(TRT01PN == 0)
      arm1_sub <- data_sub %>% filter(TRT01PN == 1)

      if (nrow(arm0_sub) == 0 || nrow(arm1_sub) == 0) next

      fit0 <- tryCatch(survfit(Surv(AVAL, 1 - CNSR) ~ 1, data = arm0_sub), error = function(e) NULL)
      fit1 <- tryCatch(survfit(Surv(AVAL, 1 - CNSR) ~ 1, data = arm1_sub), error = function(e) NULL)

      med_exp <- NA
      med_ctrl <- NA
      if (!is.null(fit1)) {
        tab1 <- summary(fit1)$table
        med_exp <- unname(tab1["median"])
        if (!is.na(med_exp)) med_exp <- round(med_exp, 2)
      }
      if (!is.null(fit0)) {
        tab0 <- summary(fit0)$table
        med_ctrl <- unname(tab0["median"])
        if (!is.na(med_ctrl)) med_ctrl <- round(med_ctrl, 2)
      }

      # Cox PH for subgroup HR
      cox_sub <- tryCatch(
        coxph(Surv(AVAL, 1 - CNSR) ~ TRT01PN, data = data_sub),
        error = function(e) NULL
      )
      hr_sub <- if (!is.null(cox_sub)) round(exp(coef(cox_sub)["TRT01PN"]), 4) else NA

      subgroups[[length(subgroups) + 1]] <- list(
        variable = var,
        level = as.character(lvl),
        median_exp = med_exp,
        median_ctrl = med_ctrl,
        n_exp = nrow(arm1_sub),
        n_ctrl = nrow(arm0_sub),
        hr = hr_sub
      )
    }
  }

  # Censoring summary (among SD subjects)
  n_censored <- as.integer(sum(data_sd$CNSR, na.rm = TRUE))
  n_events_sd <- as.integer(sum(1 - data_sd$CNSR, na.rm = TRUE))
  n_sd_total <- nrow(data_sd)

  result <- list(
    test_case_id = "TC-027",
    endpoint = "Duration of Stable Disease",
    population = "ITT with BOR=SD",
    arm_control = results_arm0,
    arm_experimental = results_arm1,
    subgroups = subgroups,
    censoring_summary = list(
      n_censored = n_censored,
      n_events = n_events_sd,
      censoring_rate = if (n_sd_total > 0) round(n_censored / n_sd_total, 4) else NA
    ),
    language = "R",
    version = "1.0"
  )

  cat("\n──────────────────────────────────────────────\n")
  cat(sprintf("Endpoint:       %s\n", result$endpoint))
  cat(sprintf("Population:     %s\n", result$population))
  if (results_arm1$estimable) {
    cat(sprintf("Median DOSD (exp):  %.1f months\n", results_arm1$median_dosd))
    cat(sprintf("Median DOSD (ctrl): %.1f months\n", results_arm0$median_dosd))
  } else {
    cat("Median DOSD:     Not estimable\n")
  }
  cat(sprintf("N SD subjects: %d (ctrl: %d, exp: %d)\n",
              n_sd_total, results_arm0$n_sd, results_arm1$n_sd))
  cat(sprintf("N events:       %d\n", n_events_sd))
  cat("──────────────────────────────────────────────\n")

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
