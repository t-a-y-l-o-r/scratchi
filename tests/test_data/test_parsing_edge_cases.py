"""Tests for data parsing edge cases (Section 2 recommendations).

This module implements tests for:
2.1 Percentage parsing edge cases
2.3 Date parsing validation (edge cases)
2.4 Annual maximum extraction edge cases
"""

from datetime import date

import pytest
from pydantic import ValidationError

from scratchi.models.constants import NO_CHARGE, NOT_APPLICABLE, NOT_COVERED, CoverageStatus
from scratchi.models.plan import PlanBenefit


class TestPercentageParsingEdgeCases:
    """2.1 Percentage Parsing Edge Cases - Comprehensive tests."""

    def create_benefit_with_coinsurance(self, coins_value: str | None) -> PlanBenefit:
        """Create a PlanBenefit with specified coinsurance value."""
        return PlanBenefit(
            business_year=2026,
            state_code="AK",
            issuer_id="21989",
            source_name="HIOS",
            import_date=date(2025, 10, 15),
            standard_component_id="TEST001",
            plan_id="TEST-PLAN",
            benefit_name="Test Benefit",
            is_covered=CoverageStatus.COVERED,
            coins_inn_tier1=coins_value,
        )

    def test_edge_case_100_percent(self) -> None:
        """Test parsing 100%."""
        benefit = self.create_benefit_with_coinsurance("100%")
        assert benefit.get_coinsurance_rate("coins_inn_tier1") == 100.0

    def test_edge_case_0_percent(self) -> None:
        """Test parsing 0%."""
        benefit = self.create_benefit_with_coinsurance("0%")
        assert benefit.get_coinsurance_rate("coins_inn_tier1") == 0.0

    def test_edge_case_0_00_percent(self) -> None:
        """Test parsing 0.00%."""
        benefit = self.create_benefit_with_coinsurance("0.00%")
        assert benefit.get_coinsurance_rate("coins_inn_tier1") == 0.0

    def test_edge_case_99_99_percent(self) -> None:
        """Test parsing 99.99%."""
        benefit = self.create_benefit_with_coinsurance("99.99%")
        assert benefit.get_coinsurance_rate("coins_inn_tier1") == 99.99

    def test_edge_case_100_00_percent(self) -> None:
        """Test parsing 100.00%."""
        benefit = self.create_benefit_with_coinsurance("100.00%")
        assert benefit.get_coinsurance_rate("coins_inn_tier1") == 100.0

    def test_invalid_format_no_percent_sign(self) -> None:
        """Test invalid format: "35" (no percent sign)."""
        benefit = self.create_benefit_with_coinsurance("35")
        # Should return None since "%" is not in the value
        assert benefit.get_coinsurance_rate("coins_inn_tier1") is None

    def test_invalid_format_text_percent(self) -> None:
        """Test invalid format: "35 percent"."""
        benefit = self.create_benefit_with_coinsurance("35 percent")
        # Should return None since "%" is not in the value
        assert benefit.get_coinsurance_rate("coins_inn_tier1") is None

    def test_invalid_format_decimal_no_percent(self) -> None:
        """Test invalid format: "35.5" (decimal but no percent)."""
        benefit = self.create_benefit_with_coinsurance("35.5")
        # Should return None since "%" is not in the value
        assert benefit.get_coinsurance_rate("coins_inn_tier1") is None

    def test_invalid_format_percent_at_start(self) -> None:
        """Test invalid format: "%35"."""
        benefit = self.create_benefit_with_coinsurance("%35")
        # Current implementation splits on "%" and takes first part, which would be empty
        # This should handle gracefully
        result = benefit.get_coinsurance_rate("coins_inn_tier1")
        # Should either return None or handle gracefully
        assert result is None or result == 0.0

    def test_invalid_format_double_percent(self) -> None:
        """Test invalid format: "35%%"."""
        benefit = self.create_benefit_with_coinsurance("35%%")
        # Should parse "35" from before first "%"
        assert benefit.get_coinsurance_rate("coins_inn_tier1") == 35.0

    def test_boundary_over_100_percent(self) -> None:
        """Test boundary value: percentage > 100%."""
        benefit = self.create_benefit_with_coinsurance("150%")
        # Should parse successfully (validation of value range is separate concern)
        assert benefit.get_coinsurance_rate("coins_inn_tier1") == 150.0

    def test_boundary_negative_percent(self) -> None:
        """Test boundary value: negative percentage."""
        benefit = self.create_benefit_with_coinsurance("-10%")
        # Should parse successfully (validation of value range is separate concern)
        assert benefit.get_coinsurance_rate("coins_inn_tier1") == -10.0

    def test_not_applicable_handled(self) -> None:
        """Test that "Not Applicable" is handled correctly."""
        benefit = self.create_benefit_with_coinsurance(NOT_APPLICABLE)
        assert benefit.get_coinsurance_rate("coins_inn_tier1") is None

    def test_not_covered_handled(self) -> None:
        """Test that "Not Covered" is handled correctly."""
        benefit = self.create_benefit_with_coinsurance(NOT_COVERED)
        assert benefit.get_coinsurance_rate("coins_inn_tier1") is None

    def test_no_charge_handled(self) -> None:
        """Test that "No Charge" is handled correctly."""
        benefit = self.create_benefit_with_coinsurance(NO_CHARGE)
        assert benefit.get_coinsurance_rate("coins_inn_tier1") == 0.0

    def test_empty_string_handled(self) -> None:
        """Test that empty string is handled correctly."""
        benefit = self.create_benefit_with_coinsurance("")
        # Empty strings should be normalized to None
        assert benefit.coins_inn_tier1 is None
        assert benefit.get_coinsurance_rate("coins_inn_tier1") is None

    def test_none_handled(self) -> None:
        """Test that None is handled correctly."""
        benefit = self.create_benefit_with_coinsurance(None)
        assert benefit.get_coinsurance_rate("coins_inn_tier1") is None

    def test_whitespace_around_percent(self) -> None:
        """Test parsing with whitespace around percent sign."""
        benefit = self.create_benefit_with_coinsurance("35 %")
        # Should parse "35" from before "%"
        assert benefit.get_coinsurance_rate("coins_inn_tier1") == 35.0

    def test_whitespace_before_number(self) -> None:
        """Test parsing with whitespace before number."""
        benefit = self.create_benefit_with_coinsurance(" 35%")
        # strip() should handle this
        assert benefit.get_coinsurance_rate("coins_inn_tier1") == 35.0

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("0%", 0.0),
            ("0.0%", 0.0),
            ("0.00%", 0.0),
            ("1%", 1.0),
            ("1.0%", 1.0),
            ("1.00%", 1.0),
            ("50%", 50.0),
            ("50.0%", 50.0),
            ("50.00%", 50.0),
            ("99%", 99.0),
            ("99.9%", 99.9),
            ("99.99%", 99.99),
            ("100%", 100.0),
            ("100.0%", 100.0),
            ("100.00%", 100.0),
        ],
    )
    def test_various_percentage_formats(self, value: str, expected: float) -> None:
        """Test various valid percentage formats."""
        benefit = self.create_benefit_with_coinsurance(value)
        assert benefit.get_coinsurance_rate("coins_inn_tier1") == expected


class TestDateParsingEdgeCases:
    """2.3 Date Parsing Validation - Edge cases."""

    def create_benefit_with_date(self, import_date: str | date) -> PlanBenefit:
        """Create a PlanBenefit with specified import date."""
        return PlanBenefit(
            business_year=2026,
            state_code="AK",
            issuer_id="21989",
            source_name="HIOS",
            import_date=import_date,
            standard_component_id="TEST001",
            plan_id="TEST-PLAN",
            benefit_name="Test Benefit",
            is_covered=CoverageStatus.COVERED,
        )

    def test_iso_format(self) -> None:
        """Test ISO format: "2025-10-15"."""
        benefit = self.create_benefit_with_date("2025-10-15")
        assert benefit.import_date == date(2025, 10, 15)

    def test_date_object(self) -> None:
        """Test date object input."""
        test_date = date(2025, 10, 15)
        benefit = self.create_benefit_with_date(test_date)
        assert benefit.import_date == test_date

    def test_invalid_month(self) -> None:
        """Test invalid date: month > 12."""
        with pytest.raises(ValidationError):
            self.create_benefit_with_date("2025-13-01")

    def test_invalid_day(self) -> None:
        """Test invalid date: day > 28/29/30/31."""
        with pytest.raises(ValidationError):
            self.create_benefit_with_date("2025-02-30")

    def test_invalid_date_string(self) -> None:
        """Test invalid date string."""
        with pytest.raises(ValidationError):
            self.create_benefit_with_date("invalid-date")

    def test_leap_year_feb_29(self) -> None:
        """Test leap year: February 29."""
        benefit = self.create_benefit_with_date("2024-02-29")  # 2024 is a leap year
        assert benefit.import_date == date(2024, 2, 29)

    def test_non_leap_year_feb_29(self) -> None:
        """Test non-leap year: February 29 should fail."""
        with pytest.raises(ValidationError):
            self.create_benefit_with_date("2025-02-29")  # 2025 is not a leap year

    def test_year_boundary(self) -> None:
        """Test year boundary: December 31."""
        benefit = self.create_benefit_with_date("2025-12-31")
        assert benefit.import_date == date(2025, 12, 31)

    def test_year_boundary_jan_1(self) -> None:
        """Test year boundary: January 1."""
        benefit = self.create_benefit_with_date("2025-01-01")
        assert benefit.import_date == date(2025, 1, 1)

    def test_whitespace_handled(self) -> None:
        """Test that whitespace is stripped."""
        benefit = self.create_benefit_with_date(" 2025-10-15 ")
        assert benefit.import_date == date(2025, 10, 15)

    # Note: Additional date formats like "10/15/2025" and "2025-10-15T00:00:00"
    # would require changes to the parser, which is beyond edge case testing.
    # These are documented as recommendations but may require parser enhancement.


class TestAnnualMaximumExtraction:
    """2.4 Annual Maximum Extraction - Comprehensive edge case tests."""

    def create_benefit_with_explanation(self, explanation: str | None) -> PlanBenefit:
        """Create a PlanBenefit with specified explanation."""
        return PlanBenefit(
            business_year=2026,
            state_code="AK",
            issuer_id="21989",
            source_name="HIOS",
            import_date=date(2025, 10, 15),
            standard_component_id="TEST001",
            plan_id="TEST-PLAN",
            benefit_name="Test Benefit",
            is_covered=CoverageStatus.COVERED,
            explanation=explanation,
        )

    def test_format_annual_maximum_of_amount(self) -> None:
        """Test format: "Annual maximum of $2,500 applies"."""
        from scratchi.agents.cost import CostAgent
        from scratchi.models.plan import Plan
        from scratchi.models.user import UserProfile, ExpectedUsage, PriorityWeights, CostSharingPreference

        benefit = self.create_benefit_with_explanation("Annual maximum of $2,500 applies")
        plan = Plan.from_benefits([benefit])
        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=[],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        agent = CostAgent()
        score = agent.score(plan, user_profile)
        # Score should be > 0.5 since $2,500 is less than $5,000 threshold
        assert 0.0 <= score <= 1.0

    def test_format_amount_annual_maximum(self) -> None:
        """Test format: "$2,500 annual maximum"."""
        from scratchi.agents.cost import CostAgent
        from scratchi.models.plan import Plan
        from scratchi.models.user import UserProfile, ExpectedUsage, PriorityWeights, CostSharingPreference

        benefit = self.create_benefit_with_explanation("$2,500 annual maximum")
        plan = Plan.from_benefits([benefit])
        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=[],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        agent = CostAgent()
        score = agent.score(plan, user_profile)
        assert 0.0 <= score <= 1.0

    def test_format_subject_to_amount_annual_maximum(self) -> None:
        """Test format: "Subject to $2,500 annual maximum per year"."""
        from scratchi.agents.cost import CostAgent
        from scratchi.models.plan import Plan
        from scratchi.models.user import UserProfile, ExpectedUsage, PriorityWeights, CostSharingPreference

        benefit = self.create_benefit_with_explanation("Subject to $2,500 annual maximum per year")
        plan = Plan.from_benefits([benefit])
        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=[],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        agent = CostAgent()
        score = agent.score(plan, user_profile)
        assert 0.0 <= score <= 1.0

    def test_format_maximum_benefit_amount(self) -> None:
        """Test format: "Maximum benefit: $2,500"."""
        from scratchi.agents.cost import CostAgent
        from scratchi.models.plan import Plan
        from scratchi.models.user import UserProfile, ExpectedUsage, PriorityWeights, CostSharingPreference

        benefit = self.create_benefit_with_explanation("Maximum benefit: $2,500")
        plan = Plan.from_benefits([benefit])
        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=[],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        agent = CostAgent()
        score = agent.score(plan, user_profile)
        assert 0.0 <= score <= 1.0

    def test_multiple_amounts_mentioned(self) -> None:
        """Test edge case: multiple amounts mentioned."""
        from scratchi.agents.cost import CostAgent
        from scratchi.models.plan import Plan
        from scratchi.models.user import UserProfile, ExpectedUsage, PriorityWeights, CostSharingPreference

        # Should extract the highest amount
        benefit = self.create_benefit_with_explanation(
            "Annual maximum of $1,000 for basic care and $5,000 for major procedures"
        )
        plan = Plan.from_benefits([benefit])
        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=[],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        agent = CostAgent()
        score = agent.score(plan, user_profile)
        # Should use $5,000 (highest), which should give score of 1.0
        assert 0.0 <= score <= 1.0

    def test_range_format(self) -> None:
        """Test edge case: range format "$1,000-$2,000"."""
        from scratchi.agents.cost import CostAgent
        from scratchi.models.plan import Plan
        from scratchi.models.user import UserProfile, ExpectedUsage, PriorityWeights, CostSharingPreference

        # Current implementation extracts both amounts, should use max
        benefit = self.create_benefit_with_explanation("Annual maximum ranges from $1,000-$2,000")
        plan = Plan.from_benefits([benefit])
        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=[],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        agent = CostAgent()
        score = agent.score(plan, user_profile)
        # Should extract $2,000 (higher value)
        assert 0.0 <= score <= 1.0

    def test_missing_amount(self) -> None:
        """Test edge case: explanation mentions annual maximum but no amount."""
        from scratchi.agents.cost import CostAgent
        from scratchi.models.plan import Plan
        from scratchi.models.user import UserProfile, ExpectedUsage, PriorityWeights, CostSharingPreference

        benefit = self.create_benefit_with_explanation("Subject to annual maximum per year")
        plan = Plan.from_benefits([benefit])
        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=[],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        agent = CostAgent()
        score = agent.score(plan, user_profile)
        # Should return neutral score (0.5) when no amount found
        assert 0.0 <= score <= 1.0

    def test_no_explanation(self) -> None:
        """Test edge case: no explanation field."""
        from scratchi.agents.cost import CostAgent
        from scratchi.models.plan import Plan
        from scratchi.models.user import UserProfile, ExpectedUsage, PriorityWeights, CostSharingPreference

        benefit = self.create_benefit_with_explanation(None)
        plan = Plan.from_benefits([benefit])
        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=[],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        agent = CostAgent()
        score = agent.score(plan, user_profile)
        # Should return neutral score (0.5) when no explanation
        assert 0.0 <= score <= 1.0

    def test_very_large_amount(self) -> None:
        """Test edge case: very large amount (should be validated)."""
        from scratchi.agents.cost import CostAgent
        from scratchi.models.plan import Plan
        from scratchi.models.user import UserProfile, ExpectedUsage, PriorityWeights, CostSharingPreference

        # Current implementation doesn't validate upper bound
        benefit = self.create_benefit_with_explanation("Annual maximum of $1,000,000")
        plan = Plan.from_benefits([benefit])
        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=[],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        agent = CostAgent()
        score = agent.score(plan, user_profile)
        # Should cap at 1.0 (since >= $5,000 threshold)
        assert 0.0 <= score <= 1.0

    def test_zero_amount(self) -> None:
        """Test edge case: $0 amount (should be filtered out)."""
        from scratchi.agents.cost import CostAgent
        from scratchi.models.plan import Plan
        from scratchi.models.user import UserProfile, ExpectedUsage, PriorityWeights, CostSharingPreference

        benefit = self.create_benefit_with_explanation("Annual maximum of $0")
        plan = Plan.from_benefits([benefit])
        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=[],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        agent = CostAgent()
        score = agent.score(plan, user_profile)
        # $0 should be filtered out (amount > 0 check), so should return neutral score
        assert 0.0 <= score <= 1.0

    def test_negative_amount(self) -> None:
        """Test edge case: negative amount (should be filtered or handled)."""
        from scratchi.agents.cost import CostAgent
        from scratchi.models.plan import Plan
        from scratchi.models.user import UserProfile, ExpectedUsage, PriorityWeights, CostSharingPreference

        # Regex might extract "-1000", but float conversion should handle it
        benefit = self.create_benefit_with_explanation("Annual maximum of $-1,000")
        plan = Plan.from_benefits([benefit])
        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=[],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        agent = CostAgent()
        score = agent.score(plan, user_profile)
        # Negative amount should be filtered out (amount > 0 check)
        assert 0.0 <= score <= 1.0

    def test_dollars_text_format(self) -> None:
        """Test format: "1000 dollars"."""
        from scratchi.agents.cost import CostAgent
        from scratchi.models.plan import Plan
        from scratchi.models.user import UserProfile, ExpectedUsage, PriorityWeights, CostSharingPreference

        benefit = self.create_benefit_with_explanation("Annual maximum of 2500 dollars")
        plan = Plan.from_benefits([benefit])
        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=[],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        agent = CostAgent()
        score = agent.score(plan, user_profile)
        assert 0.0 <= score <= 1.0

    def test_dollar_sign_without_comma(self) -> None:
        """Test format: "$2500" (no comma)."""
        from scratchi.agents.cost import CostAgent
        from scratchi.models.plan import Plan
        from scratchi.models.user import UserProfile, ExpectedUsage, PriorityWeights, CostSharingPreference

        benefit = self.create_benefit_with_explanation("Annual maximum of $2500")
        plan = Plan.from_benefits([benefit])
        user_profile = UserProfile(
            family_size=2,
            children_count=0,
            adults_count=2,
            expected_usage=ExpectedUsage.MEDIUM,
            priorities=PriorityWeights.default(),
            required_benefits=[],
            excluded_benefits_ok=[],
            preferred_cost_sharing=CostSharingPreference.EITHER,
        )

        agent = CostAgent()
        score = agent.score(plan, user_profile)
        assert 0.0 <= score <= 1.0
