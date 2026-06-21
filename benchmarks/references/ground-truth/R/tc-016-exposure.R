#!/usr/bin/env Rscript
# TC-016: Exposure Summary Table
# Treatment exposure: duration, cumulative dose, dose intensity, relative dose intensity
# Output: JSON with summary stats per treatment arm

args <- commandArgs(trailingOnly = TRUE)
seed <- 42; n <- 200; output <- ""; data_csv <- ""
i <- 1
while (i <= length(args)) {
  if (args[i] == "--seed") { seed <- as.integer(args[i+1]); i <- i + 2 }
  else if (args[i] == "--n") { n <- as.integer(args[i+1]); i <- i + 2 }
  else if (args[i] == "--output") { output <- args[i+1]; i <- i + 2 }
  else if (args[i] == "--data") { data_csv <- args[i+1]; i <- i + 2 }
  else { i <- i + 1 }
}

cat(sprintf("[%s] TC-016 Exposure Summary Table | seed=%d n=%d\n", Sys.time(), seed, n))

# --- Data generation ---
generate_exposure <- function(n, seed) {
  set.seed(seed)
  n_exp <- n %/% 2; n_ctl <- n - n_exp
  trt <- rep(c(1, 0), times = c(n_exp, n_ctl))
  # Shuffle
  trt <- sample(trt)

  # Treatment duration (weeks): Experimental ~ 40-60, Control ~ 20-40
  dur <- ifelse(trt == 1,
    round(rnorm(n_exp + n_ctl, mean = 48, sd = 12)),
    round(rnorm(n_exp + n_ctl, mean = 28, sd = 8)))
  dur <- pmax(dur, 2)  # min 2 weeks

  # Planned daily dose (mg): Exp=10, Ctl=5
  planned_daily <- ifelse(trt == 1, 10, 5)

  # Actual cumulative dose (with some missed doses, ~90-100% adherence)
  adherence <- runif(n, min = 0.75, max = 1.0)
  cum_dose <- planned_daily * dur * 7 * adherence  # daily * weeks * 7 * adherence

  # Dose intensity (% of planned)
  dose_intensity <- (cum_dose / (planned_daily * dur * 7)) * 100

  # Dose reductions (binary)
  dose_reduced <- rbinom(n, 1, ifelse(trt == 1, 0.15, 0.08))

  data.frame(
    USUBJID = sprintf("SUB%04d", seq_len(n)),
    TRT01PN = trt,
    TRT01A = ifelse(trt == 1, "Experimental", "Control"),
    TREATDUR = dur,                           # treatment duration in weeks
    CUMDOSE = round(cum_dose, 2),             # cumulative dose (mg)
    PLANDOSE = planned_daily * dur * 7,       # planned cumulative dose
    DOSEINT = round(dose_intensity, 2),       # dose intensity (%)
    DOSERED = dose_reduced,                   # dose reduced (0/1)
    stringsAsFactors = FALSE
  )
}

if (data_csv != "") {
  df <- read.csv(data_csv, stringsAsFactors = FALSE)
} else {
  df <- generate_exposure(n, seed)
}

library(jsonlite)

# --- Summary function ---
summarize_cont <- function(x) {
  list(
    n = length(x),
    mean = round(mean(x), 4),
    sd = round(sd(x), 4),
    median = round(median(x), 4),
    min = round(min(x), 4),
    max = round(max(x), 4),
    q1 = round(quantile(x, 0.25), 4),
    q3 = round(quantile(x, 0.75), 4)
  )
}

summarize_categorical <- function(x) {
  tab <- table(x)
  list(
    n = length(x),
    n_yes = as.integer(sum(x == 1)),
    n_no = as.integer(sum(x == 0)),
    pct_yes = round(sum(x == 1) / length(x) * 100, 2)
  )
}

exp_df <- df[df$TRT01PN == 1, ]
ctl_df <- df[df$TRT01PN == 0, ]

result <- list(
  tc_id = "TC-016",
  tc_name = "Exposure Summary Table",
  metadata = list(
    n_total = nrow(df),
    n_experimental = nrow(exp_df),
    n_control = nrow(ctl_df),
    population = "SAFETY",
    duration_unit = "weeks",
    dose_unit = "mg",
    r_version = R.version.string
  ),
  treatment_duration = list(
    experimental = summarize_cont(exp_df$TREATDUR),
    control = summarize_cont(ctl_df$TREATDUR)
  ),
  cumulative_dose = list(
    experimental = summarize_cont(exp_df$CUMDOSE),
    control = summarize_cont(ctl_df$CUMDOSE)
  ),
  dose_intensity = list(
    experimental = summarize_cont(exp_df$DOSEINT),
    control = summarize_cont(ctl_df$DOSEINT)
  ),
  dose_reduction = list(
    experimental = summarize_categorical(exp_df$DOSERED),
    control = summarize_categorical(ctl_df$DOSERED)
  )
)

# Convert integers
result$metadata$n_total <- as.integer(result$metadata$n_total)
result$metadata$n_experimental <- as.integer(result$metadata$n_experimental)
result$metadata$n_control <- as.integer(result$metadata$n_control)

json <- toJSON(result, auto_unbox = TRUE, pretty = TRUE)

if (output != "") {
  writeLines(json, output)
  cat(sprintf("Written: %s\n", output))
} else {
  cat(json, "\n")
}
