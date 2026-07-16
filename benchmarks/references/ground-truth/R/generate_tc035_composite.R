#!/usr/bin/env Rscript
# TC-035 Shared Dataset Generator: Composite Efficacy (ORR/DCR/DOR)
# Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark
#
# Generates a single integrated dataset that supports:
#   - ORR (CR+PR rate) from BOR
#   - DCR (CR+PR+SD rate) from BOR
#   - DOR (KM median) from responders' time-to-event
#
# Cross-TFL consistency is built in: the same BOR determines responder
# status for DOR, ensuring ORR responders == DOR population.

library(dplyr)

# ─────────────────────────────────────────────────────
# Generate composite efficacy dataset
# ─────────────────────────────────────────────────────

generate_composite_efficacy <- function(seed = 42, n_subjects = 200, hr = 0.75) {
  set.seed(seed)

  base_rate <- log(2) / 6.0  # median PFS control = 6 months
  trt <- sample(0:1, n_subjects, replace = TRUE)
  hazard_mult <- ifelse(trt == 0, 1.0, hr)

  # Demographics
  sex <- sample(c("Male", "Female"), n_subjects, replace = TRUE, prob = c(0.55, 0.45))
  age <- round(rnorm(n_subjects, mean = 58, sd = 12))
  agegr1 <- ifelse(age < 65, "<65", ">=65")
  ecog <- sample(0:1, n_subjects, replace = TRUE, prob = c(0.6, 0.4))

  # Response probability (same as TC-020/TC-023 for cross-TFL consistency)
  orr_prob <- ifelse(trt == 1,
                     ifelse(ecog == 0, 0.45, 0.30),
                     ifelse(ecog == 0, 0.25, 0.15))

  is_responder <- rbinom(n_subjects, 1, orr_prob)
  is_cr <- ifelse(is_responder == 1, rbinom(n_subjects, 1, 0.3), 0)
  bor <- ifelse(is_cr == 1, "CR",
                ifelse(is_responder == 1, "PR",
                       sample(c("SD", "PD"), n_subjects, replace = TRUE, prob = c(0.4, 0.6))))

  # ITTFL flag
  ittfl <- ifelse(runif(n_subjects) < 0.95, "Y", "N")
  saffl <- ifelse(runif(n_subjects) < 0.98, "Y", "N")

  # DOR time-to-event data (for responders only)
  # Time to response: exponential with mean ~2 months
  time_to_response <- ifelse(is_responder == 1,
                              rexp(n_subjects, rate = 1.0 / 2.0),
                              NA)

  # Time to progression or death (from randomization)
  prog_time <- rexp(n_subjects, rate = base_rate * hazard_mult)
  death_time <- rexp(n_subjects, rate = base_rate * 0.3 * hazard_mult)
  cens_time <- rexp(n_subjects, rate = base_rate * 0.3 / 0.7)

  event_time_from_rand <- pmin(prog_time, death_time)

  # For responders: DOR = time from response to event or censoring
  has_event_after_response <- is_responder == 1 & event_time_from_rand > time_to_response
  has_cens_before_event <- is_responder == 1 & cens_time < event_time_from_rand & cens_time > time_to_response

  dor_time <- ifelse(has_event_after_response,
                     event_time_from_rand - time_to_response,
                     NA)
  dor_time <- ifelse(has_cens_before_event,
                     cens_time - time_to_response,
                     dor_time)
  dor_cnsr <- ifelse(has_event_after_response & !has_cens_before_event, 0, 1)
  dor_cnsr <- ifelse(has_cens_before_event, 1, dor_cnsr)
  dor_cnsr <- ifelse(is_responder == 0, NA, dor_cnsr)
  dor_time <- ifelse(is_responder == 0, NA, dor_time)

  data.frame(
    USUBJID = sprintf("SUBJ-%04d", 1:n_subjects),
    STUDYID = "BENCHMARK-001",
    TRT01PN = trt,
    TRT01A = ifelse(trt == 0, "Control", "Experimental"),
    SEX = sex,
    AGEGR1 = agegr1,
    ECOG = ecog,
    ITTFL = ittfl,
    SAFFL = saffl,
    BOR = bor,
    AVAL_ORR = ifelse(bor %in% c("CR", "PR"), 1, 0),
    AVAL_DCR = ifelse(bor %in% c("CR", "PR", "SD"), 1, 0),
    IS_RESPONDER = is_responder,
    TIME_TO_RESPONSE = round(time_to_response, 2),
    AVAL_DOR = round(dor_time, 2),
    CNSR_DOR = dor_cnsr,
    stringsAsFactors = FALSE
  )
}

# ─────────────────────────────────────────────────────
# Write shared dataset to CSV
# ─────────────────────────────────────────────────────

# When sourced, provides generate_composite_efficacy()
# When run directly, writes CSV to path provided as first arg

if (sys.nframe() == 0) {
  args <- commandArgs(trailingOnly = TRUE)
  seed <- as.integer(ifelse(length(args) >= 1, args[1], "42"))
  n <- as.integer(ifelse(length(args) >= 2, args[2], "200"))
  output <- ifelse(length(args) >= 3, args[3], "tc035_composite.csv")

  data <- generate_composite_efficacy(seed = seed, n_subjects = n)
  write.csv(data, output, row.names = FALSE)
  cat(sprintf("Generated %d subjects → %s\n", nrow(data), output))
  cat(sprintf("Responders: %d (Exp=%d, Ctl=%d)\n",
              sum(data$IS_RESPONDER),
              sum(data$IS_RESPONDER[data$TRT01PN == 1]),
              sum(data$IS_RESPONDER[data$TRT01PN == 0])))
}
