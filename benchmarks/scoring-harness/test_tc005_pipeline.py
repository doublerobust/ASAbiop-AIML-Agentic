#!/usr/bin/env python3
"""End-to-end test for TC-005 (TFL Package QC Review) pipeline.

Tests:
1. Clean package generation (no errors)
2. Error-injected package generation (v1, v2, v3)
3. Scoring function with a perfect agent response
4. Scoring function with a partial agent response
5. Scoring function with an empty agent response (floor)

Usage:
  python test_tc005_pipeline.py
"""

import json
import sys
import os
from pathlib import Path

# Add scoring-harness to path
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from error_injection import score_tc005, load_error_catalog
from generate_tfl_package import generate_clean_package, generate_package_with_errors


def test_clean_package():
    """Test 1: Generate a clean package and verify structure."""
    print("Test 1: Clean package generation...")
    package = generate_clean_package(seed=42, n=200)

    assert len(package) == 6, f"Expected 6 TFLs, got {len(package)}"
    for tfl_id in ["table-001", "table-002", "table-003",
                   "figure-001", "figure-002", "listing-001"]:
        assert tfl_id in package, f"Missing TFL: {tfl_id}"
        assert "data" in package[tfl_id], f"No data for {tfl_id}"
        assert "title" in package[tfl_id], f"No title for {tfl_id}"

    print("  ✅ PASSED — 6 TFLs generated with correct structure")
    return package


def test_error_injection_all_variants():
    """Test 2: Generate error-injected packages for all 3 variants."""
    print("Test 2: Error injection (v1, v2, v3)...")
    catalog = load_error_catalog()

    for variant_id in ["v1", "v2", "v3"]:
        result = generate_package_with_errors(seed=42, n=200, variant_id=variant_id)

        expected_errors = catalog["error_class_distribution"][variant_id]["total"]
        actual_errors = len(result["ground_truth"])
        assert actual_errors == expected_errors, \
            f"Variant {variant_id}: expected {expected_errors} errors, got {actual_errors}"

        # Verify clean TFLs match catalog
        expected_clean = catalog["error_class_distribution"][variant_id]["clean_tfls"]
        actual_clean = result["clean_tfls"]
        assert set(actual_clean) == set(expected_clean), \
            f"Variant {variant_id}: expected clean {expected_clean}, got {actual_clean}"

        # Verify error classes
        classes = {"A": 0, "B": 0, "C": 0}
        for err in result["ground_truth"]:
            classes[err["class"]] += 1
        expected_classes = catalog["error_class_distribution"][variant_id]
        for cls in ["A", "B", "C"]:
            assert classes[cls] == expected_classes[cls], \
                f"Variant {variant_id}: class {cls} expected {expected_classes[cls]}, got {classes[cls]}"

        print(f"  ✅ Variant {variant_id}: {actual_errors} errors, "
              f"classes A={classes['A']} B={classes['B']} C={classes['C']}, "
              f"clean={actual_clean}")

    print("  ✅ PASSED — All 3 variants inject correctly")


def test_scoring_perfect():
    """Test 3: Perfect agent response → score should be high."""
    print("Test 3: Scoring with perfect agent response...")

    result = generate_package_with_errors(seed=42, n=200, variant_id="v1")
    gt_errors = result["ground_truth"]

    # Simulate a perfect agent response
    perfect_output = {
        "discrepancies": [
            {
                "error_id": e["error_id"],
                "class": e["class"],
                "location": e["location"],
                "description": e["description"],
            }
            for e in gt_errors
        ],
        "cross_tfl_checks": [
            {"check": "N-count consistency between table-001 and table-002"}
        ],
        "language": "R",
        "variant_id": "v1",
    }

    score = score_tc005(perfect_output, gt_errors)

    assert score["component_scores"]["true_positives"] == len(gt_errors), \
        f"Expected {len(gt_errors)} TPs, got {score['component_scores']['true_positives']}"
    assert score["component_scores"]["false_positives"] == 0, "Expected 0 FPs"
    assert score["component_scores"]["false_negatives"] == 0, "Expected 0 FNs"
    assert score["component_scores"]["error_detection"] == 1.0, "Expected perfect detection"
    assert score["component_scores"]["error_classification"] == 1.0, "Expected perfect classification"

    print(f"  ✅ Score: {score['score']:.4f} "
          f"(TP={score['component_scores']['true_positives']}, "
          f"FP=0, FN=0, detection=1.0, classification=1.0)")


def test_scoring_partial():
    """Test 4: Partial agent response → score should be moderate."""
    print("Test 4: Scoring with partial agent response...")

    result = generate_package_with_errors(seed=42, n=200, variant_id="v1")
    gt_errors = result["ground_truth"]

    # Agent finds 5/8 errors, 1 false positive, 2 wrong classifications
    partial_output = {
        "discrepancies": [
            # 5 correct detections
            {"error_id": gt_errors[i]["error_id"],
             "class": gt_errors[i]["class"],
             "location": gt_errors[i]["location"]}
            for i in range(5)
        ],
        "cross_tfl_checks": [],
        "language": "Python",
        "variant_id": "v1",
    }

    score = score_tc005(partial_output, gt_errors)

    assert score["component_scores"]["true_positives"] == 5
    assert score["component_scores"]["false_negatives"] == 3
    assert score["component_scores"]["error_detection"] < 1.0

    print(f"  ✅ Score: {score['score']:.4f} "
          f"(TP={score['component_scores']['true_positives']}, "
          f"FN={score['component_scores']['false_negatives']}, "
          f"detection={score['component_scores']['error_detection']:.4f})")


def test_scoring_empty():
    """Test 5: Empty agent response → score should be 0."""
    print("Test 5: Scoring with empty agent response...")

    result = generate_package_with_errors(seed=42, n=200, variant_id="v1")
    gt_errors = result["ground_truth"]

    empty_output = {
        "discrepancies": [],
        "cross_tfl_checks": [],
        "language": "unknown",
        "variant_id": "v1",
    }

    score = score_tc005(empty_output, gt_errors)

    assert score["score"] == 0.0, f"Expected score 0.0, got {score['score']}"
    assert score["component_scores"]["true_positives"] == 0
    assert score["component_scores"]["false_negatives"] == len(gt_errors)

    print(f"  ✅ Score: {score['score']:.4f} (all errors missed)")


def test_variant_consistency():
    """Test 6: Same seed → same clean package across variants."""
    print("Test 6: Variant consistency (same seed → same clean data)...")

    clean1 = generate_clean_package(seed=42, n=200)
    clean2 = generate_clean_package(seed=42, n=200)

    for tfl_id in clean1:
        assert clean1[tfl_id]["data"] == clean2[tfl_id]["data"], \
            f"Clean data mismatch for {tfl_id}"

    print("  ✅ PASSED — Same seed produces identical clean packages")


def main():
    print("=" * 60)
    print("TC-005 End-to-End Pipeline Test")
    print("=" * 60)
    print()

    tests = [
        test_clean_package,
        test_error_injection_all_variants,
        test_scoring_perfect,
        test_scoring_partial,
        test_scoring_empty,
        test_variant_consistency,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ❌ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            failed += 1
        print()

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)

    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
