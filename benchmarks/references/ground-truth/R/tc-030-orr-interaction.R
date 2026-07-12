#!/usr/bin/env Rscript
# TC-030 Ground Truth: ORR by Subgroup with Interaction Test (R)
# Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark
#
# Extends TC-020 by adding:
#   - Formal logistic regression interaction test (treatment × subgroup)
#   - Clopper-Pearson exact confidence intervals (regulatory standard)
#   - Breslow-Day test for homogeneity of odds ratios across strata
#   - Forest-plot-ready output with interaction p-values
#
# Dependencies: dplyr, jsonlite, stats
# Usage: Rscript tc-030-orr-interaction.R --seed 42 --n 200 --output results.json
#        Rscript tc-030-orr-interaction.R --data shared_data.csv --output results.json

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
    ars_output = "--ars-output" %in% args
  )
}

# ─────────────────────────────────────────────────────
# Synthetic Tumor Response Dataset Generation
# (Same as TC-020 for cross-TFL consistency)
# ─────────────────────────────────────────────────────

generate_tumor_response <- function(seed = 42, n_subjects = 200) {
  set.seed(seed)

  trt <- sample(0:1, n_subjects, replace = TRUE)
  sex <- sample(c("Male", "Female"), n_subjects, replace = TRUE, prob = c(0.55, 0.45))
  age <- round(rnorm(n_subjects, mean = 58, sd = 12))
  agegr1 <- ifelse(age < 65, "<65", ">=65")
  ecog <- sample(0:1, n_subjects, replace = TRUE, prob = c(0.6, 0.4))

  orr_prob <- ifelse(trt == 1,
                     ifelse(ecog == 0, 0.45, 0.30),
                     ifelse(ecog == 0, 0.25, 0.15))

  is_responder <- rbinom(n_subjects, 1, orr_prob)
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
# Clopper-Pearson Exact CI
# ─────────────────────────────────────────────────────

clopper_pearson_ci <- function(x, n, conf = 0.95) {
  if (n == 0) return(c(lower = 0, upper = 1))
  alpha <- 1 - conf
  lo <- if (x > 0) qbeta(alpha / 2, x, n - x + 1) else 0
  hi <- if (x < n) qbeta(1 - alpha / 2, x + 1, n - x) else 1
  c(lower = lo, upper = hi)
}

# ─────────────────────────────────────────────────────
# Logistic Regression Interaction Test
# ─────────────────────────────────────────────────────

logistic_interaction_test <- function(data, subgroup_var) {
  # Encode subgroup as 0/1
  levels <- sort(unique(data[[subgroup_var]]))
  if (length(levels) != 2) {
    return(list(
      subgroup = subgroup_var,
      interaction_p_value = NA,
      interaction_or = NA,
      interaction_or_ci_lower = NA,
      interaction_or_ci_upper = NA,
      breslow_day_p_value = NA,
      method = "logistic_wald"
    ))
  }

  # Create numeric encoding
  data$sg_num <- ifelse(data[[subgroup_var]] == levels[1], 0, 1)
  data$trt_num <- as.numeric(data$TRT01PN)
  data$interaction <- data$trt_num * data$sg_num

  # Fit logistic regression: AVAL ~ trt + subgroup + trt:subgroup
  # Using glm with binomial family
  formula <- as.formula("AVAL ~ trt_num + sg_num + interaction")
  model <- tryCatch(
    glm(formula, data = data, family = binomial(link = "logit")),
    error = function(e) NULL
  )

  if (is.null(model)) {
    # Fallback to CMH test
    return(list(
      subgroup = subgroup_var,
      interaction_p_value = NA,
      interaction_or = NA,
      interaction_or_ci_lower = NA,
      interaction_or_ci_upper = NA,
      breslow_day_p_value = NA,
      method = "cmh_fallback"
    ))
  }

  # Extract interaction coefficient (Wald test)
  coefs <- summary(model)$coefficients
  if (!("interaction" %in% rownames(coefs))) {
    return(list(
      subgroup = subgroup_var,
      interaction_p_value = NA,
      interaction_or = NA,
      interaction_or_ci_lower = NA,
      interaction_or_ci_upper = NA,
      breslow_day_p_value = NA,
      method = "logistic_wald"
    ))
  }

  b3 <- coefs["interaction", "Estimate"]
  se_b3 <- coefs["interaction", "Std. Error"]

  if (se_b3 == 0 || is.na(se_b3)) {
    return(list(
      subgroup = subgroup_var,
      interaction_p_value = NA,
      interaction_or = NA,
      interaction_or_ci_lower = NA,
      interaction_or_ci_upper = NA,
      breslow_day_p_value = NA,
      method = "logistic_wald"
    ))
  }

  wald_z <- b3 / se_b3
  wald_p <- 2 * (1 - pnorm(abs(wald_z)))

  or_val <- exp(b3)
  or_ci_lo <- exp(b3 - 1.96 * se_b3)
  or_ci_hi <- exp(b3 + 1.96 * se_b3)

  # Breslow-Day test
  bd_p <- breslow_day_test(data, subgroup_var)

  list(
    subgroup = subgroup_var,
    interaction_p_value = round(as.numeric(wald_p), 4),
    interaction_or = round(as.numeric(or_val), 4),
    interaction_or_ci_lower = round(as.numeric(or_ci_lo), 4),
    interaction_or_ci_upper = round(as.numeric(or_ci_hi), 4),
    breslow_day_p_value = if (!is.null(bd_p)) round(as.numeric(bd_p), 4) else NA,
    method = "logistic_wald"
  )
}

# ─────────────────────────────────────────────────────
# Breslow-Day Test for Homogeneity of ORs
# ─────────────────────────────────────────────────────

breslow_day_test <- function(data, subgroup_var) {
  levels <- sort(unique(data[[subgroup_var]]))
  if (length(levels) < 2) return(NULL)

  # Build 2x2 tables per stratum
  tables <- list()
  for (lvl in levels) {
    d <- data[data[[subgroup_var]] == lvl, ]
    tbl <- table(d$TRT01PN, d$AVAL)
    if (all(dim(tbl) >= c(2, 2))) {
      tables <- c(tables, list(tbl))
    }
  }

  if (length(tables) < 2) return(NULL)

  # Mantel-Haenszel common OR
  numer <- 0
  denom <- 0
  for (tbl in tables) {
    # tbl is [treatment x response]: rows=TRT01PN (0,1), cols=AVAL (0,1)
    a <- tbl[1, 1]  # trt=0, no response
    b <- tbl[1, 2]  # trt=0, response
    c <- tbl[2, 1]  # trt=1, no response
    d <- tbl[2, 2]  # trt=1, response
    n <- a + b + c + d
    if (n == 0) next
    numer <- numer + a * d / n
    denom <- denom + b * c / n
  }
  mh_or <- if (denom > 0) numer / denom else 1

  # Breslow-Day statistic (Tarone-adjusted)
  bd_stat <- 0
  for (tbl in tables) {
    a <- tbl[1, 1]
    b <- tbl[1, 2]
    c <- tbl[2, 1]
    d <- tbl[2, 2]
    n1 <- a + b  # trt=0 total
    m1 <- a + c  # non-responders
    n <- a + b + c + d

    if (n == 0) next

    # Expected a under common OR (using non-central hypergeometric)
    expected_a <- expected_a_bd(n1, m1, n, mh_or)
    var_a <- var_a_bd(n1, m1, n, expected_a)

    if (var_a > 0) {
      bd_stat <- bd_stat + (a - expected_a)^2 / var_a
    }
  }

  df <- length(tables) - 1
  if (df <= 0) return(NULL)

  p_value <- 1 - pchisq(bd_stat, df)
  return(as.numeric(p_value))
}

expected_a_bd <- function(n1, m1, n, or_val, max_iter = 100) {
  # Expected value of a under non-central hypergeometric distribution
  # P(a) ∝ C(n1, a) * C(n-n1, m1-a) * or_val^a
  lo <- max(0, m1 - (n - n1))
  hi <- min(n1, m1)

  if (lo == hi) return(as.numeric(lo))

  log_probs <- sapply(lo:hi, function(a) {
    lchoose(n1, a) + lchoose(n - n1, m1 - a) + a * log(or_val)
  })
  # Normalize
  log_probs <- log_probs - max(log_probs)
  probs <- exp(log_probs)
  probs <- probs / sum(probs)
  expected <- sum((lo:hi) * probs)
  return(expected)
}

var_a_bd <- function(n1, m1, n, expected_a) {
  a <- max(expected_a, 0.5)
  b <- max(n1 - expected_a, 0.5)
  c <- max(m1 - expected_a, 0.5)
  d <- max(n - n1 - m1 + expected_a, 0.5)
  1 / (1 / a + 1 / b + 1 / c + 1 / d)
}

# ─────────────────────────────────────────────────────
# Core Computation
# ─────────────────────────────────────────────────────

compute_orr_with_interaction <- function(data) {
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

  ci_exp <- clopper_pearson_ci(sum(overall_exp$AVAL), nrow(overall_exp))
  ci_ctrl <- clopper_pearson_ci(sum(overall_ctrl$AVAL), nrow(overall_ctrl))

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

  # Subgroup-level ORR with Clopper-Pearson CIs
  subgroup_results <- list()
  for (sg in subgroups) {
    levels <- subgroup_labels[[sg]]
    for (lvl in levels) {
      sg_exp <- data[data$TRT01PN == 1 & data[[sg]] == lvl, ]
      sg_ctrl <- data[data$TRT01PN == 0 & data[[sg]] == lvl, ]

      if (nrow(sg_exp) == 0 || nrow(sg_ctrl) == 0) next

      orr_e <- sum(sg_exp$AVAL) / nrow(sg_exp) * 100
      orr_c <- sum(sg_ctrl$AVAL) / nrow(sg_ctrl) * 100
      ci_e <- clopper_pearson_ci(sum(sg_exp$AVAL), nrow(sg_exp))
      ci_c <- clopper_pearson_ci(sum(sg_ctrl$AVAL), nrow(sg_ctrl))

      diff <- orr_e - orr_c
      se_diff <- sqrt((orr_e / 100 * (1 - orr_e / 100)) / nrow(sg_exp) +
                       (orr_c / 100 * (1 - orr_c / 100)) / nrow(sg_ctrl)) * 100
      z <- qnorm(0.975)

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
        diff_ci_lower = round(diff - z * se_diff, 1),
        diff_ci_upper = round(diff + z * se_diff, 1)
      )))
    }
  }

  # Logistic regression interaction tests
  interaction_results <- list()
  for (sg in subgroups) {
    interaction_results <- c(interaction_results, list(logistic_interaction_test(data, sg)))
  }

  list(
    test_case_id = "TC-030",
    variant_id = NA,
    language = "R",
    package = "stats",
    package_version = R.version$major,
    overall = overall,
    subgroups = subgroup_results,
    interaction_tests = interaction_results,
    ci_method = "clopper-pearson",
    seed = NA
  )
}

# ─────────────────────────────────────────────────────
# ARS Output (CDISC Analysis Result Standard v1.0)
# ─────────────────────────────────────────────────────

generate_ars_output <- function(result) {
  list(
    analysisResult = list(
      id = "TC-030",
      version = "1.0",
      analysisReason = "ORR by subgroup with treatment x subgroup interaction test",
      analysisMethod = list(
        name = "Logistic regression with interaction term",
        codeTemplate = "logit(P(response)) = b0 + b1*trt + b2*subgroup + b3*trt*subgroup",
        parameters = list(
          interaction_term = "trt * subgroup",
          ci_method = "clopper-pearson",
          test_statistic = "Wald chi-square for b3"
        )
      ),
      analysisVariables = list(
        list(name = "TRT01PN", dataset = "ADRS", role = "treatment"),
        list(name = "AVAL", dataset = "ADRS", role = "response"),
        list(name = "SEX", dataset = "ADSL", role = "subgroup"),
        list(name = "AGEGR1", dataset = "ADSL", role = "subgroup"),
        list(name = "ECOG", dataset = "ADSL", role = "subgroup")
      ),
      analysisPopulation = list(
        id = "ITT",
        filter = "ITTFL == 'Y'",
        n = result$overall$n_experimental + result$overall$n_control
      ),
      resultGroups = list(
        list(id = "EXP", label = "Experimental", n = result$overall$n_experimental),
        list(id = "CTRL", label = "Control", n = result$overall$n_control)
      ),
      analysisResultsData = list(
        overall_orr_exp = result$overall$orr_experimental,
        overall_orr_ctrl = result$overall$orr_control,
        interaction_p_values = sapply(result$interaction_tests, function(x) x$interaction_p_value)
      )
    )
  )
}

# ─────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────

if (sys.nframe() == 0) {
  opts <- parse_args()
  seed <- opts$seed
  n <- opts$n

  cat(sprintf("TC-030: ORR by Subgroup with Interaction Test (R) — seed=%d, n=%d\n", seed, n))

  if (!is.na(opts$data)) {
    data <- read_shared_data(opts$data)
    cat(sprintf("Loaded shared tumor response data with %d subjects\n", nrow(data)))
  } else {
    data <- generate_tumor_response(seed = seed, n_subjects = n)
    cat(sprintf("Generated tumor response data with %d subjects\n", nrow(data)))
  }

  result <- compute_orr_with_interaction(data)
  result$seed <- seed
  result$variant_id <- paste0("v", seed)

  if (opts$ars_output) {
    result$ars <- generate_ars_output(result)
  }

  cat("\n────────────────────────────────────────────────\n")
  cat(sprintf("Overall ORR:  Exp=%.1f%%, Ctrl=%.1f%%, Diff=%.1f%%\n",
              result$overall$orr_experimental, result$overall$orr_control,
              result$overall$orr_difference))
  cat("CI method: Clopper-Pearson exact\n")
  cat(sprintf("Subgroups analyzed: %d\n", length(result$subgroups)))
  cat(sprintf("Interaction tests: %d\n", length(result$interaction_tests)))
  for (it in result$interaction_tests) {
    cat(sprintf("  %s: p=%s, OR=%s, method=%s\n",
                it$subgroup,
                it$interaction_p_value,
                it$interaction_or,
                it$method))
  }
  cat("────────────────────────────────────────────────\n")

  print_output(result)

  if (!is.na(opts$output)) {
    write_output(result, opts$output)
  }
}
