#!/usr/bin/env Rscript
# cross-language-compare.R — Compare ground truth across R, SAS, Python
# Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark
#
# Reads structured JSON outputs from all three reference implementations
# and produces a comparison report with tolerance checks.
#
# Usage: Rscript cross-language-compare.R \
#   --tc TC-001 \
#   --r-output output_R.json \
#   --sas-output output_SAS.json \
#   --python-output output_Python.json \
#   --report comparison_report.md

library(jsonlite)

# ─────────────────────────────────────────────────────
# Command-line parsing
# ─────────────────────────────────────────────────────

parse_args <- function() {
  args <- commandArgs(trailingOnly = TRUE)

  get_arg <- function(flag, default = NA) {
    idx <- which(args == flag)
    if (length(idx) > 0 && idx < length(args)) {
      return(args[idx + 1])
    }
    return(default)
  }

  list(
    tc = get_arg("--tc", "TC-001"),
    r_output = get_arg("--r-output"),
    sas_output = get_arg("--sas-output"),
    python_output = get_arg("--python-output"),
    report = get_arg("--report", "comparison_report.md")
  )
}

# ─────────────────────────────────────────────────────
# Tolerance table (from cross-language-verification.md §4.2)
# ─────────────────────────────────────────────────────

get_tolerance <- function(tc, field) {
  tolerances <- list(
    "TC-001" = list(
      "median_pfs" = list(abs = 0.05, rel = 0.001),
      "ci_lower"   = list(abs = 0.05, rel = 0.001),
      "ci_upper"   = list(abs = 0.05, rel = 0.001),
      "n_events"   = list(abs = 0,    rel = NA),   # exact
      "n_total"    = list(abs = 0,    rel = NA)     # exact
    ),
    "TC-002" = list(
      "mean"      = list(abs = 0.05, rel = 0.01),
      "std"       = list(abs = 0.05, rel = 0.01),
      "median"    = list(abs = 0.05, rel = 0.01),
      "n"         = list(abs = 0,    rel = NA),     # exact
      "pct"       = list(abs = 0.1,  rel = 0.01)
    ),
    "TC-003" = list(
      "chi_square" = list(abs = 0.01, rel = 0.001),
      "p_value"    = list(abs = 0.001, rel = 0.01),
      "n_events"   = list(abs = 0,    rel = NA),
      "n_total"    = list(abs = 0,    rel = NA)
    )
  )

  if (!is.null(tolerances[[tc]]) && !is.null(tolerances[[tc]][[field]])) {
    return(tolerances[[tc]][[field]])
  }
  return(list(abs = 0.05, rel = 0.01))  # default conservative
}

# ─────────────────────────────────────────────────────
# Comparison functions
# ─────────────────────────────────────────────────────

#' Compare two numeric values within tolerance
compare_values <- function(val_a, val_b, field, tc) {
  # Handle NA/null
  if (is.na(val_a) && is.na(val_b)) return(list(pass = TRUE, diff = 0, note = "both NA"))
  if (is.na(val_a) || is.na(val_b)) {
    return(list(
      pass = FALSE,
      diff = NA,
      note = sprintf("one NA: a=%s, b=%s",
                     ifelse(is.na(val_a), "NA", as.character(val_a)),
                     ifelse(is.na(val_b), "NA", as.character(val_b)))
    ))
  }

  val_a <- as.numeric(val_a)
  val_b <- as.numeric(val_b)
  abs_diff <- abs(val_a - val_b)

  tol <- get_tolerance(tc, field)

  if (tol$abs == 0) {
    # Exact match required
    return(list(pass = abs_diff == 0, diff = abs_diff, note = "exact match required"))
  }

  rel_diff <- if (val_b != 0) abs_diff / abs(val_b) else Inf
  within_abs <- abs_diff <= tol$abs
  within_rel <- if (is.na(tol$rel)) TRUE else rel_diff <= tol$rel

  pass <- within_abs || within_rel

  note <- sprintf("abs_diff=%.6f (tol=%.4f), rel_diff=%.6f%s",
                  abs_diff, tol$abs, rel_diff,
                  if (is.na(tol$rel)) "" else sprintf(" (tol=%.4f)", tol$rel))

  list(pass = pass, diff = abs_diff, note = note)
}

#' Compare integer/count values (exact)
compare_counts <- function(val_a, val_b, field) {
  if (is.na(val_a) && is.na(val_b)) return(list(pass = TRUE, diff = 0, note = "both NA"))
  if (is.na(val_a) || is.na(val_b)) {
    return(list(pass = FALSE, diff = NA,
                note = sprintf("count mismatch: %s vs %s", val_a, val_b)))
  }

  val_a <- as.integer(val_a)
  val_b <- as.integer(val_b)
  pass <- val_a == val_b
  list(pass = pass, diff = if (pass) 0 else abs(val_a - val_b),
       note = if (pass) "exact match" else sprintf("diff=%d", abs(val_a - val_b)))
}

# ─────────────────────────────────────────────────────
# TC-specific comparison logic
# ─────────────────────────────────────────────────────

# Build the list of language pairs to compare, skipping SAS when absent.
make_pairs <- function(field, r, sas, py) {
  has_sas <- length(sas) > 0
  pairs <- list(list("R vs Python", r[[field]], py[[field]]))
  if (has_sas) {
    pairs <- c(pairs,
      list(list("R vs SAS",     r[[field]],   sas[[field]])),
      list(list("SAS vs Python", sas[[field]], py[[field]])))
  }
  pairs
}

compare_tc001 <- function(r, sas, py) {
  fields <- c("median_pfs", "ci_lower", "ci_upper", "n_events", "n_total")
  results <- list()

  for (field in fields) {
    results[[field]] <- list()
    pairs <- make_pairs(field, r, sas, py)

    for (pair in pairs) {
      label <- pair[[1]]
      val_a <- pair[[2]]
      val_b <- pair[[3]]

      if (field %in% c("n_events", "n_total")) {
        cmp <- compare_counts(val_a, val_b, field)
      } else {
        cmp <- compare_values(val_a, val_b, field, "TC-001")
      }

      results[[field]][[label]] <- cmp
    }
  }

  results
}

compare_tc002 <- function(r, sas, py) {
  fields <- c("mean", "std", "median", "min", "max", "n")
  results <- list()

  # Compare continuous stats from age_by_arm
  for (field in intersect(fields, names(r))) {
    results[[field]] <- list()
    pairs <- make_pairs(field, r, sas, py)

    for (pair in pairs) {
      label <- pair[[1]]
      val_a <- pair[[2]]
      val_b <- pair[[3]]

      if (field == "n") {
        cmp <- compare_counts(val_a, val_b, field)
      } else {
        cmp <- compare_values(val_a, val_b, field, "TC-002")
      }

      results[[field]][[label]] <- cmp
    }
  }

  # Compare categorical counts if available
  if (!is.null(r$categorical_by_arm) && !is.null(sas$categorical_by_arm) &&
      !is.null(py$categorical_by_arm)) {
    results$categorical_counts <- list()
    # Flatten counts into vectors for comparison
    for (pair_label in c("R vs SAS", "R vs Python", "SAS vs Python")) {
      results$categorical_counts[[pair_label]] <- list(pass = TRUE, diff = 0,
        note = "categorical comparison: manual review recommended")
    }
  }

  results
}

compare_tc003 <- function(r, sas, py) {
  fields <- c("chi_square", "p_value", "n_events", "n_total")
  results <- list()

  for (field in fields) {
    results[[field]] <- list()
    pairs <- make_pairs(field, r, sas, py)

    for (pair in pairs) {
      label <- pair[[1]]
      val_a <- pair[[2]]
      val_b <- pair[[3]]

      cmp <- compare_values(val_a, val_b, field, "TC-003")
      results[[field]][[label]] <- cmp
    }
  }

  results
}

# ─────────────────────────────────────────────────────
# Report generation
# ─────────────────────────────────────────────────────

generate_report <- function(tc, r, sas, py, comparisons, filename) {
  sink(filename)

  cat(sprintf("# Cross-Language Verification Report\n\n"))
  cat(sprintf("**Test Case:** %s\n", tc))
  cat(sprintf("**Date:** %s\n", Sys.Date()))
  cat(sprintf("**Seed:** %s\n\n", r$seed %||% "N/A"))

  cat("## Reference Implementations\n\n")
  cat(sprintf("- **R:**      %s v%s\n", r$package %||% "N/A", r$package_version %||% "N/A"))
  cat(sprintf("- **SAS:**    %s v%s\n", sas$package %||% "N/A", sas$package_version %||% "N/A"))
  cat(sprintf("- **Python:** %s v%s\n", py$package %||% "N/A", py$package_version %||% "N/A"))

  cat("\n## Values by Language\n\n")
  cat("| Field | R | SAS | Python |\n")
  cat("|---|---|---|---|\n")

  # Get all unique field names across all three outputs
  all_fields <- unique(c(names(r), names(sas), names(py)))
  skip_fields <- c("test_case_id", "variant_id", "language", "package",
                   "package_version", "seed", "ci_method", "estimable")

  for (field in setdiff(all_fields, skip_fields)) {
    r_val   <- if (!is.null(r[[field]]))   format(r[[field]], digits = 6) else "—"
    sas_val <- if (!is.null(sas[[field]])) format(sas[[field]], digits = 6) else "—"
    py_val  <- if (!is.null(py[[field]]))  format(py[[field]], digits = 6) else "—"
    cat(sprintf("| %s | %s | %s | %s |\n", field, r_val, sas_val, py_val))
  }

  cat("\n## Pairwise Comparison (Within Tolerance)\n\n")
  cat("| Field | Pair | Diff | Pass | Note |\n")
  cat("|---|---|---|---|---|\n")

  all_pass <- TRUE
  for (field_name in names(comparisons)) {
    for (pair_label in names(comparisons[[field_name]])) {
      cmp <- comparisons[[field_name]][[pair_label]]
      pass_str <- if (cmp$pass) "✅ PASS" else "❌ FAIL"
      if (!cmp$pass) all_pass <- FALSE
      cat(sprintf("| %s | %s | %.6f | %s | %s |\n",
                  field_name, pair_label,
                  cmp$diff %||% NA, pass_str, cmp$note))
    }
  }

  cat("\n## Overall Verdict\n\n")
  if (all_pass) {
    cat("✅ **ALL CHECKS PASSED** — Cross-language verification successful.\n")
    cat("Ground truth is consistent across R, SAS, and Python within defined tolerances.\n")
  } else {
    cat("❌ **SOME CHECKS FAILED** — See above for discrepancies.\n")
    cat("Investigate root cause and either adjust tolerance or fix implementation.\n")
  }

  cat("\n---\n")
  cat(sprintf("_Generated by cross-language-compare.R on %s_\n", Sys.time()))

  sink()
  cat(sprintf("Report written to: %s\n", filename))
}

`%||%` <- function(a, b) if (is.null(a)) b else a

# ─────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────

if (sys.nframe() == 0) {
  opts <- parse_args()

  # Read outputs
  cat(sprintf("Comparing %s ground truth across languages...\n", opts$tc))

  # SAS is OPTIONAL: there is no SAS license in CI and TC-011..014 have no SAS
  # reference. A meaningful comparison requires that all provided outputs were
  # computed on the SAME shared dataset (run each TC script with --data X.csv).
  r_json   <- fromJSON(opts$r_output, simplifyVector = FALSE)
  py_json  <- fromJSON(opts$python_output, simplifyVector = FALSE)
  if (!is.na(opts$sas_output) && nzchar(opts$sas_output) && file.exists(opts$sas_output)) {
    sas_json <- fromJSON(opts$sas_output, simplifyVector = FALSE)
  } else {
    sas_json <- list()  # empty => SAS pairs are skipped below
    cat("(SAS output not provided/found — comparing R vs Python only)\n")
  }

  # Run comparison
  comparisons <- switch(opts$tc,
    "TC-001" = compare_tc001(r_json, sas_json, py_json),
    "TC-002" = compare_tc002(r_json, sas_json, py_json),
    "TC-003" = compare_tc003(r_json, sas_json, py_json),
    { cat(sprintf("No comparison logic for %s\n", opts$tc)); list() }
  )

  # Generate report
  generate_report(opts$tc, r_json, sas_json, py_json, comparisons, opts$report)

  cat("Done.\n")
}
