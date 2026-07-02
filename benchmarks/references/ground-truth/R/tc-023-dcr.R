#!/usr/bin/env Rscript
# TC-023 Ground Truth: Disease Control Rate (DCR)
# Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark
#
# DCR is defined as the proportion of subjects with disease control,
# where disease control = CR + PR + SD (best overall response).
#
# Key difference from TC-020 (ORR):
#   ORR (TC-020): CR + PR rate
#   DCR (TC-023): CR + PR + SD rate (broader benefit measure)
#
# This tests:
#   1. Correct response categorization (CR/PR/SD = disease control)
#   2. Binomial proportion CI (Wilson score interval)
#   3. Risk difference with CI between arms
#   4. Cross-TFL consistency: DCR >= ORR (every responder also has disease control)
#
# Dependencies: dplyr, jsonlite, stats
# Usage: Rscript tc-023-dcr.R --seed 42 --n 200 --output results.json

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
    output = get_arg("--output", NA),
    ars_output = get_arg("--ars-output", NA)
  )
}

# ─────────────────────────────────────────────────────
# Synthetic Tumor Response Dataset Generation
# ─────────────────────────────────────────────────────
# Generates the same data structure as TC-020, ensuring cross-TFL
# consistency between ORR and DCR.

generate_tumor_response <- function(seed = 42, n_subjects = 200) {
  set.seed(seed)

  trt <- sample(0:1, n_subjects, replace = TRUE)

  # Subgroups: SEX, AGEGR1, ECOG
  sex <- sample(c("Male", "Female"), n_subjects, replace = TRUE, prob = c(0.55, 0.45))
  age <- round(rnorm(n_subjects, mean = 58, sd = 12))
  agegr1 <- ifelse(age < 65, "<65", ">=65")
  ecog <- sample(0:1, n_subjects, replace = TRUE, prob = c(0.6, 0.4))

  # Response probability depends on treatment and ECOG
  # Same probabilities as TC-020 for cross-TFL consistency
  orr_prob <- ifelse(trt == 1,
                     ifelse(ecog == 0, 0.45, 0.30),
                     ifelse(ecog == 0, 0.25, 0.15))

  is_responder <- rbinom(n_subjects, 1, orr_prob)
  is_cr <- ifelse(is_responder == 1, rbinom(n_subjects, 1, 0.3), 0)
  bor <- ifelse(is_cr == 1, "CR",
                ifelse(is_responder == 1, "PR",
                       sample(c("SD", "PD"), n_subjects, replace = TRUE, prob = c(0.4, 0.6))))

  # ITTFL flag
  ittfl <- ifelse(runif(n_subjects) < 0.95, "Y", "N")

  data.frame(
    USUBJID = sprintf("SUBJ-%04d", 1:n_subjects),
    STUDYID = "BENCHMARK-001",
    TRT01PN = trt,
    TRT01A = ifelse(trt == 0, "Control", "Experimental"),
    SEX = sex,
    AGEGR1 = agegr1,
    ECOG = ecog,
    BOR = bor,
    AVAL_ORR = ifelse(bor %in% c("CR", "PR"), 1, 0),
    AVAL_DCR = ifelse(bor %in% c("CR", "PR", "SD"), 1, 0),
    ITTFL = ittfl,
    stringsAsFactors = FALSE
  )
}

# ─────────────────────────────────────────────────────
# Wilson score confidence interval
# ─────────────────────────────────────────────────────

wilson_ci <- function(x, n, conf = 0.95) {
  z <- qnorm(1 - (1 - conf) / 2)
  p <- x / n
  denom <- 1 + z^2 / n
  center <- (p + z^2 / (2 * n)) / denom
  margin <- z * sqrt(p * (1 - p) / n + z^2 / (4 * n^2)) / denom
  c(lower = center - margin, upper = center + margin)
}

# ─────────────────────────────────────────────────────
# TC-023 Core Computation
# ─────────────────────────────────────────────────────

compute_dcr <- function(data) {
  # Filter to ITT population
  data <- data %>% filter(ITTFL == "Y")

  overall_exp <- data[data$TRT01PN == 1, ]
  overall_ctrl <- data[data$TRT01PN == 0, ]

  # Overall DCR
  dcr_exp <- sum(overall_exp$AVAL_DCR) / nrow(overall_exp) * 100
  dcr_ctrl <- sum(overall_ctrl$AVAL_DCR) / nrow(overall_ctrl) * 100

  ci_exp <- wilson_ci(sum(overall_exp$AVAL_DCR), nrow(overall_exp))
  ci_ctrl <- wilson_ci(sum(overall_ctrl$AVAL_DCR), nrow(overall_ctrl))

  # Risk difference
  diff <- dcr_exp - dcr_ctrl
  se_diff <- sqrt((dcr_exp / 100 * (1 - dcr_exp / 100)) / nrow(overall_exp) +
                   (dcr_ctrl / 100 * (1 - dcr_ctrl / 100)) / nrow(overall_ctrl)) * 100
  z <- qnorm(0.975)
  diff_ci_lower <- round(diff - z * se_diff, 1)
  diff_ci_upper <- round(diff + z * se_diff, 1)

  # Disease control counts by BOR category
  bor_counts_exp <- overall_exp %>%
    group_by(BOR) %>%
    summarise(n = n(), .groups = "drop") %>%
    arrange(desc(n))
  bor_counts_ctrl <- overall_ctrl %>%
    group_by(BOR) %>%
    summarise(n = n(), .groups = "drop") %>%
    arrange(desc(n))

  overall <- list(
    dcr_experimental = round(dcr_exp, 1),
    dcr_control = round(dcr_ctrl, 1),
    n_experimental = nrow(overall_exp),
    n_control = nrow(overall_ctrl),
    disease_controlled_exp = sum(overall_exp$AVAL_DCR),
    disease_controlled_ctrl = sum(overall_ctrl$AVAL_DCR),
    ci_lower_experimental = round(ci_exp["lower"] * 100, 1),
    ci_upper_experimental = round(ci_exp["upper"] * 100, 1),
    ci_lower_control = round(ci_ctrl["lower"] * 100, 1),
    ci_upper_control = round(ci_ctrl["upper"] * 100, 1),
    dcr_difference = round(diff, 1),
    diff_ci_lower = diff_ci_lower,
    diff_ci_upper = diff_ci_upper
  )

  # Subgroup-level DCR (same subgroups as TC-020)
  subgroups <- c("SEX", "AGEGR1", "ECOG")
  subgroup_labels <- list(
    SEX = c("Male", "Female"),
    AGEGR1 = c("<65", ">=65"),
    ECOG = c("0", "1")
  )

  subgroup_results <- list()
  for (sg in subgroups) {
    levels <- subgroup_labels[[sg]]
    for (lvl in levels) {
      sg_exp <- data[data$TRT01PN == 1 & data[[sg]] == lvl, ]
      sg_ctrl <- data[data$TRT01PN == 0 & data[[sg]] == lvl, ]

      if (nrow(sg_exp) == 0 || nrow(sg_ctrl) == 0) next

      dcr_e <- sum(sg_exp$AVAL_DCR) / nrow(sg_exp) * 100
      dcr_c <- sum(sg_ctrl$AVAL_DCR) / nrow(sg_ctrl) * 100
      ci_e <- wilson_ci(sum(sg_exp$AVAL_DCR), nrow(sg_exp))
      ci_c <- wilson_ci(sum(sg_ctrl$AVAL_DCR), nrow(sg_ctrl))

      sg_diff <- dcr_e - dcr_c
      sg_se <- sqrt((dcr_e / 100 * (1 - dcr_e / 100)) / nrow(sg_exp) +
                     (dcr_c / 100 * (1 - dcr_c / 100)) / nrow(sg_ctrl)) * 100
      sg_diff_ci_lower <- round(sg_diff - z * sg_se, 1)
      sg_diff_ci_upper <- round(sg_diff + z * sg_se, 1)

      subgroup_results <- c(subgroup_results, list(list(
        subgroup = sg,
        level = lvl,
        dcr_experimental = round(dcr_e, 1),
        dcr_control = round(dcr_c, 1),
        n_experimental = nrow(sg_exp),
        n_control = nrow(sg_ctrl),
        disease_controlled_exp = sum(sg_exp$AVAL_DCR),
        disease_controlled_ctrl = sum(sg_ctrl$AVAL_DCR),
        ci_lower_experimental = round(ci_e["lower"] * 100, 1),
        ci_upper_experimental = round(ci_e["upper"] * 100, 1),
        ci_lower_control = round(ci_c["lower"] * 100, 1),
        ci_upper_control = round(ci_c["upper"] * 100, 1),
        dcr_difference = round(sg_diff, 1),
        diff_ci_lower = sg_diff_ci_lower,
        diff_ci_upper = sg_diff_ci_upper
      )))
    }
  }

  # BOR distribution by arm
  bor_distribution <- list()
  for (arm_val in c(1, 0)) {
    arm_label <- ifelse(arm_val == 1, "Experimental", "Control")
    arm_data <- data[data$TRT01PN == arm_val, ]
    for (bor_cat in c("CR", "PR", "SD", "PD")) {
      n_cat <- sum(arm_data$BOR == bor_cat)
      bor_distribution <- c(bor_distribution, list(list(
        arm = arm_label,
        bor = bor_cat,
        n = n_cat,
        pct = round(n_cat / nrow(arm_data) * 100, 1)
      )))
    }
  }

  list(
    test_case_id = "TC-023",
    variant_id = NA,
    language = "R",
    package = "stats",
    package_version = R.version$major,
    overall = overall,
    subgroups = subgroup_results,
    bor_distribution = bor_distribution,
    endpoint = "DCR",
    population = "ITT",
    dcr_definition = "CR + PR + SD",
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

  cat(sprintf("TC-023: Disease Control Rate (R) — seed=%d, n=%d\n", seed, n))

  if (!is.na(opts$data)) {
    data <- read_shared_data(opts$data)
    cat(sprintf("Loaded shared tumor response data with %d subjects\n", nrow(data)))
  } else {
    data <- generate_tumor_response(seed = seed, n_subjects = n)
    cat(sprintf("Generated tumor response data with %d subjects\n", nrow(data)))
  }

  result <- compute_dcr(data)
  result$seed <- seed
  result$variant_id <- paste0("v", seed)

  cat("\n──────────────────────────────────────────────\n")
  cat(sprintf("DCR Definition: %s\n", result$dcr_definition))
  cat(sprintf("Overall DCR:   Exp=%.1f%%, Ctrl=%.1f%%, Diff=%.1f%%\n",
              result$overall$dcr_experimental, result$overall$dcr_control,
              result$overall$dcr_difference))
  cat(sprintf("95%% CI (Exp):   (%.1f, %.1f)\n",
              result$overall$ci_lower_experimental, result$overall$ci_upper_experimental))
  cat(sprintf("95%% CI (Ctrl):  (%.1f, %.1f)\n",
              result$overall$ci_lower_control, result$overall$ci_upper_control))
  cat(sprintf("Subgroups analyzed: %d\n", length(result$subgroups)))
  cat("──────────────────────────────────────────────\n")

  print_output(result)

  if (!is.na(opts$output)) {
    write_output(result, opts$output)
  }

  # ARS-compatible output envelope (CDISC ARS v1.0)
  if (!is.na(opts$ars_output)) {
    ars_envelope <- list(
      ars_version = "1.0",
      analysisResult = list(
        id = "TC-023",
        version = "1.0",
        analysisReason = "Secondary efficacy endpoint: disease control rate",
        analysisMethod = list(
          name = "Binomial proportion with Wilson CI",
          codeTemplate = "sum(BOR %in% c('CR','PR','SD')) / n * 100",
          parameters = list(
            ci_method = "Wilson score",
            alpha = 0.05,
            dcr_definition = "CR + PR + SD",
            risk_difference_ci = "normal approximation"
          )
        ),
        analysisVariables = list(
          list(name = "BOR", dataset = "ADRS", role = "best overall response"),
          list(name = "TRT01A", dataset = "ADSL", role = "treatment"),
          list(name = "ITTFL", dataset = "ADSL", role = "population flag")
        ),
        analysisPopulation = list(
          name = "ITT",
          filter = "ITTFL = 'Y'"
        ),
        analysisDataset = "ADRS",
        resultGroups = list(
          list(id = "Experimental",
               n = result$overall$n_experimental,
               events = result$overall$disease_controlled_exp),
          list(id = "Control",
               n = result$overall$n_control,
               events = result$overall$disease_controlled_ctrl)
        ),
        documentation = "DCR = CR+PR+SD rate with Wilson CI; risk difference with normal approximation CI",
        analysisResultsData = list(
          statistics = list(
            list(name = "dcr_experimental", value = result$overall$dcr_experimental, unit = "percent"),
            list(name = "dcr_control", value = result$overall$dcr_control, unit = "percent"),
            list(name = "dcr_difference", value = result$overall$dcr_difference, unit = "percent"),
            list(name = "ci_lower_experimental", value = result$overall$ci_lower_experimental),
            list(name = "ci_upper_experimental", value = result$overall$ci_upper_experimental),
            list(name = "ci_lower_control", value = result$overall$ci_lower_control),
            list(name = "ci_upper_control", value = result$overall$ci_upper_control),
            list(name = "diff_ci_lower", value = result$overall$diff_ci_lower),
            list(name = "diff_ci_upper", value = result$overall$diff_ci_upper),
            list(name = "n_experimental", value = result$overall$n_experimental),
            list(name = "n_control", value = result$overall$n_control)
          )
        )
      )
    )
    ars_json <- jsonlite::toJSON(ars_envelope, auto_unbox = TRUE, pretty = TRUE)
    writeLines(ars_json, opts$ars_output)
    cat(sprintf("Wrote ARS-compatible output to: %s\n", opts$ars_output))
  }
}
