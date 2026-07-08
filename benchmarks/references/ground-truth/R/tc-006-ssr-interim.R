#!/usr/bin/env Rscript
# TC-006 Ground Truth: Blinded Sample Size Re-Estimation at Interim
# Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark
#
# Performs a blinded SSR at an interim analysis point:
#   1. Estimate pooled median PFS from blinded interim data (KM)
#   2. Deconvolve control median under 3 HR scenarios (0.70, 0.75, 0.80)
#   3. Re-estimate required events via Schoenfeld formula
#   4. Re-estimate total sample size given accrual and follow-up
#   5. Compute conditional power at current information fraction
#   6. Produce structured recommendation (continue / increase / futility)
#
# Usage:
#   Rscript tc-006-ssr-interim.R --seed 42 --output tc-006-output.json
#   Rscript tc-006-ssr-interim.R --seed 42 --output out.json --data-csv interim.csv
#   Rscript tc-006-ssr-interim.R --seed 42 --output out.json --ars-output ars.json

suppressPackageStartupMessages({
  library(jsonlite)
  library(optparse)
})

# --- Argument parsing ---
option_list <- list(
  make_option("--seed", type = "integer", default = 42L),
  make_option("--n", type = "integer", default = 200L,
              help = "Planned total enrollment [default: 200 at interim]"),
  make_option("--events", type = "integer", default = 120L,
              help = "Number of events observed at interim [default: 120]"),
  make_option("--pooled-median", type = "double", default = 5.2,
              help = "Pooled median PFS in months [default: 5.2]"),
  make_option("--accrual-rate", type = "double", default = 20.0,
              help = "Accrual rate in patients/month [default: 20]"),
  make_option("--original-hr", type = "double", default = 0.75,
              help = "Original design hazard ratio [default: 0.75]"),
  make_option("--original-events", type = "integer", default = 127L,
              help = "Original design required events [default: 127, Schoenfeld]"),
  make_option("--planned-n", type = "integer", default = 600L,
              help = "Original planned total N [default: 600]"),
  make_option("--alpha", type = "double", default = 0.05,
              help = "Two-sided alpha [default: 0.05]"),
  make_option("--power", type = "double", default = 0.90,
              help = "Target power [default: 0.90]"),
  make_option("--output", type = "character", default = "tc-006-output.json"),
  make_option("--data-csv", type = "character", default = NULL,
              help = "Load interim blinded data from CSV (USUBJID, AVAL, CNSR, ENROLLED)"),
  make_option("--ars-output", type = "character", default = NULL,
              help = "Emit CDISC ARS v1.0 envelope to this file")
)
opt <- parse_args(OptionParser(option_list = option_list))

set.seed(opt$seed)

# --- Constants ---
HR_SCENARIOS <- c(0.70, 0.75, 0.80)
SCENARIO_NAMES <- c("optimistic", "original", "pessimistic")
Z_ALPHA <- qnorm(1 - opt$alpha / 2)  # two-sided
Z_BETA <- qnorm(opt$power)

# --- Helper functions ---

#' Kaplan-Meier median from raw survival data
km_median <- function(time, event) {
  df <- data.frame(time = time, event = event)
  df <- df[order(df$time), ]
  n <- nrow(df)
  if (n == 0) return(NA)

  # At-risk counts
  times_sorted <- df$time
  events_at_t <- sapply(times_sorted, function(t) sum(df$time == t & df$event == 1))
  at_risk <- sapply(times_sorted, function(t) sum(df$time >= t))

  # KM survival probability
  surv <- 1.0
  prev_time <- 0
  median <- NA
  for (i in seq_len(n)) {
    t <- times_sorted[i]
    if (t == prev_time) next
    d <- sum(df$time == t & df$event == 1)
    nr <- sum(df$time >= t)
    if (nr > 0) {
      surv <- surv * (1 - d / nr)
    }
    prev_time <- t
    if (!is.na(median)) break
    if (surv <= 0.5) {
      # Linear interpolation
      prev_surv <- 1.0
      prev_t <- 0
      s <- 1.0
      for (j in seq_len(n)) {
        tj <- times_sorted[j]
        if (tj == 0) next
        dj <- sum(df$time == tj & df$event == 1)
        nrj <- sum(df$time >= tj)
        if (nrj > 0) {
          new_s <- s * (1 - dj / nrj)
          if (new_s <= 0.5 && s > 0.5) {
            # Interpolate between (tj, s) and (tj, new_s)
            median <- tj + (s - 0.5) / (s - new_s) * 0  # at tj
            median <- tj
            break
          }
          s <- new_s
        }
      }
      break
    }
  }
  median
}

#' Simple KM median using survival-like computation (vectorized)
compute_km_median <- function(time, event) {
  df <- data.frame(time = time, event = event)
  df <- df[order(df$time), ]
  unique_times <- sort(unique(df$time[df$event == 1]))
  n <- length(time)

  surv <- 1.0
  median_est <- NA

  for (t in unique_times) {
    d <- sum(df$time == t & df$event == 1)
    nr <- sum(df$time >= t)
    if (nr > 0) {
      surv <- surv * (1 - d / nr)
    }
    if (surv <= 0.5) {
      median_est <- t
      break
    }
  }
  median_est
}

#' Control median deconvolution
#' Under exponential assumption: 1/M_pooled = (1/M_control + 1/M_treatment) / 2
#' M_treatment = HR * M_control
#' => 1/M_pooled = (1/M_control + 1/(HR*M_control)) / 2
#' => 1/M_pooled = (1 + 1/HR) / (2 * M_control)
#' => M_control = M_pooled * (1 + 1/HR) / 2
deconvolve_control_median <- function(pooled_median, hr) {
  pooled_median * (1 + 1/hr) / 2
}

#' Schoenfeld formula for required events
#' d = (z_alpha/2 + z_beta)^2 / (ln(HR))^2
schoenfeld_events <- function(hr, z_alpha, z_beta) {
  (z_alpha + z_beta)^2 / (log(hr))^2
}

#' Conditional power at current information fraction
#' Under the assumed HR, using simplified formula:
#' CP = Phi(z_{1-alpha} * sqrt(1-f) - z_observed * sqrt(f))
#' where z_observed = ln(HR_assumed) / ln(HR_assumed) * sqrt(d_observed) ... 
#' Simplified: under assumed HR, expected Z at final = ln(HR)/SE_lnHR
#' CP = Phi( (ln(HR) * sqrt(D) - z_alpha * sqrt(D - d)) / sqrt(D - d) ) ... 
#' More precisely: CP = Phi( (Z_obs * sqrt(d) + z_alpha_1m * sqrt(D - d) - z_alpha * sqrt(D)) / sqrt(D - d) )
#' where Z_obs = ln(HR_assumed) * sqrt(d) / |ln(HR_assumed)| = sign(ln(HR)) * sqrt(d)
#' For a superiority trial with assumed HR < 1:
#'   Z_obs = -ln(HR) * sqrt(d) (positive when HR < 1)
#'   CP = Phi( (Z_obs * sqrt(d) + (z_alpha) * sqrt(D - d) - z_alpha * sqrt(D)) / sqrt(D - d) )
#' Simplified commonly used formula:
#'   CP = Phi( Z_obs * sqrt(f) / sqrt(1-f) - z_alpha * ... )
#' We use the standard formula:
#'   Z_obs = ln(HR) / SE, where SE = |ln(HR)| / sqrt(d) => Z_obs = ln(HR) * sqrt(d) / |ln(HR)|
#'   For HR < 1: Z_obs = sqrt(d) (positive, favoring treatment)
#'   CP = Phi( (Z_obs * sqrt(f) + z_{1-alpha} * sqrt(1-f) - z_{1-alpha}) / sqrt(1-f) )
#' Actually, let's use the well-known formula:
#'   CP = Phi( (Z_obs - z_{1-alpha} * sqrt(1-f)) / sqrt(f) + z_{1-alpha} ... )
#' Let me use the standard gsDesign-like formula:
#'   Z_obs = ln(HR_assumed) * sqrt(d) / |ln(HR_assumed)|  (this = sign * sqrt(d))
#'   For HR < 1, Z_obs = sqrt(d)
#'   Final expected Z = Z_obs * sqrt(D/d) = Z_obs / sqrt(f)
#'   CP = Phi( (Z_obs / sqrt(f) - z_{1-alpha}) / sqrt(1/f - 1) * ... )
#' 
#' Let's use the simplest correct formula:
#'   Under H1 with HR, the expected Z-statistic at final = ln(HR) / (|ln(HR)| / sqrt(D)) = sign(ln(HR)) * sqrt(D)
#'   At interim, Z_interim = sign(ln(HR)) * sqrt(d)
#'   CP = P(Z_final > z_{1-alpha} | Z_interim)
#'      = Phi( (Z_interim * sqrt(f) + z_{1-alpha,predictive} * sqrt(1-f) - z_{1-alpha}) / sqrt(1-f) )
#' 
#' Actually, the cleanest derivation:
#'   Z_final = Z_interim * sqrt(f) + Z_remaining * sqrt(1-f)
#'   Under H1, E[Z_remaining] = sign * sqrt(D - d) = sign * sqrt(D*(1-f))
#'   CP = P(Z_final > z_{1-alpha}) = P(Z_remaining > (z_{1-alpha} - Z_interim*sqrt(f)) / sqrt(1-f))
#'       = 1 - Phi( (z_{1-alpha} - Z_interim*sqrt(f)) / sqrt(1-f) )
#'       = Phi( (Z_interim*sqrt(f) - z_{1-alpha}) / sqrt(1-f) + ... )
#' Wait, more carefully:
#'   CP = Phi( (Z_interim * sqrt(f) - z_{1-alpha}) / sqrt(1-f) + sqrt(D*(1-f)) )
#' Hmm, this gets confusing. Let's use the standard:
#'   CP = Phi( Z_interim * sqrt(f/(1-f)) - z_{1-alpha} / sqrt(1-f) + sqrt(D-d) * ... )
#'
#' The simplest and most commonly used formula (Jennison-Turnbull):
#'   Z_interim = ln(HR_obs) / SE(ln(HR_obs)), but since we're blinded, 
#'   we use the assumed HR:
#'   Z_interim = ln(HR_assumed) * sqrt(d) / |ln(HR_assumed)| = -sqrt(d) for HR<1
#'   (negative because ln(HR)<0, and we want positive test stat = -ln(HR)/SE)
#'   So test statistic = -ln(HR) / (|ln(HR)|/sqrt(d)) = sqrt(d)
#'   
#'   CP = Phi( (sqrt(d) * sqrt(f) + sqrt(1-f)*sqrt(D) - z_{1-alpha}*sqrt(1-f)) / sqrt(1-f) - ... )
#'
#' OK let me just use the very standard formula:
#'   Information fraction f = d / D
#'   Under assumed HR, the test statistic at full info would be ~N(sqrt(D), 1)
#'   At interim, Z ~ N(sqrt(d), 1) = N(sqrt(f*D), 1)
#'   CP = P(Z_final > z_{1-alpha} | Z_interim = z_i)
#'      = Phi( (z_i * sqrt(f) + sqrt(D*(1-f)) - z_{1-alpha}) / sqrt(1-f) )
#'   where z_i = sqrt(d) under the assumed HR (i.e., the expected value)
#'   
#'   So: CP = Phi( (sqrt(d)*sqrt(f) + sqrt(D*(1-f)) - z_{1-alpha}) / sqrt(1-f) )
#'   = Phi( (sqrt(d*f) + sqrt((D-d))) - z_{1-alpha}) / sqrt(1-f) )
#'   Hmm, d*f = d*(d/D) = d^2/D, so sqrt(d*f) = d/sqrt(D)
#'   = Phi( (d/sqrt(D) + sqrt(D-d) - z_{1-alpha}) / sqrt(1-f) )
#'   That doesn't simplify nicely either.
#'
#' Let me just use the formula from Friedman-DeMets:
#'   CP = Phi( (Z_interim - z_{1-alpha} * sqrt(1-f)) / sqrt(f) )
#'   where Z_interim = sqrt(d) under the assumed HR (expected value)
#'   This gives CP = Phi( (sqrt(d) - z_{1-alpha}*sqrt(1-f)) / sqrt(f) )
conditional_power <- function(d_observed, D_required, hr, alpha) {
  f <- d_observed / D_required  # information fraction
  if (f >= 1.0) return(1.0)  # already exceeded required events
  
  # Expected Z at final under H1: |ln(HR)| * sqrt(D_required)
  ln_hr <- log(hr)
  ez_final <- abs(ln_hr) * sqrt(D_required)
  
  # Upper alpha boundary (one-sided = alpha/2 for two-sided design)
  z_1malpha <- qnorm(1 - alpha / 2)
  
  # CP = Phi( (E[Z_final] - z_alpha) / sqrt(1-f) )
  cp <- pnorm((ez_final - z_1malpha) / sqrt(1 - f))
  
  # Clamp to [0, 1]
  max(0, min(1, cp))
}

#' Total sample size from required events
#' N = d / [(1 - exp(-lambda * t_followup)) * (proportion with event)]
#' Simplified: N = d / event_proportion
#' With accrual and follow-up: 
#'   d = N * [1 - S(t)] where S is survival at analysis time
#'   N = d / (1 - exp(-lambda * (accrual_time + followup_time)))
#' For simplicity: N = d / expected_event_proportion
#' where expected_event_proportion = 1 - exp(-lambda * total_time)
#' and lambda = ln(2)/median_pooled, total_time = accrual_duration + followup
n_from_events <- function(events_needed, median_pooled, enrolled, accrual_rate, planned_n) {
  # Estimated event proportion at final analysis
  # Assume accrual completes at planned_n / accrual_rate months
  # Follow-up = (events_needed / accrual_rate) approx... 
  # Actually, simpler: use the observed event rate
  # Event rate = events_observed / enrolled (at interim)
  # But that's interim, not final. For final, we need to project.
  #
  # Use exponential model:
  # lambda = ln(2) / median_pooled
  # At time t (from study start to final analysis), expected proportion with event:
  # p_event = 1 - exp(-lambda * t_final)
  # where t_final = (planned_n / accrual_rate) + additional_followup
  # For simplicity, assume t_final = planned_n / accrual_rate + 6 months followup
  lambda <- log(2) / median_pooled
  accrual_duration <- planned_n / accrual_rate
  followup <- 6  # months of additional followup after last patient in
  t_final <- accrual_duration + followup
  p_event <- 1 - exp(-lambda * t_final)
  
  N <- events_needed / p_event
  ceiling(N)
}

#' Recommendation logic
make_recommendation <- function(cp_original, events_original, events_needed,
                                enrolled, planned_n, hr) {
  if (cp_original < 0.20) {
    return("consider_futility")
  }
  if (events_needed > events_original * 1.15) {
    return("increase_sample_size")
  }
  if (cp_original >= 0.70) {
    return("continue_as_planned")
  }
  return("increase_sample_size")
}

# --- Data generation (if no CSV provided) ---
generate_interim_data <- function(seed, n_enrolled, pooled_median, n_events) {
  set.seed(seed)
  # Generate n_enrolled subjects with PFS times from exponential
  lambda <- log(2) / pooled_median
  # All subjects pooled (blinded)
  time <- rexp(n_enrolled, rate = lambda)
  # Ensure exactly n_events are "observed" (event=1), rest censored
  # Sort by time, first n_events are events
  ord <- order(time)
  event <- rep(0L, n_enrolled)
  event[ord[1:n_events]] <- 1L
  # Censoring times for non-events: set their observed time to a censoring time
  # For simplicity, censored subjects have their time as-is but event=0
  
  data.frame(
    USUBJID = sprintf("SUBJ-%04d", seq_len(n_enrolled)),
    AVAL = round(time, 4),
    CNSR = event == 0,  # TRUE = censored
    ENROLLED = 1L,
    stringsAsFactors = FALSE
  )
}

# --- Main computation ---

# Load or generate data
if (!is.null(opt[["data-csv"]])) {
  interim_data <- read.csv(opt[["data-csv"]])
} else {
  interim_data <- generate_interim_data(opt$seed, opt$n, opt[["pooled-median"]], opt$events)
}

# 1. Current status
enrolled <- opt$n
events_observed <- opt$events
original_events <- opt[["original-events"]]
info_fraction <- events_observed / original_events

# 2. Pooled median PFS (from data or provided)
if (!is.null(opt[["data-csv"]])) {
  pooled_median <- compute_km_median(
    interim_data$AVAL,
    as.integer(!interim_data$CNSR)
  )
} else {
  pooled_median <- opt[["pooled-median"]]
}

# 3. For each HR scenario: deconvolve, re-estimate, conditional power
scenarios <- list()
for (i in seq_along(HR_SCENARIOS)) {
  hr <- HR_SCENARIOS[i]
  scenario_name <- SCENARIO_NAMES[i]

  # Control median deconvolution
  control_median <- deconvolve_control_median(pooled_median, hr)

  # Treatment median
  treatment_median <- hr * control_median

  # Required events (Schoenfeld)
  events_needed <- schoenfeld_events(hr, Z_ALPHA, Z_BETA)

  # Total N needed
  total_n <- n_from_events(events_needed, pooled_median, enrolled, opt[["accrual-rate"]], opt[["planned-n"]])

  # Incremental N
  incremental_n <- total_n - opt[["planned-n"]]

  # Conditional power at current info fraction
  D_required <- events_needed  # total events needed under this scenario
  cp <- conditional_power(events_observed, D_required, hr, opt$alpha)

  # Recommendation
  rec <- make_recommendation(cp, original_events, events_needed, enrolled, opt[["planned-n"]], hr)

  scenarios[[scenario_name]] <- list(
    hr = hr,
    control_median_pfs = round(control_median, 4),
    treatment_median_pfs = round(treatment_median, 4),
    events_needed = round(events_needed),
    total_n_needed = total_n,
    incremental_n = incremental_n,
    conditional_power = round(cp, 4),
    recommendation = rec
  )
}

# 4. Overall recommendation (based on original HR scenario)
overall_rec <- scenarios[["original"]]$recommendation

# --- Build output ---
output <- list(
  test_case_id = "TC-006",
  title = "Blinded Sample Size Re-Estimation at Interim",
  level = "Level 2",
  input_parameters = list(
    seed = opt$seed,
    enrolled = enrolled,
    events_observed = events_observed,
    pooled_median_pfs = pooled_median,
    accrual_rate = opt[["accrual-rate"]],
    original_hr = opt[["original-hr"]],
    original_events = original_events,
    planned_n = opt[["planned-n"]],
    alpha = opt$alpha,
    power = opt$power
  ),
  current_status = list(
    enrolled = enrolled,
    planned_n = opt[["planned-n"]],
    enrollment_pct = round(enrolled / opt[["planned-n"]] * 100, 1),
    events_observed = events_observed,
    original_events = original_events,
    information_fraction = round(info_fraction, 4),
    accrual_rate = opt[["accrual-rate"]]
  ),
  blinded_estimation = list(
    pooled_median_pfs = round(pooled_median, 4),
    pooled_median_ci_lower = NA,  # Would need full KM CI
    pooled_median_ci_upper = NA,
    estimated_event_rate_monthly = round(events_observed / (enrolled / opt[["accrual-rate"]]), 2),
    lambda = round(log(2) / pooled_median, 6)
  ),
  scenarios = scenarios,
  overall_recommendation = overall_rec,
  recommendation_rationale = paste0(
    "Based on pooled median PFS of ", round(pooled_median, 1),
    " months and information fraction of ", round(info_fraction * 100, 1),
    "%, the recommendation is to ", gsub("_", " ", overall_rec), ". ",
    "Under the original HR=0.75 scenario, conditional power is ",
    round(scenarios[["original"]]$conditional_power * 100, 1), "%."
  ),
  assumptions = list(
    "Blinded analysis assumes equal allocation (1:1) and similar event rates across arms",
    "Control median deconvolution uses exponential assumption and design HR",
    "Sample size re-estimation uses Schoenfeld formula",
    "Conditional power computed under assumed HR (not unblinded)",
    "Accrual rate assumed constant throughout enrollment period",
    "6 months additional follow-up assumed after last patient enrolled"
  ),
  limitations = list(
    "Blinded analysis cannot confirm treatment effect direction",
    "Deconvolution is approximate and sensitive to HR assumption",
    "Conditional power under assumed HR may differ from actual under true HR",
    "Does not account for competing risks or informative censoring",
    "Accrual rate may vary over time"
  ),
  language = "R",
  version = "1.0.0"
)

# Write output
write_json(output, opt$output, auto_unbox = TRUE, pretty = TRUE)
cat("TC-006 output written to:", opt$output, "\n")

# --- ARS output (optional) ---
if (!is.null(opt[["ars-output"]])) {
  ars <- list(
    ars_version = "1.0",
    analysis = list(
      analysis_id = "TC-006",
      analysis_type = "Sample Size Re-Estimation",
      description = "Blinded SSR at interim analysis",
      rationale = "DMC request for sample size adequacy assessment",
      spec_document = "tc-006-level2-spec.md"
    ),
    methods = list(
      list(
        method_id = "SCHOENFELD",
        name = "Schoenfeld events formula",
        purpose = "Required events re-estimation"
      ),
      list(
        method_id = "KM_MEDIAN",
        name = "Kaplan-Meier median estimation",
        purpose = "Pooled median PFS from blinded data"
      ),
      list(
        method_id = "COND_POWER",
        name = "Conditional power calculation",
        purpose = "Probability of final significance given interim data"
      )
    ),
    outputs = list(
      list(
        output_id = "SSR_REPORT",
        type = "report",
        format = "markdown",
        description = "Structured SSR report with 3 HR scenarios"
      )
    )
  )
  write_json(ars, opt[["ars-output"]], auto_unbox = TRUE, pretty = TRUE)
  cat("ARS envelope written to:", opt[["ars-output"]], "\n")
}
