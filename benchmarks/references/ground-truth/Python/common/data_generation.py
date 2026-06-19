"""data_generation.py — Synthetic CDISC-compliant clinical trial data

Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark.
Common utilities used by all Python ground truth reference implementations.

Dependencies: numpy, pandas

NOTE ON CROSS-LANGUAGE VERIFICATION:
    numpy's RNG (PCG64) and R's RNG (Mersenne-Twister) produce DIFFERENT random
    streams for the same seed. Generating data independently in each language
    therefore yields DIFFERENT datasets; ground-truth statistics CANNOT be
    expected to match across languages. To verify that R/SAS/Python compute the
    SAME statistic on the SAME data, generate the data once and share it as a
    CSV (see read_shared_data() / get_adtte() and the --data flag in each TC
    script). Independent generation is for single-language smoke tests only.
"""

import numpy as np
import pandas as pd


def generate_adtte(
    seed: int = 42,
    n_subjects: int = 200,
    n_arms: int = 2,
    median_pfs_control: float = 6.0,
    hr: float = 0.75,
    censoring_rate: float = 0.30,
    p_itt: float = 0.95,
) -> pd.DataFrame:
    """Generate synthetic ADTTE dataset for survival test cases.

    Args:
        seed: Random seed for reproducibility
        n_subjects: Total number of subjects
        n_arms: Number of treatment arms (1 or 2)
        median_pfs_control: Median PFS in control arm (months)
        hr: Hazard ratio for treatment vs. control
        censoring_rate: Overall censoring rate
        p_itt: Proportion ITT population

    Returns:
        DataFrame in ADTTE-like format
    """
    rng = np.random.default_rng(seed)

    # Base hazard (exponential)
    base_rate = np.log(2) / median_pfs_control

    # Treatment assignment
    trt = rng.integers(0, n_arms, size=n_subjects)

    # Hazard multiplier by arm
    hazard_mult = np.where(trt == 0, 1.0, hr)

    # Generate survival times from exponential
    aval = rng.exponential(scale=1.0 / (base_rate * hazard_mult))

    # Generate independent censoring times
    # BUGFIX: size=n_subjects is REQUIRED. Without it, numpy returns a single
    # scalar censoring time applied to all subjects, which over-censors the
    # data (drives the event rate far below target and can make the median
    # non-estimable). This previously caused TC-001 to return median=null.
    cens_time = rng.exponential(
        scale=1.0 / (base_rate * censoring_rate / (1 - censoring_rate)),
        size=n_subjects,
    )

    # Observed time = min(event, censoring)
    observed_time = np.minimum(aval, cens_time)
    cnsr = np.where(aval <= cens_time, 0, 1).astype(int)

    # Stratification factors
    sex = rng.choice(["Male", "Female"], size=n_subjects, p=[0.5, 0.5])
    ecog = rng.choice([0, 1], size=n_subjects, p=[0.6, 0.4])

    # ITT flag
    ittfl = np.where(rng.uniform(size=n_subjects) < p_itt, "Y", "N").astype(str)
    saffl = np.where(rng.uniform(size=n_subjects) < 0.98, "Y", "N").astype(str)

    # Build DataFrame
    df = pd.DataFrame({
        "USUBJID": [f"SUBJ-{i:04d}" for i in range(1, n_subjects + 1)],
        "STUDYID": "BENCHMARK-001",
        "TRT01PN": trt,
        "TRT01P": np.where(trt == 0, "Placebo", "Active"),
        "AVAL": np.round(observed_time, 2),
        "CNSR": cnsr,
        "ITTFL": ittfl,
        "SAFFL": saffl,
        "SEX": sex,
        "ECOG": ecog,
    })

    return df


def generate_adsl(
    seed: int = 42,
    n_subjects: int = 400,
    n_arms: int = 2,
) -> pd.DataFrame:
    """Generate synthetic ADSL dataset for demographics test cases.

    Args:
        seed: Random seed
        n_subjects: Number of subjects
        n_arms: Number of treatment arms

    Returns:
        DataFrame in ADSL-like format
    """
    rng = np.random.default_rng(seed)

    trt = rng.integers(0, n_arms, size=n_subjects)

    age = np.round(rng.normal(58, 12, size=n_subjects)).astype(int)

    df = pd.DataFrame({
        "USUBJID": [f"SUBJ-{i:04d}" for i in range(1, n_subjects + 1)],
        "STUDYID": "BENCHMARK-001",
        "TRT01PN": trt,
        "TRT01P": np.where(trt == 0, "Placebo", "Active"),
        "AGE": age,
        # AGEGR1 derived deterministically from AGE (CDISC convention), not random
        "AGEGR1": np.where(age < 65, "<65", ">=65"),
        "SEX": rng.choice(["M", "F"], size=n_subjects, p=[0.55, 0.45]),
        "RACE": rng.choice(
            ["White", "Black", "Asian", "Other"],
            size=n_subjects,
            p=[0.60, 0.15, 0.20, 0.05],
        ),
        "REGION1": rng.choice(
            ["North America", "Europe", "Asia", "Rest of World"],
            size=n_subjects,
            p=[0.35, 0.30, 0.20, 0.15],
        ),
        "ECOG": rng.choice([0, 1, 2], size=n_subjects, p=[0.4, 0.4, 0.2]),
        "SAFFL": np.where(rng.uniform(size=n_subjects) < 0.98, "Y", "N").astype(str),
        "ITTFL": np.where(rng.uniform(size=n_subjects) < 0.95, "Y", "N").astype(str),
    })

    return df


# ---------------------------------------------------------------------------
# Shared-data helpers (for TRUE cross-language verification)
# ---------------------------------------------------------------------------

def read_shared_data(filepath) -> pd.DataFrame:
    """Read a shared dataset CSV (the preferred path for cross-language runs)."""
    return pd.read_csv(filepath)


def get_adtte(data_path=None, seed: int = 42, n_subjects: int = 200, **kwargs) -> pd.DataFrame:
    """Read shared CSV if provided, else generate in-language.

    Cross-language verification REQUIRES a shared CSV; in-language generation
    is for single-language smoke tests only.
    """
    if data_path:
        return read_shared_data(data_path)
    return generate_adtte(seed=seed, n_subjects=n_subjects, **kwargs)


def get_adsl(data_path=None, seed: int = 42, n_subjects: int = 400, **kwargs) -> pd.DataFrame:
    if data_path:
        return read_shared_data(data_path)
    return generate_adsl(seed=seed, n_subjects=n_subjects, **kwargs)
