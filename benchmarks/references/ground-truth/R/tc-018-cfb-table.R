#!/usr/bin/env Rscript
# TC-018: Change from Baseline Table
# Longitudinal efficacy: baseline, change from baseline at each visit, CIs, p-values
# Output: JSON with visit-wise summary stats and treatment comparisons

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

cat(sprintf("[%s] TC-018 Change from Baseline Table | seed=%d n=%d\n", Sys.time(), seed, n))

# --- Data generation ---
generate_cfb <- function(n, seed) {
  set.seed(seed)
  n_exp <- n %/% 2; n_ctl <- n - n_exp
  trt <- rep(c(1, 0), times = c(n_exp, n_ctl))
  trt <- sample(trt)

  visits <- c("BASELINE", "WEEK_6", "WEEK_12", "WEEK_18", "WEEK_24")
  n_visits <- length(visits)

  # Tumor size baseline (mm): mean 50, sd 15
  baseline <- rnorm(n, mean = 50, sd = 15)

  # Treatment effect: Experimental decreases over time, Control stable
  # Change from baseline per visit
  visits_data <- list()
  for (v in seq_along(visits)) {
    vn <- visits[v]
    if (vn == "BASELINE") {
      vals <- baseline
      cfbs <- rep(0, n)
    } else {
      # Time effect in weeks
      weeks <- as.numeric(gsub("WEEK_", "", vn))
      # Experimental: -0.8 mm/week + noise
      # Control: -0.1 mm/week + noise
      change <- ifelse(trt == 1,
        -0.8 * weeks + rnorm(n, 0, 8),
        -0.1 * weeks + rnorm(n, 0, 8))
      vals <- baseline + change
      cfbs <- change
    }
    visits_data[[vn]] <- data.frame(
      USUBJID = sprintf("SUB%04d", seq_len(n)),
      TRT01PN = trt,
      TRT01A = ifelse(trt == 1, "Experimental", "Control"),
      AVISIT = vn,
      AVISITN = v - 1,
      AVAL = round(vals, 2),
      CHG = round(cfbs, 2),
      BASE = round(baseline, 2)
    )
  }
  do.call(rbind, visits_data)
}

if (data_csv != "") {
  df <- read.csv(data_csv, stringsAsFactors = FALSE)
} else {
  df <- generate_cfb(n, seed)
}

library(jsonlite)

# --- Summarize change from baseline per visit, per arm ---
summarize_chg <- function(d) {
  list(
    n = nrow(d),
    mean_chg = round(mean(d$CHG), 4),
    sd_chg = round(sd(d$CHG), 4),
    median_chg = round(median(d$CHG), 4),
    se_chg = round(sd(d$CHG) / sqrt(nrow(d)), 4),
    ci_lower = round(mean(d$CHG) - 1.96 * sd(d$CHG) / sqrt(nrow(d)), 4),
    ci_upper = round(mean(d$CHG) + 1.96 * sd(d$CHG) / sqrt(nrow(d)), 4),
    mean_aval = round(mean(d$AVAL), 4),
    sd_aval = round(sd(d$AVAL), 4)
  )
}

visits <- unique(df$AVISIT)
visits <- visits[order(unique(df$AVISITN))]

# Build visit-wise summaries
visit_results <- list()
for (vn in visits) {
  vd <- df[df$AVISIT == vn, ]
  exp_d <- vd[vd$TRT01PN == 1, ]
  ctl_d <- vd[vd$TRT01PN == 0, ]

  # T-test at post-baseline visits
  p_val <- NA_real_
  if (vn != "BASELINE" && nrow(exp_d) > 1 && nrow(ctl_d) > 1) {
    tt <- t.test(exp_d$CHG, ctl_d$CHG)
    p_val <- round(tt$p.value, 6)
  } else if (vn == "BASELINE") {
    # Baseline: test AVAL equivalence
    tt <- t.test(exp_d$AVAL, ctl_d$AVAL)
    p_val <- round(tt$p.value, 6)
  }

  visit_results[[vn]] <- list(
    visit = vn,
    experimental = summarize_chg(exp_d),
    control = summarize_chg(ctl_d),
    p_value = p_val
  )
}

result <- list(
  tc_id = "TC-018",
  tc_name = "Change from Baseline Table",
  metadata = list(
    n_total = length(unique(df$USUBJID)),
    n_experimental = length(unique(df$USUBJID[df$TRT01PN == 1])),
    n_control = length(unique(df$USUBJID[df$TRT01PN == 0])),
    population = "ITT",
    visits = visits,
    endpoint = "Tumor Size",
    endpoint_unit = "mm",
    r_version = R.version.string
  ),
  visits = visit_results
)

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
