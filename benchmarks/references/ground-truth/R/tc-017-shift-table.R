#!/usr/bin/env Rscript
# TC-017: Laboratory Shift Table
# Baseline vs post-baseline lab category shifts (LOW/NORMAL/HIGH)
# Output: JSON with shift counts per cell, overall percentages

args <- commandArgs(trailingOnly = TRUE)
seed <- 42; n <- 200; output <- ""; data_csv <- ""
i <- 1
while (i <= length(args)) {
  if (args[i] == "--seed") { seed <- as.integer(args[i+1]); i <- i + 2 }
  else if (args[i] == "--n") { n <- as.integer(args[i+1]); i <- i + 2 }
  else if (args[i] == "--output") { output <- args[i+1]; i <- i + 2 }
  else if (args[i] == "--data") { data_csv <- args[i+1]; i <- i + 2 }
  else { i <- i + 1 }
}

cat(sprintf("[%s] TC-017 Lab Shift Table | seed=%d n=%d\n", Sys.time(), seed, n))

# --- Data generation ---
generate_labs <- function(n, seed) {
  set.seed(seed)
  # Hemoglobin (g/L): normal range ~120-160 (F), 130-180 (M)
  # Low <120, Normal 120-160, High >160
  n_subj <- n
  n_visits <- 4  # baseline + 3 post-baseline

  subjects <- sprintf("SUB%04d", seq_len(n_subj))
  trt <- rep(c(1, 0), each = n_subj %/% 2)
  trt <- sample(trt)

  # Baseline lab values
  baseline_hgb <- rnorm(n_subj, mean = 140, sd = 18)

  # Worst post-baseline (most extreme deviation from normal)
  post_hgb <- mapply(function(bl, t) {
    # Treatment effect: experimental arm tends to decrease
    effect <- ifelse(t == 1, -5, 0)
    vals <- rnorm(3, mean = bl + effect, sd = 10)  # 3 post-baseline visits
    min(vals)  # worst = lowest for hemoglobin
  }, baseline_hgb, trt)

  # Categorize
  categorize <- function(x) {
    ifelse(x < 120, "LOW", ifelse(x > 160, "HIGH", "NORMAL"))
  }

  bl_cat <- categorize(baseline_hgb)
  post_cat <- categorize(post_hgb)

  data.frame(
    USUBJID = subjects,
    TRT01PN = trt,
    TRT01A = ifelse(trt == 1, "Experimental", "Control"),
    LBTEST = "Hemoglobin",
    BL_VAL = round(baseline_hgb, 2),
    BL_CAT = bl_cat,
    POST_VAL = round(post_hgb, 2),
    POST_CAT = post_cat,
    stringsAsFactors = FALSE
  )
}

if (data_csv != "") {
  df <- read.csv(data_csv, stringsAsFactors = FALSE)
} else {
  df <- generate_labs(n, seed)
}

library(jsonlite)

# --- Build shift table ---
build_shift <- function(d) {
  cats <- c("LOW", "NORMAL", "HIGH")
  # Initialize 3x3 matrix of zeros
  mat <- matrix(0L, nrow = 3, ncol = 3,
    dimnames = list(Baseline = cats, PostBaseline = cats))

  for (i in seq_len(nrow(d))) {
    bl <- d$BL_CAT[i]; post <- d$POST_CAT[i]
    if (bl %in% cats && post %in% cats) {
      mat[bl, post] <- mat[bl, post] + 1L
    }
  }

  # Convert to list format
  rows <- lapply(cats, function(bl) {
    setNames(as.list(as.integer(mat[bl, ])), cats)
  })
  names(rows) <- cats

  n_total <- sum(mat)
  # Overall percentages
  pct <- round(mat / n_total * 100, 2)

  list(
    counts = rows,
    percentages = lapply(cats, function(bl) {
      setNames(as.list(as.numeric(pct[bl, ])), cats)
    }),
    n_total = as.integer(n_total),
    # Shift summary
    n_stable_normal = as.integer(mat["NORMAL", "NORMAL"]),
    n_low_to_normal = as.integer(mat["LOW", "NORMAL"]),
    n_normal_to_low = as.integer(mat["NORMAL", "LOW"]),
    n_normal_to_high = as.integer(mat["NORMAL", "HIGH"]),
    n_high_to_normal = as.integer(mat["HIGH", "NORMAL"])
  )
}

exp_shift <- build_shift(df[df$TRT01PN == 1, ])
ctl_shift <- build_shift(df[df$TRT01PN == 0, ])
overall_shift <- build_shift(df)

result <- list(
  tc_id = "TC-017",
  tc_name = "Laboratory Shift Table",
  metadata = list(
    n_total = nrow(df),
    n_experimental = sum(df$TRT01PN == 1),
    n_control = sum(df$TRT01PN == 0),
    population = "SAFETY",
    lab_test = "Hemoglobin",
    lab_unit = "g/L",
    categories = c("LOW", "NORMAL", "HIGH"),
    thresholds = list(low = 120, high = 160),
    n_post_baseline_visits = 3,
    r_version = R.version.string
  ),
  shift_overall = overall_shift,
  shift_experimental = exp_shift,
  shift_control = ctl_shift
)

# Integer metadata
result$metadata$n_total <- as.integer(result$metadata$n_total)
result$metadata$n_experimental <- as.integer(result$metadata$n_experimental)
result$metadata$n_control <- as.integer(result$metadata$n_control)

json <- toJSON(result, auto_unbox = TRUE, pretty = TRUE)

if (output != "") {
  writeLines(json, output)
  cat(sprintf("Written: %s\n", output))
} else {
  cat(json, "\n")
}
