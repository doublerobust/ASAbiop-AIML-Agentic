#!/usr/bin/env Rscript
# generate_tc010_csr.R — TC-010 Data Generator
# Level 3: CSR Statistical Sections (ICH E3)
#
# Generates a full ADaM suite (ADSL, ADTTE, ADRS, ADAE, ADLB) for a completed
# Phase III oncology trial of Drug X (Active) vs Placebo, with PFS as the
# primary endpoint per RECIST 1.1. The data are generated ONCE and shared as
# CSVs so that R and Python ground-truth scripts compute IDENTICAL CSR
# statistics on the SAME data (exact cross-language verification).
#
# REGULATORY NOTE (ITT-only):
#   This is a Phase III oncology superiority trial. ITT is the SOLE primary
#   analysis population. No per-protocol analysis is performed, per FDA/EMA
#   regulatory standards. The generator sets ITTFL="Y" for all randomized
#   subjects; there is no PPFL (per-protocol flag).
#
# Datasets:
#   adsl_tc010.csv  — subject-level (demographics, disposition, exposure, deviations)
#   adtte_tc010.csv — time-to-event (PFS primary, OS secondary) per subject per endpoint
#   adrs_tc010.csv  — tumor response records (BOR: CR/PR/SD/PD/NE) per subject
#   adae_tc010.csv  — adverse event records (SOC/PT/severity/serious/action/day)
#   adlb_tc010.csv  — per-subject lab maxima (ALT/AST/BILI/HB/creatinine)
#
# Usage:
#   Rscript generate_tc010_csr.R [--seed SEED] [--n N_PER_ARM] [--out DIR]

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

cat(sprintf("[TC-010 generator] seed=%d n_per_arm=%d n_total=%d out=%s\n",
            seed, n_per_arm, n_total, out_dir))

# ─────────────────────────────────────────────────────────
# ADSL: demographics, disposition, exposure, protocol deviations
# ─────────────────────────────────────────────────────────

sex <- sample(c("M", "F"), n_total, replace = TRUE, prob = c(0.55, 0.45))
age <- round(pmax(pmin(rnorm(n_total, mean = 62, sd = 10), 85), 35))
agegr1 <- ifelse(age < 65, "<65", ">=65")
race <- sample(c("White", "Asian", "Black", "Other"), n_total, replace = TRUE,
               prob = c(0.70, 0.15, 0.10, 0.05))
ecog <- sample(c(0, 1), n_total, replace = TRUE, prob = c(0.60, 0.40))
disease_stage <- sample(c("IIIB", "IV"), n_total, replace = TRUE, prob = c(0.30, 0.70))

# Disposition: ~80% completed study, ~20% discontinued
discontinued <- rbinom(n_total, 1, ifelse(trt == "Active", 0.18, 0.22))
disc_reason <- character(n_total)
disc_reason[discontinued == 0] <- "Completed"
disc_reason_active <- sample(c("Disease progression", "Adverse event", "Withdrawal by subject", "Physician decision"),
                            sum(discontinued == 1 & trt == "Active"), replace = TRUE,
                            prob = c(0.40, 0.30, 0.20, 0.10))
disc_reason_placebo <- sample(c("Disease progression", "Adverse event", "Withdrawal by subject", "Physician decision"),
                             sum(discontinued == 1 & trt == "Placebo"), replace = TRUE,
                             prob = c(0.55, 0.15, 0.20, 0.10))
disc_reason[discontinued == 1 & trt == "Active"] <- disc_reason_active
disc_reason[discontinued == 1 & trt == "Placebo"] <- disc_reason_placebo

# Treatment exposure (months): median ~9 months
trt_dur <- round(pmax(0.5, rnorm(n_total, mean = 9, sd = 3.5)), 1)
trt_dur[discontinued == 1] <- round(pmax(0.5, runif(sum(discontinued == 1), 1, 6)), 1)

# Follow-up (days): median ~420 days
followup_days <- round(pmax(30, rnorm(n_total, mean = 420, sd = 100)))
followup_days[discontinued == 1] <- round(pmax(30, followup_days[discontinued == 1] *
                                                     runif(sum(discontinued == 1), 0.2, 0.7)))

# Death on study / during follow-up: higher in Placebo
died <- rbinom(n_total, 1, ifelse(trt == "Active", 0.22, 0.38))

# Major protocol deviations: ~15% overall
major_deviation <- rbinom(n_total, 1, 0.15)
n_deviations <- ifelse(major_deviation == 1,
                       sample(1:3, n_total, replace = TRUE, prob = c(0.70, 0.25, 0.05)),
                       0)

adsl <- data.frame(
  USUBJID = usubjid,
  STUDYID = "BENCHMARK-010",
  TRT01P = trt,
  TRT01PN = trt01pn,
  ITTFL = "Y",
  SAFFL = "Y",
  SEX = sex,
  AGE = age,
  AGEGR1 = agegr1,
  RACE = race,
  ECOG = ecog,
  DISEASE_STAGE = disease_stage,
  DISCONTINUED = discontinued,
  DISC_REASON = disc_reason,
  TRT_DURATION_MO = trt_dur,
  FOLLOWUP_DAYS = followup_days,
  DIED = died,
  MAJOR_DEVIATION = major_deviation,
  N_DEVIATIONS = n_deviations,
  stringsAsFactors = FALSE
)

# ─────────────────────────────────────────────────────────
# ADTTE: time-to-event (PFS primary, OS secondary)
# ─────────────────────────────────────────────────────────
# PFS: exponential, median ~5.5 months Placebo, HR ~0.62 Active (significant benefit)
# Censoring ~30%
pfs_rate_placebo <- log(2) / 5.5
pfs_rate_active <- pfs_rate_placebo * 0.62

pfs_event_time <- ifelse(trt == "Active",
                          rexp(n_total, rate = pfs_rate_active),
                          rexp(n_total, rate = pfs_rate_placebo))
pfs_censor_time <- rexp(n_total, rate = log(2) / 14)  # independent censoring, median ~14 mo
pfs_aval <- round(pmin(pfs_event_time, pfs_censor_time) * 30.44, 1)  # convert months→days
pfs_cnsr <- as.integer(pfs_event_time > pfs_censor_time)  # 1 = censored, 0 = event
pfs_cnsr[pfs_aval > 730] <- 1L
pfs_aval[pfs_aval > 730] <- 730

# OS: exponential, median ~16 months Placebo, HR ~0.72 Active
os_rate_placebo <- log(2) / 16
os_rate_active <- os_rate_placebo * 0.72

os_event_time <- ifelse(trt == "Active",
                         rexp(n_total, rate = os_rate_active),
                         rexp(n_total, rate = os_rate_placebo))
os_censor_time <- rexp(n_total, rate = log(2) / 30)
os_aval <- round(pmin(os_event_time, os_censor_time) * 30.44, 1)
os_cnsr <- as.integer(os_event_time > os_censor_time)
os_aval[os_aval > 1460] <- 1460
os_cnsr[os_aval > 1460] <- 1L

adtte <- data.frame(
  USUBJID = rep(usubjid, 2),
  STUDYID = "BENCHMARK-010",
  TRT01P = rep(trt, 2),
  TRT01PN = rep(trt01pn, 2),
  ITTFL = "Y",
  PARAM = rep(c("PFS", "OS"), each = n_total),
  PARAMCD = rep(c("PFS", "OS"), each = n_total),
  AVAL = c(pfs_aval, os_aval),
  CNSR = c(pfs_cnsr, os_cnsr),
  stringsAsFactors = FALSE
)

# ─────────────────────────────────────────────────────────
# ADRS: tumor response (BOR per RECIST 1.1)
# ─────────────────────────────────────────────────────────
# Active: ORR ~35% (CR 5% + PR 30%), Placebo: ORR ~6% (CR 1% + PR 5%)
# DCR = CR + PR + SD
bor_active <- sample(c("CR", "PR", "SD", "PD", "NE"), n_per_arm, replace = TRUE,
                     prob = c(0.05, 0.30, 0.35, 0.25, 0.05))
bor_placebo <- sample(c("CR", "PR", "SD", "PD", "NE"), n_per_arm, replace = TRUE,
                      prob = c(0.01, 0.05, 0.39, 0.50, 0.05))
bor <- c(bor_placebo, bor_active)
response_day <- round(runif(n_total, 30, 120))

adrs <- data.frame(
  USUBJID = usubjid,
  STUDYID = "BENCHMARK-010",
  TRT01P = trt,
  TRT01PN = trt01pn,
  ITTFL = "Y",
  PARAM = "Best Overall Response",
  PARAMCD = "BOR",
  AVALC = bor,
  AVAL = match(bor, c("CR", "PR", "SD", "PD", "NE")) - 1,  # 0=NE,1=PD,2=SD,3=PR,4=CR
  RESPONSE_DAY = response_day,
  stringsAsFactors = FALSE
)

# ─────────────────────────────────────────────────────────
# ADAE: adverse events (SOC/PT/severity/serious/action/day)
# ─────────────────────────────────────────────────────────
soc_pts <- list(
  "Gastrointestinal disorders" = c("Nausea", "Diarrhoea", "Vomiting", "Constipation", "Abdominal pain"),
  "General disorders" = c("Fatigue", "Pyrexia", "Oedema peripheral"),
  "Skin and subcutaneous tissue disorders" = c("Rash", "Pruritus", "Alopecia"),
  "Blood and lymphatic system disorders" = c("Anaemia", "Neutropenia", "Thrombocytopenia"),
  "Nervous system disorders" = c("Headache", "Dizziness", "Peripheral sensory neuropathy"),
  "Respiratory, thoracic and mediastinal disorders" = c("Cough", "Dyspnoea"),
  "Investigations" = c("AST increased", "ALT increased", "Blood creatinine increased"),
  "Metabolism and nutrition disorders" = c("Decreased appetite", "Hypokalaemia")
)

ae_rows <- list()
ae_id <- 1
for (s in seq_len(n_total)) {
  # Active: ~85% have any AE, Placebo: ~65%
  p_any <- ifelse(trt[s] == "Active", 0.85, 0.65)
  if (runif(1) < p_any) {
    n_ae <- sample(1:6, 1, prob = c(0.20, 0.30, 0.25, 0.15, 0.07, 0.03))
    soc_names <- names(soc_pts)
    chosen_soc <- sample(soc_names, n_ae, replace = TRUE)
    for (j in seq_len(n_ae)) {
      soc <- chosen_soc[j]
      pt <- sample(soc_pts[[soc]], 1)
      grade <- sample(1:5, 1, prob = c(0.55, 0.25, 0.12, 0.06, 0.02))
      serious <- as.integer(grade >= 4 | (grade == 3 && runif(1) < 0.3))
      action <- ifelse(grade >= 4, "Drug withdrawn",
                       ifelse(grade == 3 && runif(1) < 0.4, "Dose reduced",
                              ifelse(runif(1) < 0.15, "Dose interrupted", "None")))
      ae_day <- round(runif(1, 1, max(1, followup_days[s])))
      ae_rows[[ae_id]] <- data.frame(
        USUBJID = usubjid[s], STUDYID = "BENCHMARK-010",
        TRT01P = trt[s], TRT01PN = trt01pn[s], SAFFL = "Y",
        AESOC = soc, AEDECOD = pt,
        AESEV = paste0("Grade ", grade), AETOXGR = grade,
        AESER = ifelse(serious == 1, "Y", "N"),
        AEACN = action, AESTDY = ae_day,
        stringsAsFactors = FALSE
      )
      ae_id <- ae_id + 1
    }
  }
}
adae <- do.call(rbind, ae_rows)
rownames(adae) <- NULL

# ─────────────────────────────────────────────────────────
# ADLB: per-subject lab maxima (ALT, AST, BILIRUBIN, HEMOGLOBIN, CREATININE)
# ─────────────────────────────────────────────────────────
alt_uln <- 40; ast_uln <- 40; bili_uln <- 1.2
alt_max <- round(pmax(5, rnorm(n_total, ifelse(trt == "Active", 30, 24), 12)), 1)
ast_max <- round(pmax(5, rnorm(n_total, ifelse(trt == "Active", 28, 24), 10)), 1)
bili_max <- round(pmax(0.2, rnorm(n_total, 0.7, 0.25)), 2)
hb_max <- round(pmax(6, rnorm(n_total, ifelse(trt == "Active", 11.5, 12.5), 1.5)), 1)
creat_max <- round(pmax(0.4, rnorm(n_total, 0.9, 0.2)), 2)

adlb <- data.frame(
  USUBJID = usubjid, STUDYID = "BENCHMARK-010",
  TRT01P = trt, TRT01PN = trt01pn, SAFFL = "Y",
  ALT_MAX = alt_max, AST_MAX = ast_max, BILI_MAX = bili_max,
  HB_MAX = hb_max, CREAT_MAX = creat_max,
  ALT_3XULN = as.integer(alt_max > 3 * alt_uln),
  AST_3XULN = as.integer(ast_max > 3 * ast_uln),
  BILI_2XULN = as.integer(bili_max > 2 * bili_uln),
  stringsAsFactors = FALSE
)

# ─── Write shared CSVs ───
write.csv(adsl, file.path(out_dir, "adsl_tc010.csv"), row.names = FALSE)
write.csv(adtte, file.path(out_dir, "adtte_tc010.csv"), row.names = FALSE)
write.csv(adrs, file.path(out_dir, "adrs_tc010.csv"), row.names = FALSE)
write.csv(adae, file.path(out_dir, "adae_tc010.csv"), row.names = FALSE)
write.csv(adlb, file.path(out_dir, "adlb_tc010.csv"), row.names = FALSE)

cat(sprintf("[TC-010 generator] Wrote 5 datasets to %s/\n", out_dir))
cat(sprintf("  ADSL: %d subjects | ADTTE: %d rows | ADRS: %d | ADAE: %d rows | ADLB: %d\n",
            nrow(adsl), nrow(adtte), nrow(adrs), nrow(adae), nrow(adlb)))
cat("[TC-010 generator] Done.\n")
