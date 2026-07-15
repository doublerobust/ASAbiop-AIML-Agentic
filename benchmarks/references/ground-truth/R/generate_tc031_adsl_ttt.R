#!/usr/bin/env Rscript
#' Generate shared ADSL dataset for TC-031 Time-to-First-Treatment cross-language verification
#' Outputs: adsl_ttt.csv with USUBJID, TRT01PN, TRT01A, RANDDT, FIRSTDOSEDT,
#'          TTT_DAYS, TTT_MONTHS, RECEIVED_TX, CNSR_TTT, ITTFL, SAFFL, SEX, AGEGR1, ECOG

suppressPackageStartupMessages({
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
seed <- 42
n <- 200
output <- "adsl_ttt.csv"

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

# Randomization date
rand_date <- as.Date("2023-01-01") + sample(0:365, n, replace = TRUE)

# Time-to-first-treatment (days from randomization to first dose)
# Most subjects receive treatment within 1-7 days of randomization
# But some have delays (10-30 days) and a small fraction never receive treatment
ttt_days <- ifelse(trt == 1,
  round(rnorm(n, mean = 3, sd = 2)),
  round(rnorm(n, mean = 5, sd = 3)))
ttt_days <- pmax(ttt_days, 0)

# Some subjects never receive treatment (~5%)
never_tx_idx <- sample(seq_len(n), size = max(1, round(n * 0.05)))
ttt_days[never_tx_idx] <- NA

# First dose date (NA for those who never received treatment)
first_dose_date <- rand_date + ttt_days
first_dose_date[is.na(ttt_days)] <- NA

# Received treatment flag
received_tx <- as.integer(!is.na(ttt_days))

# Censoring for TTT KM: 1 = event (received treatment), 0 = censored (never treated)
cnsr_ttt <- as.integer(is.na(ttt_days))

# For censored subjects, set TTT to follow-up time (censored at last follow-up)
# Use a reasonable follow-up window for censored subjects
fu_days_censored <- round(rnorm(length(never_tx_idx), mean = 180, sd = 60))
fu_days_censored <- pmax(fu_days_censored, 30)
ttt_days[is.na(ttt_days)] <- fu_days_censored

# TTT in months (for reporting)
ttt_months <- round(ttt_days / 30.4375, 4)

# Stratification factors
sex <- sample(c("M", "F"), n, replace = TRUE)
agegr1 <- sample(c("<65", ">=65"), n, replace = TRUE)
ecog <- sample(c(0, 1), n, replace = TRUE)

# Flags
ittfl <- ifelse(runif(n) < 0.95, "Y", "N")
saffl <- ifelse(runif(n) < 0.98, "Y", "N")

df <- data.frame(
  USUBJID = sprintf("SUB%04d", seq_len(n)),
  TRT01PN = trt,
  TRT01A = ifelse(trt == 1, "Experimental", "Control"),
  RANDDT = rand_date,
  FIRSTDOSEDT = first_dose_date,
  TTT_DAYS = ttt_days,
  TTT_MONTHS = ttt_months,
  RECEIVED_TX = received_tx,
  CNSR_TTT = cnsr_ttt,
  ITTFL = ittfl,
  SAFFL = saffl,
  SEX = sex,
  AGEGR1 = agegr1,
  ECOG = ecog,
  stringsAsFactors = FALSE
)

write.csv(df, output, row.names = FALSE)
cat(sprintf("Generated TC-031 ADSL TTT dataset: %d subjects -> %s\n", n, output))
cat(sprintf("  Received treatment: %d (%.1f%%)\n", sum(received_tx), 100 * sum(received_tx) / n))
cat(sprintf("  Never treated (censored): %d (%.1f%%)\n", sum(cnsr_ttt), 100 * sum(cnsr_ttt) / n))
