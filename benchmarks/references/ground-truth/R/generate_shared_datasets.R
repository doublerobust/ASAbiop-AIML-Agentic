#!/usr/bin/env Rscript
#' Generate shared datasets for cross-language verification
#'
#' Creates CSV files for TC-011 (ADAE), TC-013 (tumor response/ADVS),
#' and TC-014 (protocol deviations) so R and Python can load the same
#' data and produce identical outputs.
#'
#' Usage:
#'   Rscript generate_shared_datasets.R --seed 42 --n 200 --output-dir /path/to/shared/

suppressPackageStartupMessages({
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
seed <- 42
n_subjects <- 200
output_dir <- "."

i <- 1
while (i <= length(args)) {
  if (args[i] == "--seed") { seed <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--n") { n_subjects <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--output-dir") { output_dir <- args[i + 1]; i <- i + 2 }
  else { i <- i + 1 }
}

set.seed(seed)
n_arm <- n_subjects %/% 2

# ============================================================
# TC-011: Shared ADAE dataset
# ============================================================
generate_adae <- function(n_subjects, seed) {
  set.seed(seed)
  n_arm <- n_subjects %/% 2
  arms <- rep(c("Experimental", "Control"), each = n_arm)
  subjid <- paste0("SUBJ-", sprintf("%04d", 1:n_subjects))

  ae_catalog <- list(
    "Gastrointestinal disorders" = c("Nausea", "Diarrhoea", "Vomiting", "Abdominal pain", "Constipation"),
    "General disorders and administration site conditions" = c("Fatigue", "Pyrexia", "Oedema peripheral", "Asthenia"),
    "Nervous system disorders" = c("Headache", "Dizziness", "Neuropathy peripheral", "Dysgeusia"),
    "Skin and subcutaneous tissue disorders" = c("Rash", "Pruritus", "Alopecia", "Dry skin"),
    "Investigations" = c("ALT increased", "AST increased", "Blood creatinine increased", "Weight decreased"),
    "Respiratory, thoracic and mediastinal disorders" = c("Cough", "Dyspnoea", "Epistaxis"),
    "Musculoskeletal and connective tissue disorders" = c("Arthralgia", "Myalgia", "Back pain"),
    "Infections and infestations" = c("Upper respiratory tract infection", "Urinary tract infection", "Nasopharyngitis")
  )

  records <- list()
  for (arm_idx in seq_along(arms)) {
    arm <- arms[arm_idx]
    arm_subj <- subjid[arms == arm]
    rate_mult <- if (arm == "Experimental") 1.3 else 1.0

    for (soc in names(ae_catalog)) {
      for (pt in ae_catalog[[soc]]) {
        base_rate <- runif(1, 0.02, 0.25)
        adj_rate <- min(base_rate * rate_mult, 0.95)
        n_events <- rbinom(1, length(arm_subj), adj_rate)
        if (n_events > 0) {
          affected <- sample(arm_subj, n_events)
          for (s in affected) {
            records[[length(records) + 1]] <- list(
              USUBJID = s,
              TRT01A = arm,
              AEBODSYS = soc,
              AEDECOD = pt,
              AESEV = as.character(sample(1:5, 1, prob = c(0.50, 0.30, 0.15, 0.04, 0.01))),
              AESER = sample(c("Y", "N"), 1, prob = c(0.1, 0.9)),
              AEACN = sample(c("DOSE NOT CHANGED", "DOSE REDUCED", "DRUG WITHDRAWN"), 1, prob = c(0.7, 0.2, 0.1))
            )
          }
        }
      }
    }
  }

  if (length(records) == 0) return(data.frame())
  do.call(rbind, lapply(records, as.data.frame, stringsAsFactors = FALSE))
}

adae <- generate_adae(n_subjects, seed)
write.csv(adae, file.path(output_dir, "adae.csv"), row.names = FALSE)
cat(sprintf("ADAE: %d rows written to %s\n", nrow(adae), file.path(output_dir, "adae.csv")))

# ============================================================
# TC-013: Shared tumor response dataset (ADVS-like)
# ============================================================
generate_tumor <- function(n_subjects, seed) {
  set.seed(seed)
  n_arm <- n_subjects %/% 2

  records <- list()
  for (i in seq_len(n_subjects)) {
    subj <- paste0("SUBJ-", sprintf("%04d", i))
    arm <- if (i <= n_arm) "Experimental" else "Control"

    if (arm == "Experimental") {
      category <- sample(c("CR", "PR", "SD", "PD"), 1, prob = c(0.15, 0.35, 0.30, 0.20))
    } else {
      category <- sample(c("CR", "PR", "SD", "PD"), 1, prob = c(0.05, 0.20, 0.35, 0.40))
    }

    pct_change <- switch(category,
      "CR" = -100.0,
      "PR" = round(runif(1, -99.0, -30.0), 1),
      "SD" = round(runif(1, -29.9, 19.9), 1),
      "PD" = round(runif(1, 20.0, 200.0), 1)
    )

    records[[i]] <- list(
      USUBJID = subj,
      TRT01A = arm,
      BASELINE = round(runif(1, 15, 100), 1),
      BESTPCHG = pct_change,
      BOR = category
    )
  }

  do.call(rbind, lapply(records, as.data.frame, stringsAsFactors = FALSE))
}

tumor_df <- generate_tumor(n_subjects, seed)
write.csv(tumor_df, file.path(output_dir, "advs_tumor.csv"), row.names = FALSE)
cat(sprintf("ADVS: %d rows written to %s\n", nrow(tumor_df), file.path(output_dir, "advs_tumor.csv")))

# ============================================================
# TC-014: Shared protocol deviation dataset
# ============================================================
generate_pds <- function(n_subjects, seed) {
  set.seed(seed)
  n_arm <- n_subjects %/% 2

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

  subjid_exp <- paste0("SUBJ-", sprintf("%04d", 1:n_arm))
  subjid_ctl <- paste0("SUBJ-", sprintf("%04d", (n_arm + 1):n_subjects))

  records <- list()

  for (subj_set in list(list(subj = subjid_exp, arm = "Experimental", offset = 100),
                         list(subj = subjid_ctl, arm = "Control", offset = 200))) {
    # Note: we use the SAME seed for both arms to ensure reproducibility
    # The offset is NOT used here — we want the same RNG stream pattern
    # Actually, to match the original code structure, we DO use offsets
    set.seed(seed + subj_set$offset)

    pd_subjects <- sample(subj_set$subj, floor(length(subj_set$subj) * 0.30))

    for (subj in pd_subjects) {
      n_pds <- sample(1:3, 1, prob = c(0.6, 0.3, 0.1))
      cats <- sample(names(pd_catalog), min(n_pds, length(pd_catalog)))

      for (cat in cats) {
        code_desc <- sample(pd_catalog[[cat]], 1)[[1]]
        study_day <- sample(1:365, 1)
        pd_date <- as.Date("2025-01-15") + study_day
        severity <- sample(c("Major", "Minor", "Critical"), 1, prob = c(0.5, 0.35, 0.15))

        records[[length(records) + 1]] <- list(
          USUBJID = subj,
          TRT01A = subj_set$arm,
          PD_CAT = cat,
          PD_CODE = code_desc[1],
          PDDESC = code_desc[2],
          PDDY = study_day,
          PDDTC = format(pd_date, "%Y-%m-%d"),
          SEVERITY = severity
        )
      }
    }
  }

  if (length(records) == 0) return(data.frame())
  do.call(rbind, lapply(records, as.data.frame, stringsAsFactors = FALSE))
}

pd_df <- generate_pds(n_subjects, seed)
write.csv(pd_df, file.path(output_dir, "protocol_deviations.csv"), row.names = FALSE)
cat(sprintf("PD: %d rows written to %s\n", nrow(pd_df), file.path(output_dir, "protocol_deviations.csv")))

cat("\nAll shared datasets generated successfully.\n")
