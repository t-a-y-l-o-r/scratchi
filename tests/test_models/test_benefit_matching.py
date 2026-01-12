"""Tests for benefit name matching (Section 3.1 recommendations).

This module implements tests for:
3.1 Benefit name matching - normalization and edge cases
"""

from datetime import date

import pytest

from scratchi.models.constants import CoverageStatus
from scratchi.models.plan import Plan, PlanBenefit


class TestBenefitNameMatching:
    """3.1 Benefit Name Matching - Edge cases and normalization tests."""

    def create_test_plan_with_benefit(self, benefit_name: str) -> Plan:
        """Create a test plan with a single benefit."""
        benefit = PlanBenefit(
            business_year=2026,
            state_code="AK",
            issuer_id="21989",
            source_name="HIOS",
            import_date=date(2025, 10, 15),
            standard_component_id="TEST001",
            plan_id="TEST-PLAN",
            benefit_name=benefit_name,
            is_covered=CoverageStatus.COVERED,
        )
        return Plan.from_benefits([benefit])

    def test_case_sensitivity_exact_match(self) -> None:
        """Test that exact case matches work."""
        plan = self.create_test_plan_with_benefit("Basic Dental Care - Adult")
        benefit = plan.get_benefit("Basic Dental Care - Adult")
        assert benefit is not None
        assert benefit.benefit_name == "Basic Dental Care - Adult"

    def test_case_sensitivity_different_case(self) -> None:
        """Test that different case matches after normalization."""
        plan = self.create_test_plan_with_benefit("Basic Dental Care - Adult")
        benefit = plan.get_benefit("basic dental care - adult")
        # After normalization: should match
        assert benefit is not None, "Case-insensitive matching should work"
        assert benefit.benefit_name == "Basic Dental Care - Adult"  # Original name preserved

    def test_case_sensitivity_mixed_case(self) -> None:
        """Test that mixed case matches after normalization."""
        plan = self.create_test_plan_with_benefit("Basic Dental Care - Adult")
        benefit = plan.get_benefit("Basic DENTAL Care - Adult")
        # After normalization: should match
        assert benefit is not None, "Case-insensitive matching should work"

    def test_whitespace_trailing_space(self) -> None:
        """Test that trailing whitespace matches after normalization."""
        plan = self.create_test_plan_with_benefit("Basic Dental Care - Adult")
        benefit = plan.get_benefit("Basic Dental Care - Adult ")
        # After normalization: should match
        assert benefit is not None, "Whitespace normalization should work"

    def test_whitespace_leading_space(self) -> None:
        """Test that leading whitespace matches after normalization."""
        plan = self.create_test_plan_with_benefit("Basic Dental Care - Adult")
        benefit = plan.get_benefit(" Basic Dental Care - Adult")
        # After normalization: should match
        assert benefit is not None, "Whitespace normalization should work"

    def test_whitespace_multiple_spaces(self) -> None:
        """Test that multiple spaces match after normalization."""
        plan = self.create_test_plan_with_benefit("Basic Dental Care - Adult")
        benefit = plan.get_benefit("Basic  Dental  Care - Adult")
        # After normalization: should match
        assert benefit is not None, "Whitespace normalization should work"

    def test_partial_match_not_implemented(self) -> None:
        """Test that partial matches do NOT work (exact match required)."""
        plan = self.create_test_plan_with_benefit("Basic Dental Care - Adult")
        benefit = plan.get_benefit("Basic Dental Care")
        # Partial matching is not implemented - requires exact normalized match
        assert benefit is None, "Partial matching not implemented - requires exact match"

    def test_exact_match_with_normalization(self) -> None:
        """Test that normalization preserves exact matches."""
        # This test will pass once normalization is implemented
        plan = self.create_test_plan_with_benefit("Basic Dental Care - Adult")
        # Normalized lookup should still work
        benefit = plan.get_benefit("Basic Dental Care - Adult")
        assert benefit is not None

    def test_case_insensitive_match_after_normalization(self) -> None:
        """Test that case-insensitive matching works after normalization."""
        plan = self.create_test_plan_with_benefit("Basic Dental Care - Adult")
        # After normalization, this should match
        benefit = plan.get_benefit("basic dental care - adult")
        assert benefit is not None, "Case-insensitive matching should work after normalization"


class TestBenefitNameNormalization:
    """Tests for benefit name normalization function."""

    def test_normalize_lowercase(self) -> None:
        """Test normalizing to lowercase."""
        from scratchi.models.plan import normalize_benefit_name

        assert normalize_benefit_name("Basic Dental Care - Adult") == "basic dental care - adult"

    def test_normalize_whitespace(self) -> None:
        """Test normalizing whitespace."""
        from scratchi.models.plan import normalize_benefit_name

        assert normalize_benefit_name("Basic  Dental  Care - Adult") == "basic dental care - adult"
        assert normalize_benefit_name(" Basic Dental Care - Adult ") == "basic dental care - adult"
        assert normalize_benefit_name("Basic\tDental\nCare - Adult") == "basic dental care - adult"

    def test_normalize_preserves_structure(self) -> None:
        """Test that normalization preserves benefit name structure."""
        from scratchi.models.plan import normalize_benefit_name

        # Should preserve hyphens and structure
        assert normalize_benefit_name("Basic Dental Care - Adult") == "basic dental care - adult"
        assert normalize_benefit_name("Orthodontia - Child") == "orthodontia - child"

    def test_normalize_empty_string(self) -> None:
        """Test normalizing empty string."""
        from scratchi.models.plan import normalize_benefit_name

        assert normalize_benefit_name("") == ""
        assert normalize_benefit_name("   ") == ""

    def test_normalize_special_characters(self) -> None:
        """Test normalizing special characters."""
        from scratchi.models.plan import normalize_benefit_name

        # Special characters should be preserved (not removed)
        assert normalize_benefit_name("Basic (Dental) Care - Adult") == "basic (dental) care - adult"
        assert normalize_benefit_name("Basic: Dental Care - Adult") == "basic: dental care - adult"


class TestPlanWithNormalizedMatching:
    """Tests for Plan.get_benefit() with normalized matching."""

    def test_get_benefit_case_insensitive(self) -> None:
        """Test that get_benefit works with case-insensitive matching."""
        benefit = PlanBenefit(
            business_year=2026,
            state_code="AK",
            issuer_id="21989",
            source_name="HIOS",
            import_date=date(2025, 10, 15),
            standard_component_id="TEST001",
            plan_id="TEST-PLAN",
            benefit_name="Basic Dental Care - Adult",
            is_covered=CoverageStatus.COVERED,
        )
        plan = Plan.from_benefits([benefit])

        # After normalization, these should all match
        assert plan.get_benefit("Basic Dental Care - Adult") is not None
        assert plan.get_benefit("basic dental care - adult") is not None
        assert plan.get_benefit("BASIC DENTAL CARE - ADULT") is not None
        assert plan.get_benefit("Basic DENTAL Care - Adult") is not None

    def test_get_benefit_whitespace_normalized(self) -> None:
        """Test that get_benefit works with whitespace normalization."""
        benefit = PlanBenefit(
            business_year=2026,
            state_code="AK",
            issuer_id="21989",
            source_name="HIOS",
            import_date=date(2025, 10, 15),
            standard_component_id="TEST001",
            plan_id="TEST-PLAN",
            benefit_name="Basic Dental Care - Adult",
            is_covered=CoverageStatus.COVERED,
        )
        plan = Plan.from_benefits([benefit])

        # After normalization, these should all match
        assert plan.get_benefit("Basic Dental Care - Adult") is not None
        assert plan.get_benefit("Basic Dental Care - Adult ") is not None
        assert plan.get_benefit(" Basic Dental Care - Adult") is not None
        assert plan.get_benefit("Basic  Dental  Care - Adult") is not None

    def test_get_benefit_multiple_benefits(self) -> None:
        """Test normalized matching with multiple benefits."""
        benefits = [
            PlanBenefit(
                business_year=2026,
                state_code="AK",
                issuer_id="21989",
                source_name="HIOS",
                import_date=date(2025, 10, 15),
                standard_component_id="TEST001",
                plan_id="TEST-PLAN",
                benefit_name="Basic Dental Care - Adult",
                is_covered=CoverageStatus.COVERED,
            ),
            PlanBenefit(
                business_year=2026,
                state_code="AK",
                issuer_id="21989",
                source_name="HIOS",
                import_date=date(2025, 10, 15),
                standard_component_id="TEST001",
                plan_id="TEST-PLAN",
                benefit_name="Orthodontia - Child",
                is_covered=CoverageStatus.COVERED,
            ),
        ]
        plan = Plan.from_benefits(benefits)

        # After normalization, should find both benefits
        assert plan.get_benefit("basic dental care - adult") is not None
        assert plan.get_benefit("orthodontia - child") is not None
        assert plan.get_benefit("ORTHODONTIA - CHILD") is not None
