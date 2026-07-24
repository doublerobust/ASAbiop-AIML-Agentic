#!/usr/bin/env Rscript
# tc-009-safety-signal.R — TC-009 Ground Truth Analysis
# Level 3: Safety Signal Evaluation and DMC Report
#
# Performs a comprehensive safety signal evaluation for a Phase 3 oncology
# trial DMC review, covering all 8 areas specified in the TC-009 design:
#   1. AE Overview — overall/SAE/discontinuation/death rates by arm
#   2. Exposure-Adjusted AE Rates — per 100 patient-years
#   3. Grade 3+ Events — with risk difference and 95% CI
#   4. Laboratory Abnormalities — Hy's Law (hepatotoxicity), QTc prolongation
#   5. Time-to-First Grade 3+ AE — KM median, log-rank, Cox PH
#   6. AE of Special Interest — irAEs with onset timing
#   7. Statistical Signal Detection — Empirical Bayes (MGPS), risk difference
#   8. Safety Recommendation — Continue / Modify / Pause based on totality
#
# Usage:
#   Rscript tc-009-safety-signal.R --data-adsl <path> --data-adae <path> --data-adlb <path> [--out <path>]
#   Rscript tc-009-safety-signal.R  # generates data internally via generator
#
# Dependencies: survival, dplyr, jsonlite

library(survival)
library(dplyr)
library(jsonlite)

source("common/data-generation.R")

# ─── Helpers ───
# Risk difference (Active - Placebo) with 95% normal approximation CI
risk_diff_ci <- function(n_active, n_total_active, n_placebo, n_total_placebo) {
  p_a <- n_active / n_total_active
  p_p <- n_placebo / n_total_placebo
  rd <- p_a - p_p
  se <- sqrt(p_a * (1 - p_a) / n_total_active + p_p * (1 - p_p) / n_total_placebo)
  z <- qnorm(0.975)
  list(rd = round(rd, 4), ci_lower = round(rd - z * se, 4), ci_upper = round(rd + z * se, 4),
       pct_active = round(p_a * 100, 2), pct_placebo = round(p_p * 100, 2))
}

fisher_p <- function(a, b, c, d) {
  m <- matrix(c(a, b, c, d), nrow = 2)
  round(fisher.test(m)$p.value, 6)
}

# ─── Parse args ───
args <- commandArgs(trailingOnly = TRUE)
data_adsl <- NA
data_adae <- NA
data_adlb <- NA
out_path <- NA

i <- 1
while (i <= length(args)) {
  if (args[i] == "--data-adsl" && i + 1 <= length(args)) { data_adsl <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--data-adae" && i + 1 <= length(args)) { data_adae <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--data-adlb" && i + 1 <= length(args)) { data_adlb <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--out" && i + 1 <= length(args)) { out_path <- args[i + 1]; i <- i + 2 }
  else { i <- i + 1 }
}

# ─── Load or generate data ───
if (!is.na(data_adsl) && !is.na(data_adae) && !is.na(data_adlb)) {
  adsl <- read_shared_data(data_adsl)
  adae <- read_shared_data(data_adae)
  adlb <- read_shared_data(data_adlb)
} else {
  source("generate_tc009_safety_signal.R")
  shared_dir <- "cross-lang-results/shared"
  adsl <- read_shared_data(file.path(shared_dir, "adsl_tc009.csv"))
  adae <- read_shared_data(file.path(shared_dir, "adae_tc009.csv"))
  adlb <- read_shared_data(file.path(shared_dir, "adlb_tc009.csv"))
}

n_active  <- sum(adsl$TRT01P == "Active")
n_placebo <- sum(adsl$TRT01P == "Placebo")
n_total   <- n_active + n_placebo
py_active  <- round(sum(adsl$EXPOSURE_PY[adsl$TRT01P == "Active"]), 4)
py_placebo <- round(sum(adsl$EXPOSURE_PY[adsl$TRT01P == "Placebo"]), 4)

# ─── 1. AE Overview ───
# Subject-level (de-duplicated) AE flags
ae_subj <- adae %>%
  group_by(USUBJID, TRT01P) %>%
  summarise(any_ae = any(AESEV >= 1),
            any_sae = any(AESER == "Y"),
            any_disc = any(AEACN %in% c("DRUG_WITHDRAWN")),
            any_died = any(AEDECOD == "Death" | AESEV == 5),
            .groups = "drop")

# Join to ADSL to get all subjects (including those with no AE)
ae_overview_subj <- adsl %>%
  left_join(ae_subj, by = c("USUBJID", "TRT01P")) %>%
  mutate(any_ae = tidyr::replace_na(any_ae, FALSE),
         any_sae = tidyr::replace_na(any_sae, FALSE),
         any_disc = tidyr::replace_na(any_disc, FALSE),
         any_died = tidyr::replace_na(any_died, FALSE))

n_any_ae_a   <- sum(ae_overview_subj$any_ae  & ae_overview_subj$TRT01P == "Active")
n_any_ae_p   <- sum(ae_overview_subj$any_ae  & ae_overview_subj$TRT01P == "Placebo")
n_sae_a      <- sum(ae_overview_subj$any_sae & ae_overview_subj$TRT01P == "Active")
n_sae_p      <- sum(ae_overview_subj$any_sae & ae_overview_subj$TRT01P == "Placebo")
n_disc_a     <- sum(ae_overview_subj$any_disc & ae_overview_subj$TRT01P == "Active")
n_disc_p     <- sum(ae_overview_subj$any_disc & ae_overview_subj$TRT01P == "Placebo")
n_died_a     <- sum(ae_overview_subj$any_died & ae_overview_subj$TRT01P == "Active")
n_died_p     <- sum(ae_overview_subj$any_died & ae_overview_subj$TRT01P == "Placebo")

rd_any  <- risk_diff_ci(n_any_ae_a,  n_active, n_any_ae_p,  n_placebo)
rd_sae  <- risk_diff_ci(n_sae_a,     n_active, n_sae_p,     n_placebo)
rd_disc <- risk_diff_ci(n_disc_a,    n_active, n_disc_p,    n_placebo)
rd_died <- risk_diff_ci(n_died_a,    n_active, n_died_p,    n_placebo)

ae_overview <- list(
  by_arm = list(
    Active = list(n = n_active, n_any_ae = n_any_ae_a, pct_any_ae = rd_any$pct_active,
                  n_sae = n_sae_a, pct_sae = rd_sae$pct_active,
                  n_disc = n_disc_a, pct_disc = rd_disc$pct_active,
                  n_died = n_died_a, pct_died = rd_died$pct_active,
                  total_ae_reports = sum(adae$TRT01P == "Active")),
    Placebo = list(n = n_placebo, n_any_ae = n_any_ae_p, pct_any_ae = rd_any$pct_placebo,
                   n_sae = n_sae_p, pct_sae = rd_sae$pct_placebo,
                   n_disc = n_disc_p, pct_disc = rd_disc$pct_placebo,
                   n_died = n_died_p, pct_died = rd_died$pct_placebo,
                   total_ae_reports = sum(adae$TRT01P == "Placebo"))
  ),
  risk_difference = list(
    any_ae = list(rd = rd_any$rd, ci_lower = rd_any$ci_lower, ci_upper = rd_any$ci_upper,
                  fisher_p = fisher_p(n_any_ae_a, n_active - n_any_ae_a, n_any_ae_p, n_placebo - n_any_ae_p)),
    sae = list(rd = rd_sae$rd, ci_lower = rd_sae$ci_lower, ci_upper = rd_sae$ci_upper,
               fisher_p = fisher_p(n_sae_a, n_active - n_sae_a, n_sae_p, n_placebo - n_sae_p)),
    discontinuation = list(rd = rd_disc$rd, ci_lower = rd_disc$ci_lower, ci_upper = rd_disc$ci_upper,
                           fisher_p = fisher_p(n_disc_a, n_active - n_disc_a, n_disc_p, n_placebo - n_disc_p)),
    death = list(rd = rd_died$rd, ci_lower = rd_died$ci_lower, ci_upper = rd_died$ci_upper,
                 fisher_p = fisher_p(n_died_a, n_active - n_died_a, n_died_p, n_placebo - n_died_p))
  )
)

# ─── 2. Exposure-Adjusted AE Rates ───
# AEs >=5% in either arm (subject-level), rate per 100 PY
pt_freq <- adae %>%
  group_by(TRT01P, AEDECOD) %>%
  summarise(n_subjects = n_distinct(USUBJID), .groups = "drop") %>%
  mutate(pct = round(n_subjects / ifelse(TRT01P == "Active", n_active, n_placebo) * 100, 2))

common_pts <- unique(pt_freq$AEDECOD[pt_freq$pct >= 5.0])

ea_rows <- list()
for (pt in common_pts) {
  n_a <- sum(adae$AEDECOD == pt & adae$TRT01P == "Active" & !duplicated(adae$USUBJID[adae$AEDECOD == pt & adae$TRT01P == "Active"]))
  # subject-level count
  n_a <- pt_freq$n_subjects[pt_freq$AEDECOD == pt & pt_freq$TRT01P == "Active"]
  n_p <- pt_freq$n_subjects[pt_freq$AEDECOD == pt & pt_freq$TRT01P == "Placebo"]
  rate_a <- round(as.numeric(n_a) / py_active * 100, 2)
  rate_p <- round(as.numeric(n_p) / py_placebo * 100, 2)
  rd <- risk_diff_ci(as.numeric(n_a), n_active, as.numeric(n_p), n_placebo)
  ea_rows[[pt]] <- list(pt = pt, n_active = as.integer(n_a), n_placebo = as.integer(n_p),
                        rate_per_100py_active = rate_a, rate_per_100py_placebo = rate_p,
                        rd_per_100py = round(rate_a - rate_p, 2),
                        rd_pct_ci_lower = rd$ci_lower, rd_pct_ci_upper = rd$ci_upper)
}

exposure_adjusted <- list(
  total_patient_years = list(Active = py_active, Placebo = py_placebo),
  ae_per_100py = list(Active = round(sum(adae$TRT01P == "Active") / py_active * 100, 2),
                      Placebo = round(sum(adae$TRT01P == "Placebo") / py_placebo * 100, 2)),
  sae_per_100py = list(Active = round(sum(adae$TRT01P == "Active" & adae$AESER == "Y") / py_active * 100, 2),
                       Placebo = round(sum(adae$TRT01P == "Placebo" & adae$AESER == "Y") / py_placebo * 100, 2)),
  common_pts = ea_rows
)

# ─── 3. Grade 3+ Events ───
g3_subj <- adae %>%
  filter(AESEV >= 3) %>%
  group_by(TRT01P) %>%
  summarise(n_subjects = n_distinct(USUBJID), .groups = "drop")

n_g3_a <- as.integer(g3_subj$n_subjects[g3_subj$TRT01P == "Active"])
n_g3_p <- as.integer(g3_subj$n_subjects[g3_subj$TRT01P == "Placebo"])
rd_g3 <- risk_diff_ci(n_g3_a, n_active, n_g3_p, n_placebo)

# Top Grade 3+ PTs
g3_pt <- adae %>%
  filter(AESEV >= 3) %>%
  group_by(TRT01P, AEDECOD) %>%
  summarise(n = n_distinct(USUBJID), .groups = "drop")

g3_top <- list()
for (pt in unique(g3_pt$AEDECOD)) {
  n_a <- as.integer(g3_pt$n[g3_pt$AEDECOD == pt & g3_pt$TRT01P == "Active"])
  n_p <- as.integer(g3_pt$n[g3_pt$AEDECOD == pt & g3_pt$TRT01P == "Placebo"])
  if (length(n_a) == 0) n_a <- 0L
  if (length(n_p) == 0) n_p <- 0L
  rd <- risk_diff_ci(n_a, n_active, n_p, n_placebo)
  g3_top[[pt]] <- list(pt = pt, n_active = n_a, n_placebo = n_p,
                       rd = rd$rd, ci_lower = rd$ci_lower, ci_upper = rd$ci_upper)
}

grade3_plus <- list(
  by_arm = list(Active = list(n = n_g3_a, pct = rd_g3$pct_active),
                Placebo = list(n = n_g3_p, pct = rd_g3$pct_placebo)),
  risk_difference = rd_g3$rd,
  rd_ci = list(lower = rd_g3$ci_lower, upper = rd_g3$ci_upper),
  fisher_p = fisher_p(n_g3_a, n_active - n_g3_a, n_g3_p, n_placebo - n_g3_p),
  top_pts = g3_top
)

# ─── 4. Laboratory Abnormalities (Hy's Law & QTc) ───
hys_a <- sum(adlb$HYS_LAW == "Y" & adlb$TRT01P == "Active")
hys_p <- sum(adlb$HYS_LAW == "Y" & adlb$TRT01P == "Placebo")
rd_hys <- risk_diff_ci(hys_a, n_active, hys_p, n_placebo)

alt3_a <- sum(adlb$ALT_3XULN == "Y" & adlb$TRT01P == "Active")
alt3_p <- sum(adlb$ALT_3XULN == "Y" & adlb$TRT01P == "Placebo")
ast3_a <- sum(adlb$AST_3XULN == "Y" & adlb$TRT01P == "Active")
ast3_p <- sum(adlb$AST_3XULN == "Y" & adlb$TRT01P == "Placebo")
bili2_a <- sum(adlb$BILI_2XULN == "Y" & adlb$TRT01P == "Active")
bili2_p <- sum(adlb$BILI_2XULN == "Y" & adlb$TRT01P == "Placebo")

qtc_a <- sum(adlb$QTC_PROLONGED == "Y" & adlb$TRT01P == "Active")
qtc_p <- sum(adlb$QTC_PROLONGED == "Y" & adlb$TRT01P == "Placebo")
rd_qtc <- risk_diff_ci(qtc_a, n_active, qtc_p, n_placebo)

lab_abnormalities <- list(
  hys_law = list(
    n_active = as.integer(hys_a), n_placebo = as.integer(hys_p),
    pct_active = rd_hys$pct_active, pct_placebo = rd_hys$pct_placebo,
    risk_difference = rd_hys$rd, rd_ci = list(lower = rd_hys$ci_lower, upper = rd_hys$ci_upper),
    fisher_p = fisher_p(hys_a, n_active - hys_a, hys_p, n_placebo - hys_p),
    interpretation = "Hy's Law: ALT or AST >3xULN AND bilirubin >2xULN. Indicates high risk of severe drug-induced liver injury (DILI)."
  ),
  qtc_prolongation = list(
    n_active = as.integer(qtc_a), n_placebo = as.integer(qtc_p),
    pct_active = rd_qtc$pct_active, pct_placebo = rd_qtc$pct_placebo,
    risk_difference = rd_qtc$rd, rd_ci = list(lower = rd_qtc$ci_lower, upper = rd_qtc$ci_upper),
    fisher_p = fisher_p(qtc_a, n_active - qtc_a, qtc_p, n_placebo - qtc_p),
    definition = "QTc > 480ms or increase > 60ms from baseline"
  ),
  alt_elevation_3xuln = list(n_active = as.integer(alt3_a), n_placebo = as.integer(alt3_p)),
  ast_elevation_3xuln = list(n_active = as.integer(ast3_a), n_placebo = as.integer(ast3_p)),
  bili_elevation_2xuln = list(n_active = as.integer(bili2_a), n_placebo = as.integer(bili2_p))
)

# ─── 5. Time-to-First Grade 3+ AE (KM) ───
# Build per-subject time-to-event: first Grade 3+ AE day, else censored at follow-up
g3_first <- adae %>%
  filter(AESEV >= 3) %>%
  group_by(USUBJID) %>%
  summarise(first_g3_day = min(AESTDY), .groups = "drop")

tte <- adsl %>%
  left_join(g3_first, by = "USUBJID") %>%
  mutate(time = ifelse(is.na(first_g3_day), FOLLOWUP_DAYS, first_g3_day),
         event = ifelse(is.na(first_g3_day), 0, 1)) %>%
  filter(!is.na(time) & time > 0)

km_fit <- survfit(Surv(time, event) ~ TRT01P, data = tte)
km_summary <- summary(km_fit)$table
get_median_ci <- function(arm_name) {
  idx <- grep(arm_name, rownames(km_summary))
  if (length(idx) == 0) return(list(median = NA_real_, ci_lower = NA_real_, ci_upper = NA_real_))
  row <- km_summary[idx, , drop = FALSE]
  med <- as.numeric(unname(row[, "median"]))
  lcl <- as.numeric(unname(row[, "0.95LCL"]))
  ucl <- as.numeric(unname(row[, "0.95UCL"]))
  list(median = round(med, 4), ci_lower = round(lcl, 4), ci_upper = round(ucl, 4))
}

lr <- survdiff(Surv(time, event) ~ TRT01P, data = tte)
lr_p <- round(1 - pchisq(lr$chisq, df = 1), 6)

tte$TRT01P_f <- factor(tte$TRT01P, levels = c("Placebo", "Active"))
cox <- coxph(Surv(time, event) ~ TRT01P_f, data = tte)
cox_s <- summary(cox)
cox_hr <- round(cox_s$coefficients[1, "exp(coef)"], 4)
cox_ci_lo <- round(cox_s$conf.int[1, "lower .95"], 4)
cox_ci_hi <- round(cox_s$conf.int[1, "upper .95"], 4)
cox_p <- round(cox_s$coefficients[1, "Pr(>|z|)"], 6)

time_to_grade3 <- list(
  n_with_g3 = as.integer(sum(tte$event)),
  median_active = get_median_ci("Active"),
  median_placebo = get_median_ci("Placebo"),
  logrank_p = lr_p,
  cox_hr = cox_hr,
  cox_ci = list(lower = cox_ci_lo, upper = cox_ci_hi),
  cox_p = cox_p,
  n_active_events = as.integer(sum(tte$event[tte$TRT01P == "Active"])),
  n_placebo_events = as.integer(sum(tte$event[tte$TRT01P == "Placebo"]))
)

# ─── 6. AE of Special Interest (irAE) ───
irae_subj <- adae %>%
  filter(AEOSI == "Y") %>%
  group_by(TRT01P, USUBJID) %>%
  summarise(onset_day = min(AESTDY), .groups = "drop") %>%
  group_by(TRT01P) %>%
  summarise(n_subjects = n_distinct(USUBJID),
            median_onset = round(median(onset_day), 2),
            .groups = "drop")

n_irae_a <- as.integer(irae_subj$n_subjects[irae_subj$TRT01P == "Active"])
n_irae_p <- as.integer(irae_subj$n_subjects[irae_subj$TRT01P == "Placebo"])
med_onset_a <- as.numeric(irae_subj$median_onset[irae_subj$TRT01P == "Active"])
med_onset_p <- as.numeric(irae_subj$median_onset[irae_subj$TRT01P == "Placebo"])
rd_irae <- risk_diff_ci(n_irae_a, n_active, n_irae_p, n_placebo)

ae_special_interest <- list(
  irae = list(
    n_active = n_irae_a, n_placebo = n_irae_p,
    pct_active = rd_irae$pct_active, pct_placebo = rd_irae$pct_placebo,
    risk_difference = rd_irae$rd, rd_ci = list(lower = rd_irae$ci_lower, upper = rd_irae$ci_upper),
    fisher_p = fisher_p(n_irae_a, n_active - n_irae_a, n_irae_p, n_placebo - n_irae_p),
    median_onset_active = med_onset_a, median_onset_placebo = med_onset_p
  )
)

# ─── 7. Statistical Signal Detection ───
# 7a. MGPS (Empirical Bayes) — simplified EBGM with add-one-half shrinkage
# For each PT, observed (Active) vs expected (under independence) reporting
pt_active  <- adae %>% filter(TRT01P == "Active")  %>% group_by(AEDECOD) %>% summarise(o_active = n_distinct(USUBJID), .groups = "drop")
pt_placebo <- adae %>% filter(TRT01P == "Placebo") %>% group_by(AEDECOD) %>% summarise(o_placebo = n_distinct(USUBJID), .groups = "drop")
pt_all     <- full_join(pt_active, pt_placebo, by = "AEDECOD")
pt_all$o_active[is.na(pt_all$o_active)] <- 0
pt_all$o_placebo[is.na(pt_all$o_placebo)] <- 0
pt_all$n_pt_total <- pt_all$o_active + pt_all$o_placebo

mgps_rows <- list()
for (r in seq_len(nrow(pt_all))) {
  pt <- pt_all$AEDECOD[r]
  o_a <- as.numeric(pt_all$o_active[r])
  o_p <- as.numeric(pt_all$o_placebo[r])
  n_pt <- as.numeric(pt_all$n_pt_total[r])
  # Expected under independence: (n_active * n_pt_total) / n_total
  e_a <- (n_active * n_pt) / n_total
  e_p <- (n_placebo * n_pt) / n_total
  # EBGM (add-one-half shrinkage, Beta(0.5,0.5) prior on reporting proportion)
  ebgm_a <- if (e_a > 0) round((o_a + 0.5) / (e_a + 0.5), 4) else 0
  ebgm_p <- if (e_p > 0) round((o_p + 0.5) / (e_p + 0.5), 4) else 0
  signal_a <- (ebgm_a >= 2.0 && o_a >= 3 && e_a > 0)
  signal_p <- (ebgm_p >= 2.0 && o_p >= 3 && e_p > 0)
  mgps_rows[[pt]] <- list(pt = pt, o_active = as.integer(o_a), o_placebo = as.integer(o_p),
                          e_active = round(e_a, 4), e_placebo = round(e_p, 4),
                          ebgm_active = ebgm_a, ebgm_placebo = ebgm_p,
                          signal_active = signal_a, signal_placebo = signal_p)
}

# 7b. Risk difference signals (Active - Placebo, 95% CI excludes 0)
rd_signal_rows <- list()
for (pt in common_pts) {
  n_a <- as.numeric(pt_freq$n_subjects[pt_freq$AEDECOD == pt & pt_freq$TRT01P == "Active"])
  n_p <- as.numeric(pt_freq$n_subjects[pt_freq$AEDECOD == pt & pt_freq$TRT01P == "Placebo"])
  rd <- risk_diff_ci(n_a, n_active, n_p, n_placebo)
  signal <- (rd$ci_lower > 0)  # Active significantly higher
  rd_signal_rows[[pt]] <- list(pt = pt, n_active = as.integer(n_a), n_placebo = as.integer(n_p),
                               rd = rd$rd, ci_lower = rd$ci_lower, ci_upper = rd$ci_upper,
                               fisher_p = fisher_p(n_a, n_active - n_a, n_p, n_placebo - n_p),
                               signal_active_higher = signal)
}

signal_detection <- list(
  mgps = list(method = "Empirical Bayes (MGPS-style, add-one-half shrinkage)",
              threshold = "EBGM >= 2.0 AND observed >= 3",
              results = mgps_rows),
  risk_difference_signals = rd_signal_rows
)

# ─── 8. Safety Recommendation ───
# Deterministic logic based on totality of evidence
hys_signal <- (hys_a >= 5) && (rd_hys$ci_lower > 0)
qtc_signal <- (qtc_a >= 5) && (rd_qtc$ci_lower > 0)
irae_signal <- (n_irae_a >= 10) && (rd_irae$ci_lower > 0)
g3_signal <- (rd_g3$ci_lower > 0)
disc_signal <- (rd_disc$ci_lower > 0)
died_signal <- (rd_died$ci_lower > 0)

n_signals <- sum(hys_signal, qtc_signal, irae_signal, g3_signal, disc_signal)

key_findings <- c()
if (hys_signal) key_findings <- c(key_findings, sprintf("Hy's Law cases significantly higher in Active arm (%d vs %d, Fisher p=%.4f) — high DILI risk", hys_a, hys_p, lab_abnormalities$hys_law$fisher_p))
if (qtc_signal) key_findings <- c(key_findings, sprintf("QTc prolongation signal in Active arm (%d vs %d, Fisher p=%.4f)", qtc_a, qtc_p, lab_abnormalities$qtc_prolongation$fisher_p))
if (irae_signal) key_findings <- c(key_findings, sprintf("Immune-related AEs significantly higher in Active arm (%d vs %d, Fisher p=%.4f)", n_irae_a, n_irae_p, ae_special_interest$irae$fisher_p))
if (g3_signal) key_findings <- c(key_findings, sprintf("Grade 3+ AE rate higher in Active (RD=%.2f%%, 95%% CI [%.2f, %.2f])", rd_g3$rd*100, rd_g3$ci_lower*100, rd_g3$ci_upper*100))
if (disc_signal) key_findings <- c(key_findings, sprintf("Treatment discontinuation due to AEs higher in Active (RD=%.2f%%)", rd_disc$rd*100))

# Recommendation logic:
# - Hy's Law signal is the most serious (potential for fatal DILI) → at least "Modify"
# - "Pause" requires a very heavy signal burden (>=4 signals incl. Hy's Law),
#   reflecting study-halting concern. Absent fatal hepatotoxicity cases, a
#   confirmed Hy's Law signal with co-occurring irAE/Grade3+ signals warrants
#   protocol modification and enhanced monitoring ("Modify") — the standard DMC
#   action per FDA DILI guidance (Hy's Law cases trigger lab intensification,
#   not automatic termination, unless fatal DILI is observed).
if (hys_signal && n_signals >= 4) {
  recommendation <- "Pause"
  rationale <- "Multiple significant safety signals including Hy's Law hepatotoxicity with heavy overall signal burden. Recommend pausing enrollment pending protocol amendment and DMC charter review."
} else if (hys_signal || (qtc_signal && irae_signal)) {
  recommendation <- "Modify"
  rationale <- "Significant safety signal(s) detected (Hy's Law hepatotoxicity and/or combined QTc+irAE signals). Recommend continuing with enhanced monitoring, protocol amendment for hepatotoxicity/cardiac monitoring, and tighter stopping rules."
} else if (n_signals >= 2) {
  recommendation <- "Modify"
  rationale <- "Multiple safety signals detected. Recommend enhanced monitoring and protocol amendment."
} else {
  recommendation <- "Continue with enhanced monitoring"
  rationale <- "No critical safety signals requiring modification. Recommend continuing with routine DMC monitoring schedule."
}

conditions <- c()
if (hys_signal) conditions <- c(conditions, "Implement enhanced hepatotoxicity monitoring (weekly LFTs for first 8 weeks)", "Protocol amendment for Hy's Law case management algorithm", "Consider independent hepatic safety review board")
if (qtc_signal) conditions <- c(conditions, "Implement serial ECG monitoring (baseline, C1D1, C2D1, then monthly)", "Exclude subjects with baseline QTc > 470ms", "Protocol amendment for QTc prolongation management")
if (irae_signal) conditions <- c(conditions, "Implement irAE management guidelines per ASCO/NCCN", "Mandatory corticosteroid availability for Grade 2+ irAE management")
conditions <- c(conditions, "Continue routine DMC safety reviews at planned intervals")

recommendation_out <- list(
  overall = recommendation,
  rationale = rationale,
  key_findings = key_findings,
  conditions = conditions,
  signals_summary = list(hys_law = hys_signal, qtc = qtc_signal, irae = irae_signal,
                         grade3_plus = g3_signal, discontinuation = disc_signal,
                         death = died_signal, n_signals = as.integer(n_signals))
)

# ─── Assemble output ───
result <- list(
  tc_id = "TC-009",
  tc_title = "Safety Signal Evaluation and DMC Report",
  level = 3,
  study_design = list(
    n_subjects = as.integer(n_active + n_placebo),
    n_per_arm = list(Active = as.integer(n_active), Placebo = as.integer(n_placebo)),
    total_patient_years = list(Active = py_active, Placebo = py_placebo),
    arms = c("Active", "Placebo")
  ),
  ae_overview = ae_overview,
  exposure_adjusted = exposure_adjusted,
  grade3_plus = grade3_plus,
  lab_abnormalities = lab_abnormalities,
  time_to_grade3 = time_to_grade3,
  ae_special_interest = ae_special_interest,
  signal_detection = signal_detection,
  recommendation = recommendation_out
)

# ─── Output (use na="null" so non-estimable CIs serialize as JSON null,
#     matching Python's None → null) ───
write_output_tc009 <- function(result, filepath) {
  output <- jsonlite::toJSON(result, auto_unbox = TRUE, pretty = TRUE, na = "null")
  writeLines(output, filepath)
  cat(sprintf("Wrote output to: %s\n", filepath))
  invisible(result)
}

print_output_tc009 <- function(result) {
  cat("\n=== BENCHMARK OUTPUT ===\n")
  cat(jsonlite::toJSON(result, auto_unbox = TRUE, pretty = TRUE, na = "null"))
  cat("\n=== END OUTPUT ===\n")
}

if (!is.na(out_path) && nzchar(out_path)) {
  write_output_tc009(result, out_path)
} else {
  print_output_tc009(result)
}
