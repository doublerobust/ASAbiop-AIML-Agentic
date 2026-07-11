#!/usr/bin/env Rscript
#' TC-033: Dose Intensity Summary (Relative Dose Intensity)
#'
#' Computes Relative Dose Intensity (RDI) per subject and summarizes by arm:
#'   RDI = (actual cumulative dose / planned cumulative dose) × 100
#'
#' Output: Per-subject RDI, arm-level summary (N, mean, SD, median, range),
#'         % subjects with RDI >= 80%, % with dose reduction, % with dose interruption
#'
#' Usage:
#'   Rscript tc-033-dose-intensity.R --seed 42 --n 200 --output tc-033-output.json
#'   Rscript tc-033-dose-intensity.R --data shared_adsl.csv --output tc-033-output.json --ars-output tc-033-ars.json

suppressPackageStartupMessages({
  library(jsonlite)
  library(dplyr)
})

# --- Argument parsing ---
args <- commandArgs(trailingOnly = TRUE)
seed <- 42
n_subjects <- 200
output_file <- ""
data_csv <- ""
ars_output <- ""

i <- 1
while (i <= length(args)) {
  if (args[i] == "--seed") { seed <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--n") { n_subjects <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--output") { output_file <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--data") { data_csv <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--ars-output") { ars_output <- args[i + 1]; i <- i + 2 }
  else { i <- i + 1 }
}

cat(sprintf("[%s] TC-033 Dose Intensity Summary | seed=%d n=%d\n", Sys.time(), seed, n_subjects))

# --- Data generation ---
# ADEX-style: per-subject exposure records with planned vs actual dose
generate_exposure_data <- function(n, seed) {
  set.seed(seed)
  n_exp <- n %/% 2
  n_ctl <- n - n_exp
  trt <- rep(c(1, 0), times = c(n_exp, n_ctl))
  trt <- sample(trt)  # shuffle

  # Treatment duration (weeks): Exp ~ 36-60, Ctl ~ 18-36
  dur <- ifelse(trt == 1,
    round(rnorm(n, mean = 48, sd = 10)),
    round(rnorm(n, mean = 27, sd = 7)))
  dur <- pmax(dur, 2)

  # Planned daily dose (mg): Exp=12, Ctl=6
  planned_daily <- ifelse(trt == 1, 12, 6)
  planned_cum <- planned_daily * dur * 7

  # Adherence: Exp ~85-100%, Ctl ~90-100%
  adherence <- ifelse(trt == 1,
    runif(n, min = 0.70, max = 1.0),
    runif(n, min = 0.80, max = 1.0))

  actual_cum <- planned_cum * adherence

  # Dose reduction (binary): Exp ~15%, Ctl ~8%
  dose_reduced <- rbinom(n, 1, ifelse(trt == 1, 0.15, 0.08))

  # Dose interruption (binary): Exp ~10%, Ctl ~5%
  dose_interrupt <- rbinom(n, 1, ifelse(trt == 1, 0.10, 0.05))

  # RDI
  rdi <- (actual_cum / planned_cum) * 100

  data.frame(
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
}

if (data_csv != "" && file.exists(data_csv)) {
  df <- read.csv(data_csv, stringsAsFactors = FALSE)
  cat(sprintf("Loaded data: %s (%d rows)\n", data_csv, nrow(df)))
} else {
  df <- generate_exposure_data(n_subjects, seed)
  cat(sprintf("Generated data: %d subjects\n", nrow(df)))
}

# --- Summary functions ---
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

# --- Compute summaries ---
exp_df <- df[df$TRT01PN == 1, ]
ctl_df <- df[df$TRT01PN == 0, ]

# RDI >= 80% indicator
rdi_ge80_exp <- sum(exp_df$RDI >= 80)
rdi_ge80_ctl <- sum(ctl_df$RDI >= 80)

# Dose reduction count
dose_red_exp <- sum(exp_df$DOSERED)
dose_red_ctl <- sum(ctl_df$DOSERED)

# Dose interruption count
dose_int_exp <- sum(exp_df$DOSEINT)
dose_int_ctl <- sum(ctl_df$DOSEINT)

result <- list(
  tc_id = "TC-033",
  tc_name = "Dose Intensity Summary",
  metadata = list(
    n_total = as.integer(nrow(df)),
    n_experimental = as.integer(nrow(exp_df)),
    n_control = as.integer(nrow(ctl_df)),
    population = "SAFETY",
    rdi_threshold = 80,
    duration_unit = "weeks",
    dose_unit = "mg",
    r_version = R.version.string
  ),
  rdi_summary = list(
    experimental = summarize_cont(exp_df$RDI),
    control = summarize_cont(ctl_df$RDI)
  ),
  rdi_ge80 = list(
    experimental = list(
      n = as.integer(rdi_ge80_exp),
      pct = round(rdi_ge80_exp / nrow(exp_df) * 100, 2)
    ),
    control = list(
      n = as.integer(rdi_ge80_ctl),
      pct = round(rdi_ge80_ctl / nrow(ctl_df) * 100, 2)
    )
  ),
  dose_reduction = list(
    experimental = list(
      n = as.integer(dose_red_exp),
      pct = round(dose_red_exp / nrow(exp_df) * 100, 2)
    ),
    control = list(
      n = as.integer(dose_red_ctl),
      pct = round(dose_red_ctl / nrow(ctl_df) * 100, 2)
    )
  ),
  dose_interruption = list(
    experimental = list(
      n = as.integer(dose_int_exp),
      pct = round(dose_int_exp / nrow(exp_df) * 100, 2)
    ),
    control = list(
      n = as.integer(dose_int_ctl),
      pct = round(dose_int_ctl / nrow(ctl_df) * 100, 2)
    )
  ),
  treatment_duration = list(
    experimental = summarize_cont(exp_df$TREATDUR),
    control = summarize_cont(ctl_df$TREATDUR)
  ),
  per_subject = lapply(seq_len(nrow(df)), function(i) {
    list(
      USUBJID = df$USUBJID[i],
      TRT01A = df$TRT01A[i],
      TREATDUR = df$TREATDUR[i],
      PLANDOSE = df$PLANDOSE[i],
      ACTUALDOSE = df$ACTUALDOSE[i],
      RDI = df$RDI[i],
      DOSERED = df$DOSERED[i],
      DOSEINT = df$DOSEINT[i]
    )
  })
)

json_out <- toJSON(result, auto_unbox = TRUE, pretty = TRUE)

if (output_file != "") {
  writeLines(json_out, output_file)
  cat(sprintf("Written: %s\n", output_file))
} else {
  cat(json_out, "\n")
}

# --- ARS output ---
if (ars_output != "") {
  ars <- list(
    analysisResult = list(
      id = "TC-033",
      version = "1.0",
      analysisReason = "Summary of relative dose intensity by treatment arm",
      analysisMethod = list(
        name = "Dose Intensity Summary",
        codeTemplate = "RDI = (ACTUALDOSE / PLANDOSE) * 100",
        parameters = list(
          list(name = "actual_dose", role = "input", source = "ADEX.ACTUALDOSE"),
          list(name = "planned_dose", role = "input", source = "ADEX.PLANDOSE"),
          list(name = "rdi_threshold", role = "parameter", value = 80)
        )
      ),
      analysisVariables = list(
        list(name = "TRT01A", role = "treatment", dataset = "ADSL"),
        list(name = "RDI", role = "result", dataset = "derived"),
        list(name = "DOSERED", role = "flag", dataset = "ADEX"),
        list(name = "DOSEINT", role = "flag", dataset = "ADEX")
      ),
      analysisPopulation = list(
        id = "SAFETY",
        filter = "SAFFL == 'Y'",
        n = as.integer(nrow(df))
      ),
      resultGroups = list(
        list(id = "EXP", label = "Experimental", n = as.integer(nrow(exp_df))),
        list(id = "CTL", label = "Control", n = as.integer(nrow(ctl_df)))
      ),
      analysisResultsData = list(
        list(groupId = "EXP", metric = "mean_RDI", value = round(mean(exp_df$RDI), 4)),
        list(groupId = "CTL", metric = "mean_RDI", value = round(mean(ctl_df$RDI), 4)),
        list(groupId = "EXP", metric = "pct_RDI_ge80", value = round(rdi_ge80_exp / nrow(exp_df) * 100, 2)),
        list(groupId = "CTL", metric = "pct_RDI_ge80", value = round(rdi_ge80_ctl / nrow(ctl_df) * 100, 2))
      )
    )
  )
  writeLines(toJSON(ars, auto_unbox = TRUE, pretty = TRUE), ars_output)
  cat(sprintf("ARS written: %s\n", ars_output))
}
