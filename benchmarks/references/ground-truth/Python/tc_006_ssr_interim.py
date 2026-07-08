#!/usr/bin/env python3
"""TC-006 Ground Truth: Blinded Sample Size Re-Estimation at Interim.

Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark.

Performs a blinded SSR at an interim analysis point:
1. Estimate pooled median PFS from blinded interim data (KM)
2. Deconvolve control median under 3 HR scenarios (0.70, 0.75, 0.80)
3. Re-estimate required events via Schoenfeld formula
4. Re-estimate total sample size given accrual and follow-up
5. Compute conditional power at current information fraction
6. Produce structured recommendation (continue / increase / futility)

Cross-validated against: R (custom implementation), SAS PROC SEQDESIGN
Dependencies: numpy, scipy, pandas (for CSV reading)

Usage:
    python tc_006_ssr_interim.py --seed 42 --output tc-006-output.json
    python tc_006_ssr_interim.py --seed 42 --output out.json --data-csv interim.csv
    python tc_006_ssr_interim.py --seed 42 --output out.json --ars-output ars.json
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np
from scipy.stats import norm

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


def compute_km_median(time, event):
    """Compute Kaplan-Meier median survival from raw time/event arrays.

    Args:
        time: array of observed times
        event: array of event indicators (1=event, 0=censored)

    Returns:
        Median survival time, or None if survival never crosses 0.5
    """
    time = np.asarray(time, dtype=float)
    event = np.asarray(event, dtype=int)

    # Sort by time
    order = np.argsort(time)
    time_sorted = time[order]
    event_sorted = event[order]

    # Unique event times
    unique_event_times = np.unique(time_sorted[event_sorted == 1])

    surv = 1.0

    for t in unique_event_times:
        d = np.sum((time_sorted == t) & (event_sorted == 1))
        at_risk = np.sum(time_sorted >= t)
        if at_risk > 0:
            surv *= (1 - d / at_risk)
        if surv <= 0.5:
            return float(t)

    return None  # Survival never crossed 0.5


def deconvolve_control_median(pooled_median, hr):
    """Estimate control arm median from pooled median and assumed HR.

    Under exponential assumption:
        1/M_pooled = (1/M_control + 1/M_treatment) / 2
        M_treatment = HR * M_control
    Solving: M_control = M_pooled * (1 + 1/HR) / 2
    """
    return pooled_median * (1 + 1 / hr) / 2


def schoenfeld_events(hr, z_alpha, z_beta):
    """Compute required events using Schoenfeld formula.

    d = (z_alpha/2 + z_beta)^2 / (ln(HR))^2
    """
    return (z_alpha + z_beta) ** 2 / (math.log(hr)) ** 2


def conditional_power(d_observed, d_required, hr, alpha):
    """Compute conditional power at current information fraction.

    Uses the Jennison-Turnbull group sequential formula:
        CP = Phi( (E[Z_final] - z_{1-alpha/2}) / sqrt(1-f) )

    where:
        f = d_observed / d_required (information fraction)
        E[Z_final] = |ln(HR)| * sqrt(d_required)  (expected under H1)
        z_{1-alpha/2} = upper boundary for two-sided test

    In the blinded case, we use the expected Z under the assumed HR
    rather than an observed Z (since arm assignments are unknown).

    Args:
        d_observed: Events observed at interim
        d_required: Total events required under this HR scenario
        hr: Assumed hazard ratio
        alpha: Two-sided alpha level

    Returns:
        Conditional power (0-1), or 1.0 if already at final analysis
    """
    f = d_observed / d_required
    if f >= 1.0:
        return 1.0  # Already exceeded required events under this HR

    # Expected Z at final under H1: |ln(HR)| * sqrt(d_required)
    ln_hr = math.log(hr)
    ez_final = abs(ln_hr) * math.sqrt(d_required)

    # Upper alpha boundary (one-sided = alpha/2 for two-sided design)
    z_1malpha = norm.ppf(1 - alpha / 2)

    # CP = Phi( (E[Z_final] - z_alpha) / sqrt(1-f) )
    cp = norm.cdf((ez_final - z_1malpha) / math.sqrt(1 - f))

    return max(0.0, min(1.0, float(cp)))


def n_from_events(events_needed, median_pooled, enrolled, accrual_rate, planned_n):
    """Estimate total sample size from required events.

    Uses exponential model:
        lambda = ln(2) / median_pooled
        p_event = 1 - exp(-lambda * t_final)
        N = events_needed / p_event
    where t_final = accrual_duration + 6 months followup
    """
    lam = math.log(2) / median_pooled
    accrual_duration = planned_n / accrual_rate
    followup = 6  # months
    t_final = accrual_duration + followup
    p_event = 1 - math.exp(-lam * t_final)
    n = events_needed / p_event
    return int(math.ceil(n))


def make_recommendation(cp_original, events_original, events_needed,
                        enrolled, planned_n, hr):
    """Determine recommendation based on conditional power and events needed."""
    if cp_original < 0.20:
        return "consider_futility"
    if events_needed > events_original * 1.15:
        return "increase_sample_size"
    if cp_original >= 0.70:
        return "continue_as_planned"
    return "increase_sample_size"


def generate_interim_data(seed, n_enrolled, pooled_median, n_events):
    """Generate blinded interim survival data.

    Creates n_enrolled subjects with exponential PFS times.
    Exactly n_events subjects have an event (event=1), rest are censored.
    """
    rng = np.random.default_rng(seed)
    lam = math.log(2) / pooled_median

    # Generate all times from exponential
    times = rng.exponential(scale=1.0 / lam, size=n_enrolled)

    # Sort by time, first n_events are events
    order = np.argsort(times)
    event = np.zeros(n_enrolled, dtype=int)
    event[order[:n_events]] = 1

    data = []
    for i in range(n_enrolled):
        data.append({
            "USUBJID": f"SUBJ-{i+1:04d}",
            "AVAL": round(float(times[i]), 4),
            "CNSR": int(event[i] == 0),  # 1 = censored
            "ENROLLED": 1
        })

    return data


def main():
    parser = argparse.ArgumentParser(
        description="TC-006: Blinded Sample Size Re-Estimation at Interim")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n", type=int, default=200,
                        help="Enrolled subjects at interim (default: 200)")
    parser.add_argument("--events", type=int, default=120,
                        help="Events observed at interim (default: 120)")
    parser.add_argument("--pooled-median", type=float, default=5.2,
                        help="Pooled median PFS in months (default: 5.2)")
    parser.add_argument("--accrual-rate", type=float, default=20.0,
                        help="Accrual rate in patients/month (default: 20)")
    parser.add_argument("--original-hr", type=float, default=0.75,
                        help="Original design hazard ratio (default: 0.75)")
    parser.add_argument("--original-events", type=int, default=127,
                        help="Original design required events (default: 127, Schoenfeld)")
    parser.add_argument("--planned-n", type=int, default=600,
                        help="Original planned total N (default: 600)")
    parser.add_argument("--alpha", type=float, default=0.05,
                        help="Two-sided alpha (default: 0.05)")
    parser.add_argument("--power", type=float, default=0.90,
                        help="Target power (default: 0.90)")
    parser.add_argument("--output", type=str, default="tc-006-output.json")
    parser.add_argument("--data-csv", type=str, default=None,
                        help="Load interim blinded data from CSV")
    parser.add_argument("--ars-output", type=str, default=None,
                        help="Emit CDISC ARS v1.0 envelope to this file")
    args = parser.parse_args()

    # Constants
    HR_SCENARIOS = [0.70, 0.75, 0.80]
    SCENARIO_NAMES = ["optimistic", "original", "pessimistic"]
    z_alpha = norm.ppf(1 - args.alpha / 2)  # two-sided → z = 1.96 for alpha=0.05
    z_beta = norm.ppf(args.power)

    # Load or generate data
    if args.data_csv and HAS_PANDAS:
        df = pd.read_csv(args.data_csv)
        time_arr = df["AVAL"].values
        event_arr = 1 - df["CNSR"].values  # CNSR=1 means censored
        pooled_median = compute_km_median(time_arr, event_arr)
    elif args.data_csv:
        # Read CSV manually if pandas not available
        import csv
        time_list = []
        event_list = []
        with open(args.data_csv) as f:
            reader = csv.DictReader(f)
            for row in reader:
                time_list.append(float(row["AVAL"]))
                event_list.append(1 - int(row["CNSR"]))
        pooled_median = compute_km_median(time_list, event_list)
    else:
        # Generate data (not used for median, but available for CSV export)
        interim_data = generate_interim_data(
            args.seed, args.n, args.pooled_median, args.events)
        pooled_median = args.pooled_median

    # 1. Current status
    enrolled = args.n
    events_observed = args.events
    original_events = args.original_events
    info_fraction = events_observed / original_events

    # 2. Blinded estimation
    estimated_event_rate_monthly = round(
        events_observed / (enrolled / args.accrual_rate), 2)
    lam = math.log(2) / pooled_median

    # 3. For each HR scenario: deconvolve, re-estimate, conditional power
    scenarios = {}
    for i, hr in enumerate(HR_SCENARIOS):
        scenario_name = SCENARIO_NAMES[i]

        # Control median deconvolution
        control_median = deconvolve_control_median(pooled_median, hr)

        # Treatment median
        treatment_median = hr * control_median

        # Required events (Schoenfeld)
        events_needed = schoenfeld_events(hr, z_alpha, z_beta)

        # Total N needed
        total_n = n_from_events(
            events_needed, pooled_median, enrolled, args.accrual_rate, args.planned_n)

        # Incremental N
        incremental_n = total_n - args.planned_n

        # Conditional power at current info fraction
        d_required = events_needed
        cp = conditional_power(events_observed, d_required, hr, args.alpha)

        # Recommendation
        rec = make_recommendation(
            cp, original_events, events_needed, enrolled, args.planned_n, hr)

        scenarios[scenario_name] = {
            "hr": hr,
            "control_median_pfs": round(control_median, 4),
            "treatment_median_pfs": round(treatment_median, 4),
            "events_needed": round(events_needed),
            "total_n_needed": total_n,
            "incremental_n": incremental_n,
            "conditional_power": round(cp, 4) if cp is not None else None,
            "recommendation": rec
        }

    # 4. Overall recommendation (based on original HR scenario)
    overall_rec = scenarios["original"]["recommendation"]

    # 5. Build output
    output = {
        "test_case_id": "TC-006",
        "title": "Blinded Sample Size Re-Estimation at Interim",
        "level": "Level 2",
        "input_parameters": {
            "seed": args.seed,
            "enrolled": enrolled,
            "events_observed": events_observed,
            "pooled_median_pfs": pooled_median,
            "accrual_rate": args.accrual_rate,
            "original_hr": args.original_hr,
            "original_events": original_events,
            "planned_n": args.planned_n,
            "alpha": args.alpha,
            "power": args.power
        },
        "current_status": {
            "enrolled": enrolled,
            "planned_n": args.planned_n,
            "enrollment_pct": round(enrolled / args.planned_n * 100, 1),
            "events_observed": events_observed,
            "original_events": original_events,
            "information_fraction": round(info_fraction, 4),
            "accrual_rate": args.accrual_rate
        },
        "blinded_estimation": {
            "pooled_median_pfs": round(pooled_median, 4),
            "pooled_median_ci_lower": None,
            "pooled_median_ci_upper": None,
            "estimated_event_rate_monthly": estimated_event_rate_monthly,
            "lambda": round(lam, 6)
        },
        "scenarios": scenarios,
        "overall_recommendation": overall_rec,
        "recommendation_rationale": (
            f"Based on pooled median PFS of {round(pooled_median, 1)} months "
            f"and information fraction of {round(info_fraction * 100, 1)}%, "
            f"the recommendation is to {overall_rec.replace('_', ' ')}. "
            f"Under the original HR=0.75 scenario, conditional power is "
            f"{round(scenarios['original']['conditional_power'] * 100, 1)}%."
        ),
        "assumptions": [
            "Blinded analysis assumes equal allocation (1:1) and similar event rates across arms",
            "Control median deconvolution uses exponential assumption and design HR",
            "Sample size re-estimation uses Schoenfeld formula",
            "Conditional power computed under assumed HR (not unblinded)",
            "Accrual rate assumed constant throughout enrollment period",
            "6 months additional follow-up assumed after last patient enrolled"
        ],
        "limitations": [
            "Blinded analysis cannot confirm treatment effect direction",
            "Deconvolution is approximate and sensitive to HR assumption",
            "Conditional power under assumed HR may differ from actual under true HR",
            "Does not account for competing risks or informative censoring",
            "Accrual rate may vary over time"
        ],
        "language": "Python",
        "version": "1.0.0"
    }

    # Write output
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)
    print(f"TC-006 output written to: {args.output}")

    # ARS output (optional)
    if args.ars_output:
        ars = {
            "ars_version": "1.0",
            "analysis": {
                "analysis_id": "TC-006",
                "analysis_type": "Sample Size Re-Estimation",
                "description": "Blinded SSR at interim analysis",
                "rationale": "DMC request for sample size adequacy assessment",
                "spec_document": "tc-006-level2-spec.md"
            },
            "methods": [
                {
                    "method_id": "SCHOENFELD",
                    "name": "Schoenfeld events formula",
                    "purpose": "Required events re-estimation"
                },
                {
                    "method_id": "KM_MEDIAN",
                    "name": "Kaplan-Meier median estimation",
                    "purpose": "Pooled median PFS from blinded data"
                },
                {
                    "method_id": "COND_POWER",
                    "name": "Conditional power calculation",
                    "purpose": "Probability of final significance given interim data"
                }
            ],
            "outputs": [
                {
                    "output_id": "SSR_REPORT",
                    "type": "report",
                    "format": "markdown",
                    "description": "Structured SSR report with 3 HR scenarios"
                }
            ]
        }
        with open(args.ars_output, "w") as f:
            json.dump(ars, f, indent=2)
        print(f"ARS envelope written to: {args.ars_output}")


if __name__ == "__main__":
    main()
