#!/usr/bin/env Rscript
# generate_tc007_itt_pp.R — TC-007 Data Generator
# Level 3: Regulatory Response to ITT vs. PP Discrepancy
#
# Generates ADSL + ADTTE with seeded protocol deviations that create
# a realistic ITT vs. PP discrepancy in PFS analysis.
#
# Usage:
#   Rscript generate_tc007_itt_pp.R [--seed SEED] [--n N] [--out DIR]
#
# Parameters:
#   --seed     Random seed (default: 42)
#   --n        Number of subjects (default: 500)
#   --out      Output directory (default: cross-lang-results/shared)
#   --itt-hr   Target ITT HR (default: 0.72)
#   --pp-hr    Target PP HR (default: 0.84)
#   --pp-excl  Fraction excluded from PP (default: 0.174 ≈ 87/500)
#
# Output:
#   adsl_tc007.csv  — Subject-level dataset with PPFL, exclusion reasons
#   adtte_tc007.csv — Time-to-event dataset (PFS)

source("common/data-generation.R")

# ─── Parse args ───
args <- commandArgs(trailingOnly = TRUE)
seed <- 42
n_subjects <- 500
out_dir <- "cross-lang-results/shared"
itt_hr_target <- 0.72
pp_hr_target <- 0.84
pp_excl_frac <- 0.174

i <- 1
while (i <= length(args)) {
  if (args[i] == "--seed" && i + 1 <= length(args)) { seed <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--n" && i + 1 <= length(args)) { n_subjects <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--out" && i + 1 <= length(args)) { out_dir <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--itt-hr" && i + 1 <= length(args)) { itt_hr_target <- as.numeric(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--pp-hr" && i + 1 <= length(args)) { pp_hr_target <- as.numeric(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--pp-excl" && i + 1 <= length(args)) { pp_excl_frac <- as.numeric(args[i + 1]); i <- i + 2 }
  else { i <- i + 1 }
}

dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

set.seed(seed)

# ─── Treatment assignment (1:1 randomization) ───
trt <- rep(c(0, 1), each = n_subjects / 2)
# Random shuffle to mix arms
perm <- sample(seq_len(n_subjects))
trt <- trt[perm]

trt_label <- ifelse(trt == 0, "Placebo", "Active")

# ─── Survival times (exponential) ───
# Control median PFS = 6 months → base_rate = log(2)/6
base_rate <- log(2) / 6.0

# ITT: HR ≈ 0.72 (Active vs Placebo)
# Generate with HR = 0.72, then the PP exclusion will shift it toward 0.84
true_hr_itt <- itt_hr_target
hazard_active <- base_rate * true_hr_itt
hazard_placebo <- base_rate

aval_itt <- ifelse(
  trt == 0,
  rexp(n_subjects, rate = hazard_placebo),
  rexp(n_subjects, rate = hazard_active)
)

# ─── Censoring (administrative + random) ───
censor_rate <- 0.30
cens_rate <- 0.30
cens_time <- rexp(n_subjects, rate = base_rate * cens_rate / (1 - cens_rate))
observed_time <- pmin(aval_itt, cens_time)
cnsr <- ifelse(aval_itt <= cens_time, 0, 1)

# ─── PP Exclusions ───
# Target: ~17.4% excluded (87/500), balanced across arms
n_excl <- round(n_subjects * pp_excl_frac)

# Exclusion reasons:
#   Major protocol violations: 28/87 ≈ 32%
#   Early discontinuation before first post-baseline: 35/87 ≈ 40%
#   Prohibited medication use: 24/87 ≈ 28%
excl_reasons <- c(
  rep("Major protocol violation", round(n_excl * 0.32)),
  rep("Early discontinuation before first post-baseline assessment", round(n_excl * 0.40)),
  rep("Prohibited medication use", n_excl - round(n_excl * 0.32) - round(n_excl * 0.40))
)

# Assign exclusions: slightly more in Active arm (44 vs 43) to create imbalance
# Select subjects for PP exclusion
excl_indices <- sample(seq_len(n_subjects), n_excl)

# Bias: prefer censored subjects in Active arm and event subjects in Placebo arm
# This creates the ITT/PP discrepancy (PP HR shifts toward null)
# But we mix in some opposite types for realism
excl_in_active <- round(n_excl * 0.51)  # ~44 in Active, ~43 in Placebo
active_indices <- which(trt == 1)
placebo_indices <- which(trt == 0)

# Among active subjects, prefer censored (~70%) but include some events (~30%)
active_with_censor <- active_indices[which(cnsr[active_indices] == 1)]
active_with_events <- active_indices[which(cnsr[active_indices] == 0)]
n_active_censor <- min(round(excl_in_active * 0.70), length(active_with_censor))
n_active_events <- min(excl_in_active - n_active_censor, length(active_with_events))
excl_active <- c(
  sample(active_with_censor, n_active_censor),
  sample(active_with_events, n_active_events)
)

excl_in_placebo <- n_excl - length(excl_active)
# Among placebo subjects, prefer events (~70%) but include some censored (~30%)
placebo_with_events <- placebo_indices[which(cnsr[placebo_indices] == 0)]
placebo_with_censor <- placebo_indices[which(cnsr[placebo_indices] == 1)]
n_placebo_events <- min(round(excl_in_placebo * 0.70), length(placebo_with_events))
n_placebo_censor <- min(excl_in_placebo - n_placebo_events, length(placebo_with_censor))
excl_placebo <- c(
  sample(placebo_with_events, n_placebo_events),
  sample(placebo_with_censor, n_placebo_censor)
)

excl_indices <- c(excl_active, excl_placebo)
# Trim if overshot
excl_indices <- excl_indices[1:min(length(excl_indices), n_excl)]

# Build PP flag
ppfl <- rep("Y", n_subjects)
ppfl[excl_indices] <- "N"

# Assign exclusion reasons
ppdecod <- rep(NA_character_, n_subjects)
reason_assignment <- sample(excl_reasons, length(excl_indices))
for (j in seq_along(excl_indices)) {
  ppdecod[excl_indices[j]] <- reason_assignment[j]
}

# ─── Build ADSL ───
age <- round(rnorm(n_subjects, mean = 58, sd = 12))
sex <- sample(c("M", "F"), n_subjects, replace = TRUE, prob = c(0.55, 0.45))
race <- sample(c("White", "Black", "Asian", "Other"), n_subjects, replace = TRUE,
               prob = c(0.60, 0.15, 0.20, 0.05))
ecog <- sample(0:1, n_subjects, replace = TRUE, prob = c(0.6, 0.4))

adsl <- data.frame(
  USUBJID = sprintf("SUBJ-%04d", 1:n_subjects),
  STUDYID = "BENCHMARK-001",
  TRT01PN = trt,
  TRT01P = trt_label,
  AGE = age,
  AGEGR1 = ifelse(age < 65, "<65", ">=65"),
  SEX = sex,
  RACE = race,
  ECOG = ecog,
  ITTFL = "Y",
  SAFFL = "Y",
  PPFL = ppfl,
  PPDECOD = ppdecod,
  stringsAsFactors = FALSE
)

# ─── Build ADTTE ───
adtte <- data.frame(
  USUBJID = adsl$USUBJID,
  STUDYID = "BENCHMARK-001",
  TRT01PN = trt,
  TRT01P = trt_label,
  AVAL = round(observed_time, 2),
  CNSR = cnsr,
  PARAMCD = "PFS",
  PARAM = "Progression-Free Survival",
  ITTFL = "Y",
  PPFL = ppfl,
  stringsAsFactors = FALSE
)

# ─── Write shared datasets ───
adsl_path <- file.path(out_dir, "adsl_tc007.csv")
adtte_path <- file.path(out_dir, "adtte_tc007.csv")
write_shared_data(adsl, adsl_path)
write_shared_data(adtte, adtte_path)

# ─── Summary ───
cat("\n=== TC-007 Data Generation Summary ===\n")
cat(sprintf("Seed: %d  N: %d\n", seed, n_subjects))
cat(sprintf("ITT population: %d (100%%)\n", n_subjects))
cat(sprintf("PP population: %d (%.1f%%)\n", sum(ppfl == "Y"), 100 * sum(ppfl == "Y") / n_subjects))
cat(sprintf("PP exclusions: %d\n", sum(ppfl == "N")))
cat(sprintf("  Active arm exclusions: %d\n", sum(ppfl == "N" & trt == 1)))
cat(sprintf("  Placebo arm exclusions: %d\n", sum(ppfl == "N" & trt == 0)))
cat(sprintf("  Exclusions with events (cnsr==0): %d\n", sum(ppfl == "N" & cnsr == 0)))
cat(sprintf("  Exclusions censored (cnsr==1): %d\n", sum(ppfl == "N" & cnsr == 1)))
cat("\nExclusion reasons:\n")
print(table(ppdecod, useNA = "ifany"))
cat(sprintf("\nFiles written:\n  %s\n  %s\n", adsl_path, adtte_path))
