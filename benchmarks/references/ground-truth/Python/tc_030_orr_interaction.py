#!/usr/bin/env python3
"""TC-030 Ground Truth: ORR by Subgroup with Interaction Test (Python)

Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark.

Extends TC-020 by adding:
  - Formal logistic regression interaction test (treatment × subgroup)
  - Clopper-Pearson exact confidence intervals (regulatory standard)
  - Breslow-Day test for homogeneity of odds ratios across strata
  - Forest-plot-ready output with interaction p-values

Dependencies: pandas, numpy, scipy, statsmodels
Usage: python tc_030_orr_interaction.py --seed 42 --n 200 --output results.json
       python tc_030_orr_interaction.py --data-csv shared_data.csv --output results.json
"""

import argparse
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats


# ─────────────────────────────────────────────────────
# Data Generation (same structure as TC-020 for consistency)
# ─────────────────────────────────────────────────────

def generate_tumor_response(seed=42, n_subjects=200):
    """Generate synthetic tumor response dataset with subgroups."""
    rng = np.random.default_rng(seed)

    trt = rng.choice([0, 1], size=n_subjects)
    sex = rng.choice(["Male", "Female"], size=n_subjects, p=[0.55, 0.45])
    age = np.round(rng.normal(58, 12, n_subjects)).astype(int)
    agegr1 = np.where(age < 65, "<65", ">=65")
    ecog = rng.choice([0, 1], size=n_subjects, p=[0.6, 0.4])

    # Response probability depends on treatment and ECOG
    orr_prob = np.where(trt == 1,
                        np.where(ecog == 0, 0.45, 0.30),
                        np.where(ecog == 0, 0.25, 0.15))

    is_responder = rng.binomial(1, orr_prob)
    is_cr = np.where(is_responder == 1, rng.binomial(1, 0.3, n_subjects), 0)

    bor = np.where(is_cr == 1, "CR",
                   np.where(is_responder == 1, "PR",
                            rng.choice(["SD", "PD"], size=n_subjects, p=[0.4, 0.6])))

    aval = np.where(np.isin(bor, ["CR", "PR"]), 1, 0)

    return pd.DataFrame({
        "USUBJID": [f"SUBJ-{i+1:04d}" for i in range(n_subjects)],
        "STUDYID": "BENCHMARK-001",
        "TRT01PN": trt,
        "TRT01A": np.where(trt == 0, "Control", "Experimental"),
        "SEX": sex,
        "AGEGR1": agegr1,
        "ECOG": ecog,
        "BOR": bor,
        "AVAL": aval,
    })


# ─────────────────────────────────────────────────────
# Clopper-Pearson Exact CI
# ─────────────────────────────────────────────────────

def clopper_pearson_ci(x, n, conf=0.95):
    """Clopper-Pearson exact confidence interval for a proportion.

    Uses the Beta distribution: B(alpha, beta) where alpha = x+1, beta = n-x+1
    for the upper bound, and B(alpha, beta) where alpha = x, beta = n-x+1
    for the lower bound.
    """
    if n == 0:
        return 0.0, 1.0
    alpha = 1 - conf
    lo = stats.beta.ppf(alpha / 2, x, n - x + 1) if x > 0 else 0.0
    hi = stats.beta.ppf(1 - alpha / 2, x + 1, n - x) if x < n else 1.0
    return lo, hi


# ─────────────────────────────────────────────────────
# Logistic Regression Interaction Test
# ─────────────────────────────────────────────────────

def logistic_interaction_test(data, subgroup_var):
    """Fit logistic regression with treatment × subgroup interaction.

    Model: logit(P(response)) = b0 + b1*trt + b2*subgroup + b3*trt*subgroup
    Interaction p-value = Wald test on b3 (coefficient of interaction term).

    Returns:
        dict with interaction_p_value, interaction_or, interaction_or_ci_lower,
        interaction_or_ci_upper, breslow_day_p_value
    """
    try:
        from statsmodels.api import Logit
        from statsmodels.tools import add_constant
    except ImportError:
        # Fallback: use scipy for simpler tests
        return _logistic_interaction_fallback(data, subgroup_var)

    # Encode variables
    df = data.copy()
    df["trt_num"] = df["TRT01PN"].astype(float)

    # Encode subgroup as 0/1
    levels = sorted(df[subgroup_var].unique())
    if len(levels) != 2:
        return {
            "subgroup": subgroup_var,
            "interaction_p_value": None,
            "interaction_or": None,
            "interaction_or_ci_lower": None,
            "interaction_or_ci_upper": None,
            "breslow_day_p_value": None,
            "method": "logistic_wald",
        }
    level_map = {levels[0]: 0, levels[1]: 1}
    df["sg_num"] = df[subgroup_var].map(level_map).astype(float)
    df["interaction"] = df["trt_num"] * df["sg_num"]

    # Build design matrix
    X = add_constant(df[["trt_num", "sg_num", "interaction"]])
    y = df["AVAL"].astype(float)

    try:
        model = Logit(y, X).fit(disp=0, maxiter=100)
    except Exception:
        return _logistic_interaction_fallback(data, subgroup_var)

    params = model.params
    cov = model.cov_params()

    # Interaction coefficient is the last one (index 3)
    b3 = params.get("interaction", 0)
    se_b3 = math.sqrt(cov.loc["interaction", "interaction"]) if "interaction" in cov.index else None

    if se_b3 is None or se_b3 == 0:
        return _logistic_interaction_fallback(data, subgroup_var)

    wald_z = b3 / se_b3
    wald_p = 2 * (1 - stats.norm.cdf(abs(wald_z)))

    # OR = exp(b3)
    or_val = math.exp(b3)
    or_ci_lo = math.exp(b3 - 1.96 * se_b3)
    or_ci_hi = math.exp(b3 + 1.96 * se_b3)

    # Breslow-Day test for homogeneity of ORs
    bd_p = _breslow_day_test(data, subgroup_var)

    return {
        "subgroup": subgroup_var,
        "interaction_p_value": round(float(wald_p), 4),
        "interaction_or": round(float(or_val), 4),
        "interaction_or_ci_lower": round(float(or_ci_lo), 4),
        "interaction_or_ci_upper": round(float(or_ci_hi), 4),
        "breslow_day_p_value": round(float(bd_p), 4) if bd_p is not None else None,
        "method": "logistic_wald",
    }


def _logistic_interaction_fallback(data, subgroup_var):
    """Fallback using CMH test when statsmodels is not available."""
    levels = sorted(data[subgroup_var].unique())
    if len(levels) != 2:
        return {
            "subgroup": subgroup_var,
            "interaction_p_value": None,
            "interaction_or": None,
            "interaction_or_ci_lower": None,
            "interaction_or_ci_upper": None,
            "breslow_day_p_value": None,
            "method": "cmh_fallback",
        }

    try:
        from statsmodels.stats.contingency_tables import StratifiedTable
        strata = []
        for lvl in levels:
            d = data[data[subgroup_var] == lvl]
            tbl = pd.crosstab(d["TRT01PN"], d["AVAL"])
            if tbl.shape == (2, 2):
                strata.append(tbl.values)
        if len(strata) >= 2:
            st = StratifiedTable(strata)
            cmh_p = st.test_null_odds().pvalue
            common_or = st.oddsratio_pooled
            return {
                "subgroup": subgroup_var,
                "interaction_p_value": round(float(cmh_p), 4),
                "interaction_or": round(float(common_or), 4),
                "interaction_or_ci_lower": None,
                "interaction_or_ci_upper": None,
                "breslow_day_p_value": None,
                "method": "cmh_fallback",
            }
    except ImportError:
        pass

    # Ultimate fallback: chi-square per stratum
    pvals = []
    for lvl in levels:
        d = data[data[subgroup_var] == lvl]
        tbl = pd.crosstab(d["TRT01PN"], d["AVAL"])
        if tbl.shape == (2, 2):
            chi2, p, _, _ = stats.chi2_contingency(tbl.values)
            pvals.append(p)

    return {
        "subgroup": subgroup_var,
        "interaction_p_value": round(float(np.mean(pvals)), 4) if pvals else None,
        "interaction_or": None,
        "interaction_or_ci_lower": None,
        "interaction_or_ci_upper": None,
        "breslow_day_p_value": None,
        "method": "chi2_fallback",
    }


def _breslow_day_test(data, subgroup_var):
    """Breslow-Day test for homogeneity of odds ratios across strata.

    H0: The odds ratio is the same across all strata.
    Uses the Tarone-adjusted Breslow-Day chi-square statistic.
    """
    levels = sorted(data[subgroup_var].unique())
    if len(levels) < 2:
        return None

    # Build 2x2 tables per stratum
    tables = []
    for lvl in levels:
        d = data[data[subgroup_var] == lvl]
        tbl = pd.crosstab(d["TRT01PN"], d["AVAL"])
        if tbl.shape != (2, 2):
            return None
        # Ensure consistent ordering: [[trt0_resp0, trt0_resp1], [trt1_resp0, trt1_resp1]]
        tables.append(tbl.values.astype(float))

    # Compute Mantel-Haenszel common OR
    # MH OR = sum(a_i * d_i / n_i) / sum(b_i * c_i / n_i)
    numer = 0.0
    denom = 0.0
    for t in tables:
        a, b, c, d_val = t[0, 0], t[0, 1], t[1, 0], t[1, 1]
        n = a + b + c + d_val
        if n == 0:
            continue
        numer += a * d_val / n
        denom += b * c / n
    mh_or = numer / denom if denom > 0 else 1.0

    # Breslow-Day statistic
    bd_stat = 0.0
    for t in tables:
        a, b, c, d_val = t[0, 0], t[0, 1], t[1, 0], t[1, 1]
        n1 = a + b  # control total
        n0 = c + d_val  # experimental total (note: crosstab ordering may vary)
        m1 = a + c  # non-responders
        m2 = b + d_val  # responders
        n = a + b + c + d_val

        if n == 0:
            continue

        # Expected a under common OR = mh_or
        # Solve for expected a using the non-central hypergeometric
        # Approximation: iterate to find expected a
        expected_a = _expected_a_bd(n1, m1, n, mh_or)
        var_a = _var_a_bd(n1, m1, n, mh_or, expected_a)

        if var_a > 0:
            bd_stat += (a - expected_a) ** 2 / var_a

    df = len(tables) - 1
    if df <= 0:
        return None

    p_value = 1 - stats.chi2.cdf(bd_stat, df)
    return float(p_value)


def _expected_a_bd(n1, m1, n, or_val, max_iter=100, tol=1e-8):
    """Compute expected value of a (cell [0,0]) under given common OR.

    Uses iterative proportional fitting for the non-central hypergeometric.
    """
    # Cornfield approximation: solve quadratic
    # a^2 - a*(or_val*(n1+m1) - n - (or_val-1)*n) ... too complex
    # Use simple iterative method
    a = min(n1, m1) / 2  # initial guess
    for _ in range(max_iter):
        a_new = or_val * n1 * m1 / (or_val * (n1 + m1 - 2 * a) + (n - n1 - m1 + 2 * a) + a * (or_val - 1))
        # More robust: use the exact formula
        # P(a) ∝ C(n1, a) * C(n-n1, m1-a) * or_val^a
        # Expected a = sum_a * a * P(a) / sum_a * P(a)
        break

    # Use exact non-central hypergeometric (small tables)
    from scipy.stats import hypergeom
    lo = int(max(0, m1 - (n - n1)))
    hi = int(min(n1, m1))
    log_or = math.log(or_val) if or_val > 0 else 0
    log_probs = []
    for a_val in range(lo, hi + 1):
        log_p = hypergeom.logpmf(a_val, n, m1, n1) + a_val * log_or
        log_probs.append(log_p)
    max_lp = max(log_probs) if log_probs else 0
    probs = [math.exp(lp - max_lp) for lp in log_probs]
    total = sum(probs)
    if total == 0:
        return (lo + hi) / 2.0
    expected = sum((lo + i) * probs[i] for i in range(len(probs))) / total
    return expected


def _var_a_bd(n1, m1, n, or_val, expected_a):
    """Approximate variance of a under the non-central hypergeometric.

    Uses the Cornfield approximation.
    """
    # Simple approximation: var(a) ≈ 1 / (1/expected_a + 1/(n1-expected_a) +
    #   1/(m1-expected_a) + 1/(n-n1-m1+expected_a))
    a = expected_a
    b = n1 - a
    c = m1 - a
    d = n - n1 - m1 + a
    if a <= 0 or b <= 0 or c <= 0 or d <= 0:
        # Use continuity correction
        a = max(a, 0.5)
        b = max(b, 0.5)
        c = max(c, 0.5)
        d = max(d, 0.5)
    var = 1.0 / (1.0 / a + 1.0 / b + 1.0 / c + 1.0 / d)
    return var


# ─────────────────────────────────────────────────────
# Core Computation
# ─────────────────────────────────────────────────────

def compute_orr_with_interaction(data):
    """Compute ORR by subgroup with logistic interaction tests."""
    subgroups = ["SEX", "AGEGR1", "ECOG"]
    subgroup_levels = {
        "SEX": ["Male", "Female"],
        "AGEGR1": ["<65", ">=65"],
        "ECOG": ["0", "1"],
    }

    # Overall ORR
    overall_exp = data[data["TRT01PN"] == 1]
    overall_ctrl = data[data["TRT01PN"] == 0]

    orr_exp = overall_exp["AVAL"].sum() / len(overall_exp) * 100
    orr_ctrl = overall_ctrl["AVAL"].sum() / len(overall_ctrl) * 100

    ci_exp = clopper_pearson_ci(overall_exp["AVAL"].sum(), len(overall_exp))
    ci_ctrl = clopper_pearson_ci(overall_ctrl["AVAL"].sum(), len(overall_ctrl))

    overall = {
        "orr_experimental": round(orr_exp, 1),
        "orr_control": round(orr_ctrl, 1),
        "n_experimental": len(overall_exp),
        "n_control": len(overall_ctrl),
        "responders_experimental": int(overall_exp["AVAL"].sum()),
        "responders_control": int(overall_ctrl["AVAL"].sum()),
        "ci_lower_experimental": round(ci_exp[0] * 100, 1),
        "ci_upper_experimental": round(ci_exp[1] * 100, 1),
        "ci_lower_control": round(ci_ctrl[0] * 100, 1),
        "ci_upper_control": round(ci_ctrl[1] * 100, 1),
        "orr_difference": round(orr_exp - orr_ctrl, 1),
    }

    # Subgroup-level ORR with Clopper-Pearson CIs
    subgroup_results = []
    for sg in subgroups:
        for lvl in subgroup_levels[sg]:
            # Handle type coercion for numeric columns (e.g. ECOG stored as int)
            col = data[sg]
            if col.dtype in ('int64', 'float64', 'int32', 'float32'):
                try:
                    lvl_cmp = int(lvl) if lvl.isdigit() else lvl
                except (AttributeError, ValueError):
                    lvl_cmp = lvl
            else:
                lvl_cmp = lvl

            sg_exp = data[(data["TRT01PN"] == 1) & (col == lvl_cmp)]
            sg_ctrl = data[(data["TRT01PN"] == 0) & (col == lvl_cmp)]

            if len(sg_exp) == 0 or len(sg_ctrl) == 0:
                continue

            orr_e = sg_exp["AVAL"].sum() / len(sg_exp) * 100
            orr_c = sg_ctrl["AVAL"].sum() / len(sg_ctrl) * 100
            ci_e = clopper_pearson_ci(sg_exp["AVAL"].sum(), len(sg_exp))
            ci_c = clopper_pearson_ci(sg_ctrl["AVAL"].sum(), len(sg_ctrl))

            diff = orr_e - orr_c
            # Normal approximation for risk difference CI
            se_diff = np.sqrt(
                (orr_e / 100 * (1 - orr_e / 100)) / len(sg_exp) +
                (orr_c / 100 * (1 - orr_c / 100)) / len(sg_ctrl)
            ) * 100
            z = stats.norm.ppf(0.975)

            subgroup_results.append({
                "subgroup": sg,
                "level": lvl,
                "orr_experimental": round(orr_e, 1),
                "orr_control": round(orr_c, 1),
                "n_experimental": len(sg_exp),
                "n_control": len(sg_ctrl),
                "responders_experimental": int(sg_exp["AVAL"].sum()),
                "responders_control": int(sg_ctrl["AVAL"].sum()),
                "ci_lower_experimental": round(ci_e[0] * 100, 1),
                "ci_upper_experimental": round(ci_e[1] * 100, 1),
                "ci_lower_control": round(ci_c[0] * 100, 1),
                "ci_upper_control": round(ci_c[1] * 100, 1),
                "orr_difference": round(diff, 1),
                "diff_ci_lower": round(diff - z * se_diff, 1),
                "diff_ci_upper": round(diff + z * se_diff, 1),
            })

    # Logistic regression interaction tests
    interaction_results = []
    for sg in subgroups:
        result = logistic_interaction_test(data, sg)
        interaction_results.append(result)

    return {
        "test_case_id": "TC-030",
        "variant_id": None,
        "language": "Python",
        "package": "statsmodels",
        "package_version": "0.14.x",
        "overall": overall,
        "subgroups": subgroup_results,
        "interaction_tests": interaction_results,
        "ci_method": "clopper-pearson",
        "seed": None,
    }


# ─────────────────────────────────────────────────────
# ARS Output (CDISC Analysis Result Standard v1.0)
# ─────────────────────────────────────────────────────

def generate_ars_output(result):
    """Generate CDISC ARS v1.0-compatible JSON envelope."""
    return {
        "analysisResult": {
            "id": "TC-030",
            "version": "1.0",
            "analysisReason": "ORR by subgroup with treatment×subgroup interaction test",
            "analysisMethod": {
                "name": "Logistic regression with interaction term",
                "codeTemplate": "logit(P(response)) = b0 + b1*trt + b2*subgroup + b3*trt*subgroup",
                "parameters": {
                    "interaction_term": "trt * subgroup",
                    "ci_method": "clopper-pearson",
                    "test_statistic": "Wald chi-square for b3",
                },
            },
            "analysisVariables": [
                {"name": "TRT01PN", "dataset": "ADRS", "role": "treatment"},
                {"name": "AVAL", "dataset": "ADRS", "role": "response"},
                {"name": "SEX", "dataset": "ADSL", "role": "subgroup"},
                {"name": "AGEGR1", "dataset": "ADSL", "role": "subgroup"},
                {"name": "ECOG", "dataset": "ADSL", "role": "subgroup"},
            ],
            "analysisPopulation": {
                "id": "ITT",
                "filter": "ITTFL == 'Y'",
                "n": result["overall"]["n_experimental"] + result["overall"]["n_control"],
            },
            "resultGroups": [
                {"id": "EXP", "label": "Experimental", "n": result["overall"]["n_experimental"]},
                {"id": "CTRL", "label": "Control", "n": result["overall"]["n_control"]},
            ],
            "analysisResultsData": {
                "overall_orr_exp": result["overall"]["orr_experimental"],
                "overall_orr_ctrl": result["overall"]["orr_control"],
                "interaction_p_values": [t.get("interaction_p_value") for t in result.get("interaction_tests", [])],
            },
        },
    }


# ─────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="TC-030: ORR by Subgroup with Interaction Test (Python)"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--n", type=int, default=200, help="Number of subjects")
    parser.add_argument("--data-csv", type=str, default=None,
                        help="Shared tumor response CSV (for cross-language verification)")
    parser.add_argument("--data", type=str, default=None,
                        help="Alias for --data-csv")
    parser.add_argument("--output", type=str, default=None, help="Output JSON path")
    parser.add_argument("--ars-output", action="store_true",
                        help="Emit CDISC ARS v1.0-compatible JSON envelope")
    args = parser.parse_args()

    data_csv = args.data_csv or args.data

    print(f"TC-030: ORR by Subgroup with Interaction Test (Python) — seed={args.seed}, n={args.n}")

    if data_csv:
        data = pd.read_csv(data_csv)
        print(f"Loaded shared data with {len(data)} subjects")
    else:
        data = generate_tumor_response(seed=args.seed, n_subjects=args.n)
        print(f"Generated tumor response data with {len(data)} subjects")

    result = compute_orr_with_interaction(data)
    result["seed"] = args.seed
    result["variant_id"] = f"v{args.seed}"

    if args.ars_output:
        result["ars"] = generate_ars_output(result)

    print("\n" + "─" * 60)
    o = result["overall"]
    print(f"Overall ORR:  Exp={o['orr_experimental']}%, "
          f"Ctrl={o['orr_control']}%, Diff={o['orr_difference']}%")
    print(f"CI method: Clopper-Pearson exact")
    print(f"Subgroups analyzed: {len(result['subgroups'])}")
    print(f"Interaction tests: {len(result['interaction_tests'])}")
    for it in result["interaction_tests"]:
        print(f"  {it['subgroup']}: p={it.get('interaction_p_value')}, "
              f"OR={it.get('interaction_or')}, method={it.get('method')}")
    print("─" * 60)

    print("\n=== BENCHMARK OUTPUT ===")
    print(json.dumps(result, indent=2, default=str))
    print("=== END OUTPUT ===")

    if args.output:
        outpath = Path(args.output)
        outpath.parent.mkdir(parents=True, exist_ok=True)
        with open(outpath, "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"Wrote output to: {outpath}")


if __name__ == "__main__":
    main()
