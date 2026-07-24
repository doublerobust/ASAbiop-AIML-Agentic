#!/usr/bin/env Rscript
# generate_tc009_safety_signal.R — TC-009 Data Generator
# Level 3: Safety Signal Evaluation and DMC Report
#
# Generates three shared CSV datasets with PLANTED SAFETY SIGNALS so that
# R and Python ground-truth scripts compute IDENTICAL safety analyses on the
# SAME data (exact cross-language verification).
#
# Planted signals:
#   1. Hepatotoxicity / Hy's Law — ~10 Active, ~2 Placebo subjects with
#      ALT or AST > 3xULN AND total bilirubin > 2xULN (classic DILI risk)
#   2. QTc prolongation — ~8 Active, ~3 Placebo with QTc > 480ms or Δ > 60ms
#   3. Immune-related AEs (irAEs) — ~15 Active, ~5 Placebo
#   4. Elevated Grade 3+ AE rate in Active arm
#   5. Higher overall AE/SAE/discontinuation rates in Active arm
#
# Usage:
#   Rscript generate_tc009_safety_signal.R [--seed SEED] [--n N_PER_ARM] [--out DIR]
#
# Output:
#   adsl_tc009.csv  — subject-level (disposition, exposure, follow-up)
#   adae_tc009.csv  — adverse event records (SOC/PT/severity/serious/action/SOSI/day)
#   adlb_tc009.csv  — per-subject lab maxima (ALT/AST/BILI/QTC, Hy's Law + QTc flags)

source("common/data-generation.R")

# ─── Parse args ───
args <- commandArgs(trailingOnly = TRUE)
seed <- 42
n_per_arm <- 200
out_dir <- "cross-lang-results/shared"

i <- 1
while (i <= length(args)) {
  if (args[i] == "--seed" && i + 1 <= length(args)) { seed <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--n" && i + 1 <= length(args)) { n_per_arm <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--out" && i + 1 <= length(args)) { out_dir <- args[i + 1]; i <- i + 2 }
  else { i <- i + 1 }
}

dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)
set.seed(seed)

n_total <- n_per_arm * 2
trt <- rep(c("Placebo", "Active"), each = n_per_arm)
trt01pn <- ifelse(trt == "Active", 1, 0)
usubjid <- sprintf("SUBJ-%04d", seq_len(n_total))

# ─── ADSL: disposition, exposure, follow-up ───
# Follow-up duration (days): median ~14 months (425 days), range 180-730
followup_days <- round(pmax(180, rnorm(n_total, mean = 425, sd = 90)))
followup_days <- pmin(followup_days, 730)

# Exposure (patient-years): roughly follow-up / 365, slightly less for discontinued
discontinued <- rbinom(n_total, 1, ifelse(trt == "Active", 0.18, 0.12))
# Discontinued subjects have shorter exposure
followup_days <- ifelse(discontinued == 1,
                        pmin(followup_days, round(runif(n_total, 60, 300))),
                        followup_days)
exposure_py <- round(followup_days / 365.25, 4)

# Death on study: higher in Placebo (worse outcomes) for efficacy balance,
# but Active has drug-related deaths (captured in ADAE as Grade 5)
died <- rbinom(n_total, 1, ifelse(trt == "Active", 0.06, 0.09))

# Demographics
sex <- sample(c("Male", "Female"), n_total, replace = TRUE, prob = c(0.55, 0.45))
age <- round(rnorm(n_total, mean = 62, sd = 10))
age <- pmax(pmin(age, 85), 35)
agegr1 <- ifelse(age < 65, "<65", ">=65")

adsl <- data.frame(
  USUBJID = usubjid,
  STUDYID = "BENCHMARK-009",
  TRT01P = trt,
  TRT01PN = trt01pn,
  SAFFL = "Y",
  ITTFL = "Y",
  SEX = sex,
  AGE = age,
  AGEGR1 = agegr1,
  FOLLOWUP_DAYS = followup_days,
  EXPOSURE_PY = exposure_py,
  DISCONTINUED = discontinued,
  DIED = died,
  stringsAsFactors = FALSE
)

# ─── ADLB: per-subject lab maxima with planted hepatotoxicity & QTc signals ───
# ULN (upper limit of normal): ALT=40, AST=40, Bilirubin=1.2, QTc threshold=450 (M)/470 (F) absolute
alt_uln <- 40
ast_uln <- 40
bili_uln <- 1.2

# Baseline labs (within normal range, mostly)
alt_base <- round(pmax(5, rnorm(n_total, 22, 8)), 1)
ast_base <- round(pmax(5, rnorm(n_total, 24, 8)), 1)
bili_base <- round(pmax(0.2, rnorm(n_total, 0.6, 0.2)), 2)
qtc_base <- round(pmax(380, rnorm(n_total, 415, 20)), 1)

# Post-baseline maxima — mostly normal but with planted signals
alt_max <- round(alt_base + pmax(0, rnorm(n_total, 8, 12)), 1)
ast_max <- round(ast_base + pmax(0, rnorm(n_total, 8, 12)), 1)
bili_max <- round(bili_base + pmax(0, rnorm(n_total, 0.1, 0.15)), 2)
qtc_max <- round(qtc_base + pmax(0, rnorm(n_total, 5, 15)), 1)

# ── PLANT HEPATOTOXICITY (Hy's Law) SIGNAL ──
# Hy's Law: (ALT or AST > 3xULN) AND (bilirubin > 2xULN)
# Plant ~10 in Active, ~2 in Placebo (deterministic by subject index)
active_idx <- which(trt == "Active")
placebo_idx <- which(trt == "Placebo")

hys_active <- active_idx[1:10]   # 10 Hy's Law cases in Active
hys_placebo <- placebo_idx[1:2] # 2 Hy's Law cases in Placebo
hys_all <- c(hys_active, hys_placebo)

for (s in hys_all) {
  alt_max[s] <- round(alt_uln * runif(1, 3.5, 7.0), 1)   # 3.5-7x ULN
  ast_max[s] <- round(ast_uln * runif(1, 3.2, 6.5), 1)
  bili_max[s] <- round(bili_uln * runif(1, 2.2, 4.0), 2)  # 2.2-4x ULN
}

# Also plant some isolated ALT/AST elevation (without bilirubin) — Temple's corollary
alt_only_active <- active_idx[11:18]  # 8 subjects with ALT>3xULN but normal bili
for (s in alt_only_active) {
  alt_max[s] <- round(alt_uln * runif(1, 3.1, 5.0), 1)
}

# ── PLANT QTc PROLONGATION SIGNAL ──
# QTc prolonged: max > 480ms OR delta from baseline > 60ms
# Plant ~8 in Active, ~3 in Placebo
qtc_active <- active_idx[19:26]   # 8 QTc prolongation in Active
qtc_placebo <- placebo_idx[3:5]   # 3 QTc prolongation in Placebo
qtc_all <- c(qtc_active, qtc_placebo)

for (s in qtc_all) {
  qtc_max[s] <- round(runif(1, 482, 520), 1)
}

qtc_delta <- round(qtc_max - qtc_base, 1)
qtc_prolonged <- ifelse(qtc_max > 480 | qtc_delta > 60, "Y", "N")

# Hy's Law and lab abnormality flags
alt_3x <- ifelse(alt_max > 3 * alt_uln, "Y", "N")
ast_3x <- ifelse(ast_max > 3 * ast_uln, "Y", "N")
bili_2x <- ifelse(bili_max > 2 * bili_uln, "Y", "N")
hys_law <- ifelse((alt_3x == "Y" | ast_3x == "Y") & bili_2x == "Y", "Y", "N")

adlb <- data.frame(
  USUBJID = usubjid,
  TRT01P = trt,
  TRT01PN = trt01pn,
  ALT_BASE = alt_base,
  ALT_MAX = alt_max,
  ALT_3XULN = alt_3x,
  AST_BASE = ast_base,
  AST_MAX = ast_max,
  AST_3XULN = ast_3x,
  BILI_BASE = bili_base,
  BILI_MAX = bili_max,
  BILI_2XULN = bili_2x,
  QTC_BASE = qtc_base,
  QTC_MAX = qtc_max,
  QTC_DELTA = qtc_delta,
  QTC_PROLONGED = qtc_prolonged,
  HYS_LAW = hys_law,
  stringsAsFactors = FALSE
)

# ─── ADAE: adverse event records with planted signals ───
# AE catalog: SOC / PT / typical grade distribution
ae_catalog <- list(
  list(soc = "Gastrointestinal disorders", pt = "Nausea",            base_grade = 1, active_rate = 0.45, placebo_rate = 0.30),
  list(soc = "Gastrointestinal disorders", pt = "Diarrhoea",         base_grade = 1, active_rate = 0.38, placebo_rate = 0.22),
  list(soc = "Gastrointestinal disorders", pt = "Vomiting",          base_grade = 1, active_rate = 0.25, placebo_rate = 0.15),
  list(soc = "Gastrointestinal disorders", pt = "Decreased appetite",base_grade = 1, active_rate = 0.30, placebo_rate = 0.20),
  list(soc = "Skin and subcutaneous tissue disorders", pt = "Rash",  base_grade = 1, active_rate = 0.40, placebo_rate = 0.15),
  list(soc = "Skin and subcutaneous tissue disorders", pt = "Pruritus", base_grade = 1, active_rate = 0.28, placebo_rate = 0.10),
  list(soc = "General disorders", pt = "Fatigue",                    base_grade = 1, active_rate = 0.50, placebo_rate = 0.40),
  list(soc = "General disorders", pt = "Pyrexia",                    base_grade = 1, active_rate = 0.22, placebo_rate = 0.15),
  list(soc = "Blood and lymphatic system disorders", pt = "Anaemia", base_grade = 2, active_rate = 0.20, placebo_rate = 0.15),
  list(soc = "Blood and lymphatic system disorders", pt = "Neutropenia", base_grade = 2, active_rate = 0.25, placebo_rate = 0.10),
  list(soc = "Blood and lymphatic system disorders", pt = "Thrombocytopenia", base_grade = 2, active_rate = 0.18, placebo_rate = 0.08),
  list(soc = "Nervous system disorders", pt = "Headache",            base_grade = 1, active_rate = 0.20, placebo_rate = 0.18),
  list(soc = "Nervous system disorders", pt = "Peripheral neuropathy", base_grade = 1, active_rate = 0.15, placebo_rate = 0.06),
  list(soc = "Respiratory disorders", pt = "Cough",                  base_grade = 1, active_rate = 0.18, placebo_rate = 0.12),
  list(soc = "Metabolic disorders", pt = "Hypothyroidism",           base_grade = 1, active_rate = 0.16, placebo_rate = 0.04),
  list(soc = "Investigations", pt = "Alanine aminotransferase increased", base_grade = 1, active_rate = 0.22, placebo_rate = 0.10),
  list(soc = "Investigations", pt = "Aspartate aminotransferase increased", base_grade = 1, active_rate = 0.20, placebo_rate = 0.09),
  list(soc = "Investigations", pt = "Blood bilirubin increased",     base_grade = 1, active_rate = 0.15, placebo_rate = 0.06),
  list(soc = "Hepatobiliary disorders", pt = "Drug-induced liver injury", base_grade = 3, active_rate = 0.05, placebo_rate = 0.01),
  list(soc = "Cardiac disorders", pt = "QT prolongation",            base_grade = 2, active_rate = 0.07, placebo_rate = 0.02),
  list(soc = "Cardiac disorders", pt = "Atrial fibrillation",        base_grade = 2, active_rate = 0.06, placebo_rate = 0.04),
  list(soc = "Renal and urinary disorders", pt = "Acute kidney injury", base_grade = 2, active_rate = 0.08, placebo_rate = 0.04)
)

# irAE-relevant PTs (immune-related AE of special interest)
irae_pts <- c("Rash", "Pruritus", "Hypothyroidism", "Diarrhoea", "Alanine aminotransferase increased", "Aspartate aminotransferase increased")

ae_records <- list()
rec_idx <- 1

for (s in seq_len(n_total)) {
  arm <- trt[s]
  subj_fu <- followup_days[s]
  for (ae in ae_catalog) {
    rate <- if (arm == "Active") ae$active_rate else ae$placebo_rate
    if (runif(1) < rate) {
      # Subject experiences this AE
      grade <- ae$base_grade + sample(0:2, 1, prob = c(0.55, 0.30, 0.15))
      grade <- min(grade, 5)
      # Escalate grade for planted hepatotoxicity subjects (Hy's Law → Grade 3+ liver AE)
      if (hys_law[s] == "Y" && ae$pt %in% c("Alanine aminotransferase increased", "Aspartate aminotransferase increased", "Blood bilirubin increased")) {
        grade <- max(grade, 3)
      }
      serious <- if (grade >= 4 || (grade >= 3 && runif(1) < 0.5)) "Y" else "N"
      # Action taken
      action <- if (grade >= 4) sample(c("DOSE_REDUCTION", "DRUG_WITHDRAWN"), 1, prob = c(0.4, 0.6))
                else if (grade == 3) sample(c("NONE", "DOSE_REDUCTION", "DRUG_WITHDRAWN"), 1, prob = c(0.5, 0.3, 0.2))
                else sample(c("NONE", "DOSE_REDUCTION"), 1, prob = c(0.85, 0.15))
      # AE of special interest (irAE): immune-related PTs more common in Active
      aesi <- if (ae$pt %in% irae_pts && runif(1) < ifelse(arm == "Active", 0.7, 0.3)) "Y" else "N"
      # Start day (during follow-up)
      aestdy <- round(runif(1, 1, max(2, subj_fu - 7)))

      ae_records[[rec_idx]] <- data.frame(
        USUBJID = usubjid[s],
        TRT01P = arm,
        TRT01PN = trt01pn[s],
        AESOC = ae$soc,
        AEDECOD = ae$pt,
        AESEV = as.integer(grade),
        AESER = serious,
        AEACN = action,
        AEOSI = aesi,
        AESTDY = aestdy,
        stringsAsFactors = FALSE
      )
      rec_idx <- rec_idx + 1
    }
  }
}

adae <- do.call(rbind, ae_records)

# Plant Grade 5 (death) events for subjects who died on study — drug-related in Active
died_active <- usubjid[died == 1 & trt == "Active"]
died_placebo <- usubjid[died == 1 & trt == "Placebo"]
if (length(died_active) > 0) {
  for (d in died_active) {
    s <- which(usubjid == d)
    adae <- rbind(adae, data.frame(
      USUBJID = d, TRT01P = "Active", TRT01PN = 1,
      AESOC = "General disorders", AEDECOD = "Death",
      AESEV = 5L, AESER = "Y", AEACN = "DRUG_WITHDRAWN", AEOSI = "N",
      AESTDY = followup_days[s], stringsAsFactors = FALSE))
  }
}
if (length(died_placebo) > 0) {
  for (d in died_placebo) {
    s <- which(usubjid == d)
    adae <- rbind(adae, data.frame(
      USUBJID = d, TRT01P = "Placebo", TRT01PN = 0,
      AESOC = "General disorders", AEDECOD = "Death",
      AESEV = 5L, AESER = "Y", AEACN = "DRUG_WITHDRAWN", AEOSI = "N",
      AESTDY = followup_days[s], stringsAsFactors = FALSE))
  }
}

adae <- adae[order(adae$USUBJID, adae$AESTDY), ]
rownames(adae) <- NULL

# ─── Write shared datasets ───
adsl_path  <- file.path(out_dir, "adsl_tc009.csv")
adae_path  <- file.path(out_dir, "adae_tc009.csv")
adlb_path  <- file.path(out_dir, "adlb_tc009.csv")

write_shared_data(adsl, adsl_path)
write_shared_data(adae, adae_path)
write_shared_data(adlb, adlb_path)

# ─── Summary ───
cat("\n=== TC-009 Safety Signal Data Generation Summary ===\n")
cat(sprintf("Seed: %d  N per arm: %d  N total: %d\n", seed, n_per_arm, n_total))
cat(sprintf("ADSL records: %d  ADAE records: %d  ADLB records: %d\n", nrow(adsl), nrow(adae), nrow(adlb)))
cat(sprintf("Hy's Law cases — Active: %d, Placebo: %d\n",
            sum(hys_law[trt == "Active"] == "Y"), sum(hys_law[trt == "Placebo"] == "Y")))
cat(sprintf("QTc prolonged — Active: %d, Placebo: %d\n",
            sum(qtc_prolonged[trt == "Active"] == "Y"), sum(qtc_prolonged[trt == "Placebo"] == "Y")))
cat(sprintf("Deaths on study — Active: %d, Placebo: %d\n", sum(died[trt=="Active"]), sum(died[trt=="Placebo"])))
cat(sprintf("\nFiles written:\n  %s\n  %s\n  %s\n", adsl_path, adae_path, adlb_path))
