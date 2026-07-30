#!/usr/bin/env Rscript
# TC-028 Shared Data Generator: Longitudinal Tumor Size by Cycle
# Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark
#
# Generates the longitudinal tumor size (SLD) dataset used by both
# R and Python ground truth scripts for TC-028, enabling cross-language
# verification on identical input data (cross_language_score = 1.0000).
#
# Usage:
#   Rscript generate_tc028_tumor_long.R --seed 42 --n 150 --output tc028_tumor_long.csv
#
# Output: CSV with columns USUBJID, TRT01A, TRT01PN, BASELINE_SLD,
#         CYCLE, CYCLE_NUM, SLD, PCT_CHANGE (long format, one row per visit).

suppressPackageStartupMessages({
  library(optparse)
})

option_list <- list(
  make_option("--seed", type = "integer", default = 42L),
  make_option("--n", type = "integer", default = 150L),
  make_option("--output", type = "character", default = "tc028_tumor_long.csv")
)
opt <- parse_args(OptionParser(option_list = option_list))

CYCLES <- c("C1D1", "C2D1", "C3D1", "C4D1", "C5D1", "C6D1")
BASELINE_CYCLE <- "C1D1"

set.seed(opt$seed + 200)

rows <- data.frame(
  USUBJID = character(),
  TRT01A = character(),
  TRT01PN = integer(),
  BASELINE_SLD = numeric(),
  CYCLE = character(),
  CYCLE_NUM = integer(),
  SLD = numeric(),
  PCT_CHANGE = numeric(),
  stringsAsFactors = FALSE
)

for (i in 1:opt$n) {
  subj <- sprintf("SUBJ-%04d", i)
  arm <- ifelse(i <= opt$n %/% 2, "Experimental", "Control")
  trt_pn <- ifelse(arm == "Experimental", 1L, 0L)
  baseline_sld <- round(runif(1, 20, 120), 1)

  if (arm == "Experimental") {
    initial_response <- rnorm(1, -25, 15)
    regrowth_rate <- rnorm(1, 5, 3)
    nadir_cycle <- sample(1:4, 1, prob = c(0.17, 0.33, 0.33, 0.17))
  } else {
    initial_response <- rnorm(1, -8, 12)
    regrowth_rate <- rnorm(1, 8, 4)
    nadir_cycle <- sample(1:3, 1, prob = c(0.25, 0.50, 0.25))
  }

  base_dropout <- 0.05

  for (cycle_idx in seq_along(CYCLES)) {
    cycle <- CYCLES[cycle_idx]
    if (cycle == BASELINE_CYCLE) {
      rows <- rbind(rows, data.frame(
        USUBJID = subj, TRT01A = arm, TRT01PN = trt_pn,
        BASELINE_SLD = baseline_sld, CYCLE = cycle, CYCLE_NUM = 0L,
        SLD = baseline_sld, PCT_CHANGE = 0.0,
        stringsAsFactors = FALSE
      ))
      next
    }

    dropout_prob <- base_dropout * (cycle_idx - 1)
    if (runif(1) < dropout_prob) break

    cycle_num <- cycle_idx  # 1, 2, 3, 4, 5
    if (cycle_num <= nadir_cycle) {
      pct <- initial_response * cycle_num
    } else {
      nadir_pct <- initial_response * nadir_cycle
      cycles_since_nadir <- cycle_num - nadir_cycle
      pct <- nadir_pct + regrowth_rate * cycles_since_nadir
    }

    pct <- pct + rnorm(1, 0, 3)
    sld <- max(baseline_sld * (1 + pct / 100), 0)

    rows <- rbind(rows, data.frame(
      USUBJID = subj, TRT01A = arm, TRT01PN = trt_pn,
      BASELINE_SLD = baseline_sld, CYCLE = cycle, CYCLE_NUM = cycle_num,
      SLD = round(sld, 1), PCT_CHANGE = round(pct, 1),
      stringsAsFactors = FALSE
    ))
  }
}

write.csv(rows, opt$output, row.names = FALSE)

cat("Generated TC-028 longitudinal tumor dataset:", nrow(rows), "rows ->", opt$output, "\n")
cat("  Subjects:", opt$n, "\n")
cat("  Experimental:", sum(rows$TRT01A == "Experimental" & rows$CYCLE == "C1D1"), "\n")
cat("  Control:", sum(rows$TRT01A == "Control" & rows$CYCLE == "C1D1"), "\n")