#!/usr/bin/env Rscript
# TC-025 Ground Truth: Best Overall Response (BOR) Summary Table
# Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark
#
# BOR per RECIST 1.1: CR, PR, SD, PD, NE (Not Evaluable)
# This test case evaluates:
#   1. Correct BOR derivation from individual lesion measurements
#   2. Response rates (ORR = CR+PR, DCR = CR+PR+SD) — cross-TFL with TC-020/023
#   3. Difference in response proportions between arms (Fisher exact / chi-square)
#   4. 95% CI for response rates (Clopper-Pearson exact)
#
# Dependencies: jsonlite, dplyr
# Usage: Rscript tc-025-bor-summary.R --seed 42 --n 200 --output results.json

library(jsonlite)
library(dplyr)

# Source common utilities
source("common/data-generation.R")

# ─────────────────────────────────────────────────────
# Command-line argument parsing
# ─────────────────────────────────────────────────────

parse_args <- function() {
  args <- commandArgs(trailingOnly = TRUE)
  get_arg <- function(flag, default) {
    idx <- which(args == flag)
    if (length(idx) > 0 && idx < length(args)) return(args[idx + 1])
    return(default)
  }
  list(
    seed = as.integer(get_arg("--seed", "42")),
    n = as.integer(get_arg("--n", "200")),
    data = get_arg("--data", NA),
    output = get_arg("--output", NA),
    ars_output = get_arg("--ars-output", NA)
  )
}

# ─────────────────────────────────────────────────────
# Generate BOR data
# ─────────────────────────────────────────────────────

generate_bor_data <- function(seed = 42, n_subjects = 200) {
  set.seed(seed)
  trt <- sample(0:1, n_subjects, replace = TRUE)

  # Response probabilities differ by treatment arm
  # Control: CR 2%, PR 18%, SD 45%, PD 30%, NE 5%
  # Active: CR 8%, PR 35%, SD 35%, PD 15%, NE 7%
  bor <- sapply(trt, function(a) {
    if (a == 0) {
      sample(c("CR", "PR", "SD", "PD", "NE"),
             1, prob = c(0.02, 0.18, 0.45, 0.30, 0.05))
    } else {
      sample(c("CR", "PR", "SD", "PD", "NE"),
             1, prob = c(0.08, 0.35, 0.35, 0.15, 0.07))
    }
  })

  # Strata
  sex <- sample(c("M", "F"), n_subjects, replace = TRUE, prob = c(0.55, 0.45))
  age <- round(rnorm(n_subjects, mean = 58, sd = 12))
  agegr1 <- ifelse(age < 65, "<65", ">=65")
  ecog <- sample(0:1, n_subjects, replace = TRUE, prob = c(0.6, 0.4))

  data.frame(
    USUBJID = sprintf("SUBJ-%04d", 1:n_subjects),
    STUDYID = "BENCHMARK-001",
    TRT01PN = trt,
    TRT01P = ifelse(trt == 0, "Placebo", "Active"),
    BOR = bor,
    ITTFL = ifelse(runif(n_subjects) < 0.95, "Y", "N"),
    SAFFL = ifelse(runif(n_subjects) < 0.98, "Y", "N"),
    SEX = sex,
    AGEGR1 = agegr1,
    ECOG = ecog,
    stringsAsFactors = FALSE
  )
}

# ─────────────────────────────────────────────────────
# Clopper-Pearson exact CI
# ─────────────────────────────────────────────────────

clopper_pearson_ci <- function(x, n, conf_level = 0.95) {
  alpha <- 1 - conf_level
  lower <- if (x == 0) 0 else qbeta(alpha / 2, x, n - x + 1)
  upper <- if (x == n) 1 else qbeta(1 - alpha / 2, x + 1, n - x)
  c(lower = lower, upper = upper)
}

# ─────────────────────────────────────────────────────
# TC-025 Core Computation
# ─────────────────────────────────────────────────────

compute_bor_summary <- function(data) {
  data_itt <- data %>% filter(ITTFL == "Y")

  # BOR distribution by arm
  bor_dist <- data_itt %>%
    group_by(TRT01PN, BOR) %>%
    summarise(n = n(), .groups = "drop") %>%
    arrange(TRT01PN, BOR)

  # Response rates by arm
  results <- list()
  for (arm in c(0, 1)) {
    arm_data <- data_itt %>% filter(TRT01PN == arm)
    n_total <- nrow(arm_data)

    n_cr <- sum(arm_data$BOR == "CR")
    n_pr <- sum(arm_data$BOR == "PR")
    n_sd <- sum(arm_data$BOR == "SD")
    n_pd <- sum(arm_data$BOR == "PD")
    n_ne <- sum(arm_data$BOR == "NE")

    # Evaluable subjects (exclude NE)
    n_eval <- n_total - n_ne

    # ORR = (CR + PR) / N
    n_orr <- n_cr + n_pr
    orr_rate <- n_orr / n_total
    orr_ci <- clopper_pearson_ci(n_orr, n_total)

    # DCR = (CR + PR + SD) / N
    n_dcr <- n_cr + n_pr + n_sd
    dcr_rate <- n_dcr / n_total
    dcr_ci <- clopper_pearson_ci(n_dcr, n_total)

    # CBR (Clinical Benefit Rate) = same as DCR in this context
    # Documented separately for cross-TFL consistency

    results[[as.character(arm)]] <- list(
      arm = arm,
      n_total = as.integer(n_total),
      n_evaluable = as.integer(n_eval),
      bor_counts = list(
        CR = as.integer(n_cr),
        PR = as.integer(n_pr),
        SD = as.integer(n_sd),
        PD = as.integer(n_pd),
        NE = as.integer(n_ne)
      ),
      orr_n = as.integer(n_orr),
      orr_rate = round(orr_rate, 4),
      orr_ci_lower = round(orr_ci["lower"], 4),
      orr_ci_upper = round(orr_ci["upper"], 4),
      dcr_n = as.integer(n_dcr),
      dcr_rate = round(dcr_rate, 4),
      dcr_ci_lower = round(dcr_ci["lower"], 4),
      dcr_ci_upper = round(dcr_ci["upper"], 4)
    )
  }

  # Difference in ORR (Active - Control)
  orr_exp <- results[["1"]]$orr_rate
  orr_ctrl <- results[["0"]]$orr_rate
  orr_diff <- orr_exp - orr_ctrl

  # Fisher exact test
  fisher_data <- matrix(c(
    results[["1"]]$orr_n, results[["1"]]$n_total - results[["1"]]$orr_n,
    results[["0"]]$orr_n, results[["0"]]$n_total - results[["0"]]$orr_n
  ), nrow = 2)
  fisher_test <- fisher.test(fisher_data)
  fisher_p <- round(fisher_test$p.value, 6)

  # Chi-square test
  chi_test <- chisq.test(fisher_data)
  chi_p <- round(chi_test$p.value, 6)

  # 95% CI for difference (Wald with continuity correction)
  n1 <- results[["1"]]$n_total
  n0 <- results[["0"]]$n_total
  se_diff <- sqrt(orr_exp * (1 - orr_exp) / n1 + orr_ctrl * (1 - orr_ctrl) / n0)
  diff_ci_lower <- round(orr_diff - 1.96 * se_diff, 4)
  diff_ci_upper <- round(orr_diff + 1.96 * se_diff, 4)

  list(
    by_arm = results,
    orr_difference = round(orr_diff, 4),
    orr_diff_ci_lower = diff_ci_lower,
    orr_diff_ci_upper = diff_ci_upper,
    fisher_exact_p = fisher_p,
    chi_square_p = chi_p,
    bor_distribution = lapply(split(bor_dist, bor_dist$BOR), function(d) {
      list(
        BOR = unique(d$BOR),
        n_control = as.integer(d$n[d$TRT01PN == 0]),
        n_experimental = as.integer(d$n[d$TRT01PN == 1])
      )
    })
  )
}

# ─────────────────────────────────────────────────────
# ARS Output Envelope
# ─────────────────────────────────────────────────────

write_ars_output <- function(results, filepath) {
  ars <- list(
    reportingEvent = list(
      id = "TC-025-BOR",
      name = "Best Overall Response Summary",
      version = "1.0"
    ),
    analysisResults = list(
      list(
        id = "TC-025-BOR-001",
        analysisId = "BOR-SUMMARY",
        method = "ClopperPearson",
        purpose = "Summarize best overall response per RECIST 1.1",
        results = results
      )
    ),
    referencingMetadata = list(
      dataset = "ADRS",
      paramcd = "BOR",
      population = "ITT"
    )
  )
  writeLines(jsonlite::toJSON(ars, auto_unbox = TRUE, pretty = TRUE), filepath)
  cat(sprintf("Wrote ARS output to: %s\n", filepath))
}

# ─────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────

main <- function() {
  args <- parse_args()

  if (!is.na(args$data) && nzchar(args$data)) {
    data <- read_shared_data(args$data)
  } else {
    data <- generate_bor_data(seed = args$seed, n_subjects = args$n)
  }

  result <- list(
    test_case_id = "TC-025",
    endpoint = "Best Overall Response",
    population = "ITT",
    summary = compute_bor_summary(data),
    language = "R",
    version = "1.0"
  )

  if (!is.na(args$output) && nzchar(args$output)) {
    write_output(result, args$output)
  } else {
    print_output(result)
  }

  if (!is.na(args$ars_output) && nzchar(args$ars_output)) {
    write_ars_output(result, args$ars_output)
  }
}

main()
