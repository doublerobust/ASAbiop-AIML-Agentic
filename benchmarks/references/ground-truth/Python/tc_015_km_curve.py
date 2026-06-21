#!/usr/bin/env python3
"""TC-015: Kaplan-Meier Curve with Risk Table
Generates KM survival curve coordinates and risk table counts.
Output: JSON with curve coordinates, CI, and risk set at specified time points.

Dependencies: lifelines, numpy, pandas
"""

import argparse
import json
import sys
import numpy as np
import pandas as pd


def generate_adtte(n: int, seed: int) -> pd.DataFrame:
    """Generate synthetic ADTTE dataset matching R structure."""
    rng = np.random.default_rng(seed)
    n_exp = n // 2
    n_ctl = n - n_exp
    trt = np.array([1] * n_exp + [0] * n_ctl)
    # Shuffle treatment assignment
    rng.shuffle(trt)

    # Survival times: gamma distribution
    ttev = np.where(
        trt == 1,
        rng.gamma(shape=1.3, scale=14.0, size=n),
        rng.gamma(shape=1.1, scale=8.0, size=n),
    )
    # Censoring: uniform
    cens = rng.uniform(low=6, high=30, size=n)
    ev = (ttev <= cens).astype(int)
    ttev = np.minimum(ttev, cens)

    # Strata
    sex = rng.choice(["F", "M"], size=n)
    ecog = rng.choice([0, 1], size=n, p=[0.6, 0.4])

    return pd.DataFrame(
        {
            "USUBJID": [f"SUB{i:04d}" for i in range(1, n + 1)],
            "TRT01PN": trt.astype(int),
            "TRT01A": np.where(trt == 1, "Experimental", "Control"),
            "AVAL": np.round(ttev, 4),
            "CNSR": 1 - ev,
            "EVNT": ev,
            "SEX": sex,
            "ECOG": ecog,
        }
    )


def extract_curve(kmf, time_points, label):
    """Extract KM curve at specified time points using lifelines."""
    from lifelines import KaplanMeierFitter

    surv_at_tps = []
    ci_lower_at_tps = []
    ci_upper_at_tps = []
    n_at_risk = []
    n_events_at_tps = []
    n_censored_at_tps = []

    ci_df = kmf.confidence_interval_

    for tp in time_points:
        # Survival probability at time t
        s = kmf.predict(tp)
        surv_at_tps.append(round(float(s), 6))

        # CI at time t — lifelines CI is indexed by timeline
        # Get the closest timeline point <= tp
        mask = kmf.survival_function_.index <= tp
        if mask.any():
            closest_idx = kmf.survival_function_.index[mask][-1]
            ci_row = ci_df.loc[closest_idx]
            ci_lower_at_tps.append(round(float(ci_row.iloc[0]), 6))
            ci_upper_at_tps.append(round(float(ci_row.iloc[1]), 6))
        else:
            ci_lower_at_tps.append(1.0)
            ci_upper_at_tps.append(1.0)

    # Number at risk at each time point
    risk_tbl = kmf.event_table
    for tp in time_points:
        at_risk_mask = (risk_tbl.index <= tp)
        if at_risk_mask.any():
            idx = np.searchsorted(risk_tbl.index.values, tp, side="right") - 1
            if idx < 0:
                idx = 0
            n_at_risk.append(int(risk_tbl.iloc[idx]["at_risk"]))
            n_events_at_tps.append(int(risk_tbl.iloc[idx]["observed"]))
            n_censored_at_tps.append(int(risk_tbl.iloc[idx]["censored"]))
        else:
            n_at_risk.append(int(risk_tbl.iloc[0]["at_risk"]))
            n_events_at_tps.append(0)
            n_censored_at_tps.append(0)

    return {
        "time_points": [float(t) for t in time_points],
        "survival": surv_at_tps,
        "ci_lower": ci_lower_at_tps,
        "ci_upper": ci_upper_at_tps,
        "n_at_risk": n_at_risk,
        "n_events": n_events_at_tps,
        "n_censored": n_censored_at_tps,
    }


def main():
    parser = argparse.ArgumentParser(description="TC-015: KM Curve with Risk Table")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--output", type=str, default="")
    parser.add_argument("--data", type=str, default="")
    args = parser.parse_args()

    print(f"[{pd.Timestamp.now()}] TC-015 KM Curve + Risk Table | seed={args.seed} n={args.n}")

    if args.data:
        adtte = pd.read_csv(args.data)
    else:
        adtte = generate_adtte(args.n, args.seed)

    from lifelines import KaplanMeierFitter
    from lifelines.statistics import multivariate_logrank_test

    time_points = [0, 3, 6, 9, 12, 15, 18, 21, 24, 30]

    # Fit KM for each arm
    kmf_exp = KaplanMeierFitter()
    kmf_ctl = KaplanMeierFitter()

    exp_df = adtte[adtte["TRT01PN"] == 1]
    ctl_df = adtte[adtte["TRT01PN"] == 0]

    kmf_exp.fit(exp_df["AVAL"], event_observed=exp_df["EVNT"], label="Experimental")
    kmf_ctl.fit(ctl_df["AVAL"], event_observed=ctl_df["EVNT"], label="Control")

    curve_exp = extract_curve(kmf_exp, time_points, "Experimental")
    curve_ctl = extract_curve(kmf_ctl, time_points, "Control")

    # Overall median
    kmf_all = KaplanMeierFitter()
    kmf_all.fit(adtte["AVAL"], event_observed=adtte["EVNT"])
    from lifelines.utils import median_survival_times

    overall_median_val = median_survival_times(kmf_all)
    overall_ci = median_survival_times(kmf_all.confidence_interval_)

    # Log-rank test
    lr_result = multivariate_logrank_test(
        adtte["AVAL"], adtte["TRT01PN"], adtte["EVNT"]
    )
    lr_chisq = float(lr_result.test_statistic)
    lr_p = float(lr_result.p_value)

    result = {
        "tc_id": "TC-015",
        "tc_name": "KM Curve with Risk Table",
        "metadata": {
            "n_total": int(len(adtte)),
            "n_experimental": int(len(exp_df)),
            "n_control": int(len(ctl_df)),
            "events_experimental": int(exp_df["EVNT"].sum()),
            "events_control": int(ctl_df["EVNT"].sum()),
            "population": "ITT",
            "time_unit": "months",
            "time_points": time_points,
            "python_version": sys.version.split()[0],
            "package": "lifelines",
        },
        "overall_median": {
            "median": round(float(overall_median_val), 4),
            "ci_lower": round(float(overall_ci.iloc[0, 0]), 4),
            "ci_upper": round(float(overall_ci.iloc[0, 1]), 4),
        },
        "logrank": {
            "chisq": round(lr_chisq, 6),
            "df": 1,
            "p_value": round(lr_p, 6),
        },
        "curve_experimental": curve_exp,
        "curve_control": curve_ctl,
    }

    js = json.dumps(result, indent=2)
    if args.output:
        with open(args.output, "w") as f:
            f.write(js)
        print(f"Written: {args.output}")
    else:
        print(js)


if __name__ == "__main__":
    main()
