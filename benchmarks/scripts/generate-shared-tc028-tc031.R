#!/usr/bin/env Rscript
# Generate shared CSV datasets for TC-028 and TC-031 cross-language verification.
# Uses R's data generation logic, writes CSVs that both R and Python can read.

suppressPackageStartupMessages({
  library(jsonlite)
})

# ─── TC-028: Longitudinal tumor size ───
# Self-contained data generation (mirrors tc-028-tumor-size-by-cycle.R logic)
set.seed(42)
# Re-generate using the same function from the sourced script
CYCLES <- c("C1D1", "C2D1", "C3D1", "C4D1", "C5D1", "C6D1")
BASELINE_CYCLE <- "C1D1"

# Replicate the generation function (since the sourced one used opt$seed)
generate_longitudinal_tumor_shared <- function(n, seed_offset) {
  set.seed(42 + seed_offset)
  records <- list()
  for (i in 1:n) {
    subj <- sprintf("SUBJ-%04d", i)
    arm <- ifelse(i <= n %/% 2, "Experimental", "Control")
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
        records[[length(records) + 1]] <- data.frame(
          USUBJID = subj, TRT01A = arm, TRT01PN = ifelse(arm == "Experimental", 1, 0),
          BASELINE_SLD = baseline_sld, CYCLE = cycle, CYCLE_NUM = 0,
          SLD = baseline_sld, PCT_CHANGE = 0.0, stringsAsFactors = FALSE
        )
        next
      }
      dropout_prob <- base_dropout * (cycle_idx - 1)
      if (runif(1) < dropout_prob) break
      cycle_num <- cycle_idx
      if (cycle_num <= nadir_cycle) {
        pct <- initial_response * cycle_num
      } else {
        nadir_pct <- initial_response * nadir_cycle
        cycles_since_nadir <- cycle_num - nadir_cycle
        pct <- nadir_pct + regrowth_rate * cycles_since_nadir
      }
      pct <- pct + rnorm(1, 0, 3)
      sld <- max(baseline_sld * (1 + pct / 100), 0)
      records[[length(records) + 1]] <- data.frame(
        USUBJID = subj, TRT01A = arm, TRT01PN = ifelse(arm == "Experimental", 1, 0),
        BASELINE_SLD = baseline_sld, CYCLE = cycle, CYCLE_NUM = cycle_num,
        SLD = round(sld, 1), PCT_CHANGE = round(pct, 1), stringsAsFactors = FALSE
      )
    }
  }
  do.call(rbind, records)
}

tc028_df <- generate_longitudinal_tumor_shared(150, 200)
write.csv(tc028_df, "cross-lang-results/shared/tc028_shared.csv", row.names = FALSE)
cat(sprintf("TC-028: wrote %d rows to cross-lang-results/shared/tc028_shared.csv\n", nrow(tc028_df)))

# ─── TC-031: Time-to-first-treatment ───
cat("Generating TC-031 shared data...\n")
set.seed(42)
n <- 200
n_exp <- n %/% 2
n_ctl <- n - n_exp
trt <- rep(c(1, 0), times = c(n_exp, n_ctl))
trt <- sample(trt)

rand_date <- as.Date("2023-01-01") + sample(0:365, n, replace = TRUE)

ttt_days <- ifelse(trt == 1,
  round(rnorm(n, mean = 3, sd = 2)),
  round(rnorm(n, mean = 5, sd = 3)))
ttt_days <- pmax(ttt_days, 0)

never_tx_idx <- sample(seq_len(n), size = max(1, round(n * 0.05)))
ttt_days_orig <- ttt_days
ttt_days[never_tx_idx] <- NA

first_dose_date <- rand_date + ttt_days
first_dose_date[is.na(ttt_days)] <- NA

received_tx <- as.integer(!is.na(ttt_days))
cnsr_ttt <- as.integer(is.na(ttt_days))

fu_days_censored <- round(rnorm(length(never_tx_idx), mean = 180, sd = 60))
fu_days_censored <- pmax(fu_days_censored, 30)
ttt_days[is.na(ttt_days)] <- fu_days_censored

ttt_months <- round(ttt_days / 30.4375, 4)

sex <- sample(c("M", "F"), n, replace = TRUE)
agegr1 <- sample(c("<65", ">=65"), n, replace = TRUE)
ecog <- sample(c(0, 1), n, replace = TRUE)
ittfl <- ifelse(runif(n) < 0.95, "Y", "N")
safl <- ifelse(runif(n) < 0.98, "Y", "N")

tc031_df <- data.frame(
  USUBJID = sprintf("SUB%04d", seq_len(n)),
  TRT01PN = trt,
  TRT01A = ifelse(trt == 1, "Experimental", "Control"),
  RANDDT = as.character(rand_date),
  FIRSTDOSEDT = as.character(first_dose_date),
  TTT_DAYS = ttt_days,
  TTT_MONTHS = ttt_months,
  RECEIVED_TX = received_tx,
  CNSR_TTT = cnsr_ttt,
  ITTFL = ittfl,
  SAFFL = safl,
  SEX = sex,
  AGEGR1 = agegr1,
  ECOG = ecog,
  stringsAsFactors = FALSE
)

write.csv(tc031_df, "cross-lang-results/shared/tc031_shared.csv", row.names = FALSE)
cat(sprintf("TC-031: wrote %d rows to cross-lang-results/shared/tc031_shared.csv\n", nrow(tc031_df)))

cat("\nDone. Shared CSVs ready for cross-language verification.\n")
