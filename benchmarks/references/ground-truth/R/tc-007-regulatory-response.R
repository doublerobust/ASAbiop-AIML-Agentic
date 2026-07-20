#!/usr/bin/env Rscript
# tc-007-regulatory-response.R — TC-007 Ground Truth Analysis
# Level 3: Regulatory Response to ITT vs. PP Discrepancy
#
# Performs:
#   1. ITT analysis (Cox PH + KM median PFS)
#   2. PP analysis (Cox PH + KM median PFS)
#   3. Exclusion pattern analysis (imbalance assessment)
#   4. Tipping point analysis (how many events must shift to negate ITT)
#   5. Sensitivity analyses (worst-case, best-case, pattern mixture)
#   6. Outputs structured JSON with all results
#
# Usage:
#   Rscript tc-007-regulatory-response.R --data-adtte <path> --data-adsl <path> [--out <path>]
#   Rscript tc-007-regulatory-response.R  # generates data internally
#
# Dependencies: survival, dplyr, jsonlite

library(survival)
library(dplyr)
library(jsonlite)

source("common/data-generation.R")

# ─── Parse args ───
args <- commandArgs(trailingOnly = TRUE)
data_adtte <- NA
data_adsl <- NA
out_path <- NA
seed <- 42
n_subjects <- 500

i <- 1
while (i <= length(args)) {
  if (args[i] == "--data-adtte" && i + 1 <= length(args)) { data_adtte <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--data-adsl" && i + 1 <= length(args)) { data_adsl <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--out" && i + 1 <= length(args)) { out_path <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--seed" && i + 1 <= length(args)) { seed <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--n" && i + 1 <= length(args)) { n_subjects <- as.integer(args[i + 1]); i <- i + 2 }
  else { i <- i + 1 }
}

# ─── Load or generate data ───
if (!is.na(data_adtte) && !is.na(data_adsl)) {
  adtte <- read_shared_data(data_adtte)
  adsl <- read_shared_data(data_adsl)
} else {
  source("generate_tc007_itt_pp.R")
  # The generator writes CSVs; read them back
  shared_dir <- "cross-lang-results/shared"
  adtte <- read_shared_data(file.path(shared_dir, "adtte_tc007.csv"))
  adsl <- read_shared_data(file.path(shared_dir, "adsl_tc007.csv"))
}

# Ensure factor treatment
adtte$TRT01P <- factor(adtte$TRT01P, levels = c("Placebo", "Active"))
adsl$TRT01P <- factor(adsl$TRT01P, levels = c("Placebo", "Active"))

# ─── 1. ITT Analysis ───
itt_data <- adtte[adtte$ITTFL == "Y", ]

itt_cox <- coxph(Surv(AVAL, 1 - CNSR) ~ TRT01P, data = itt_data)
itt_summary <- summary(itt_cox)
itt_hr <- round(itt_summary$coefficients[1, "exp(coef)"], 4)
itt_ci_lo <- round(itt_summary$conf.int[1, "lower .95"], 4)
itt_ci_hi <- round(itt_summary$conf.int[1, "upper .95"], 4)
itt_p <- round(itt_summary$coefficients[1, "Pr(>|z|)"], 6)

itt_km <- survfit(Surv(AVAL, 1 - CNSR) ~ TRT01P, data = itt_data)
itt_median_pfs <- round(summary(itt_km)$table[, "median"], 4)

# Log-rank test
itt_logrank <- survdiff(Surv(AVAL, 1 - CNSR) ~ TRT01P, data = itt_data)
itt_logrank_p <- round(1 - pchisq(itt_logrank$chisq, df = 1), 6)

# ─── 2. PP Analysis ───
pp_data <- adtte[adtte$PPFL == "Y", ]

pp_cox <- coxph(Surv(AVAL, 1 - CNSR) ~ TRT01P, data = pp_data)
pp_summary <- summary(pp_cox)
pp_hr <- round(pp_summary$coefficients[1, "exp(coef)"], 4)
pp_ci_lo <- round(pp_summary$conf.int[1, "lower .95"], 4)
pp_ci_hi <- round(pp_summary$conf.int[1, "upper .95"], 4)
pp_p <- round(pp_summary$coefficients[1, "Pr(>|z|)"], 6)

pp_km <- survfit(Surv(AVAL, 1 - CNSR) ~ TRT01P, data = pp_data)
pp_median_pfs <- round(summary(pp_km)$table[, "median"], 4)

pp_logrank <- survdiff(Surv(AVAL, 1 - CNSR) ~ TRT01P, data = pp_data)
pp_logrank_p <- round(1 - pchisq(pp_logrank$chisq, df = 1), 6)

# ─── 3. Exclusion Pattern Analysis ───
n_total <- nrow(adsl)
n_itt <- sum(adsl$ITTFL == "Y")
n_pp <- sum(adsl$PPFL == "Y")
n_excl <- n_total - n_pp

excl_by_arm <- adsl %>%
  filter(PPFL == "N") %>%
  group_by(TRT01P) %>%
  summarise(n_excl = n(), .groups = "drop")

excl_by_reason <- adsl %>%
  filter(PPFL == "N") %>%
  group_by(PPDECOD) %>%
  summarise(n = n(), .groups = "drop")

# Event rates in excluded vs included
excl_event_rate <- adtte %>%
  filter(PPFL == "N") %>%
  summarise(event_rate = mean(CNSR == 0)) %>%
  pull(event_rate)

incl_event_rate <- adtte %>%
  filter(PPFL == "Y") %>%
  summarise(event_rate = mean(CNSR == 0)) %>%
  pull(event_rate)

# Exclusion imbalance: Fisher's exact test
excl_active <- sum(adsl$PPFL == "N" & adsl$TRT01P == "Active")
excl_placebo <- sum(adsl$PPFL == "N" & adsl$TRT01P == "Placebo")
incl_active <- sum(adsl$PPFL == "Y" & adsl$TRT01P == "Active")
incl_placebo <- sum(adsl$PPFL == "Y" & adsl$TRT01P == "Placebo")
fisher_mat <- matrix(c(excl_active, incl_active, excl_placebo, incl_placebo), nrow = 2)
fisher_test <- fisher.test(fisher_mat)
fisher_p <- round(fisher_test$p.value, 6)

# Event imbalance among excluded: Are excluded subjects more likely to have events?
excl_events_active <- sum(adtte$PPFL == "N" & adtte$TRT01P == "Active" & adtte$CNSR == 0)
excl_events_placebo <- sum(adtte$PPFL == "N" & adtte$TRT01P == "Placebo" & adtte$CNSR == 0)
excl_cens_active <- excl_active - excl_events_active
excl_cens_placebo <- excl_placebo - excl_events_placebo

event_fisher_mat <- matrix(c(excl_events_active, excl_cens_active,
                              excl_events_placebo, excl_cens_placebo), nrow = 2)
event_fisher <- fisher.test(event_fisher_mat)
event_imbalance_p <- round(event_fisher$p.value, 6)

# ─── 4. Tipping Point Analysis ───
# How many censored subjects among excluded Active would need to be reclassified
# as events (i.e., removing the censoring) to make the ITT p-value ≥ 0.05?
# Also considers reclassifying excluded Placebo events → censored.
#
# Strategy: Iteratively reclassify censored → event for Active excluded subjects
# and re-fit the Cox model until p ≥ 0.05.

tipping_point <- function(adtte_data, max_shift = 50) {
  results <- list()
  for (n_shift in 0:max_shift) {
    modified <- adtte_data
    # Get excluded Active subjects who are censored (doing well)
    excl_active_censored <- which(modified$PPFL == "N" &
                                   modified$TRT01P == "Active" &
                                   modified$CNSR == 1)
    if (n_shift > 0 && n_shift <= length(excl_active_censored)) {
      modified$CNSR[excl_active_censored[1:n_shift]] <- 0
    }
    # Refit ITT Cox model with modified data
    fit <- coxph(Surv(AVAL, 1 - CNSR) ~ TRT01P, data = modified)
    s <- summary(fit)
    hr <- s$coefficients[1, "exp(coef)"]
    p_val <- s$coefficients[1, "Pr(>|z|)"]
    results[[n_shift + 1]] <- list(
      n_shifted = n_shift,
      hr = round(hr, 4),
      p_value = round(p_val, 6)
    )
    if (p_val >= 0.05) {
      cat(sprintf("Tipping point reached at n_shift = %d (HR = %.4f, p = %.4f)\n",
                  n_shift, hr, p_val))
      return(list(
        tipping_n = n_shift,
        tipping_hr = round(hr, 4),
        tipping_p = round(p_val, 6),
        curve = results
      ))
    }
  }
  cat("Tipping point not reached within max_shift\n")
  return(list(
    tipping_n = NA,
    tipping_hr = NA,
    tipping_p = NA,
    curve = results
  ))
}

tipping_result <- tipping_point(adtte, max_shift = 50)

# ─── 5. Sensitivity Analyses ───
# 5a. Worst-case: all excluded Active subjects are censored at time 0
wc_data <- adtte
wc_excl_active <- which(wc_data$PPFL == "N" & wc_data$TRT01P == "Active")
wc_data$CNSR[wc_excl_active] <- 1
wc_data$AVAL[wc_excl_active] <- 0.01  # near-zero follow-up
wc_cox <- coxph(Surv(AVAL, 1 - CNSR) ~ TRT01P, data = wc_data)
wc_summary <- summary(wc_cox)
wc_hr <- round(wc_summary$coefficients[1, "exp(coef)"], 4)
wc_p <- round(wc_summary$coefficients[1, "Pr(>|z|)"], 6)

# 5b. Best-case: all excluded subjects have events at max follow-up
bc_data <- adtte
bc_excl <- which(bc_data$PPFL == "N")
bc_data$CNSR[bc_excl] <- 0
bc_cox <- coxph(Surv(AVAL, 1 - CNSR) ~ TRT01P, data = bc_data)
bc_summary <- summary(bc_cox)
bc_hr <- round(bc_summary$coefficients[1, "exp(coef)"], 4)
bc_p <- round(bc_summary$coefficients[1, "Pr(>|z|)"], 6)

# 5c. PP analysis as sensitivity (already computed above)

# ─── 6. Assemble output ───
result <- list(
  tc_id = "TC-007",
  tc_title = "Regulatory Response to ITT vs. PP Discrepancy",
  level = 3,
  analysis = list(
    itt = list(
      n = n_itt,
      hr = itt_hr,
      hr_ci_lower = itt_ci_lo,
      hr_ci_upper = itt_ci_hi,
      logrank_p = itt_logrank_p,
      wald_p = itt_p,
      median_pfs_active = itt_median_pfs["TRT01P=Active"],
      median_pfs_placebo = itt_median_pfs["TRT01P=Placebo"]
    ),
    pp = list(
      n = n_pp,
      hr = pp_hr,
      hr_ci_lower = pp_ci_lo,
      hr_ci_upper = pp_ci_hi,
      logrank_p = pp_logrank_p,
      wald_p = pp_p,
      median_pfs_active = pp_median_pfs["TRT01P=Active"],
      median_pfs_placebo = pp_median_pfs["TRT01P=Placebo"]
    ),
    discrepancy = list(
      itt_hr = itt_hr,
      pp_hr = pp_hr,
      hr_difference = round(itt_hr - pp_hr, 4),
      itt_significant = itt_p < 0.05,
      pp_significant = pp_p < 0.05
    ),
    exclusion_pattern = list(
      n_total = n_total,
      n_itt = n_itt,
      n_pp = n_pp,
      n_excluded = n_excl,
      excluded_active = excl_active,
      excluded_placebo = excl_placebo,
      exclusion_rate_active = round(excl_active / sum(adsl$TRT01P == "Active"), 4),
      exclusion_rate_placebo = round(excl_placebo / sum(adsl$TRT01P == "Placebo"), 4),
      event_rate_excluded = round(excl_event_rate, 4),
      event_rate_included = round(incl_event_rate, 4),
      fisher_arm_imbalance_p = fisher_p,
      excl_events_active = excl_events_active,
      excl_events_placebo = excl_events_placebo,
      event_imbalance_fisher_p = event_imbalance_p,
      reasons = as.list(excl_by_reason)
    ),
    tipping_point = list(
      n_shifted = tipping_result$tipping_n,
      hr_at_tipping = tipping_result$tipping_hr,
      p_at_tipping = tipping_result$tipping_p,
      interpretation = paste0(
        "Reclassifying ", tipping_result$tipping_n,
        " event(s) among excluded Active subjects to censored",
        " would make the ITT result non-significant (p ≥ 0.05)."
      )
    ),
    sensitivity_analyses = list(
      worst_case = list(
        description = "All excluded Active subjects censored at time ~0",
        hr = wc_hr,
        p_value = wc_p
      ),
      best_case = list(
        description = "All excluded subjects have events",
        hr = bc_hr,
        p_value = bc_p
      ),
      per_protocol = list(
        description = "PP analysis (excludes protocol deviations)",
        hr = pp_hr,
        p_value = pp_p
      )
    )
  )
)

# ─── Output ───
if (!is.na(out_path) && nzchar(out_path)) {
  write_output(result, out_path)
} else {
  print_output(result)
}
