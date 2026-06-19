#!/usr/bin/env Rscript
#' TC-014: Listing of Key Protocol Deviations
#'
#' Usage:
#'   Rscript tc-014-pd-listing.R --seed 42 --n 200 --output tc-014-output.json

suppressPackageStartupMessages({
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
seed <- 42; n_subjects <- 200; output_file <- "tc-014-output.json"
i <- 1
while (i <= length(args)) {
  if (args[i] == "--seed") { seed <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--n") { n_subjects <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--output") { output_file <- args[i + 1]; i <- i + 2 }
  else { i <- i + 1 }
}

set.seed(seed)
n_arm <- n_subjects / 2

# PD catalog
pd_catalog <- list(
  "Eligibility" = list(
    c("ELIG-01", "Inclusion criterion not met: baseline lab value outside range"),
    c("ELIG-02", "Exclusion criterion violated: prior therapy within washout period"),
    c("ELIG-03", "Informed consent obtained after first dose")
  ),
  "Visit Window" = list(
    c("VISIT-01", "Visit conducted outside protocol-specified window (+7 days)"),
    c("VISIT-02", "Missing required assessment at scheduled visit"),
    c("VISIT-03", "Visit conducted >14 days outside window")
  ),
  "Prohibited Medication" = list(
    c("PROHIB-01", "Concomitant medication prohibited per protocol"),
    c("PROHIB-02", "Prior medication washout period not completed")
  ),
  "Dose Modification" = list(
    c("DOSE-01", "Dose modification not per protocol algorithm"),
    c("DOSE-02", "Treatment delay >7 days without protocol authorization"),
    c("DOSE-03", "Dose administered outside \u00b110% of protocol-specified dose")
  ),
  "Consent" = list(
    c("CONSENT-01", "Informed consent form version not current"),
    c("CONSENT-02", "Consent re-consent not obtained after protocol amendment")
  ),
  "Endpoint Deviation" = list(
    c("ENDPT-01", "Primary endpoint assessment not performed per schedule"),
    c("ENDPT-02", "Imaging assessment not reviewed by independent radiologist")
  )
)

generate_pds <- function(subjids, arm, seed_offset) {
  set.seed(seed + seed_offset)
  study_start <- as.Date("2025-01-15")
  records <- list()

  pd_subjects <- sample(subjids, floor(length(subjids) * 0.30))

  for (subj in pd_subjects) {
    n_pds <- sample(1:3, 1, prob = c(0.6, 0.3, 0.1))
    cats <- sample(names(pd_catalog), min(n_pds, length(pd_catalog)))

    for (cat in cats) {
      code_desc <- sample(pd_catalog[[cat]], 1)[[1]]
      study_day <- sample(1:365, 1)
      pd_date <- study_start + study_day

      severity <- sample(c("Major", "Minor", "Critical"), 1, prob = c(0.5, 0.35, 0.15))

      records[[length(records) + 1]] <- list(
        USUBJID = subj, TRT01A = arm, PD_CAT = cat,
        PD_CODE = code_desc[1], PDDESC = code_desc[2],
        PDDY = study_day, PDDTC = format(pd_date, "%Y-%m-%d"),
        SEVERITY = severity
      )
    }
  }

  if (length(records) == 0) return(data.frame())
  do.call(rbind, lapply(records, as.data.frame, stringsAsFactors = FALSE))
}

subjid_exp <- paste0("SUBJ-", sprintf("%04d", 1:n_arm))
subjid_ctl <- paste0("SUBJ-", sprintf("%04d", (n_arm + 1):n_subjects))

pds_exp <- generate_pds(subjid_exp, "Experimental", 100)
pds_ctl <- generate_pds(subjid_ctl, "Control", 200)
all_pds <- rbind(pds_exp, pds_ctl)

# Sort
all_pds <- all_pds[order(all_pds$TRT01A, all_pds$USUBJID, all_pds$PDDY), ]

# Summary
compute_summary <- function(df, arm = NULL) {
  if (!is.null(arm)) df <- df[df$TRT01A == arm, ]
  by_cat <- list()
  for (cat in names(pd_catalog)) {
    cat_df <- df[df$PD_CAT == cat, ]
    by_cat[[cat]] <- list(
      n_subjects = length(unique(cat_df$USUBJID)),
      n_deviations = nrow(cat_df)
    )
  }
  by_sev <- list(
    Critical = sum(df$SEVERITY == "Critical"),
    Major = sum(df$SEVERITY == "Major"),
    Minor = sum(df$SEVERITY == "Minor")
  )
  list(
    n_subjects_with_pd = length(unique(df$USUBJID)),
    n_total_deviations = nrow(df),
    by_category = by_cat,
    by_severity = by_sev
  )
}

output <- list(
  test_case_id = "TC-014",
  title = "Listing of Key Protocol Deviations",
  parameters = list(seed = seed, n_subjects = n_subjects),
  population = list(
    description = "All randomized subjects",
    n_experimental = n_arm, n_control = n_arm
  ),
  summary = list(
    all = compute_summary(all_pds),
    experimental = compute_summary(all_pds, "Experimental"),
    control = compute_summary(all_pds, "Control")
  ),
  listing = lapply(seq_len(nrow(all_pds)), function(i) as.list(all_pds[i, ])),
  metadata = list(
    language = "R",
    sorting = "TRT01A, USUBJID, PDDY",
    packages = c("jsonlite")
  )
)

write_json(output, output_file, auto_unbox = TRUE, pretty = TRUE)
cat("TC-014 output written to:", output_file, "\n")
