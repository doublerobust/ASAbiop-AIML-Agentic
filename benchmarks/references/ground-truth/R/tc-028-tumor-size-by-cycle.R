#!/usr/bin/env Rscript
# TC-028 Ground Truth: Change in Tumor Size by Cycle (Longitudinal)
# Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark
#
# Computes percentage change from baseline in tumor size (SLD) at each
# treatment cycle (C1D1 through C6D1) for each subject, with visit-wise
# summary statistics by arm.
#
# Usage:
#   Rscript tc-028-tumor-size-by-cycle.R --seed 42 --n 150 --output tc-028-output.json
#   Rscript tc-028-tumor-size-by-cycle.R --seed 42 --n 150 --output out.json --ars-output ars.json

suppressPackageStartupMessages({
  library(jsonlite)
  library(optparse)
})

# --- Argument parsing ---
option_list <- list(
  make_option("--seed", type = "integer", default = 42L),
  make_option("--n", type = "integer", default = 150L),
  make_option("--output", type = "character", default = "tc-028-output.json"),
  make_option("--data-csv", type = "character", default = NULL),
  make_option("--ars-output", type = "character", default = NULL)
)
opt <- parse_args(OptionParser(option_list = option_list))

set.seed(opt$seed)
n_subjects <- opt$n

# Treatment cycles
CYCLES <- c("C1D1", "C2D1", "C3D1", "C4D1", "C5D1", "C6D1")
BASELINE_CYCLE <- "C1D1"

# --- Data generation ---
generate_longitudinal_tumor <- function(n, seed_offset) {
  set.seed(opt$seed + seed_offset)
  records <- list()

  for (i in 1:n) {
    subj <- sprintf("SUBJ-%04d", i)
    arm <- ifelse(i <= n %/% 2, "Experimental", "Control")
    baseline_sld <- round(runif(1, 20, 120), 1)

    if (arm == "Experimental") {
      initial_response <- rnorm(1, -25, 15)
      regrowth_rate <- rnorm(1, 5, 3)
      nadir_cycle <- sample(1:4, 1, prob = c(0.17, 0.33, 0.33, 0.17))
    } else {
      initial_response <- rnorm(1, -8, 12)
      regrowth_rate <- rnorm(1, 8, 4)
      nadir_cycle <- sample(1:3, 1, prob = c(0.25, 0.50, 0.25))
    }

    base_dropout <- 0.05
    visits <- list()

    for (cycle_idx in seq_along(CYCLES)) {
      cycle <- CYCLES[cycle_idx]
      if (cycle == BASELINE_CYCLE) {
        visits[[length(visits) + 1]] <- list(
          cycle = cycle, cycle_num = 0,
          sld = baseline_sld, pct_change = 0.0, available = TRUE
        )
        next
      }

      dropout_prob <- base_dropout * (cycle_idx - 1)
      if (runif(1) < dropout_prob) break

      cycle_num <- cycle_idx  # 1, 2, 3, 4, 5
      if (cycle_num <= nadir_cycle) {
        pct <- initial_response * cycle_num
      } else {
        nadir_pct <- initial_response * nadir_cycle
        cycles_since_nadir <- cycle_num - nadir_cycle
        pct <- nadir_pct + regrowth_rate * cycles_since_nadir
      }

      pct <- pct + rnorm(1, 0, 3)
      sld <- max(baseline_sld * (1 + pct / 100), 0)

      visits[[length(visits) + 1]] <- list(
        cycle = cycle, cycle_num = cycle_num,
        sld = round(sld, 1), pct_change = round(pct, 1), available = TRUE
      )
    }

    records[[i]] <- list(
      USUBJID = subj, TRT01A = arm,
      TRT01PN = ifelse(arm == "Experimental", 1, 0),
      BASELINE_SLD = baseline_sld,
      N_VISITS = length(visits),
      VISITS = visits
    )
  }

  return(records)
}

# --- Load data or generate ---
if (!is.null(opt$`data-csv`)) {
  df <- read.csv(opt$`data-csv`, stringsAsFactors = FALSE)
  subjects <- split(df, df$USUBJID)
  subject_list <- lapply(names(subjects), function(id) {
    rows <- subjects[[id]]
    visits <- lapply(1:nrow(rows), function(j) {
      list(
        cycle = rows$CYCLE[j], cycle_num = rows$CYCLE_NUM[j],
        sld = rows$SLD[j], pct_change = rows$PCT_CHANGE[j],
        available = TRUE
      )
    })
    list(
      USUBJID = id, TRT01A = rows$TRT01A[1], TRT01PN = rows$TRT01PN[1],
      BASELINE_SLD = rows$BASELINE_SLD[1], N_VISITS = nrow(rows),
      VISITS = visits
    )
  })
} else {
  subject_list <- generate_longitudinal_tumor(n_subjects, 200)
}

# --- Visit-wise summary ---
compute_visit_summary <- function(subjects, cycle, arm = NULL) {
  if (!is.null(arm)) {
    subset <- Filter(function(s) s$TRT01A == arm, subjects)
  } else {
    subset <- subjects
  }

  pct_changes <- c()
  slds <- c()
  n_with_visit <- 0

  for (subj in subset) {
    for (v in subj$VISITS) {
      if (v$cycle == cycle && isTRUE(v$available)) {
        pct_changes <- c(pct_changes, v$pct_change)
        slds <- c(slds, v$sld)
        n_with_visit <- n_with_visit + 1
        break
      }
    }
  }

  n_total <- length(subset)
  n_missing <- n_total - n_with_visit

  if (length(pct_changes) > 0) {
    se <- sd(pct_changes) / sqrt(length(pct_changes))
    list(
      cycle = cycle, arm = ifelse(is.null(arm), "All", arm),
      n_total = n_total, n_assessed = n_with_visit, n_missing = n_missing,
      mean_pct_change = round(mean(pct_changes), 2),
      median_pct_change = round(median(pct_changes), 2),
      se_pct_change = round(se, 3),
      mean_sld = round(mean(slds), 2),
      median_sld = round(median(slds), 2),
      min_pct_change = round(min(pct_changes), 1),
      max_pct_change = round(max(pct_changes), 1)
    )
  } else {
    list(
      cycle = cycle, arm = ifelse(is.null(arm), "All", arm),
      n_total = n_total, n_assessed = 0, n_missing = n_total,
      mean_pct_change = NA, median_pct_change = NA, se_pct_change = NA,
      mean_sld = NA, median_sld = NA, min_pct_change = NA, max_pct_change = NA
    )
  }
}

visit_summaries <- list()
for (cycle in CYCLES) {
  visit_summaries[[cycle]] <- list(
    all = compute_visit_summary(subject_list, cycle),
    experimental = compute_visit_summary(subject_list, cycle, "Experimental"),
    control = compute_visit_summary(subject_list, cycle, "Control")
  )
}

# --- Per-subject summary ---
compute_subject_summary <- function(subjects) {
  lapply(subjects, function(subj) {
    non_baseline <- Filter(function(v) v$cycle != BASELINE_CYCLE && isTRUE(v$available),
                           subj$VISITS)
    if (length(non_baseline) == 0) {
      return(list(
        USUBJID = subj$USUBJID, TRT01A = subj$TRT01A,
        best_pct_change = NA, worst_pct_change = NA,
        time_to_best_cycle = NA, n_assessments = 0
      ))
    }

    pct_values <- sapply(non_baseline, function(v) v$pct_change)
    best_idx <- which.min(pct_values)
    worst_idx <- which.max(pct_values)

    list(
      USUBJID = subj$USUBJID, TRT01A = subj$TRT01A,
      best_pct_change = round(pct_values[best_idx], 1),
      worst_pct_change = round(pct_values[worst_idx], 1),
      time_to_best_cycle = non_baseline[[best_idx]]$cycle,
      time_to_worst_cycle = non_baseline[[worst_idx]]$cycle,
      n_assessments = length(pct_values)
    )
  })
}

subject_summaries <- compute_subject_summary(subject_list)

# --- Arm-level overall summary ---
arm_overall <- function(summaries, arm) {
  subset <- Filter(function(s) s$TRT01A == arm, summaries)
  best_vals <- sapply(subset, function(s) s$best_pct_change)
  best_vals <- best_vals[!is.na(best_vals)]
  worst_vals <- sapply(subset, function(s) s$worst_pct_change)
  worst_vals <- worst_vals[!is.na(worst_vals)]
  n_assess <- sapply(subset, function(s) s$n_assessments)

  list(
    arm = arm, n_subjects = length(subset),
    mean_best_pct_change = ifelse(length(best_vals) > 0, round(mean(best_vals), 2), NA),
    median_best_pct_change = ifelse(length(best_vals) > 0, round(median(best_vals), 2), NA),
    mean_worst_pct_change = ifelse(length(worst_vals) > 0, round(mean(worst_vals), 2), NA),
    median_worst_pct_change = ifelse(length(worst_vals) > 0, round(median(worst_vals), 2), NA),
    mean_n_assessments = ifelse(length(n_assess) > 0, round(mean(n_assess), 1), NA)
  )
}

overall_summary <- list(
  experimental = arm_overall(subject_summaries, "Experimental"),
  control = arm_overall(subject_summaries, "Control")
)

# --- Output ---
output <- list(
  test_case_id = "TC-028",
  title = "Change in Tumor Size by Cycle (Longitudinal)",
  parameters = list(seed = opt$seed, n_subjects = n_subjects),
  cycles = CYCLES,
  baseline_cycle = BASELINE_CYCLE,
  visit_summaries = visit_summaries,
  overall_summary = overall_summary,
  subject_summaries = subject_summaries,
  n_subjects = length(subject_list),
  metadata = list(language = "R", packages = c("jsonlite", "optparse"))
)

writeLines(toJSON(output, auto_unbox = TRUE, pretty = TRUE), opt$output)
cat("TC-028 output written to:", opt$output, "\n")

# --- ARS Output (optional) ---
if (!is.null(opt$`ars-output`)) {
  ars_envelope <- list(
    analysisResult = list(
      id = "TC-028", version = "1.0",
      analysisReason = "Longitudinal tumor size change assessment per RECIST 1.1"
    ),
    analysisMethod = list(
      name = "Descriptive statistics of percentage change from baseline in tumor size by cycle",
      codeTemplate = "mean/median/min/max of pct_change by cycle and arm",
      parameters = list(cycles = CYCLES, baseline_cycle = BASELINE_CYCLE)
    ),
    analysisVariables = list(
      list(name = "SLD", dataset = "ADTR", role = "analysis"),
      list(name = "PCT_CHANGE", dataset = "ADTR", role = "derived"),
      list(name = "TRT01A", dataset = "ADSL", role = "grouping"),
      list(name = "AVISIT", dataset = "ADTR", role = "timing")
    ),
    analysisPopulation = list(name = "ITT", filter = "ITTFL='Y'"),
    resultGroups = list(
      list(name = "Experimental", n = sum(sapply(subject_list, function(s) s$TRT01A == "Experimental"))),
      list(name = "Control", n = sum(sapply(subject_list, function(s) s$TRT01A == "Control")))
    ),
    analysisResultsData = list(
      statistics = c(
        lapply(CYCLES, function(c) list(name = paste0("mean_pct_change_", c, "_experimental"),
                                         value = visit_summaries[[c]]$experimental$mean_pct_change)),
        lapply(CYCLES, function(c) list(name = paste0("mean_pct_change_", c, "_control"),
                                         value = visit_summaries[[c]]$control$mean_pct_change))
      )
    )
  )
  writeLines(toJSON(ars_envelope, auto_unbox = TRUE, pretty = TRUE), opt$`ars-output`)
  cat("TC-028 ARS envelope written to:", opt$`ars-output`, "\n")
}
