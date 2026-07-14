#!/usr/bin/env Rscript
#' Generate shared ADSL follow-up dataset for TC-034 cross-language verification
#' Outputs: adsl_fu.csv with USUBJID, TRT01PN, TRT01A, RANDDT, LASTDOSEDT, LASTFUDT,
#'          TREATDUR_W, FU_POST_DOSE, FU_FROM_RAND, ADEQUATE_FU, STATUS, STATUS_LABEL

suppressPackageStartupMessages({
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
seed <- 42
n <- 200
output <- "adsl_fu.csv"
threshold <- 90

i <- 1
while (i <= length(args)) {
  if (args[i] == "--seed") { seed <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--n") { n <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--output") { output <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--threshold") { threshold <- as.integer(args[i + 1]); i <- i + 2 }
  else { i <- i + 1 }
}

set.seed(seed)
n_exp <- n %/% 2
n_ctl <- n - n_exp
trt <- rep(c(1, 0), times = c(n_exp, n_ctl))
trt <- sample(trt)

# Randomization date
rand_date <- as.Date("2023-01-01") + sample(0:365, n, replace = TRUE)

# Treatment duration (weeks)
treat_dur_weeks <- ifelse(trt == 1,
  round(rnorm(n, mean = 42, sd = 10)),
  round(rnorm(n, mean = 24, sd = 7)))
treat_dur_weeks <- pmax(treat_dur_weeks, 2)

# Last dose date
last_dose_date <- rand_date + treat_dur_weeks * 7

# Follow-up post last dose (days)
fu_post_dose <- ifelse(trt == 1,
  round(rnorm(n, mean = 120, sd = 40)),
  round(rnorm(n, mean = 100, sd = 35)))
fu_post_dose <- pmax(fu_post_dose, 0)

# Subject status: 1=Ongoing, 2=Completed, 3=Discontinued, 4=Died
status_prob <- matrix(c(
  0.20, 0.55, 0.15, 0.10,
  0.15, 0.65, 0.12, 0.08
), nrow = 2, byrow = TRUE)

status <- integer(n)
for (j in 1:n) {
  status[j] <- sample(1:4, 1, prob = status_prob[trt[j] + 1, ])
}

# Cap follow-up for died subjects
died_idx <- which(status == 4)
if (length(died_idx) > 0) {
  fu_post_dose[died_idx] <- pmax(round(rnorm(length(died_idx), mean = 45, sd = 20)), 0)
}

# Last follow-up date
last_fu_date <- last_dose_date + fu_post_dose

# Follow-up from randomization
fu_from_rand <- as.numeric(last_fu_date - rand_date)

# Adequate follow-up
adequate <- as.integer(fu_post_dose >= threshold & status != 4)

# Status labels
status_labels <- c("ONGOING", "COMPLETED", "DISCONTINUED", "DIED")[status]

df <- data.frame(
  USUBJID = sprintf("SUB%04d", seq_len(n)),
  TRT01PN = trt,
  TRT01A = ifelse(trt == 1, "Experimental", "Control"),
  RANDDT = as.character(rand_date),
  LASTDOSEDT = as.character(last_dose_date),
  LASTFUDT = as.character(last_fu_date),
  TREATDUR_W = treat_dur_weeks,
  FU_POST_DOSE = fu_post_dose,
  FU_FROM_RAND = fu_from_rand,
  ADEQUATE_FU = adequate,
  STATUS = status,
  STATUS_LABEL = status_labels,
  stringsAsFactors = FALSE
)

write.csv(df, output, row.names = FALSE)
cat(sprintf("Written: %s (%d rows)\n", output, nrow(df)))
