#!/usr/bin/env python3
"""tc_008_dose_finding.py — TC-008 Ground Truth Analysis (Python)

Level 3: End-to-End Dose-Finding Study Design with Expansion Cohort

Implements a BOIN (Bayesian Optimal Interval) dose-finding design and
simulates operating characteristics (OCs) over n_sim trials.

Mirrors the R implementation: BOIN algorithm, simulation OCs, expansion cohort.

Usage:
    python tc_008_dose_finding.py --params <path> --draws <path> [--out <path>]
    python tc_008_dose_finding.py  # uses default parameters, generates internally

Dependencies: pandas, numpy
"""

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd


# ─── Default design parameters ───
DEFAULT_DESIGN = {
    "method": "BOIN",
    "method_full": "Bayesian Optimal Interval",
    "target_dlt_rate": 0.30,
    "n_doses": 5,
    "dose_levels": [10, 20, 40, 80, 120],
    "true_dlt_rates": [0.05, 0.12, 0.25, 0.35, 0.45],
    "cohort_size": 3,
    "max_n": 30,
    "starting_dose": 1,
    "escalation_boundary": round(0.30 / 1.30, 6),
    "deescalation_boundary": round(0.30 / 0.70, 6),
    "expansion_cohort_size": 6,
}


# ─── BOIN single trial simulation ───
def simulate_boin_trial(draws_row, design):
    """Simulate a single BOIN dose-finding trial.

    Args:
        draws_row: 1D array of uniform(0,1) random draws for this trial
        design: dict with design parameters

    Returns:
        dict with rpd, total_n, total_dlt, stopped_early, stop_reason, etc.
    """
    n_doses = design["n_doses"]
    true_rates = design["true_dlt_rates"]
    cohort_size = design["cohort_size"]
    max_n = design["max_n"]
    current_dose = design["starting_dose"]  # 1-indexed
    lambda_e = design["escalation_boundary"]
    lambda_d = design["deescalation_boundary"]
    target = design["target_dlt_rate"]

    n_at_dose = [0] * n_doses
    dlt_at_dose = [0] * n_doses
    total_n = 0
    total_dlt = 0
    stopped = False
    stop_reason = ""
    draw_idx = 0  # 0-indexed in Python

    while not stopped and total_n < max_n:
        cohort_n = min(cohort_size, max_n - total_n)

        for _ in range(cohort_n):
            if draw_idx < len(draws_row):
                u = draws_row[draw_idx]
            else:
                u = np.random.random()
            draw_idx += 1

            # DLT outcome: DLT = 1 if u < true_rate[current_dose - 1] (0-indexed)
            dlt = 1 if u < true_rates[current_dose - 1] else 0

            n_at_dose[current_dose - 1] += 1
            dlt_at_dose[current_dose - 1] += dlt
            total_n += 1
            total_dlt += dlt

        # Observed DLT rate at current dose
        obs_rate = dlt_at_dose[current_dose - 1] / n_at_dose[current_dose - 1]

        # Decision
        if obs_rate < lambda_e and current_dose < n_doses:
            current_dose += 1  # Escalate
        elif obs_rate > lambda_d:
            if current_dose > 1:
                current_dose -= 1  # De-escalate
            else:
                stopped = True
                stop_reason = "Dose 1 too toxic"
        # else: stay

    if not stopped and total_n >= max_n:
        stop_reason = "Max sample size reached"

    # Select MTD/RP2D: dose with observed rate closest to target
    rpd = 0
    if not (stopped and stop_reason == "Dose 1 too toxic"):
        best_dist = float("inf")
        for d in range(n_doses):
            if n_at_dose[d] > 0:
                obs_r = dlt_at_dose[d] / n_at_dose[d]
                dist = abs(obs_r - target)
                if dist < best_dist:
                    best_dist = dist
                    rpd = d + 1  # 1-indexed

    return {
        "rpd": rpd,
        "total_n": total_n,
        "total_dlt": total_dlt,
        "stopped_early": stopped,
        "stop_reason": stop_reason,
        "n_at_dose": n_at_dose,
        "dlt_at_dose": dlt_at_dose,
    }


# ─── Main ───
def main():
    parser = argparse.ArgumentParser(description="TC-008 Dose-Finding Study Design")
    parser.add_argument("--params", type=str, default=None, help="Path to design params JSON")
    parser.add_argument("--draws", type=str, default=None, help="Path to simulation draws CSV")
    parser.add_argument("--out", type=str, default=None, help="Output JSON path")
    parser.add_argument("--ars-output", type=str, default=None,
                        help="Output ARS-compatible JSON envelope path")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-sim", type=int, default=2000)
    args = parser.parse_args()

    # Load or use default design parameters
    if args.params and Path(args.params).exists():
        design = json.loads(Path(args.params).read_text())
    else:
        design = dict(DEFAULT_DESIGN)

    # Load or generate simulation draws
    if args.draws and Path(args.draws).exists():
        sim_draws = pd.read_csv(args.draws).values
    else:
        rng = np.random.default_rng(args.seed)
        sim_draws = rng.random((args.n_sim, design["max_n"]))

    n_sim = sim_draws.shape[0]

    # Run simulations
    print(f"Running {n_sim} BOIN simulations...")

    rpd_counts = [0] * design["n_doses"]
    total_n_sum = 0
    total_dlt_sum = 0
    early_stop_count = 0
    rpd_no_safe = 0

    for sim in range(n_sim):
        trial = simulate_boin_trial(sim_draws[sim], design)

        if trial["rpd"] > 0:
            rpd_counts[trial["rpd"] - 1] += 1
        else:
            rpd_no_safe += 1
        total_n_sum += trial["total_n"]
        total_dlt_sum += trial["total_dlt"]
        if trial["stopped_early"]:
            early_stop_count += 1

    # Operating characteristics
    prob_select_rpd = [round(c / n_sim, 4) for c in rpd_counts]
    expected_n = round(total_n_sum / n_sim, 4)
    expected_dlts = round(total_dlt_sum / n_sim, 4)
    prob_early_stop = round(early_stop_count / n_sim, 4)
    prob_no_safe = round(rpd_no_safe / n_sim, 4)

    # Expansion cohort
    rpd_modal = rpd_counts.index(max(rpd_counts)) + 1  # 1-indexed
    rpd_rate = design["true_dlt_rates"][rpd_modal - 1]

    expansion = {
        "rpd": rpd_modal,
        "rpd_dose": design["dose_levels"][rpd_modal - 1],
        "n_expansion": design["expansion_cohort_size"],
        "expected_dlt_rate_at_rpd": rpd_rate,
        "purpose": "Preliminary efficacy and safety assessment at recommended Phase 2 dose",
    }

    # Assemble output
    result = {
        "tc_id": "TC-008",
        "tc_title": "End-to-End Dose-Finding Study Design with Expansion Cohort",
        "level": 3,
        "design": {
            "method": design["method"],
            "method_full": design["method_full"],
            "target_dlt_rate": design["target_dlt_rate"],
            "n_doses": design["n_doses"],
            "dose_levels": design["dose_levels"],
            "true_dlt_rates": design["true_dlt_rates"],
            "cohort_size": design["cohort_size"],
            "max_n": design["max_n"],
            "starting_dose": design["starting_dose"],
            "escalation_boundary": design["escalation_boundary"],
            "deescalation_boundary": design["deescalation_boundary"],
            "expansion_cohort_size": design["expansion_cohort_size"],
        },
        "simulation": {
            "n_sim": n_sim,
            "seed": args.seed,
            "operating_characteristics": {
                "prob_select_rpd": prob_select_rpd,
                "prob_no_safe_dose": prob_no_safe,
                "expected_n_dlts": expected_dlts,
                "expected_sample_size": expected_n,
                "prob_early_stop": prob_early_stop,
            },
        },
        "expansion_cohort": expansion,
        "stopping_rules": [
            {"id": "SR-1", "description": "Stop if dose 1 observed DLT rate exceeds de-escalation boundary (all doses too toxic)"},
            {"id": "SR-2", "description": "Stop if total sample size reaches max_n"},
            {"id": "SR-3", "description": "Select MTD/RP2D as dose with observed DLT rate closest to target"},
        ],
    }

    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2, default=str))
        print(f"Wrote output to: {args.out}")
    else:
        print("\n=== BENCHMARK OUTPUT ===")
        print(json.dumps(result, indent=2, default=str))
        print("=== END OUTPUT ===")

    # ─────────────────────────────────────────────────────
    # ARS-compatible output envelope (CDISC ARS v1.0)
    # Phase I dose-finding design — ITT/PP distinction does not apply.
    # ─────────────────────────────────────────────────────
    if args.ars_output:
        ars_envelope = build_ars(result)
        ars_path = Path(args.ars_output)
        ars_path.parent.mkdir(parents=True, exist_ok=True)
        with open(ars_path, "w") as f:
            json.dump(ars_envelope, f, indent=2, default=str)
        print(f"Wrote ARS-compatible output to: {ars_path}")


def build_ars(result: dict) -> dict:
    """Build an ARS v1.0 envelope for TC-008 dose-finding study design.

    Mirrors build_tc008() from scripts/ars-extend-level3.py. The 'result' dict
    structure matches what build_tc008 expects as 'data'.
    """
    design = result.get("design", {})
    sim = result.get("simulation", {})
    oc = sim.get("operating_characteristics", {})
    expansion = result.get("expansion_cohort", {})
    true_rates = design.get("true_dlt_rates", [])
    prob_select = oc.get("prob_select_rpd", [])
    n_doses = design.get("n_doses", 5)
    rpd = expansion.get("rpd", 3)

    def _safe_index(lst, idx):
        if lst and isinstance(lst, list) and len(lst) > idx:
            return lst[idx]
        return None

    return {
        "ars_version": "1.0",
        "analysisResult": {
            "id": "TC-008",
            "version": "1.0",
            "analysisReason": (
                "Phase I dose-finding study design with BOIN and simulation "
                "operating characteristics"
            ),
            "analysisMethod": {
                "name": "BOIN (Bayesian Optimal Interval) + Monte Carlo simulation",
                "codeTemplate": "boin(dlt_data, dose_levels, target=0.30, cohort=3, max_n=30)",
                "parameters": {
                    "target_dlt_rate": design.get("target_dlt_rate"),
                    "n_doses": design.get("n_doses"),
                    "cohort_size": design.get("cohort_size"),
                    "max_n": design.get("max_n"),
                    "escalation_boundary": design.get("escalation_boundary"),
                    "deescalation_boundary": design.get("deescalation_boundary"),
                    "n_sim": sim.get("n_sim"),
                    "seed": sim.get("seed"),
                    "expansion_cohort_size": design.get("expansion_cohort_size"),
                },
            },
            "analysisVariables": [
                {"name": "DLT", "dataset": "ADXD", "role": "dose-limiting toxicity (0/1)"},
                {"name": "DOSE", "dataset": "ADSL", "role": "dose level assigned"},
                {"name": "USUBJID", "dataset": "ADSL", "role": "subject identifier"},
            ],
            "analysisPopulation": {
                "name": "All treated patients (Phase I)",
                "filter": "SAFFL = 'Y' (all who received any study drug)",
            },
            "analysisDataset": "ADXD",
            # Dose levels are the result groups. This is a *design* test case — no
            # actual patient allocation exists yet. Per-dose sample sizes are
            # stochastic (BOIN allocates adaptively); we set n=0 to indicate the
            # design stage. Expected total N and selection probabilities are
            # captured in the statistics block.
            "resultGroups": [
                {"id": f"Dose_{i+1}", "n": 0} for i in range(n_doses)
            ],
            "documentation": (
                "Level 3 Phase I dose-finding design. ITT/PP distinction "
                "does not apply — all treated patients form the analysis set. "
                f"BOIN identifies Dose {rpd} "
                f"({expansion.get('rpd_dose')} mg) as RP2D with "
                f"{_safe_index(prob_select, rpd - 1)} "
                "selection probability. True DLT rates: "
                f"{true_rates}. Dose {rpd} (true rate "
                f"{_safe_index(true_rates, rpd - 1)}) "
                "is the true MTD (closest to target 0.30)."
            ),
            "analysisResultsData": {
                "statistics": [
                    {"name": "target_dlt_rate", "value": design.get("target_dlt_rate")},
                    {"name": "n_doses", "value": design.get("n_doses")},
                    {"name": "cohort_size", "value": design.get("cohort_size")},
                    {"name": "max_n", "value": design.get("max_n")},
                    {"name": "escalation_boundary", "value": design.get("escalation_boundary")},
                    {"name": "deescalation_boundary", "value": design.get("deescalation_boundary")},
                    {"name": "n_sim", "value": sim.get("n_sim")},
                    {"name": "prob_select_dose1", "value": _safe_index(prob_select, 0)},
                    {"name": "prob_select_dose2", "value": _safe_index(prob_select, 1)},
                    {"name": "prob_select_dose3_mtd", "value": _safe_index(prob_select, 2)},
                    {"name": "prob_select_dose4", "value": _safe_index(prob_select, 3)},
                    {"name": "prob_select_dose5", "value": _safe_index(prob_select, 4)},
                    {"name": "prob_no_safe_dose", "value": oc.get("prob_no_safe_dose")},
                    {"name": "expected_n_dlts", "value": oc.get("expected_n_dlts")},
                    {"name": "expected_sample_size", "value": oc.get("expected_sample_size")},
                    {"name": "prob_early_stop", "value": oc.get("prob_early_stop")},
                    {"name": "rpd_dose_level", "value": expansion.get("rpd")},
                    {"name": "rpd_dose_mg", "value": expansion.get("rpd_dose"), "unit": "mg"},
                    {"name": "expansion_cohort_size", "value": expansion.get("n_expansion")},
                    {"name": "expected_dlt_rate_at_rpd", "value": expansion.get("expected_dlt_rate_at_rpd")},
                ],
            },
        },
    }


if __name__ == "__main__":
    main()
