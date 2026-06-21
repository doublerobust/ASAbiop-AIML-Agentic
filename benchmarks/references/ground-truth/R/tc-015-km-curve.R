#!/usr/bin/env Rscript
# TC-015: Kaplan-Meier Curve with Risk Table
# Generates KM survival curve coordinates and risk table counts
# Output: JSON with curve coordinates, CI, and risk set at specified time points

# --- Dependencies: survival, jsonlite, dplyr ---

args <- commandArgs(trailingOnly = TRUE)
seed <- 42
n <- 200
output <- ""
data_csv <- ""

i <- 1
while (i <= length(args)) {
  if (args[i] == "--seed") { seed <- as.integer(args[i+1]); i <- i + 2 }
  else if (args[i] == "--n") { n <- as.integer(args[i+1]); i <- i + 2 }
  else if (args[i] == "--output") { output <- args[i+1]; i <- i + 2 }
  else if (args[i] == "--data") { data_csv <- args[i+1]; i <- i + 2 }
  else { i <- i + 1 }
}

cat(sprintf("[%s] TC-015 KM Curve + Risk Table | seed=%d n=%d\n", Sys.time(), seed, n))

# --- Data generation (if no shared CSV) ---
generate_adtte <- function(n, seed) {
  set.seed(seed)
  trt <- rep(c(1, 0), each = n %/% 2)
  # Experimental arm: longer median survival (~12 months)
  shape_e <- 1.3; scale_e <- 14
  shape_c <- 1.1; scale_c <- 8
  ttev <- ifelse(trt == 1,
    rgamma(n, shape = shape_e, scale = scale_e),
    rgamma(n, shape = shape_c, scale = scale_c))
  # Censoring
  cens <- runif(n, min = 6, max = 30)
  ev <- as.integer(ttev <= cens)
  ttev <- pmin(ttev, cens)
  # Strata
  sex <- sample(c("F", "M"), n, replace = TRUE)
  ecog <- sample(c(0, 1), n, replace = TRUE, prob = c(0.6, 0.4))
  data.frame(
    USUBJID = sprintf("SUB%04d", seq_len(n)),
    TRT01PN = trt,
    TRT01A = ifelse(trt == 1, "Experimental", "Control"),
    AVAL = round(ttev, 4),
    CNSR = 1 - ev,
    EVNT = ev,
    SEX = sex,
    ECOG = ecog,
    stringsAsFactors = FALSE
  )
}

if (data_csv != "") {
  adtte <- read.csv(data_csv, stringsAsFactors = FALSE)
} else {
  adtte <- generate_adtte(n, seed)
}

# --- KM estimation by treatment arm ---
library(survival)
library(jsonlite)

fit <- survfit(Surv(AVAL, EVNT) ~ TRT01PN, data = adtte)

# Extract curve at standard time points
time_points <- c(0, 3, 6, 9, 12, 15, 18, 21, 24, 30)

extract_curve <- function(fit, arm_code, time_points) {
  # Get the curve for this arm
  sd <- summary(fit, times = time_points, extend = TRUE)
  idx <- which(sd$strata == sprintf("TRT01PN=%d", arm_code))
  if (length(idx) == 0) {
    # Single stratum: no strata column
    surv_vals <- sd$surv
    lower <- sd$lower
    upper <- sd$upper
    n_risk <- sd$n.risk
    n_event <- sd$n.event
    n_censor <- sd$n.censor
  } else {
    surv_vals <- sd$surv[idx]
    lower <- sd$lower[idx]
    upper <- sd$upper[idx]
    n_risk <- sd$n.risk[idx]
    n_event <- sd$n.event[idx]
    n_censor <- sd$n.censor[idx]
  }
  list(
    time_points = as.numeric(time_points),
    survival = as.numeric(round(surv_vals, 6)),
    ci_lower = as.numeric(round(lower, 6)),
    ci_upper = as.numeric(round(upper, 6)),
    n_at_risk = as.integer(n_risk),
    n_events = as.integer(n_event),
    n_censored = as.integer(n_censor)
  )
}

curve_exp <- extract_curve(fit, 1, time_points)
curve_ctl <- extract_curve(fit, 0, time_points)

# Overall median
overall_fit <- survfit(Surv(AVAL, EVNT) ~ 1, data = adtte)
overall_median <- as.numeric(summary(overall_fit)$table["median"])
overall_ci <- as.numeric(summary(overall_fit)$table[c("0.95LCL", "0.95UCL")])

# Log-rank test
lr <- survdiff(Surv(AVAL, EVNT) ~ TRT01PN, data = adtte)
lr_chisq <- as.numeric(lr$chisq)
lr_df <- length(lr$n) - 1
lr_p <- as.numeric(1 - pchisq(lr_chisq, lr_df))

# Total subjects and events by arm
n_exp <- sum(adtte$TRT01PN == 1)
n_ctl <- sum(adtte$TRT01PN == 0)
events_exp <- sum(adtte$EVNT[adtte$TRT01PN == 1])
events_ctl <- sum(adtte$EVNT[adtte$TRT01PN == 0])

result <- list(
  tc_id = "TC-015",
  tc_name = "KM Curve with Risk Table",
  metadata = list(
    n_total = nrow(adtte),
    n_experimental = n_exp,
    n_control = n_ctl,
    events_experimental = events_exp,
    events_control = events_ctl,
    population = "ITT",
    time_unit = "months",
    time_points = time_points,
    r_version = R.version.string,
    package = "survival"
  ),
  overall_median = list(
    median = round(overall_median, 4),
    ci_lower = round(overall_ci[1], 4),
    ci_upper = round(overall_ci[2], 4)
  ),
  logrank = list(
    chisq = round(lr_chisq, 6),
    df = lr_df,
    p_value = round(lr_p, 6)
  ),
  curve_experimental = curve_exp,
  curve_control = curve_ctl
)

# Round metadata n's to integers
result$metadata$n_total <- as.integer(result$metadata$n_total)
result$metadata$n_experimental <- as.integer(result$metadata$n_experimental)
result$metadata$n_control <- as.integer(result$metadata$n_control)
result$metadata$events_experimental <- as.integer(result$metadata$events_experimental)
result$metadata$events_control <- as.integer(result$metadata$events_control)

json <- toJSON(result, auto_unbox = TRUE, pretty = TRUE)

if (output != "") {
  writeLines(json, output)
  cat(sprintf("Written: %s\n", output))
} else {
  cat(json, "\n")
}
