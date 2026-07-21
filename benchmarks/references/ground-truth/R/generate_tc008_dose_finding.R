#!/usr/bin/env Rscript
# generate_tc008_dose_finding.R — TC-008 Data/Parameter Generator
# Level 3: End-to-End Dose-Finding Study Design with Expansion Cohort
#
# Generates:
#   1. design_params_tc008.json — deterministic design parameters (shared)
#   2. sim_draws_tc008.csv — pre-generated uniform random draws for simulation
#      (n_sim × max_n matrix) so R and Python produce IDENTICAL simulation
#      results (exact cross-language verification).
#
# Usage:
#   Rscript generate_tc008_dose_finding.R [--seed SEED] [--n-sim N_SIM] [--out DIR]
#
# Parameters:
#   --seed     Random seed (default: 42)
#   --n-sim    Number of simulation trials (default: 2000)
#   --out      Output directory (default: cross-lang-results/shared)
#
# Output:
#   design_params_tc008.json — BOIN design parameters
#   sim_draws_tc008.csv      — Uniform(0,1) draws for simulation reproducibility

source("common/data-generation.R")

# ─── Parse args ───
args <- commandArgs(trailingOnly = TRUE)
seed <- 42
n_sim <- 2000
out_dir <- "cross-lang-results/shared"

i <- 1
while (i <= length(args)) {
  if (args[i] == "--seed" && i + 1 <= length(args)) { seed <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--n-sim" && i + 1 <= length(args)) { n_sim <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--out" && i + 1 <= length(args)) { out_dir <- args[i + 1]; i <- i + 2 }
  else { i <- i + 1 }
}

dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

set.seed(seed)

# ─── BOIN Design Parameters ───
# Target DLT rate (maximum tolerated dose target)
target_dlt_rate <- 0.30

# Dose levels (mg): 5 dose levels for a novel oncology agent
dose_levels <- c(10, 20, 40, 80, 120)
n_doses <- length(dose_levels)

# True (simulation) DLT rates at each dose level
# Dose 3 (40mg, rate=0.25) is the true MTD (closest to target 0.30 from below)
# Dose 4 (80mg, rate=0.35) is slightly above target
true_dlt_rates <- c(0.05, 0.12, 0.25, 0.35, 0.45)

# Cohort and sample size parameters
cohort_size <- 3
max_n <- 30  # Maximum sample size for dose escalation
starting_dose <- 1  # Start at lowest dose level

# Expansion cohort at RP2D
expansion_cohort_size <- 6

# ─── Compute BOIN boundaries ───
# Yuan & Lin (2016): Bayesian Optimal Interval design
# Escalation boundary: lambda_e = phi / (1 + phi)
# De-escalation boundary: lambda_d = phi / (1 - phi)
escalation_boundary <- round(target_dlt_rate / (1 + target_dlt_rate), 6)
deescalation_boundary <- round(target_dlt_rate / (1 - target_dlt_rate), 6)

# ─── Stopping rules ───
stopping_rules <- list(
  list(id = "SR-1", description = "Stop if dose 1 observed DLT rate exceeds de-escalation boundary (all doses too toxic)"),
  list(id = "SR-2", description = "Stop if total sample size reaches max_n (30)"),
  list(id = "SR-3", description = "Select MTD/RP2D as dose with observed DLT rate closest to target")
)

# ─── Assemble design parameters ───
design_params <- list(
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
  expansion_cohort_size = expansion_cohort_size,
  stopping_rules = stopping_rules,
  seed = seed,
  n_sim = n_sim
)

# ─── Generate simulation draws ───
# Matrix of n_sim × max_n uniform random draws
# Each row = one simulated trial, columns = subject DLT draws in enrollment order
sim_draws <- matrix(runif(n_sim * max_n), nrow = n_sim, ncol = max_n)

# ─── Write outputs ───
params_path <- file.path(out_dir, "design_params_tc008.json")
draws_path <- file.path(out_dir, "sim_draws_tc008.csv")

write_output(design_params, params_path)
write_shared_data(as.data.frame(sim_draws), draws_path)

# ─── Summary ───
cat("\n=== TC-008 Design Parameter Generation Summary ===\n")
cat(sprintf("Seed: %d  N_sim: %d\n", seed, n_sim))
cat(sprintf("Method: BOIN (Bayesian Optimal Interval)\n"))
cat(sprintf("Target DLT rate: %.2f\n", target_dlt_rate))
cat(sprintf("Dose levels: %s\n", paste(dose_levels, collapse = ", ")))
cat(sprintf("True DLT rates: %s\n", paste(true_dlt_rates, collapse = ", ")))
cat(sprintf("Escalation boundary (lambda_e): %.6f\n", escalation_boundary))
cat(sprintf("De-escalation boundary (lambda_d): %.6f\n", deescalation_boundary))
cat(sprintf("Cohort size: %d  Max N: %d  Starting dose: %d\n", cohort_size, max_n, starting_dose))
cat(sprintf("Expansion cohort size: %d\n", expansion_cohort_size))
cat(sprintf("\nFiles written:\n  %s\n  %s\n", params_path, draws_path))
