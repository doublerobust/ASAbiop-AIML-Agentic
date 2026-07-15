#!/usr/bin/env Rscript
#' TC-031: Time-to-First-Treatment
#'
#' Time from randomization to first dose of study treatment.
#' Subjects who never receive treatment are censored at their follow-up time.
#'
#' Output:
#'   - KM median time-to-first-treatment by arm with CI
#'   - Log-rank p-value (treatment arm comparison)
#'   - Cox HR for treatment arm
#'   - N received treatment, N censored by arm
#'   - TTT summary statistics by arm (mean, median, range)
#'   - Per-subject TTT details
#'
#' Usage:
#'   Rscript tc-031-time-to-first-treatment.R --seed 42 --n 200 --output tc-031-output.json
#'   Rscript tc-031-time-to-first-treatment.R --data shared_adsl_ttt.csv --output tc-031-output.json --ars-output tc-031-ars.json

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
arm <- 0  # 0 = both arms, 1 = experimental only, 2 = control only

i <- 1
while (i <= length(args)) {
  if (args[i] == "--seed") { seed <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--n") { n_subjects <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--output") { output_file <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--data") { data_csv <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--ars-output") { ars_output <- args[i + 1]; i <- i + 2 }
  else { i <- i + 1 }
}

cat(sprintf("[%s] TC-031 Time-to-First-Treatment | seed=%d n=%d\n",
    Sys.time(), seed, n_subjects))

# --- Data generation (fallback if no shared CSV) ---
generate_ttt_data <- function(n, seed) {
  set.seed(seed)
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
  saffl <- ifelse(runif(n) < 0.98, "Y", "N")

  data.frame(
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
}

if (data_csv != "" && file.exists(data_csv)) {
  df <- read.csv(data_csv, stringsAsFactors = FALSE)
  df$RANDDT <- as.Date(df$RANDDT)
  cat(sprintf("Loaded data: %s (%d rows)\n", data_csv, nrow(df)))
} else {
  df <- generate_ttt_data(n_subjects, seed)
  cat(sprintf("Generated data: %d subjects\n", nrow(df)))
}

# --- ITT population filter ---
df_itt <- df[df$ITTFL == "Y", ]

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

# --- KM median TTT per arm ---
km_median_ttt <- function(sub_df, conf_type = "log-log") {
  time <- sub_df$TTT_DAYS
  event <- 1 - sub_df$CNSR_TTT  # 1 = received treatment (event), 0 = censored
  if (sum(event) == 0) {
    return(list(median = NA_real_, ci_lower = NA_real_, ci_upper = NA_real_,
                n_events = 0L, n_total = nrow(sub_df), estimable = FALSE))
  }
  fit <- survfit(Surv(time, event) ~ 1, conf.type = conf_type)
  tab <- summary(fit)$table
  med <- unname(tab["median"])
  ci_lower <- unname(tab["0.95LCL"])
  ci_upper <- unname(tab["0.95UCL"])
  n_events <- unname(tab["events"])
  n_total <- unname(tab["records"])
  estimable <- !is.na(med)
  list(
    median = round(as.numeric(med), 4),
    ci_lower = if (is.na(ci_lower)) NA_real_ else round(as.numeric(ci_lower), 4),
    ci_upper = if (is.na(ci_upper)) NA_real_ else round(as.numeric(ci_upper), 4),
    n_events = as.integer(n_events),
    n_total = as.integer(n_total),
    estimable = estimable
  )
}

# --- Log-rank test (both arms) ---
logrank_result <- NULL
tryCatch({
  sd_fit <- survdiff(Surv(TTT_DAYS, 1 - CNSR_TTT) ~ TRT01A, data = df_itt)
  logrank_p <- 1 - pchisq(sd_fit$chisq, df = length(sd_fit$n) - 1)
  logrank_result <- list(
    chisq = round(as.numeric(sd_fit$chisq), 4),
    df = length(sd_fit$n) - 1,
    p_value = round(logrank_p, 4)
  )
}, error = function(e) {
  logrank_result <- list(chisq = NA_real_, df = NA_integer_, p_value = NA_real_)
})

# --- Cox proportional hazards HR ---
cox_result <- NULL
tryCatch({
  cox_fit <- coxph(Surv(TTT_DAYS, 1 - CNSR_TTT) ~ TRT01PN, data = df_itt)
  cox_summary <- summary(cox_fit)
  cox_result <- list(
    hr = round(cox_summary$conf.int[1, "exp(coef)"], 4),
    hr_lower = round(cox_summary$conf.int[1, "lower .95"], 4),
    hr_upper = round(cox_summary$conf.int[1, "upper .95"], 4),
    p_value = round(cox_summary$coefficients[1, "Pr(>|z|)"], 4),
    n = cox_summary$n
  )
}, error = function(e) {
  cox_result <- list(hr = NA_real_, hr_lower = NA_real_, hr_upper = NA_real_,
                     p_value = NA_real_, n = NA_integer_)
})

# --- Compute per-arm summaries ---
exp_df <- df_itt[df_itt$TRT01PN == 1, ]
ctl_df <- df_itt[df_itt$TRT01PN == 0, ]

km_exp <- km_median_ttt(exp_df)
km_ctl <- km_median_ttt(ctl_df)

# TTT summary (days)
ttt_summary_exp <- summarize_cont(exp_df$TTT_DAYS)
ttt_summary_ctl <- summarize_cont(ctl_df$TTT_DAYS)

# Received treatment counts
received_exp <- sum(exp_df$RECEIVED_TX)
received_ctl <- sum(ctl_df$RECEIVED_TX)
censored_exp <- sum(exp_df$CNSR_TTT)
censored_ctl <- sum(ctl_df$CNSR_TTT)

result <- list(
  tc_id = "TC-031",
  tc_name = "Time-to-First-Treatment",
  metadata = list(
    n_total = as.integer(nrow(df_itt)),
    n_experimental = as.integer(nrow(exp_df)),
    n_control = as.integer(nrow(ctl_df)),
    population = "ITT",
    time_unit = "days",
    censoring_rule = "subjects who never receive treatment are censored at follow-up time",
    r_version = R.version.string
  ),
  km_median_ttt = list(
    experimental = km_exp,
    control = km_ctl
  ),
  logrank_test = logrank_result,
  cox_hr = cox_result,
  ttt_summary = list(
    experimental = ttt_summary_exp,
    control = ttt_summary_ctl
  ),
  received_treatment = list(
    experimental = list(
      n_received = as.integer(received_exp),
      n_censored = as.integer(censored_exp),
      pct_received = round(received_exp / nrow(exp_df) * 100, 2)
    ),
    control = list(
      n_received = as.integer(received_ctl),
      n_censored = as.integer(censored_ctl),
      pct_received = round(received_ctl / nrow(ctl_df) * 100, 2)
    )
  ),
  per_subject = lapply(seq_len(nrow(df_itt)), function(i) {
    list(
      USUBJID = df_itt$USUBJID[i],
      TRT01A = df_itt$TRT01A[i],
      RANDDT = as.character(df_itt$RANDDT[i]),
      FIRSTDOSEDT = if (is.na(df_itt$FIRSTDOSEDT[i])) NA_character_ else as.character(df_itt$FIRSTDOSEDT[i]),
      TTT_DAYS = df_itt$TTT_DAYS[i],
      TTT_MONTHS = df_itt$TTT_MONTHS[i],
      RECEIVED_TX = df_itt$RECEIVED_TX[i],
      CNSR_TTT = df_itt$CNSR_TTT[i]
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
      id = "TC-031",
      version = "1.0",
      analysisReason = "Assess time from randomization to first dose of study treatment",
      analysisMethod = list(
        name = "Kaplan-Meier Time-to-First-Treatment",
        codeTemplate = "survival::survfit(Surv(TTT_DAYS, 1 - CNSR_TTT) ~ 1)",
        parameters = list(
          list(name = "conf_type", role = "parameter", value = "log-log"),
          list(name = "tie_method", role = "parameter", value = "efron"),
          list(name = "censoring_rule", role = "parameter", value = "never treated = censored at follow-up")
        )
      ),
      analysisVariables = list(
        list(name = "TTT_DAYS", role = "analysis time", dataset = "ADSL"),
        list(name = "CNSR_TTT", role = "censoring", dataset = "ADSL"),
        list(name = "RECEIVED_TX", role = "event flag", dataset = "ADSL"),
        list(name = "TRT01A", role = "treatment", dataset = "ADSL")
      ),
      analysisPopulation = list(
        id = "ITT",
        filter = "ITTFL = 'Y'",
        n = as.integer(nrow(df_itt))
      ),
      resultGroups = list(
        list(id = "EXP", label = "Experimental", n = as.integer(nrow(exp_df))),
        list(id = "CTL", label = "Control", n = as.integer(nrow(ctl_df)))
      ),
      analysisResultsData = list(
        list(groupId = "EXP", metric = "median_ttt_days", value = km_exp$median),
        list(groupId = "CTL", metric = "median_ttt_days", value = km_ctl$median),
        list(groupId = "EXP", metric = "n_received", value = as.integer(received_exp)),
        list(groupId = "CTL", metric = "n_received", value = as.integer(received_ctl)),
        list(groupId = "ALL", metric = "logrank_p", value = logrank_result$p_value),
        list(groupId = "ALL", metric = "cox_hr", value = cox_result$hr)
      )
    )
  )
  writeLines(toJSON(ars, auto_unbox = TRUE, pretty = TRUE), ars_output)
  cat(sprintf("ARS written: %s\n", ars_output))
}
