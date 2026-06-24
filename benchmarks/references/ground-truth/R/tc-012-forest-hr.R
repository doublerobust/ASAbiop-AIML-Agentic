#!/usr/bin/env Rscript
#' TC-012: Forest Plot Data — Subgroup Hazard Ratios
#'
#' Computes hazard ratios with 95% CIs for predefined subgroups
#' using Cox proportional hazards model.
#'
#' Usage:
#'   Rscript tc-012-forest-hr.R --seed 42 --n 300 --output tc-012-output.json

suppressPackageStartupMessages({
  library(jsonlite)
  library(survival)
})

# --- Argument parsing ---
args <- commandArgs(trailingOnly = TRUE)
seed <- 42; n_subjects <- 300; output_file <- "tc-012-output.json"; data_csv <- ""
i <- 1
while (i <= length(args)) {
  if (args[i] == "--seed") { seed <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--n") { n_subjects <- as.integer(args[i + 1]); i <- i + 2 }
  else if (args[i] == "--output") { output_file <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--data") { data_csv <- args[i + 1]; i <- i + 2 }
  else { i <- i + 1 }
}

if (data_csv != "") {
  adsl <- read.csv(data_csv, stringsAsFactors = FALSE)
} else {
set.seed(seed)
n_arm <- n_subjects / 2

# --- Data generation ---
generate_surv_data <- function(n, arm, seed_offset) {
  set.seed(seed + seed_offset)
  data.frame(
    USUBJID = paste0("SUBJ-", substr(arm, 1, 1), "-", sprintf("%04d", 1:n)),
    TRT01A = arm,
    AGEGR1 = sample(c("<65", ">=65"), n, replace = TRUE),
    SEX = sample(c("Male", "Female"), n, replace = TRUE),
    ECOGGR1 = sample(c("0", "1+"), n, replace = TRUE, prob = c(0.6, 0.4)),
    REGION = sample(c("North America", "Europe", "Asia"), n, replace = TRUE),
    PRIORTRT = sample(c("Yes", "No"), n, replace = TRUE, prob = c(0.4, 0.6)),
    stringsAsFactors = FALSE
  )
}

exp_df <- generate_surv_data(n_arm, "Experimental", 100)
ctl_df <- generate_surv_data(n_arm, "Control", 200)
adsl <- rbind(exp_df, ctl_df)

# Generate survival times
set.seed(seed + 300)
base_lambda <- ifelse(adsl$TRT01A == "Experimental", 0.05 * 0.65, 0.05)
base_lambda <- base_lambda * ifelse(adsl$AGEGR1 == ">=65", 1.2, 1.0)
base_lambda <- base_lambda * ifelse(adsl$ECOGGR1 == "1+", 1.4, 1.0)
base_lambda <- base_lambda * ifelse(adsl$PRIORTRT == "Yes", 0.9, 1.0)

tte <- rexp(nrow(adsl), base_lambda)
censor_time <- runif(nrow(adsl), 18, 24)
adsl$AVAL <- pmin(tte, censor_time)
adsl$CNSR <- as.integer(tte > censor_time)
} # end of else (data generation)

# --- Cox PH subgroup analysis ---
estimate_hr <- function(data, var = NULL, val = NULL) {
  if (!is.null(var) && !is.null(val)) {
    data <- data[data[[var]] == val, ]
  }
  if (nrow(data) < 10) return(NULL)

  cox_fit <- tryCatch(
    coxph(Surv(AVAL, 1 - CNSR) ~ TRT01A, data = data),
    error = function(e) NULL
  )
  if (is.null(cox_fit)) return(NULL)

  s <- summary(cox_fit)
  ci <- s$conf.int

  list(
    hr = round(ci[1], 3),
    ci_lower = round(ci[3], 3),
    ci_upper = round(ci[4], 3),
    n_experimental = sum(data$TRT01A == "Experimental"),
    n_control = sum(data$TRT01A == "Control"),
    events_experimental = sum(data$TRT01A == "Experimental" & data$CNSR == 0),
    events_control = sum(data$TRT01A == "Control" & data$CNSR == 0)
  )
}

overall <- estimate_hr(adsl)

# Subgroup definitions
subgroups <- list(
  list(var = "AGEGR1", val = "<65", label = "Age <65"),
  list(var = "AGEGR1", val = ">=65", label = "Age >=65"),
  list(var = "SEX", val = "Male", label = "Male"),
  list(var = "SEX", val = "Female", label = "Female"),
  list(var = "ECOGGR1", val = "0", label = "ECOG PS 0"),
  list(var = "ECOGGR1", val = "1+", label = "ECOG PS 1+"),
  list(var = "REGION", val = "North America", label = "North America"),
  list(var = "REGION", val = "Europe", label = "Europe"),
  list(var = "REGION", val = "Asia", label = "Asia"),
  list(var = "PRIORTRT", val = "Yes", label = "Prior therapy: Yes"),
  list(var = "PRIORTRT", val = "No", label = "Prior therapy: No")
)

subgroup_results <- lapply(subgroups, function(sg) {
  res <- estimate_hr(adsl, sg$var, sg$val)
  if (is.null(res)) return(NULL)
  c(list(subgroup = sg$label, variable = sg$var, value = sg$val), res)
})
subgroup_results <- Filter(Negate(is.null), subgroup_results)

# Interaction p-values
interaction_pvals <- list()
for (var in c("AGEGR1", "SEX", "ECOGGR1", "REGION", "PRIORTRT")) {
  int_fit <- tryCatch(
    coxph(Surv(AVAL, 1 - CNSR) ~ TRT01A * get(var), data = adsl),
    error = function(e) NULL
  )
  if (!is.null(int_fit)) {
    s <- summary(int_fit)
    # Get interaction term p-value
    coef_table <- s$coefficients
    int_row <- grep(":", rownames(coef_table))
    if (length(int_row) > 0) {
      interaction_pvals[[var]] <- round(coef_table[int_row[1], "Pr(>|z|)"], 4)
    }
  }
}

# --- Output ---
output <- list(
  test_case_id = "TC-012",
  title = "Forest Plot — Subgroup Hazard Ratios for PFS",
  parameters = list(seed = seed, n_subjects = n_subjects),
  overall = overall,
  subgroups = subgroup_results,
  interaction_pvalues = interaction_pvals,
  metadata = list(
    language = "R",
    method = "Cox PH (survival::coxph)",
    ci_method = "Wald (log-scale)",
    packages = c("survival", "jsonlite")
  )
)

write_json(output, output_file, auto_unbox = TRUE, pretty = TRUE)
cat("TC-012 output written to:", output_file, "\n")
