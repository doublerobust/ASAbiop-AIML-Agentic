#!/usr/bin/env Rscript
#' TC-034: Sufficient Follow-up Assessment
#'
#' Assesses whether subjects have sufficient safety follow-up per protocol
#' (e.g., 90 days post-last-dose). Also computes median follow-up duration
#' using the reverse Kaplan-Meier method.
#'
#' Output:
#'   - N (%) with adequate follow-up by arm (>= threshold days post-last-dose)
#'   - Median follow-up duration (reverse KM) by arm with CI
#'   - N still ongoing, N discontinued, N died
#'   - Per-subject follow-up details
#'
#' Usage:
#'   Rscript tc-034-sufficient-followup.R --seed 42 --n 200 --output tc-034-output.json
#'   Rscript tc-034-sufficient-followup.R --data shared_adsl.csv --output tc-034-output.json --ars-output tc-034-ars.json

suppressPackageStartupMessages({
  library(jsonlite)
  library(survival)
})

# --- Argument parsing ---
args <- commandArgs(trailingOnly = TRUE)
seed <- 42
n_subjects <- 200
output_file <- ""
data_csv <- ""
ars_output <- ""
followup_threshold <- 90  # days post-last-dose

i <- 1
while (i <= length(args)) {
  if (args[i] == "--seed") { seed <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--n") { n_subjects <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--output") { output_file <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--data") { data_csv <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--ars-output") { ars_output <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--threshold") { followup_threshold <- as.integer(args[i + 1]); i <- i + 2 }
  else { i <- i + 1 }
}

cat(sprintf("[%s] TC-034 Sufficient Follow-up Assessment | seed=%d n=%d threshold=%dd\n",
    Sys.time(), seed, n_subjects, followup_threshold))

# --- Data generation ---
# ADSL-style: per-subject with randomization date, last dose date, last follow-up date, status
generate_followup_data <- function(n, seed) {
  set.seed(seed)
  n_exp <- n %/% 2
  n_ctl <- n - n_exp
  trt <- rep(c(1, 0), times = c(n_exp, n_ctl))
  trt <- sample(trt)

  # Randomization date (study start: 2023-01-01 + random offset)
  rand_date <- as.Date("2023-01-01") + sample(0:365, n, replace = TRUE)

  # Treatment duration (weeks): Exp ~ 24-60, Ctl ~ 12-36
  treat_dur_weeks <- ifelse(trt == 1,
    round(rnorm(n, mean = 42, sd = 10)),
    round(rnorm(n, mean = 24, sd = 7)))
  treat_dur_weeks <- pmax(treat_dur_weeks, 2)

  # Last dose date = randomization + treatment duration
  last_dose_date <- rand_date + treat_dur_weeks * 7

  # Follow-up duration post-last-dose (days)
  # Exp: ~60-180 days, Ctl: ~60-150 days (some will be < 90 = inadequate)
  fu_post_dose <- ifelse(trt == 1,
    round(rnorm(n, mean = 120, sd = 40)),
    round(rnorm(n, mean = 100, sd = 35)))
  fu_post_dose <- pmax(fu_post_dose, 0)

  # Last follow-up date
  last_fu_date <- last_dose_date + fu_post_dose

  # Subject status at end of study:
  # 1 = Ongoing (still in follow-up), 2 = Completed, 3 = Discontinued, 4 = Died
  status_prob <- matrix(c(
    0.20, 0.55, 0.15, 0.10,  # Exp
    0.15, 0.65, 0.12, 0.08   # Ctl
  ), nrow = 2, byrow = TRUE)

  status <- integer(n)
  for (j in 1:n) {
    status[j] <- sample(1:4, 1, prob = status_prob[trt[j] + 1, ])
  }

  # For died subjects, cap follow-up at a reasonable time
  died_idx <- which(status == 4)
  if (length(died_idx) > 0) {
    fu_post_dose[died_idx] <- pmin(fu_post_dose[died_idx],
      round(rnorm(length(died_idx), mean = 45, sd = 20)))
    fu_post_dose[died_idx] <- pmax(fu_post_dose[died_idx], 0)
    last_fu_date[died_idx] <- last_dose_date[died_idx] + fu_post_dose[died_idx]
  }

  # Follow-up from randomization (total)
  fu_from_rand <- as.numeric(last_fu_date - rand_date)

  # Adequate follow-up: >= threshold days post-last-dose AND not died
  adequate <- as.integer(fu_post_dose >= followup_threshold & status != 4)

  data.frame(
    USUBJID = sprintf("SUB%04d", seq_len(n)),
    TRT01PN = trt,
    TRT01A = ifelse(trt == 1, "Experimental", "Control"),
    RANDDT = rand_date,
    LASTDOSEDT = last_dose_date,
    LASTFUDT = last_fu_date,
    TREATDUR_W = treat_dur_weeks,
    FU_POST_DOSE = fu_post_dose,
    FU_FROM_RAND = fu_from_rand,
    ADEQUATE_FU = adequate,
    STATUS = status,
    STATUS_LABEL = c("ONGOING", "COMPLETED", "DISCONTINUED", "DIED")[status],
    stringsAsFactors = FALSE
  )
}

if (data_csv != "" && file.exists(data_csv)) {
  df <- read.csv(data_csv, stringsAsFactors = FALSE)
  # Convert date columns
  df$RANDDT <- as.Date(df$RANDDT)
  df$LASTDOSEDT <- as.Date(df$LASTDOSEDT)
  df$LASTFUDT <- as.Date(df$LASTFUDT)
  cat(sprintf("Loaded data: %s (%d rows)\n", data_csv, nrow(df)))
} else {
  df <- generate_followup_data(n_subjects, seed)
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

# --- Reverse Kaplan-Meier for median follow-up ---
# Reverse KM: censor event deaths, treat everything else as events
# Using Fu_from_rand as time, event = 1 if not died (reverse), 0 if died
reverse_km_median <- function(time, status_label) {
  # In reverse KM, "event" = still alive (not died), "censored" = died
  event <- as.integer(status_label != "DIED")
  if (sum(event) == 0) return(list(median = NA_real_, ci_lower = NA_real_, ci_upper = NA_real_))
  surv_obj <- Surv(time, event)
  fit <- survfit(surv_obj ~ 1)
  med <- summary(fit)$table[["median"]]
  ci_lower <- summary(fit)$table[["0.95LCL"]]
  ci_upper <- summary(fit)$table[["0.95UCL"]]
  list(median = round(as.numeric(med), 4), ci_lower = round(as.numeric(ci_lower), 4), ci_upper = round(as.numeric(ci_upper), 4))
}

# --- Compute summaries ---
exp_df <- df[df$TRT01PN == 1, ]
ctl_df <- df[df$TRT01PN == 0, ]

# Adequate follow-up counts
adeq_exp <- sum(exp_df$ADEQUATE_FU)
adeq_ctl <- sum(ctl_df$ADEQUATE_FU)

# Status distribution
status_counts <- function(sub_df) {
  labels <- c("ONGOING", "COMPLETED", "DISCONTINUED", "DIED")
  sapply(labels, function(l) sum(sub_df$STATUS_LABEL == l))
}

status_exp <- status_counts(exp_df)
status_ctl <- status_counts(ctl_df)

# Reverse KM median follow-up
revkm_exp <- reverse_km_median(exp_df$FU_FROM_RAND, exp_df$STATUS_LABEL)
revkm_ctl <- reverse_km_median(ctl_df$FU_FROM_RAND, ctl_df$STATUS_LABEL)

# Follow-up post-dose summary
fu_post_exp <- summarize_cont(exp_df$FU_POST_DOSE)
fu_post_ctl <- summarize_cont(ctl_df$FU_POST_DOSE)

# Follow-up from randomization summary
fu_rand_exp <- summarize_cont(exp_df$FU_FROM_RAND)
fu_rand_ctl <- summarize_cont(ctl_df$FU_FROM_RAND)

result <- list(
  tc_id = "TC-034",
  tc_name = "Sufficient Follow-up Assessment",
  metadata = list(
    n_total = as.integer(nrow(df)),
    n_experimental = as.integer(nrow(exp_df)),
    n_control = as.integer(nrow(ctl_df)),
    population = "SAFETY",
    followup_threshold_days = as.integer(followup_threshold),
    date_unit = "days",
    r_version = R.version.string
  ),
  adequate_followup = list(
    experimental = list(
      n = as.integer(adeq_exp),
      pct = round(adeq_exp / nrow(exp_df) * 100, 2)
    ),
    control = list(
      n = as.integer(adeq_ctl),
      pct = round(adeq_ctl / nrow(ctl_df) * 100, 2)
    )
  ),
  status_distribution = list(
    experimental = list(
      ongoing = as.integer(status_exp["ONGOING"]),
      completed = as.integer(status_exp["COMPLETED"]),
      discontinued = as.integer(status_exp["DISCONTINUED"]),
      died = as.integer(status_exp["DIED"])
    ),
    control = list(
      ongoing = as.integer(status_ctl["ONGOING"]),
      completed = as.integer(status_ctl["COMPLETED"]),
      discontinued = as.integer(status_ctl["DISCONTINUED"]),
      died = as.integer(status_ctl["DIED"])
    )
  ),
  reverse_km_followup = list(
    experimental = revkm_exp,
    control = revkm_ctl
  ),
  fu_post_dose = list(
    experimental = fu_post_exp,
    control = fu_post_ctl
  ),
  fu_from_randomization = list(
    experimental = fu_rand_exp,
    control = fu_rand_ctl
  ),
  per_subject = lapply(seq_len(nrow(df)), function(i) {
    list(
      USUBJID = df$USUBJID[i],
      TRT01A = df$TRT01A[i],
      RANDDT = as.character(df$RANDDT[i]),
      LASTDOSEDT = as.character(df$LASTDOSEDT[i]),
      LASTFUDT = as.character(df$LASTFUDT[i]),
      TREATDUR_W = df$TREATDUR_W[i],
      FU_POST_DOSE = df$FU_POST_DOSE[i],
      FU_FROM_RAND = df$FU_FROM_RAND[i],
      ADEQUATE_FU = df$ADEQUATE_FU[i],
      STATUS = df$STATUS[i],
      STATUS_LABEL = df$STATUS_LABEL[i]
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
      id = "TC-034",
      version = "1.0",
      analysisReason = "Assess sufficiency of safety follow-up per protocol requirements",
      analysisMethod = list(
        name = "Sufficient Follow-up Assessment",
        codeTemplate = "adequate = (fu_post_dose >= threshold) & (status != DIED)",
        parameters = list(
          list(name = "followup_threshold", role = "parameter", value = followup_threshold),
          list(name = "fu_post_dose", role = "input", source = "ADSL.LASTFUDT - ADSL.LASTDOSEDT"),
          list(name = "status", role = "input", source = "ADSL.EOSSTT")
        )
      ),
      analysisVariables = list(
        list(name = "TRT01A", role = "treatment", dataset = "ADSL"),
        list(name = "FU_POST_DOSE", role = "result", dataset = "derived"),
        list(name = "ADEQUATE_FU", role = "flag", dataset = "derived"),
        list(name = "STATUS_LABEL", role = "status", dataset = "ADSL")
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
        list(groupId = "EXP", metric = "pct_adequate_fu", value = round(adeq_exp / nrow(exp_df) * 100, 2)),
        list(groupId = "CTL", metric = "pct_adequate_fu", value = round(adeq_ctl / nrow(ctl_df) * 100, 2)),
        list(groupId = "EXP", metric = "median_followup", value = revkm_exp$median),
        list(groupId = "CTL", metric = "median_followup", value = revkm_ctl$median)
      )
    )
  )
  writeLines(toJSON(ars, auto_unbox = TRUE, pretty = TRUE), ars_output)
  cat(sprintf("ARS written: %s\n", ars_output))
}
