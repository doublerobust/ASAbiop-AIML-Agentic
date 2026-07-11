#!/usr/bin/env Rscript
#' Generate shared ADEX dataset for TC-033 cross-language verification
#' Outputs: adex.csv with USUBJID, TRT01PN, TRT01A, TREATDUR, PLANDOSE, ACTUALDOSE, RDI, DOSERED, DOSEINT

suppressPackageStartupMessages({
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
seed <- 42
n <- 200
output <- "adex.csv"

i <- 1
while (i <= length(args)) {
  if (args[i] == "--seed") { seed <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--n") { n <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--output") { output <- args[i + 1]; i <- i + 2 }
  else { i <- i + 1 }
}

set.seed(seed)
n_exp <- n %/% 2
n_ctl <- n - n_exp
trt <- rep(c(1, 0), times = c(n_exp, n_ctl))
trt <- sample(trt)

dur <- ifelse(trt == 1,
  round(rnorm(n, mean = 48, sd = 10)),
  round(rnorm(n, mean = 27, sd = 7)))
dur <- pmax(dur, 2)

planned_daily <- ifelse(trt == 1, 12, 6)
planned_cum <- planned_daily * dur * 7

adherence <- ifelse(trt == 1,
  runif(n, min = 0.70, max = 1.0),
  runif(n, min = 0.80, max = 1.0))
actual_cum <- planned_cum * adherence

dose_reduced <- rbinom(n, 1, ifelse(trt == 1, 0.15, 0.08))
dose_interrupt <- rbinom(n, 1, ifelse(trt == 1, 0.10, 0.05))
rdi <- (actual_cum / planned_cum) * 100

df <- data.frame(
  USUBJID = sprintf("SUB%04d", seq_len(n)),
  TRT01PN = trt,
  TRT01A = ifelse(trt == 1, "Experimental", "Control"),
  TREATDUR = dur,
  PLANDOSE = planned_cum,
  ACTUALDOSE = round(actual_cum, 2),
  RDI = round(rdi, 2),
  DOSERED = dose_reduced,
  DOSEINT = dose_interrupt,
  stringsAsFactors = FALSE
)

write.csv(df, output, row.names = FALSE)
cat(sprintf("Written: %s (%d rows)\n", output, nrow(df)))
