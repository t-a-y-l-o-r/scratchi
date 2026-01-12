#!/usr/bin/env python3
"""Test script to verify Phase 1 implementation.

Run this after installing dependencies:
    pip install -e .
    python scripts/test_phase1.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from scratchi.data_loader import (
    aggregate_plans_from_benefits,
    create_plan_index,
    load_plans_from_csv,
    load_plans_from_csv_aggregated,
)
from scratchi.models.constants import NOT_APPLICABLE, CoverageStatus
from scratchi.models.plan import Plan, PlanBenefit


def main() -> int:
    """Test Phase 1 implementation."""
    print("Testing Phase 1: Foundation (Data Ingestion & Plan Aggregation)")
    print("=" * 60)

    # Test loading sample CSV
    sample_csv = Path(__file__).parent.parent / "data" / "sample.csv"
    if not sample_csv.exists():
        print(f"ERROR: Sample CSV not found at {sample_csv}")
        return 1

    print(f"\n1. Loading CSV from {sample_csv}...")
    try:
        benefits = load_plans_from_csv(sample_csv)
        print(f"   ✓ Successfully loaded {len(benefits)} plan benefits")
    except Exception as error:
        print(f"   ✗ Failed to load CSV: {error}")
        return 1

    # Test a few sample benefits
    print("\n2. Testing benefit parsing...")
    if benefits:
        sample = benefits[0]
        print(f"   ✓ Parsed benefit: {sample.benefit_name}")
        print(f"     Plan ID: {sample.plan_id}")
        print(f"     Covered: {sample.is_covered}")
        print(f"     Is Covered (bool): {sample.is_covered_bool()}")

        # Test coinsurance parsing
        if sample.coins_inn_tier1:
            rate = sample.get_coinsurance_rate("coins_inn_tier1")
            if rate is not None:
                print(f"     Coinsurance Rate: {rate}%")

    # Test edge cases
    print("\n3. Testing edge cases...")
    try:
        # Test with percentage string
        test_data = {
            "business_year": 2026,
            "state_code": "AK",
            "issuer_id": "21989",
            "source_name": "HIOS",
            "import_date": "2025-10-15",
            "standard_component_id": "TEST001",
            "plan_id": "TEST001-00",
            "benefit_name": "Test Benefit",
            "coins_inn_tier1": "35.00%",
            "is_covered": CoverageStatus.COVERED,
        }
        test_benefit = PlanBenefit(**test_data)
        rate = test_benefit.get_coinsurance_rate("coins_inn_tier1")
        assert rate == 35.0, f"Expected 35.0, got {rate}"
        print("   ✓ Percentage parsing works correctly")

        # Test with "Not Applicable"
        test_data["coins_inn_tier1"] = NOT_APPLICABLE
        test_benefit2 = PlanBenefit(**test_data)
        rate2 = test_benefit2.get_coinsurance_rate("coins_inn_tier1")
        assert rate2 is None, f"Expected None for 'Not Applicable', got {rate2}"
        print("   ✓ 'Not Applicable' handling works correctly")

        # Test with empty strings
        test_data["coins_inn_tier1"] = ""
        test_benefit3 = PlanBenefit(**test_data)
        assert test_benefit3.coins_inn_tier1 is None
        print("   ✓ Empty string normalization works correctly")

    except Exception as error:
        print(f"   ✗ Edge case test failed: {error}")
        return 1

    # Test Plan aggregation
    print("\n4. Testing Plan aggregation...")
    try:
        plans = aggregate_plans_from_benefits(benefits)
        print(f"   ✓ Aggregated {len(benefits)} benefits into {len(plans)} plans")

        if plans:
            sample_plan = plans[0]
            print(f"   ✓ Sample plan: {sample_plan.plan_id}")
            print(f"     Benefits count: {len(sample_plan.benefits)}")
            print(f"     State: {sample_plan.state_code}")
            print(f"     Issuer: {sample_plan.issuer_id}")

            # Test plan methods
            first_benefit_name = list(sample_plan.benefits.keys())[0]
            assert sample_plan.has_benefit(first_benefit_name)
            assert sample_plan.get_benefit(first_benefit_name) is not None
            print(f"   ✓ Plan methods (has_benefit, get_benefit) work correctly")

            # Test covered benefits
            covered = sample_plan.get_covered_benefits()
            print(f"   ✓ Found {len(covered)} covered benefits")

    except Exception as error:
        print(f"   ✗ Plan aggregation test failed: {error}")
        return 1

    # Test plan index
    print("\n5. Testing Plan index...")
    try:
        plan_index = create_plan_index(plans)
        print(f"   ✓ Created index with {len(plan_index)} plans")

        # Test lookup
        if plans:
            test_plan_id = plans[0].plan_id
            looked_up_plan = plan_index.get(test_plan_id)
            assert looked_up_plan is not None
            assert looked_up_plan.plan_id == test_plan_id
            print(f"   ✓ Plan lookup works correctly (found plan {test_plan_id})")

    except Exception as error:
        print(f"   ✗ Plan index test failed: {error}")
        return 1

    # Test convenience function
    print("\n6. Testing convenience function...")
    try:
        aggregated_plans = load_plans_from_csv_aggregated(sample_csv)
        print(f"   ✓ load_plans_from_csv_aggregated() works correctly")
        print(f"     Loaded {len(aggregated_plans)} plans")
        assert len(aggregated_plans) == len(plans), "Aggregation results should match"
    except Exception as error:
        print(f"   ✗ Convenience function test failed: {error}")
        return 1

    print("\n" + "=" * 60)
    print("✓ Phase 1 tests passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
