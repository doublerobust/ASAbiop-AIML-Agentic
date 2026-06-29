#!/usr/bin/env Rscript
# TC-019 Ground Truth: Concomitant Medications Summary Table
# Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark
#
# Summarizes concomitant medications by ATC class and preferred name:
#   - Number of subjects taking each medication (n, %)
#   - Sorted by ATC class, then descending frequency
#   - Summary rows: Any CM, subjects with >=1 CM
#
# Dependencies: dplyr, jsonlite
# Usage: Rscript tc-019-concomitant-meds.R --seed 42 --n 200 --output results.json

library(dplyr)
library(jsonlite)

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
# Synthetic ADCM Dataset Generation
# ─────────────────────────────────────────────────────

generate_adcm <- function(seed = 42, n_subjects = 200) {
  set.seed(seed)

  # ATC classes and example medications within each
  atc_classes <- list(
    "J01" = list(name = "Antibacterials for systemic use", meds = c("Amoxicillin", "Ciprofloxacin", "Azithromycin")),
    "N02" = list(name = "Analgesics", meds = c("Paracetamol", "Ibuprofen", "Tramadol")),
    "C03" = list(name = "Diuretics", meds = c("Furosemide", "Hydrochlorothiazide")),
    "A02" = list(name = "Drugs for acid related disorders", meds = c("Omeprazole", "Pantoprazole", "Ranitidine")),
    "N05" = list(name = "Psycholeptics", meds = c("Diazepam", "Lorazepam", "Zolpidem")),
    "C07" = list(name = "Beta blocking agents", meds = c("Metoprolol", "Atenolol", "Bisoprolol")),
    "B01" = list(name = "Antithrombotic agents", meds = c("Warfarin", "Heparin", "Apixaban")),
    "M01" = list(name = "Antiinflammatory/antirheumatic products", meds = c("Naproxen", "Celecoxib", "Diclofenac"))
  )

  usubjid <- character(0)
  atcclass <- character(0)
  atcclas_name <- character(0)
  cmdecod <- character(0)
  cmindc <- character(0)
  trt01pn <- integer(0)

  # Treatment assignment matching ADSL
  trt <- sample(0:1, n_subjects, replace = TRUE)

  for (i in 1:n_subjects) {
    # Each subject takes 0-5 concomitant medications
    n_meds <- sample(0:5, 1, prob = c(0.05, 0.15, 0.25, 0.25, 0.20, 0.10))
    if (n_meds == 0) next

    chosen_classes <- sample(seq_along(atc_classes), min(n_meds, length(atc_classes)),
                             replace = FALSE)
    for (cls_idx in chosen_classes) {
      cls_code <- names(atc_classes)[cls_idx]
      cls <- atc_classes[[cls_idx]]
      med <- sample(cls$meds, 1)
      usubjid <- c(usubjid, sprintf("SUBJ-%04d", i))
      atcclass <- c(atcclass, cls_code)
      atcclas_name <- c(atcclas_name, cls$name)
      cmdecod <- c(cmdecod, med)
      cmindc <- c(cmindc, sample(c("Pain", "Infection", "Hypertension", "Anxiety",
                                    "GERD", "Thrombosis", "Inflammation", "Edema"), 1))
      trt01pn <- c(trt01pn, trt[i])
    }
  }

  data.frame(
    USUBJID = usubjid,
    STUDYID = "BENCHMARK-001",
    ATCCLAS = atcclass,
    ATCCLAS1 = atcclas_name,
    CMDECOD = cmdecod,
    CMINDC = cmindc,
    TRT01PN = trt01pn,
    stringsAsFactors = FALSE
  )
}

# ─────────────────────────────────────────────────────
# TC-019 Core Computation
# ─────────────────────────────────────────────────────

compute_cm_summary <- function(adcm, n_subjects_per_arm) {
  # Subjects per arm (denominator)
  n_exp <- n_subjects_per_arm[1]
  n_ctrl <- n_subjects_per_arm[2]

  # Summary: Any CM
  exp_subjects <- unique(adcm$USUBJID[adcm$TRT01PN == 1])
  ctrl_subjects <- unique(adcm$USUBJID[adcm$TRT01PN == 0])
  any_exp <- length(exp_subjects)
  any_ctrl <- length(ctrl_subjects)

  summary_rows <- list(
    list(category = "Any concomitant medication",
         n_experimental = any_exp, pct_experimental = round(100 * any_exp / n_exp, 1),
         n_control = any_ctrl, pct_control = round(100 * any_ctrl / n_ctrl, 1))
  )

  # By ATC class
  atc_summary <- adcm %>%
    group_by(ATCCLAS, ATCCLAS1, TRT01PN) %>%
    summarise(n_subjects = n_distinct(USUBJID), .groups = "drop") %>%
    mutate(pct = round(100 * n_subjects / ifelse(TRT01PN == 1, n_exp, n_ctrl), 1))

  # Build detailed rows sorted by ATC class
  atc_classes_sorted <- sort(unique(adcm$ATCCLAS))
  detailed_rows <- list()

  for (cls in atc_classes_sorted) {
    cls_data <- adcm[adcm$ATCCLAS == cls, ]
    cls_name <- unique(cls_data$ATCCLAS1)[1]

    exp_n <- atc_summary$n_subjects[atc_summary$ATCCLAS == cls & atc_summary$TRT01PN == 1]
    exp_pct <- atc_summary$pct[atc_summary$ATCCLAS == cls & atc_summary$TRT01PN == 1]
    ctrl_n <- atc_summary$n_subjects[atc_summary$ATCCLAS == cls & atc_summary$TRT01PN == 0]
    ctrl_pct <- atc_summary$pct[atc_summary$ATCCLAS == cls & atc_summary$TRT01PN == 0]

    if (length(exp_n) == 0) { exp_n <- 0; exp_pct <- 0 }
    if (length(ctrl_n) == 0) { ctrl_n <- 0; ctrl_pct <- 0 }
    if (length(exp_n) > 0 && is.na(exp_n)) { exp_n <- 0; exp_pct <- 0 }
    if (length(ctrl_n) > 0 && is.na(ctrl_n)) { ctrl_n <- 0; ctrl_pct <- 0 }

    detailed_rows <- c(detailed_rows, list(list(
      atc_class = cls,
      atc_class_name = cls_name,
      n_experimental = as.integer(exp_n),
      pct_experimental = as.numeric(exp_pct),
      n_control = as.integer(ctrl_n),
      pct_control = as.numeric(ctrl_pct)
    )))

    # By medication within class
    med_summary <- cls_data %>%
      group_by(CMDECOD, TRT01PN) %>%
      summarise(n_subjects = n_distinct(USUBJID), .groups = "drop") %>%
      mutate(pct = round(100 * n_subjects / ifelse(TRT01PN == 1, n_exp, n_ctrl), 1))

    meds_sorted <- sort(unique(cls_data$CMDECOD))
    for (med in meds_sorted) {
      med_exp_n <- med_summary$n_subjects[med_summary$CMDECOD == med & med_summary$TRT01PN == 1]
      med_exp_pct <- med_summary$pct[med_summary$CMDECOD == med & med_summary$TRT01PN == 1]
      med_ctrl_n <- med_summary$n_subjects[med_summary$CMDECOD == med & med_summary$TRT01PN == 0]
      med_ctrl_pct <- med_summary$pct[med_summary$CMDECOD == med & med_summary$TRT01PN == 0]

      if (length(med_exp_n) == 0) { med_exp_n <- 0; med_exp_pct <- 0 }
      if (length(med_ctrl_n) == 0) { med_ctrl_n <- 0; med_ctrl_pct <- 0 }
      if (length(med_exp_n) > 0 && is.na(med_exp_n)) { med_exp_n <- 0; med_exp_pct <- 0 }
      if (length(med_ctrl_n) > 0 && is.na(med_ctrl_n)) { med_ctrl_n <- 0; med_ctrl_pct <- 0 }

      detailed_rows <- c(detailed_rows, list(list(
        atc_class = cls,
        atc_class_name = cls_name,
        medication = med,
        n_experimental = as.integer(med_exp_n),
        pct_experimental = as.numeric(med_exp_pct),
        n_control = as.integer(med_ctrl_n),
        pct_control = as.numeric(med_ctrl_pct)
      )))
    }
  }

  list(
    test_case_id = "TC-019",
    variant_id = paste0("v", NA),
    language = "R",
    package = "dplyr",
    package_version = as.character(packageVersion("dplyr")),
    summary_rows = summary_rows,
    detailed_rows = detailed_rows,
    n_experimental = n_exp,
    n_control = n_ctrl,
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

  cat(sprintf("TC-019: Concomitant Medications Summary (R) — seed=%d, n=%d\\n", seed, n))

  if (!is.na(opts$data)) {
    adcm <- read_shared_data(opts$data)
    cat(sprintf("Loaded shared ADCM with %d records across %d subjects\\n",
                nrow(adcm), length(unique(adcm$USUBJID))))
    # Derive n per arm from the data's treatment assignment
    # Each subject appears once with a TRT01PN value in the ADCM
    adsl_unique <- adcm[!duplicated(adcm$USUBJID), ]
    n_exp <- sum(adsl_unique$TRT01PN == 1)
    n_ctrl <- sum(adsl_unique$TRT01PN == 0)
    n <- n_exp + n_ctrl
  } else {
    adcm <- generate_adcm(seed = seed, n_subjects = n)
    cat(sprintf("Generated ADCM with %d records across %d subjects\\n",
                nrow(adcm), length(unique(adcm$USUBJID))))
    # Determine subjects per arm
    trt <- sample(0:1, n, replace = TRUE)
    n_exp <- sum(trt == 1)
    n_ctrl <- sum(trt == 0)
  }

  result <- compute_cm_summary(adcm, c(n_exp, n_ctrl))
  result$seed <- seed
  result$variant_id <- paste0("v", seed)

  cat("\\n──────────────────────────────────────────────\\n")
  cat(sprintf("Any CM:  Exp=%d (%.1f%%), Ctrl=%d (%.1f%%)\\n",
              result$summary_rows[[1]]$n_experimental,
              result$summary_rows[[1]]$pct_experimental,
              result$summary_rows[[1]]$n_control,
              result$summary_rows[[1]]$pct_control))
  cat(sprintf("ATC classes: %d\\n", length(unique(adcm$ATCCLAS))))
  cat(sprintf("Medications: %d\\n", length(unique(adcm$CMDECOD))))
  cat("──────────────────────────────────────────────\\n")

  print_output(result)

  if (!is.na(opts$output)) {
    write_output(result, opts$output)
  }
}
