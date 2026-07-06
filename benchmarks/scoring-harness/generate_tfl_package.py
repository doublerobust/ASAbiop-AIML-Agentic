#!/usr/bin/env python3
"""TFL Package Generator for TC-005 (TFL Package QC Review)

Generates a clean TFL package from Level 1 ground truth outputs, then
applies error injection to create a variant TFL package for QC review.

Usage:
  python generate_tfl_package.py --seed 42 --variant v1 --output tfl_package.json
  python generate_tfl_package.py --seed 42 --variant v1 --output tfl_package.json --inject-errors
  python generate_tfl_package.py --clean-only --seed 42 --output clean_package.json

The generator:
  1. Runs Level 1 ground truth Python scripts (TC-002, TC-011, TC-012,
     TC-014, TC-015, TC-020) to produce clean TFL outputs
  2. Maps each output to a TFL ID (table-001 through listing-001)
  3. Optionally applies error injection from error_catalog.yaml
  4. Bundles everything into a single JSON package with metadata

Prerequisites:
  - Python 3.9+ with pandas, numpy, scipy, lifelines, statsmodels
  - Ground truth scripts in references/ground-truth/Python/
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Resolve paths
SCRIPT_DIR = Path(__file__).resolve().parent
BENCHMARK_DIR = SCRIPT_DIR.parent
GT_PYTHON_DIR = BENCHMARK_DIR / "references" / "ground-truth" / "Python"
GT_R_DIR = BENCHMARK_DIR / "references" / "ground-truth" / "R"

# TFL mapping: which TC produces which TFL in the package
TFL_TC_MAPPING = {
    "table-001": {
        "tc": "TC-002",
        "title": "Table 14.1: Baseline Demographics and Clinical Characteristics",
        "script": "tc_002_demographics.py",
        "format": "table",
    },
    "table-002": {
        "tc": "TC-020",
        "title": "Table 14.2: Objective Response Rate by Subgroup",
        "script": "tc_020_orr_by_subgroup.py",
        "format": "table",
    },
    "table-003": {
        "tc": "TC-011",
        "title": "Table 14.3: Adverse Events (≥5% in Either Arm)",
        "script": "tc_011_ae_summary.py",
        "format": "table",
    },
    "figure-001": {
        "tc": "TC-015",
        "title": "Figure 14.1: Kaplan-Meier Plot of Progression-Free Survival",
        "script": "tc_015_km_curve.py",
        "format": "figure",
    },
    "figure-002": {
        "tc": "TC-012",
        "title": "Figure 14.2: Forest Plot of Subgroup Analysis",
        "script": "tc_012_forest_hr.py",
        "format": "figure",
    },
    "listing-001": {
        "tc": "TC-014",
        "title": "Listing 14.1: Protocol Deviations",
        "script": "tc_014_pd_listing.py",
        "format": "listing",
    },
}


def run_ground_truth_script(script_name: str, seed: int = 42,
                             n: int = 200, output_file: str = None) -> dict:
    """Run a Python ground truth script and return its JSON output.

    Args:
        script_name: Script filename (e.g., "tc_002_demographics.py").
        seed: Random seed.
        n: Sample size.
        output_file: Path to write JSON output. If None, uses a temp file.

    Returns:
        Parsed JSON output from the script.
    """
    script_path = GT_PYTHON_DIR / script_name
    if not script_path.exists():
        raise FileNotFoundError(f"Ground truth script not found: {script_path}")

    if output_file is None:
        fd, output_file = tempfile.mkstemp(suffix=".json")
        os.close(fd)

    cmd = [sys.executable, str(script_path),
           "--seed", str(seed),
           "--n", str(n),
           "--output", output_file]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    if result.returncode != 0:
        print(f"WARNING: {script_name} failed (exit {result.returncode})")
        print(f"  stderr: {result.stderr[:500]}")
        # Return a minimal placeholder so the package can still be assembled
        return {"error": f"Script failed: {result.stderr[:200]}", "test_case_id": script_name}

    with open(output_file) as f:
        return json.load(f)


def generate_clean_package(seed: int = 42, n: int = 200) -> dict:
    """Generate a clean TFL package from Level 1 ground truth scripts.

    Args:
        seed: Random seed for data generation.
        n: Sample size.

    Returns:
        Dict mapping tfl_id -> TFL output JSON.
    """
    package = {}
    for tfl_id, spec in TFL_TC_MAPPING.items():
        print(f"  Generating {tfl_id} ({spec['tc']})...")
        output = run_ground_truth_script(spec["script"], seed=seed, n=n)
        package[tfl_id] = {
            "tfl_id": tfl_id,
            "title": spec["title"],
            "format": spec["format"],
            "source_tc": spec["tc"],
            "data": output,
        }
    return package


def generate_package_with_errors(seed: int = 42, n: int = 200,
                                   variant_id: str = "v1") -> dict:
    """Generate a TFL package with injected errors.

    Args:
        seed: Random seed.
        n: Sample size.
        variant_id: Error catalog variant to use.

    Returns:
        Dict with:
          'tfl_package': The error-injected TFL package
          'ground_truth': List of error specs applied
          'clean_tfls': List of TFL IDs with no errors
          'sap_context': SAP reference information
          'metadata': Package metadata
    """
    from error_injection import load_error_catalog, inject_all_errors

    # Step 1: Generate clean package
    print("Generating clean TFL package...")
    clean_package = generate_clean_package(seed=seed, n=n)

    # Step 2: Load error catalog
    catalog = load_error_catalog()

    # Step 3: Restructure package for error injection (pass just the data)
    data_only = {tid: item["data"] for tid, item in clean_package.items()}

    # Step 4: Inject errors
    print(f"Injecting errors (variant={variant_id})...")
    injected = inject_all_errors(data_only, catalog, variant_id=variant_id)

    # Step 5: Rebuild full package with injected data
    final_package = {}
    for tfl_id, item in clean_package.items():
        final_package[tfl_id] = {
            "tfl_id": tfl_id,
            "title": item["title"],
            "format": item["format"],
            "source_tc": item["source_tc"],
            "data": injected["tfl_package"][tfl_id],
        }

    # Step 6: Build SAP context
    sap_context = {
        "primary_endpoint": "PFS",
        "primary_analysis": "Stratified log-rank (SEX, ECOG)",
        "efficacy_population": "ITT (ITTFL='Y')",
        "safety_population": "SAFETY (SAFFL='Y')",
        "secondary_endpoints": ["ORR", "OS", "DCR", "DOR"],
        "multiplicity": "Hochberg for secondary endpoints",
        "sap_reference": "SAP Section 14.1-14.3",
    }

    # Step 7: Build metadata
    metadata = {
        "seed": seed,
        "n": n,
        "variant_id": variant_id,
        "total_tfls": len(final_package),
        "total_errors": len(injected["ground_truth"]),
        "clean_tfls": injected["clean_tfls"],
        "error_class_distribution": catalog.get("error_class_distribution", {}).get(variant_id, {}),
    }

    return {
        "tfl_package": final_package,
        "ground_truth": injected["ground_truth"],
        "clean_tfls": injected["clean_tfls"],
        "sap_context": sap_context,
        "metadata": metadata,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate TFL package for TC-005 (QC Review)"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--n", type=int, default=200, help="Sample size")
    parser.add_argument("--variant", type=str, default="v1",
                        choices=["v1", "v2", "v3"],
                        help="Error variant to generate")
    parser.add_argument("--output", type=str, required=True,
                        help="Output JSON file path")
    parser.add_argument("--inject-errors", action="store_true",
                        help="Inject errors into the package")
    parser.add_argument("--clean-only", action="store_true",
                        help="Generate only the clean package (no errors)")
    parser.add_argument("--ground-truth-output", type=str, default=None,
                        help="Also write ground truth errors to this file")

    args = parser.parse_args()

    if args.clean_only:
        print("Generating clean TFL package...")
        package = generate_clean_package(seed=args.seed, n=args.n)
        output = {
            "tfl_package": package,
            "metadata": {
                "seed": args.seed,
                "n": args.n,
                "variant_id": "clean",
                "total_tfls": len(package),
                "total_errors": 0,
            },
        }
    else:
        output = generate_package_with_errors(
            seed=args.seed, n=args.n, variant_id=args.variant
        )

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nTFL package written to: {output_path}")
    print(f"  Total TFLs: {len(output.get('tfl_package', {}))}")
    print(f"  Total errors: {output.get('metadata', {}).get('total_errors', 0)}")

    # Write ground truth if requested
    if args.ground_truth_output and "ground_truth" in output:
        gt_path = Path(args.ground_truth_output)
        gt_path.parent.mkdir(parents=True, exist_ok=True)
        with open(gt_path, "w") as f:
            json.dump(output["ground_truth"], f, indent=2)
        print(f"  Ground truth written to: {gt_path}")


if __name__ == "__main__":
    main()
