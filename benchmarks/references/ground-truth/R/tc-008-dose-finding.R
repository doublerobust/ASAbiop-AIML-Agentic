#!/usr/bin/env Rscript
# tc-008-dose-finding.R — TC-008 Ground Truth Analysis
# Level 3: End-to-End Dose-Finding Study Design with Expansion Cohort
#
# Implements a BOIN (Bayesian Optimal Interval) dose-finding design and
# simulates operating characteristics (OCs) over n_sim trials.
#
# Performs:
#   1. Load/compute BOIN design parameters (boundaries, dose levels)
#   2. Simulate n_sim dose-finding trials using BOIN algorithm
#   3. Compute operating characteristics:
#      - P(select each dose as RP2D/MTD)
#      - E[number of DLTs]
#      - E[total sample size]
#      - P(early stop for toxicity)
#   4. Design expansion cohort at selected RP2D
#   5. Output structured JSON with design + simulation results
#
# Usage:
#   Rscript tc-008-dose-finding.R --params <path> --draws <path> [--out <path>]
#   Rscript tc-008-dose-finding.R  # uses default parameters, generates internally
#
# Dependencies: dplyr, jsonlite

library(dplyr)
library(jsonlite)

source("common/data-generation.R")

# ─── Parse args ───
args <- commandArgs(trailingOnly = TRUE)
params_path <- NA
draws_path <- NA
out_path <- NA
seed <- 42
n_sim <- 2000

i <- 1
while (i <= length(args)) {
  if (args[i] == "--params" && i + 1 <= length(args)) { params_path <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--draws" && i + 1 <= length(args)) { draws_path <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--out" && i + 1 <= length(args)) { out_path <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--seed" && i + 1 <= length(args)) { seed <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--n-sim" && i + 1 <= length(args)) { n_sim <- as.integer(args[i + 1]); i <- i + 2 }
  else { i <- i + 1 }
}

# ─── Load or generate design parameters ───
if (!is.na(params_path) && file.exists(params_path)) {
  design <- fromJSON(params_path)
} else {
  # Default design parameters
  target_dlt_rate <- 0.30
  dose_levels <- c(10, 20, 40, 80, 120)
  n_doses <- length(dose_levels)
  true_dlt_rates <- c(0.05, 0.12, 0.25, 0.35, 0.45)
  cohort_size <- 3
  max_n <- 30
  starting_dose <- 1
  expansion_cohort_size <- 6
  escalation_boundary <- round(target_dlt_rate / (1 + target_dlt_rate), 6)
  deescalation_boundary <- round(target_dlt_rate / (1 - target_dlt_rate), 6)

  design <- list(
    method = "BOIN",
    method_full = "Bayesian Optimal Interval",
    target_dlt_rate = target_dlt_rate,
    n_doses = n_doses,
    dose_levels = dose_levels,
    true_dlt_rates = true_dlt_rates,
    cohort_size = cohort_size,
    max_n = max_n,
    starting_dose = starting_dose,
    escalation_boundary = escalation_boundary,
    deescalation_boundary = deescalation_boundary,
    expansion_cohort_size = expansion_cohort_size
  )
}

# ─── Load or generate simulation draws ───
if (!is.na(draws_path) && file.exists(draws_path)) {
  sim_draws <- as.matrix(read_shared_data(draws_path))
} else {
  set.seed(seed)
  sim_draws <- matrix(runif(n_sim * design$max_n), nrow = n_sim, ncol = design$max_n)
  n_sim <- n_sim
}

n_sim <- nrow(sim_draws)

# ─── BOIN single trial simulation ───
simulate_boin_trial <- function(draws_row, design) {
  n_doses <- design$n_doses
  true_rates <- design$true_dlt_rates
  cohort_size <- design$cohort_size
  max_n <- design$max_n
  starting_dose <- design$starting_dose
  lambda_e <- design$escalation_boundary
  lambda_d <- design$deescalation_boundary
  target <- design$target_dlt_rate

  # State
  current_dose <- starting_dose
  n_at_dose <- rep(0, n_doses)
  dlt_at_dose <- rep(0, n_doses)
  total_n <- 0
  total_dlt <- 0
  stopped <- FALSE
  stop_reason <- ""
  draw_idx <- 1  # Position in draws_row

  while (!stopped && total_n < max_n) {
    # Enroll a cohort at current dose
    cohort_n <- min(cohort_size, max_n - total_n)

    for (j in 1:cohort_n) {
      if (draw_idx <= length(draws_row)) {
        u <- draws_row[draw_idx]
      } else {
        u <- runif(1)
      }
      draw_idx <- draw_idx + 1

      # DLT outcome: DLT = 1 if u < true_rate[current_dose]
      dlt <- ifelse(u < true_rates[current_dose], 1, 0)

      n_at_dose[current_dose] <- n_at_dose[current_dose] + 1
      dlt_at_dose[current_dose] <- dlt_at_dose[current_dose] + dlt
      total_n <- total_n + 1
      total_dlt <- total_dlt + dlt
    }

    # Compute observed DLT rate at current dose
    obs_rate <- dlt_at_dose[current_dose] / n_at_dose[current_dose]

    # Decision
    if (obs_rate < lambda_e && current_dose < n_doses) {
      # Escalate
      current_dose <- current_dose + 1
    } else if (obs_rate > lambda_d) {
      if (current_dose > 1) {
        # De-escalate
        current_dose <- current_dose - 1
      } else {
        # At dose 1 and too toxic → stop
        stopped <- TRUE
        stop_reason <- "Dose 1 too toxic"
      }
    }
    # else: stay at current dose
  }

  if (!stopped && total_n >= max_n) {
    stop_reason <- "Max sample size reached"
  }

  # Select MTD/RP2D: dose with observed rate closest to target (among doses with data)
  rpd <- 0
  if (!stopped || stop_reason != "Dose 1 too toxic") {
    best_dist <- Inf
    for (d in 1:n_doses) {
      if (n_at_dose[d] > 0) {
        obs_r <- dlt_at_dose[d] / n_at_dose[d]
        dist <- abs(obs_r - target)
        if (dist < best_dist) {
          best_dist <- dist
          rpd <- d
        }
      }
    }
  }

  list(
    rpd = rpd,
    total_n = total_n,
    total_dlt = total_dlt,
    stopped_early = stopped,
    stop_reason = stop_reason,
    n_at_dose = n_at_dose,
    dlt_at_dose = dlt_at_dose
  )
}

# ─── Run simulations ───
cat(sprintf("Running %d BOIN simulations...\n", n_sim))

rpd_counts <- rep(0, design$n_doses)
rpd_counts[0] <- 0  # R is 1-indexed; rpd=0 means no safe dose
total_n_sum <- 0
total_dlt_sum <- 0
early_stop_count <- 0
rpd_no_safe <- 0

for (sim in 1:n_sim) {
  trial <- simulate_boin_trial(sim_draws[sim, ], design)

  if (trial$rpd > 0) {
    rpd_counts[trial$rpd] <- rpd_counts[trial$rpd] + 1
  } else {
    rpd_no_safe <- rpd_no_safe + 1
  }
  total_n_sum <- total_n_sum + trial$total_n
  total_dlt_sum <- total_dlt_sum + trial$total_dlt
  if (trial$stopped_early) {
    early_stop_count <- early_stop_count + 1
  }
}

# ─── Compute operating characteristics ───
prob_select_rpd <- round(rpd_counts / n_sim, 4)
expected_n <- round(total_n_sum / n_sim, 4)
expected_dlts <- round(total_dlt_sum / n_sim, 4)
prob_early_stop <- round(early_stop_count / n_sim, 4)
prob_no_safe <- round(rpd_no_safe / n_sim, 4)

# ─── Expansion cohort design ───
# RP2D is the most frequently selected dose across simulations
rpd_modal <- which.max(rpd_counts)
rpd_rate <- design$true_dlt_rates[rpd_modal]

expansion <- list(
  rpd = rpd_modal,
  rpd_dose = design$dose_levels[rpd_modal],
  n_expansion = design$expansion_cohort_size,
  expected_dlt_rate_at_rpd = rpd_rate,
  purpose = "Preliminary efficacy and safety assessment at recommended Phase 2 dose"
)

# ─── Assemble output ───
result <- list(
  tc_id = "TC-008",
  tc_title = "End-to-End Dose-Finding Study Design with Expansion Cohort",
  level = 3,
  design = list(
    method = design$method,
    method_full = design$method_full,
    target_dlt_rate = design$target_dlt_rate,
    n_doses = design$n_doses,
    dose_levels = design$dose_levels,
    true_dlt_rates = design$true_dlt_rates,
    cohort_size = design$cohort_size,
    max_n = design$max_n,
    starting_dose = design$starting_dose,
    escalation_boundary = design$escalation_boundary,
    deescalation_boundary = design$deescalation_boundary,
    expansion_cohort_size = design$expansion_cohort_size
  ),
  simulation = list(
    n_sim = n_sim,
    seed = seed,
    operating_characteristics = list(
      prob_select_rpd = as.list(prob_select_rpd),
      prob_no_safe_dose = prob_no_safe,
      expected_n_dlts = expected_dlts,
      expected_sample_size = expected_n,
      prob_early_stop = prob_early_stop
    )
  ),
  expansion_cohort = expansion,
  stopping_rules = list(
    list(id = "SR-1", description = "Stop if dose 1 observed DLT rate exceeds de-escalation boundary (all doses too toxic)"),
    list(id = "SR-2", description = "Stop if total sample size reaches max_n"),
    list(id = "SR-3", description = "Select MTD/RP2D as dose with observed DLT rate closest to target")
  )
)

# ─── Output ───
if (!is.na(out_path) && nzchar(out_path)) {
  write_output(result, out_path)
} else {
  print_output(result)
}
