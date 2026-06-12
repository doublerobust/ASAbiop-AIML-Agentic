#!/usr/bin/env Rscript
#' TC-013: Waterfall Plot Data — Best % Change in Tumor Size
#'
#' Per RECIST 1.1 criteria. Returns structured data for waterfall plot.
#'
#' Usage:
#'   Rscript tc-013-waterfall.R --seed 42 --n 150 --output tc-013-output.json

suppressPackageStartupMessages({
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
seed <- 42; n_subjects <- 150; output_file <- "tc-013-output.json"
i <- 1
while (i <= length(args)) {
  if (args[i] == "--seed") { seed <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--n") { n_subjects <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--output") { output_file <- args[i + 1]; i <- i + 2 }
  else { i <- i + 1 }
}

set.seed(seed)
n_arm <- n_subjects / 2

# Generate tumor response data
generate_response <- function(n, arm, seed_offset) {
  set.seed(seed + seed_offset)
  if (arm == "Experimental") {
    category <- sample(c("CR", "PR", "SD", "PD"), n, replace = TRUE,
                       prob = c(0.15, 0.35, 0.30, 0.20))
  } else {
    category <- sample(c("CR", "PR", "SD", "PD"), n, replace = TRUE,
                       prob = c(0.05, 0.20, 0.35, 0.40))
  }

  pct_change <- numeric(n)
  for (j in seq_len(n)) {
    pct_change[j] <- switch(
      category[j],
      CR = -100.0,
      PR = runif(1, -99.0, -30.0),
      SD = runif(1, -29.9, 19.9),
      PD = runif(1, 20.0, 200.0)
    )
  }

  data.frame(
    USUBJID = paste0("SUBJ-", sprintf("%04d", 1:n)),
    TRT01A = arm,
    BASELINE = round(runif(n, 15, 100), 1),
    BESTPCHG = round(pct_change, 1),
    BOR = category,
    stringsAsFactors = FALSE
  )
}

exp_df <- generate_response(n_arm, "Experimental", 100)
ctl_df <- generate_response(n_arm, "Control", 200)
all_df <- rbind(exp_df, ctl_df)

# Sort by best % change
all_df <- all_df[order(all_df$BESTPCHG), ]

# Summary function
compute_summary <- function(df) {
  n <- nrow(df)
  n_cr <- sum(df$BOR == "CR")
  n_pr <- sum(df$BOR == "PR")
  n_sd <- sum(df$BOR == "SD")
  n_pd <- sum(df$BOR == "PD")
  list(
    n = n,
    n_cr = n_cr, n_pr = n_pr, n_sd = n_sd, n_pd = n_pd,
    orr_pct = round(100 * (n_cr + n_pr) / n, 1),
    dcr_pct = round(100 * (n_cr + n_pr + n_sd) / n, 1),
    median_best_pct_change = round(median(df$BESTPCHG), 1),
    mean_best_pct_change = round(mean(df$BESTPCHG), 1)
  )
}

output <- list(
  test_case_id = "TC-013",
  title = "Waterfall Plot — Best Percentage Change in Tumor Size",
  parameters = list(seed = seed, n_subjects = n_subjects),
  response_criteria = "RECIST 1.1",
  thresholds = list(CR = -100.0, PR = -30.0, PD = 20.0),
  summary = list(
    all = compute_summary(all_df),
    experimental = compute_summary(all_df[all_df$TRT01A == "Experimental", ]),
    control = compute_summary(all_df[all_df$TRT01A == "Control", ])
  ),
  subjects = lapply(seq_len(nrow(all_df)), function(i) as.list(all_df[i, ])),
  metadata = list(
    language = "R",
    sorting = "ascending by BESTPCHG",
    packages = c("jsonlite"),
    generated_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ")
  )
)

write_json(output, output_file, auto_unbox = TRUE, pretty = TRUE)
cat("TC-013 output written to:", output_file, "\n")
