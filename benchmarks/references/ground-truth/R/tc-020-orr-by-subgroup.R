#!/usr/bin/env Rscript
# TC-020 Ground Truth: ORR (Objective Response Rate) by Subgroup
# Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark
#
# Computes ORR (CR+PR rate) by pre-specified subgroups with:
#   - Subgroup-level ORR (n/N, %) for each arm
#   - Cochran-Mantel-Haenszel chi-square test for treatment-by-subgroup interaction
#   - Forest-plot-ready output: ORR difference (Exp - Ctrl) with 95% CI per subgroup
#
# Dependencies: dplyr, jsonlite, stats
# Usage: Rscript tc-020-orr-by-subgroup.R --seed 42 --n 200 --output results.json

library(dplyr)
library(jsonlite)
library(stats)

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
    output = get_arg("--output", NA)
  )
}

# ─────────────────────────────────────────────────────
# Synthetic Tumor Response Dataset Generation
# ─────────────────────────────────────────────────────

generate_tumor_response <- function(seed = 42, n_subjects = 200) {
  set.seed(seed)

  trt <- sample(0:1, n_subjects, replace = TRUE)

  # Subgroups: SEX (Male/Female), AGEGR1 (<65/>=65), ECOG (0/1)
  sex <- sample(c("Male", "Female"), n_subjects, replace = TRUE, prob = c(0.55, 0.45))
  age <- round(rnorm(n_subjects, mean = 58, sd = 12))
  agegr1 <- ifelse(age < 65, "<65", ">=65")
  ecog <- sample(0:1, n_subjects, replace = TRUE, prob = c(0.6, 0.4))

  # Response probability depends on treatment and ECOG
  # Experimental: ORR ~45% (ECOG 0), ~30% (ECOG 1)
  # Control: ORR ~25% (ECOG 0), ~15% (ECOG 1)
  orr_prob <- ifelse(trt == 1,
                     ifelse(ecog == 0, 0.45, 0.30),
                     ifelse(ecog == 0, 0.25, 0.15))

  # Best overall response: CR, PR, SD, PD
  # Simplified: response = rbinom, then split CR vs PR
  is_responder <- rbinom(n_subjects, 1, orr_prob)
  # Among responders: ~30% CR, 70% PR
  is_cr <- ifelse(is_responder == 1, rbinom(n_subjects, 1, 0.3), 0)
  bor <- ifelse(is_cr == 1, "CR",
                ifelse(is_responder == 1, "PR",
                       sample(c("SD", "PD"), n_subjects, replace = TRUE, prob = c(0.4, 0.6))))

  data.frame(
    USUBJID = sprintf("SUBJ-%04d", 1:n_subjects),
    STUDYID = "BENCHMARK-001",
    TRT01PN = trt,
    TRT01A = ifelse(trt == 0, "Control", "Experimental"),
    SEX = sex,
    AGEGR1 = agegr1,
    ECOG = ecog,
    BOR = bor,
    AVAL = ifelse(bor %in% c("CR", "PR"), 1, 0),
    stringsAsFactors = FALSE
  )
}

# ─────────────────────────────────────────────────────
# TC-020 Core Computation
# ─────────────────────────────────────────────────────

compute_orr_by_subgroup <- function(data) {
  subgroups <- c("SEX", "AGEGR1", "ECOG")
  subgroup_labels <- list(
    SEX = c("Male", "Female"),
    AGEGR1 = c("<65", ">=65"),
    ECOG = c("0", "1")
  )

  # Overall ORR
  overall_exp <- data[data$TRT01PN == 1, ]
  overall_ctrl <- data[data$TRT01PN == 0, ]

  overall_orr_exp <- sum(overall_exp$AVAL) / nrow(overall_exp) * 100
  overall_orr_ctrl <- sum(overall_ctrl$AVAL) / nrow(overall_ctrl) * 100

  # Overall CI (Wilson interval)
  wilson_ci <- function(x, n, conf = 0.95) {
    z <- qnorm(1 - (1 - conf) / 2)
    p <- x / n
    denom <- 1 + z^2 / n
    center <- (p + z^2 / (2 * n)) / denom
    margin <- z * sqrt(p * (1 - p) / n + z^2 / (4 * n^2)) / denom
    c(lower = center - margin, upper = center + margin)
  }

  ci_exp <- wilson_ci(sum(overall_exp$AVAL), nrow(overall_exp))
  ci_ctrl <- wilson_ci(sum(overall_ctrl$AVAL), nrow(overall_ctrl))

  overall <- list(
    orr_experimental = round(overall_orr_exp, 1),
    orr_control = round(overall_orr_ctrl, 1),
    n_experimental = nrow(overall_exp),
    n_control = nrow(overall_ctrl),
    responders_experimental = sum(overall_exp$AVAL),
    responders_control = sum(overall_ctrl$AVAL),
    ci_lower_experimental = round(ci_exp["lower"] * 100, 1),
    ci_upper_experimental = round(ci_exp["upper"] * 100, 1),
    ci_lower_control = round(ci_ctrl["lower"] * 100, 1),
    ci_upper_control = round(ci_ctrl["upper"] * 100, 1),
    orr_difference = round(overall_orr_exp - overall_orr_ctrl, 1)
  )

  # Subgroup-level
  subgroup_results <- list()
  for (sg in subgroups) {
    levels <- subgroup_labels[[sg]]
    for (lvl in levels) {
      sg_exp <- data[data$TRT01PN == 1 & data[[sg]] == lvl, ]
      sg_ctrl <- data[data$TRT01PN == 0 & data[[sg]] == lvl, ]

      if (nrow(sg_exp) == 0 || nrow(sg_ctrl) == 0) next

      orr_e <- sum(sg_exp$AVAL) / nrow(sg_exp) * 100
      orr_c <- sum(sg_ctrl$AVAL) / nrow(sg_ctrl) * 100
      ci_e <- wilson_ci(sum(sg_exp$AVAL), nrow(sg_exp))
      ci_c <- wilson_ci(sum(sg_ctrl$AVAL), nrow(sg_ctrl))

      # Risk difference CI (normal approximation)
      diff <- orr_e - orr_c
      se_diff <- sqrt((orr_e / 100 * (1 - orr_e / 100)) / nrow(sg_exp) +
                       (orr_c / 100 * (1 - orr_c / 100)) / nrow(sg_ctrl)) * 100
      z <- qnorm(0.975)
      diff_ci_lower <- round(diff - z * se_diff, 1)
      diff_ci_upper <- round(diff + z * se_diff, 1)

      subgroup_results <- c(subgroup_results, list(list(
        subgroup = sg,
        level = lvl,
        orr_experimental = round(orr_e, 1),
        orr_control = round(orr_c, 1),
        n_experimental = nrow(sg_exp),
        n_control = nrow(sg_ctrl),
        responders_experimental = sum(sg_exp$AVAL),
        responders_control = sum(sg_ctrl$AVAL),
        ci_lower_experimental = round(ci_e["lower"] * 100, 1),
        ci_upper_experimental = round(ci_e["upper"] * 100, 1),
        ci_lower_control = round(ci_c["lower"] * 100, 1),
        ci_upper_control = round(ci_c["upper"] * 100, 1),
        orr_difference = round(diff, 1),
        diff_ci_lower = diff_ci_lower,
        diff_ci_upper = diff_ci_upper
      )))
    }
  }

  # Interaction p-value (CMH test for each subgroup)
  interaction_pvalues <- list()
  for (sg in subgroups) {
    # Create 2x2x2 table: treatment x response x subgroup
    tbl <- table(data$TRT01PN, data$AVAL, data[[sg]])
    if (all(dim(tbl) >= c(2, 2, 2))) {
      cmh <- mantelhaen.test(tbl)
      interaction_pvalues <- c(interaction_pvalues, list(list(
        subgroup = sg,
        cmh_p_value = round(cmh$p.value, 4),
        cmh_common_or = round(as.numeric(cmh$estimate), 4)
      )))
    }
  }

  list(
    test_case_id = "TC-020",
    variant_id = NA,
    language = "R",
    package = "stats",
    package_version = R.version$major,
    overall = overall,
    subgroups = subgroup_results,
    interaction_pvalues = interaction_pvalues,
    seed = NA
  )
}

# ─────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────

if (sys.nframe() == 0) {
  opts <- parse_args()
  seed <- opts$seed
  n <- opts$n

  cat(sprintf("TC-020: ORR by Subgroup (R) — seed=%d, n=%d\\n", seed, n))

  if (!is.na(opts$data)) {
    data <- read_shared_data(opts$data)
    cat(sprintf("Loaded shared tumor response data with %d subjects\\n", nrow(data)))
  } else {
    data <- generate_tumor_response(seed = seed, n_subjects = n)
    cat(sprintf("Generated tumor response data with %d subjects\\n", nrow(data)))
  }

  result <- compute_orr_by_subgroup(data)
  result$seed <- seed
  result$variant_id <- paste0("v", seed)

  cat("\\n──────────────────────────────────────────────\\n")
  cat(sprintf("Overall ORR:  Exp=%.1f%%, Ctrl=%.1f%%, Diff=%.1f%%\\n",
              result$overall$orr_experimental, result$overall$orr_control,
              result$overall$orr_difference))
  cat(sprintf("Subgroups analyzed: %d\\n", length(result$subgroups)))
  cat(sprintf("Interaction tests: %d\\n", length(result$interaction_pvalues)))
  cat("──────────────────────────────────────────────\\n")

  print_output(result)

  if (!is.na(opts$output)) {
    write_output(result, opts$output)
  }
}
