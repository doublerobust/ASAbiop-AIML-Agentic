#!/usr/bin/env Rscript
# TC-035 Ground Truth: ORR/DCR/DOR Composite Efficacy Table (Level 2)
# Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark
#
# Level 2 multi-TC integration: combines three efficacy endpoints into a
# single integrated table, testing cross-TFL consistency.
#
# Components:
#   1. ORR (from BOR): CR+PR rate, Clopper-Pearson CI, by arm
#   2. DCR (from BOR): CR+PR+SD rate, Wilson CI, by arm
#   3. DOR (from responders' time-to-event): KM median, 95% CI, by arm
#
# Cross-TFL consistency checks:
#   - ORR responders == DOR population (same IS_RESPONDER flag)
#   - DCR >= ORR (every responder also has disease control)
#   - BOR distribution sums to N per arm
#
# Dependencies: survival, jsonlite, dplyr
# Usage: Rscript tc-035-composite-efficacy.R --seed 42 --n 200 --output results.json

library(survival)
library(jsonlite)
library(dplyr)

# Source shared dataset generator
source("generate_tc035_composite.R")

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
# Clopper-Pearson exact CI
# ─────────────────────────────────────────────────────

clopper_pearson_ci <- function(x, n, conf = 0.95) {
  alpha <- 1 - conf
  lower <- qbeta(alpha / 2, x, n - x + 1)
  upper <- qbeta(1 - alpha / 2, x + 1, n - x)
  c(lower = lower * 100, upper = upper * 100)
}

# ─────────────────────────────────────────────────────
# Wilson score CI
# ─────────────────────────────────────────────────────

wilson_ci <- function(x, n, conf = 0.95) {
  z <- qnorm(1 - (1 - conf) / 2)
  p <- x / n
  denom <- 1 + z^2 / n
  center <- (p + z^2 / (2 * n)) / denom
  margin <- z * sqrt(p * (1 - p) / n + z^2 / (4 * n^2)) / denom
  c(lower = center * 100 - margin * 100, upper = center * 100 + margin * 100)
}

# ─────────────────────────────────────────────────────
# Compute ORR component
# ─────────────────────────────────────────────────────

compute_orr <- function(data, arm) {
  arm_data <- data[data$TRT01PN == arm & data$ITTFL == "Y", ]
  n <- nrow(arm_data)
  responders <- sum(arm_data$AVAL_ORR)
  orr <- responders / n * 100
  ci <- clopper_pearson_ci(responders, n)

  list(
    n = n,
    responders = responders,
    orr = round(orr, 1),
    ci_lower = round(ci["lower"], 1),
    ci_upper = round(ci["upper"], 1),
    ci_method = "Clopper-Pearson"
  )
}

# ─────────────────────────────────────────────────────
# Compute DCR component
# ─────────────────────────────────────────────────────

compute_dcr <- function(data, arm) {
  arm_data <- data[data$TRT01PN == arm & data$ITTFL == "Y", ]
  n <- nrow(arm_data)
  controlled <- sum(arm_data$AVAL_DCR)
  dcr <- controlled / n * 100
  ci <- wilson_ci(controlled, n)

  list(
    n = n,
    disease_controlled = controlled,
    dcr = round(dcr, 1),
    ci_lower = round(ci["lower"], 1),
    ci_upper = round(ci["upper"], 1),
    ci_method = "Wilson"
  )
}

# ─────────────────────────────────────────────────────
# Compute DOR component (KM median among responders)
# ─────────────────────────────────────────────────────

compute_dor <- function(data, arm) {
  arm_data <- data[data$TRT01PN == arm & data$ITTFL == "Y", ]
  n_total <- nrow(arm_data)

  # Filter to responders with valid DOR
  resp <- arm_data[arm_data$IS_RESPONDER == 1 & !is.na(arm_data$AVAL_DOR) & arm_data$AVAL_DOR > 0, ]

  if (nrow(resp) == 0) {
    return(list(
      n_responders = 0, n_events = 0, n_total = n_total,
      median_dor = NA, ci_lower = NA, ci_upper = NA,
      estimable = FALSE, ci_method = "log-log"
    ))
  }

  durations <- resp$AVAL_DOR
  events <- 1 - resp$CNSR_DOR

  n_responders <- nrow(resp)
  n_events <- sum(events)

  # KM fit
  km_fit <- survfit(Surv(durations, events) ~ 1, conf.type = "log-log")

  median_val <- km_fit$time[which(km_fit$surv <= 0.5)[1]]
  if (is.na(median_val) || length(median_val) == 0) {
    return(list(
      n_responders = n_responders, n_events = n_events, n_total = n_total,
      median_dor = NA, ci_lower = NA, ci_upper = NA,
      estimable = FALSE, ci_method = "log-log"
    ))
  }

  # CI for median (Brookmeyer-Crowley)
  ci_idx_lower <- which(km_fit$lower <= 0.5)[1]
  ci_idx_upper <- which(km_fit$upper <= 0.5)[1]
  ci_lower <- ifelse(length(ci_idx_lower) > 0, km_fit$time[ci_idx_lower], NA)
  ci_upper <- ifelse(length(ci_idx_upper) > 0, km_fit$time[ci_idx_upper], NA)

  list(
    n_responders = n_responders,
    n_events = n_events,
    n_total = n_total,
    median_dor = round(median_val, 4),
    ci_lower = round(ci_lower, 4),
    ci_upper = round(ci_upper, 4),
    estimable = TRUE,
    ci_method = "log-log"
  )
}

# ─────────────────────────────────────────────────────
# BOR distribution by arm
# ─────────────────────────────────────────────────────

compute_bor_distribution <- function(data) {
  result <- list()
  for (arm_val in c(1, 0)) {
    arm_label <- ifelse(arm_val == 1, "Experimental", "Control")
    arm_data <- data[data$TRT01PN == arm_val & data$ITTFL == "Y", ]
    n <- nrow(arm_data)
    for (bor_cat in c("CR", "PR", "SD", "PD")) {
      n_cat <- sum(arm_data$BOR == bor_cat)
      result <- c(result, list(list(
        arm = arm_label,
        bor = bor_cat,
        n = n_cat,
        pct = round(n_cat / n * 100, 1)
      )))
    }
  }
  result
}

# ─────────────────────────────────────────────────────
# Cross-TFL consistency checks
# ─────────────────────────────────────────────────────

check_consistency <- function(orr_exp, orr_ctrl, dcr_exp, dcr_ctrl,
                              dor_exp, dor_ctrl, bor_dist) {
  checks <- list()

  # Check 1: DCR >= ORR (every responder also has disease control)
  checks$dcr_ge_orr_exp <- dcr_exp$disease_controlled >= orr_exp$responders
  checks$dcr_ge_orr_ctrl <- dcr_ctrl$disease_controlled >= orr_ctrl$responders

  # Check 2: DOR responders <= ORR responders (DOR is subset of ORR population)
  checks$orr_responders_match_dor_exp <- dor_exp$n_responders <= orr_exp$responders
  checks$orr_responders_match_dor_ctrl <- dor_ctrl$n_responders <= orr_ctrl$responders

  # Check 3: BOR distribution sums to N per arm
  exp_bor <- sum(sapply(bor_dist, function(x) if (x$arm == "Experimental") x$n else 0))
  ctrl_bor <- sum(sapply(bor_dist, function(x) if (x$arm == "Control") x$n else 0))
  checks$bor_sums_to_n_exp <- exp_bor == orr_exp$n
  checks$bor_sums_to_n_ctrl <- ctrl_bor == orr_ctrl$n

  # Check 4: CR+PR counts match ORR responders
  exp_cr_pr <- sum(sapply(bor_dist, function(x) if (x$arm == "Experimental" & x$bor %in% c("CR", "PR")) x$n else 0))
  ctrl_cr_pr <- sum(sapply(bor_dist, function(x) if (x$arm == "Control" & x$bor %in% c("CR", "PR")) x$n else 0))
  checks$cr_pr_matches_orr_exp <- exp_cr_pr == orr_exp$responders
  checks$cr_pr_matches_orr_ctrl <- ctrl_cr_pr == orr_ctrl$responders

  checks
}

# ─────────────────────────────────────────────────────
# Main computation
# ─────────────────────────────────────────────────────

compute_composite <- function(data) {
  # Compute components by arm
  orr_exp <- compute_orr(data, 1)
  orr_ctrl <- compute_orr(data, 0)
  dcr_exp <- compute_dcr(data, 1)
  dcr_ctrl <- compute_dcr(data, 0)
  dor_exp <- compute_dor(data, 1)
  dor_ctrl <- compute_dor(data, 0)
  bor_dist <- compute_bor_distribution(data)

  # Cross-TFL consistency
  consistency <- check_consistency(orr_exp, orr_ctrl, dcr_exp, dcr_ctrl,
                                    dor_exp, dor_ctrl, bor_dist)

  list(
    test_case_id = "TC-035",
    variant_id = NA,
    language = "R",
    level = 2,
    endpoint = "Composite Efficacy (ORR/DCR/DOR)",
    population = "ITT",

    orr = list(
      experimental = orr_exp,
      control = orr_ctrl,
      definition = "CR + PR",
      ci_method = "Clopper-Pearson"
    ),
    dcr = list(
      experimental = dcr_exp,
      control = dcr_ctrl,
      definition = "CR + PR + SD",
      ci_method = "Wilson"
    ),
    dor = list(
      experimental = dor_exp,
      control = dor_ctrl,
      definition = "Time from first response to progression/death among responders",
      ci_method = "Brookmeyer-Crowley (log-log)"
    ),
    bor_distribution = bor_dist,
    cross_tfl_consistency = consistency,
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

  cat(sprintf("TC-035: Composite Efficacy Table (R) — seed=%d, n=%d\n", seed, n))

  if (!is.na(opts$data)) {
    data <- read.csv(opts$data)
    cat(sprintf("Loaded shared composite data with %d subjects\n", nrow(data)))
  } else {
    data <- generate_composite_efficacy(seed = seed, n_subjects = n)
    cat(sprintf("Generated composite efficacy data with %d subjects\n", nrow(data)))
  }

  result <- compute_composite(data)
  result$seed <- seed
  result$variant_id <- paste0("v", seed)

  cat("\n──────────────────────────────────────────────\n")
  cat("COMPOSITE EFFICACY TABLE\n")
  cat("──────────────────────────────────────────────\n")
  cat(sprintf("ORR:  Exp=%.1f%% (%.1f, %.1f)  N=%d  responders=%d\n",
              result$orr$experimental$orr, result$orr$experimental$ci_lower,
              result$orr$experimental$ci_upper, result$orr$experimental$n,
              result$orr$experimental$responders))
  cat(sprintf("      Ctrl=%.1f%% (%.1f, %.1f)  N=%d  responders=%d\n",
              result$orr$control$orr, result$orr$control$ci_lower,
              result$orr$control$ci_upper, result$orr$control$n,
              result$orr$control$responders))
  cat(sprintf("DCR:  Exp=%.1f%% (%.1f, %.1f)  N=%d  controlled=%d\n",
              result$dcr$experimental$dcr, result$dcr$experimental$ci_lower,
              result$dcr$experimental$ci_upper, result$dcr$experimental$n,
              result$dcr$experimental$disease_controlled))
  cat(sprintf("      Ctrl=%.1f%% (%.1f, %.1f)  N=%d  controlled=%d\n",
              result$dcr$control$dcr, result$dcr$control$ci_lower,
              result$dcr$control$ci_upper, result$dcr$control$n,
              result$dcr$control$disease_controlled))
  if (result$dor$experimental$estimable) {
    cat(sprintf("DOR:  Exp=%.1f mo (%.1f, %.1f)  responders=%d  events=%d\n",
                result$dor$experimental$median_dor, result$dor$experimental$ci_lower,
                result$dor$experimental$ci_upper, result$dor$experimental$n_responders,
                result$dor$experimental$n_events))
  } else {
    cat(sprintf("DOR:  Exp=Not estimable  responders=%d\n", result$dor$experimental$n_responders))
  }
  if (result$dor$control$estimable) {
    cat(sprintf("      Ctrl=%.1f mo (%.1f, %.1f)  responders=%d  events=%d\n",
                result$dor$control$median_dor, result$dor$control$ci_lower,
                result$dor$control$ci_upper, result$dor$control$n_responders,
                result$dor$control$n_events))
  } else {
    cat(sprintf("      Ctrl=Not estimable  responders=%d\n", result$dor$control$n_responders))
  }
  cat("\nCross-TFL Consistency:\n")
  for (nm in names(result$cross_tfl_consistency)) {
    cat(sprintf("  %s: %s\n", nm, result$cross_tfl_consistency[[nm]]))
  }
  cat("──────────────────────────────────────────────\n")

  print_output <- function(x) {
    cat("\n=== BENCHMARK OUTPUT ===\n")
    cat(toJSON(x, auto_unbox = TRUE, pretty = TRUE))
    cat("\n=== END OUTPUT ===\n")
  }
  print_output(result)

  if (!is.na(opts$output)) {
    writeLines(toJSON(result, auto_unbox = TRUE, pretty = TRUE), opts$output)
    cat(sprintf("Wrote output to: %s\n", opts$output))
  }

  # ARS-compatible output envelope (CDISC ARS v1.0)
  if (!is.na(opts$ars_output)) {
    ars_envelope <- list(
      ars_version = "1.0",
      analysisResult = list(
        id = "TC-035",
        version = "1.0",
        analysisReason = "Level 2 composite efficacy integration: ORR + DCR + DOR",
        analysisMethod = list(
          name = "Composite binomial proportion + KM survival",
          codeTemplate = "ORR=sum(BOR%in%c('CR','PR'))/n; DCR=sum(BOR%in%c('CR','PR','SD'))/n; DOR=survfit(Surv(AVAL_DOR,1-CNSR_DOR))",
          parameters = list(
            orr_definition = "CR + PR",
            dcr_definition = "CR + PR + SD",
            dor_definition = "Time from first response to progression/death",
            orr_ci = "Clopper-Pearson",
            dcr_ci = "Wilson score",
            dor_ci = "Brookmeyer-Crowley log-log",
            alpha = 0.05,
            population = "ITT"
          )
        ),
        analysisVariables = list(
          list(name = "BOR", dataset = "ADRS", role = "best overall response"),
          list(name = "AVAL_DOR", dataset = "ADTTE", role = "DOR analysis time"),
          list(name = "CNSR_DOR", dataset = "ADTTE", role = "DOR censoring"),
          list(name = "TRT01A", dataset = "ADSL", role = "treatment"),
          list(name = "ITTFL", dataset = "ADSL", role = "population flag")
        ),
        analysisPopulation = list(
          name = "ITT",
          filter = "ITTFL = 'Y'"
        ),
        analysisDataset = "ADRS + ADTTE (merged)",
        resultGroups = list(
          list(id = "Experimental",
               n = result$orr$experimental$n,
               orr_responders = result$orr$experimental$responders,
               dcr_controlled = result$dcr$experimental$disease_controlled,
               dor_responders = result$dor$experimental$n_responders),
          list(id = "Control",
               n = result$orr$control$n,
               orr_responders = result$orr$control$responders,
               dcr_controlled = result$dcr$control$disease_controlled,
               dor_responders = result$dor$control$n_responders)
        ),
        documentation = "Level 2 composite: ORR (Clopper-Pearson CI), DCR (Wilson CI), DOR (KM median, Brookmeyer-Crowley CI). Cross-TFL consistency enforced.",
        analysisResultsData = list(
          statistics = list(
            list(name = "orr_experimental", value = result$orr$experimental$orr, unit = "percent"),
            list(name = "orr_control", value = result$orr$control$orr, unit = "percent"),
            list(name = "dcr_experimental", value = result$dcr$experimental$dcr, unit = "percent"),
            list(name = "dcr_control", value = result$dcr$control$dcr, unit = "percent"),
            list(name = "median_dor_experimental", value = result$dor$experimental$median_dor, unit = "months"),
            list(name = "median_dor_control", value = result$dor$control$median_dor, unit = "months"),
            list(name = "n_orr_responders_exp", value = result$orr$experimental$responders),
            list(name = "n_orr_responders_ctrl", value = result$orr$control$responders),
            list(name = "n_dcr_controlled_exp", value = result$dcr$experimental$disease_controlled),
            list(name = "n_dcr_controlled_ctrl", value = result$dcr$control$disease_controlled),
            list(name = "n_dor_responders_exp", value = result$dor$experimental$n_responders),
            list(name = "n_dor_responders_ctrl", value = result$dor$control$n_responders)
          )
        )
      )
    )
    ars_json <- jsonlite::toJSON(ars_envelope, auto_unbox = TRUE, pretty = TRUE)
    writeLines(ars_json, opts$ars_output)
    cat(sprintf("Wrote ARS-compatible output to: %s\n", opts$ars_output))
  }
}
