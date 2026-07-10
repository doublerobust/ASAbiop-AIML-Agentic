#!/usr/bin/env Rscript
#' TC-029: Adverse Event Summary Table by SOC, PT, and Severity
#'
#' Generates a safety summary table with:
#' - Rows: SOC → PT → Severity Grade (CTCAE v5.0)
#' - Columns: Treatment arms (Experimental vs Control)
#' - Cells: n (%) for each AE term by severity
#' - Overall AEs by severity (Grade 1-5)
#'
#' Usage:
#'   Rscript tc-029-ae-severity.R --seed 42 --n 200 --output tc-029-output.json

suppressPackageStartupMessages({
  library(jsonlite)
  library(dplyr)
  library(tidyr)
})

# --- Argument parsing ---
args <- commandArgs(trailingOnly = TRUE)
seed <- 42
n_subjects <- 200
output_file <- "tc-029-output.json"
data_csv <- ""
ars_output <- ""

i <- 1
while (i <= length(args)) {
  if (args[i] == "--seed") { seed <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--n") { n_subjects <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--output") { output_file <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--data") { data_csv <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--ars-output") { ars_output <- args[i + 1]; i <- i + 2 }
  else { i <- i + 1 }
}

set.seed(seed)

# --- Data generation or loading ---
n_arm <- n_subjects %/% 2
arms <- rep(c("Experimental", "Control"), each = n_arm)
subjid <- paste0("SUBJ-", sprintf("%04d", 1:n_subjects))

# CTCAE v5.0 severity grades
severity_grades <- c(1, 2, 3, 4, 5)
severity_weights <- c(0.50, 0.30, 0.15, 0.04, 0.01)

if (data_csv != "") {
  adae <- read.csv(data_csv, stringsAsFactors = FALSE)
  # Derive n_exp/n_ctrl from data
  n_arm <- length(unique(adae$USUBJID[adae$TRT01A == "Experimental"]))
  n_arm_ctl <- length(unique(adae$USUBJID[adae$TRT01A == "Control"]))
  n_subjects <- n_arm + n_arm_ctl
} else {
  adsl <- data.frame(
    USUBJID = subjid,
    TRT01A = arms,
    SAFFL = "Y",
    stringsAsFactors = FALSE
  )

  ae_catalog <- list(
    "Gastrointestinal disorders" = c(
      "Nausea", "Diarrhoea", "Vomiting", "Abdominal pain", "Constipation"
    ),
    "General disorders and administration site conditions" = c(
      "Fatigue", "Pyrexia", "Oedema peripheral", "Asthenia"
    ),
    "Nervous system disorders" = c(
      "Headache", "Dizziness", "Neuropathy peripheral", "Dysgeusia"
    ),
    "Skin and subcutaneous tissue disorders" = c(
      "Rash", "Pruritus", "Alopecia", "Dry skin"
    ),
    "Investigations" = c(
      "ALT increased", "AST increased", "Blood creatinine increased", "Weight decreased"
    ),
    "Respiratory, thoracic and mediastinal disorders" = c(
      "Cough", "Dyspnoea", "Epistaxis"
    ),
    "Musculoskeletal and connective tissue disorders" = c(
      "Arthralgia", "Myalgia", "Back pain"
    ),
    "Infections and infestations" = c(
      "Upper respiratory tract infection", "Urinary tract infection", "Nasopharyngitis"
    )
  )

  generate_aes <- function(subjids, arm, ae_catalog, seed_offset) {
    set.seed(seed + seed_offset)
    records <- list()
    rate_multiplier <- if (arm == "Experimental") 1.3 else 1.0

    for (soc in names(ae_catalog)) {
      for (pt in ae_catalog[[soc]]) {
        base_rate <- runif(1, 0.02, 0.25)
        adj_rate <- min(base_rate * rate_multiplier, 0.95)

        n_events <- rbinom(1, length(subjids), adj_rate)
        if (n_events > 0) {
          affected <- sample(subjids, n_events)
          for (s in affected) {
            severity <- sample(severity_grades, 1, prob = severity_weights)
            aeser <- if (severity >= 4) "Y" else sample(c("Y", "N"), 1, prob = c(0.05, 0.95))
            if (severity >= 3) {
              aeacn <- sample(c("DOSE NOT CHANGED", "DOSE REDUCED", "DRUG WITHDRAWN"), 1, prob = c(0.4, 0.35, 0.25))
            } else {
              aeacn <- sample(c("DOSE NOT CHANGED", "DOSE REDUCED", "DRUG WITHDRAWN"), 1, prob = c(0.7, 0.2, 0.1))
            }
            records[[length(records) + 1]] <- list(
              USUBJID = s,
              TRT01A = arm,
              AEBODSYS = soc,
              AEDECOD = pt,
              AESEV = as.character(severity),
              AESER = aeser,
              AEACN = aeacn
            )
          }
        }
      }
    }

    if (length(records) == 0) return(data.frame())
    do.call(rbind, lapply(records, as.data.frame, stringsAsFactors = FALSE))
  }

  adae_exp <- generate_aes(subjid[arms == "Experimental"], "Experimental", ae_catalog, 100)
  adae_ctl <- generate_aes(subjid[arms == "Control"], "Control", ae_catalog, 200)
  adae <- rbind(adae_exp, adae_ctl)
}

# --- Compute AE summary by severity ---
n_exp <- n_arm
n_ctl <- n_subjects - n_arm

# Helper functions
pct <- function(n, total) round(100 * n / total, 1)

# Severity summary (grade 1-5)
severity_summary <- lapply(severity_grades, function(g) {
  exp_n <- length(unique(adae$USUBJID[adae$AESEV == as.character(g) & adae$TRT01A == "Experimental"]))
  ctl_n <- length(unique(adae$USUBJID[adae$AESEV == as.character(g) & adae$TRT01A == "Control"]))
  list(
    grade = g,
    n_experimental = exp_n,
    pct_experimental = if (n_exp > 0) pct(exp_n, n_exp) else 0,
    n_control = ctl_n,
    pct_control = if (n_ctl > 0) pct(ctl_n, n_ctl) else 0
  )
})

# Overall summary rows
any_exp <- length(unique(adae$USUBJID[adae$TRT01A == "Experimental"]))
any_ctl <- length(unique(adae$USUBJID[adae$TRT01A == "Control"]))
ser_exp <- length(unique(adae$USUBJID[adae$AESER == "Y" & adae$TRT01A == "Experimental"]))
ser_ctl <- length(unique(adae$USUBJID[adae$AESER == "Y" & adae$TRT01A == "Control"]))
disc_exp <- length(unique(adae$USUBJID[adae$AEACN == "DRUG WITHDRAWN" & adae$TRT01A == "Experimental"]))
disc_ctl <- length(unique(adae$USUBJID[adae$AEACN == "DRUG WITHDRAWN" & adae$TRT01A == "Control"]))

summary_rows <- list(
  list(category = "Any adverse event",
       n_experimental = any_exp,
       pct_experimental = if (n_exp > 0) pct(any_exp, n_exp) else 0,
       n_control = any_ctl,
       pct_control = if (n_ctl > 0) pct(any_ctl, n_ctl) else 0),
  list(category = "Serious adverse events",
       n_experimental = ser_exp,
       pct_experimental = if (n_exp > 0) pct(ser_exp, n_exp) else 0,
       n_control = ser_ctl,
       pct_control = if (n_ctl > 0) pct(ser_ctl, n_ctl) else 0),
  list(category = "AEs leading to discontinuation",
       n_experimental = disc_exp,
       pct_experimental = if (n_exp > 0) pct(disc_exp, n_exp) else 0,
       n_control = disc_ctl,
       pct_control = if (n_ctl > 0) pct(disc_ctl, n_ctl) else 0)
)

# By SOC → PT → Severity
ae_table <- list()

soc_names <- unique(adae$AEBODSYS)
# Sort SOCs by descending total frequency
soc_order <- sapply(soc_names, function(s) {
  length(unique(adae$USUBJID[adae$AEBODSYS == s]))
})
soc_names <- soc_names[order(soc_order, decreasing = TRUE)]

for (soc in soc_names) {
  soc_data <- adae[adae$AEBODSYS == soc, ]

  # SOC total
  soc_exp <- length(unique(soc_data$USUBJID[soc_data$TRT01A == "Experimental"]))
  soc_ctl <- length(unique(soc_data$USUBJID[soc_data$TRT01A == "Control"]))

  ae_table[[length(ae_table) + 1]] <- list(
    category = "soc",
    soc = soc,
    pt = NA,
    severity = NA,
    n_experimental = soc_exp,
    pct_experimental = if (n_exp > 0) pct(soc_exp, n_exp) else 0,
    n_control = soc_ctl,
    pct_control = if (n_ctl > 0) pct(soc_ctl, n_ctl) else 0
  )

  # SOC by severity
  for (g in severity_grades) {
    g_exp <- length(unique(soc_data$USUBJID[soc_data$AESEV == as.character(g) & soc_data$TRT01A == "Experimental"]))
    g_ctl <- length(unique(soc_data$USUBJID[soc_data$AESEV == as.character(g) & soc_data$TRT01A == "Control"]))
    ae_table[[length(ae_table) + 1]] <- list(
      category = "soc_severity",
      soc = soc,
      pt = NA,
      severity = g,
      n_experimental = g_exp,
      pct_experimental = if (n_exp > 0) pct(g_exp, n_exp) else 0,
      n_control = g_ctl,
      pct_control = if (n_ctl > 0) pct(g_ctl, n_ctl) else 0
    )
  }

  # PTs within SOC, sorted by descending max frequency
  pt_data <- soc_data %>%
    group_by(AEDECOD) %>%
    summarise(total = n_distinct(USUBJID), .groups = "drop") %>%
    arrange(desc(total))

  for (pt in pt_data$AEDECOD) {
    pt_data_sub <- soc_data[soc_data$AEDECOD == pt, ]
    pt_exp <- length(unique(pt_data_sub$USUBJID[pt_data_sub$TRT01A == "Experimental"]))
    pt_ctl <- length(unique(pt_data_sub$USUBJID[pt_data_sub$TRT01A == "Control"]))

    ae_table[[length(ae_table) + 1]] <- list(
      category = "pt",
      soc = soc,
      pt = pt,
      severity = NA,
      n_experimental = pt_exp,
      pct_experimental = if (n_exp > 0) pct(pt_exp, n_exp) else 0,
      n_control = pt_ctl,
      pct_control = if (n_ctl > 0) pct(pt_ctl, n_ctl) else 0
    )

    # PT by severity
    for (g in severity_grades) {
      g_exp <- length(unique(pt_data_sub$USUBJID[pt_data_sub$AESEV == as.character(g) & pt_data_sub$TRT01A == "Experimental"]))
      g_ctl <- length(unique(pt_data_sub$USUBJID[pt_data_sub$AESEV == as.character(g) & pt_data_sub$TRT01A == "Control"]))
      ae_table[[length(ae_table) + 1]] <- list(
        category = "pt_severity",
        soc = soc,
        pt = pt,
        severity = g,
        n_experimental = g_exp,
        pct_experimental = if (n_exp > 0) pct(g_exp, n_exp) else 0,
        n_control = g_ctl,
        pct_control = if (n_ctl > 0) pct(g_ctl, n_ctl) else 0
      )
    }
  }
}

output <- list(
  test_case_id = "TC-029",
  title = "Adverse Event Summary Table by SOC, PT, and Severity",
  parameters = list(seed = seed, n_subjects = n_subjects),
  population = list(
    description = "Safety population (SAFFL = 'Y')",
    n_experimental = n_exp,
    n_control = n_ctl
  ),
  severity_grades = severity_grades,
  severity_summary = severity_summary,
  summary = summary_rows,
  ae_table = ae_table,
  metadata = list(
    language = "R",
    packages = c("jsonlite", "dplyr", "tidyr")
  )
)

write_json(output, output_file, auto_unbox = TRUE, pretty = TRUE)

cat("TC-029 output written to", output_file, "\n")
cat("  Subjects:", n_subjects, "(Exp =", n_exp, ", Ctrl =", n_ctl, ")\n")
cat("  AE records:", nrow(adae), "\n")
cat("  Severity summary:\n")
for (i in seq_along(severity_grades)) {
  cat("    Grade", severity_grades[i], ": Exp =", severity_summary[[i]]$n_experimental,
      "Ctl =", severity_summary[[i]]$n_control, "\n")
}

# --- ARS output (optional) ---
if (ars_output != "") {
  ars_envelope <- list(
    analysisResult = list(
      id = "TC-029",
      version = "1.0",
      analysisReason = "Safety: AE summary by SOC, PT, and CTCAE severity grade",
      analysisMethod = list(
        name = "AE summary by severity",
        codeTemplate = "tc-029-ae-severity.R",
        parameters = list(
          severity_grades = severity_grades,
          population = "SAFETY"
        )
      ),
      analysisVariables = list(
        list(name = "AEBODSYS", dataset = "ADAE", role = "category"),
        list(name = "AEDECOD", dataset = "ADAE", role = "category"),
        list(name = "AESEV", dataset = "ADAE", role = "severity"),
        list(name = "TRT01A", dataset = "ADSL", role = "treatment")
      ),
      analysisPopulation = list(
        id = "SAFETY",
        filter = "SAFFL = 'Y'",
        n = n_subjects
      ),
      resultGroups = list(
        list(id = "Experimental", n = n_exp),
        list(id = "Control", n = n_ctl)
      ),
      analysisResultsData = list(
        statistics = c(
          lapply(severity_grades, function(g) {
            list(name = paste0("grade_", g, "_n_experimental"),
                 value = severity_summary[[g]]$n_experimental)
          }),
          lapply(severity_grades, function(g) {
            list(name = paste0("grade_", g, "_n_control"),
                 value = severity_summary[[g]]$n_control)
          })
        )
      )
    )
  )
  write_json(ars_envelope, ars_output, auto_unbox = TRUE, pretty = TRUE)
  cat("ARS envelope written to", ars_output, "\n")
}
