"""Integration tests for the complete recommendation pipeline."""

import csv
import tempfile
from pathlib import Path

import pytest

from scratchi.data_loader import (
    aggregate_plans_from_benefits,
    load_plans_from_csv,
)
from scratchi.models.constants import (
    CSVColumn,
    CoverageStatus,
    EHBStatus,
    YesNoStatus,
)
from scratchi.models.user import (
    CostSharingPreference,
    ExpectedUsage,
)
from scratchi.profiling.agent import create_profile_from_dict
from scratchi.reasoning.builder import ReasoningBuilder
from scratchi.scoring.orchestrator import ScoringOrchestrator


def create_test_csv_with_plans() -> Path:
    """Create a test CSV file with multiple plans."""
    csv_content = [
        [
            CSVColumn.BUSINESS_YEAR.value,
            CSVColumn.STATE_CODE.value,
            CSVColumn.ISSUER_ID.value,
            CSVColumn.SOURCE_NAME.value,
            CSVColumn.IMPORT_DATE.value,
            CSVColumn.STANDARD_COMPONENT_ID.value,
            CSVColumn.PLAN_ID.value,
            CSVColumn.BENEFIT_NAME.value,
            CSVColumn.COPAY_INN_TIER1.value,
            CSVColumn.COPAY_INN_TIER2.value,
            CSVColumn.COPAY_OUTOF_NET.value,
            CSVColumn.COINS_INN_TIER1.value,
            CSVColumn.COINS_INN_TIER2.value,
            CSVColumn.COINS_OUTOF_NET.value,
            CSVColumn.IS_EHB.value,
            CSVColumn.IS_COVERED.value,
            CSVColumn.QUANT_LIMIT_ON_SVC.value,
            CSVColumn.LIMIT_QTY.value,
            CSVColumn.LIMIT_UNIT.value,
            CSVColumn.EXCLUSIONS.value,
            CSVColumn.EXPLANATION.value,
            CSVColumn.EHB_VAR_REASON.value,
            CSVColumn.IS_EXCL_FROM_INN_MOOP.value,
            CSVColumn.IS_EXCL_FROM_OON_MOOP.value,
        ],
        # Plan 1: Good coverage, moderate cost
        [
            "2026",
            "AK",
            "21989",
            "HIOS",
            "2025-10-15",
            "PLAN001",
            "PLAN-001",
            "Basic Dental Care - Adult",
            "",
            "",
            "",
            "30%",
            "",
            "40%",
            EHBStatus.YES,
            CoverageStatus.COVERED,
            YesNoStatus.NO,
            "",
            "",
            "",
            "Annual maximum of $2,000",
            EHBStatus.NOT_EHB,
            YesNoStatus.NO,
            YesNoStatus.NO,
        ],
        [
            "2026",
            "AK",
            "21989",
            "HIOS",
            "2025-10-15",
            "PLAN001",
            "PLAN-001",
            "Orthodontia - Child",
            "",
            "",
            "",
            "50%",
            "",
            "50%",
            EHBStatus.YES,
            CoverageStatus.COVERED,
            YesNoStatus.NO,
            "",
            "",
            "",
            "",
            EHBStatus.NOT_EHB,
            YesNoStatus.NO,
            YesNoStatus.NO,
        ],
        # Plan 2: Lower cost, missing some benefits
        [
            "2026",
            "AK",
            "21989",
            "HIOS",
            "2025-10-15",
            "PLAN002",
            "PLAN-002",
            "Basic Dental Care - Adult",
            "$25",
            "",
            "",
            "",
            "",
            "",
            EHBStatus.YES,
            CoverageStatus.COVERED,
            YesNoStatus.NO,
            "",
            "",
            "",
            "Annual maximum of $1,000",
            EHBStatus.NOT_EHB,
            YesNoStatus.NO,
            YesNoStatus.NO,
        ],
    ]

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".csv",
        delete=False,
        newline="",
    ) as temp_file:
        writer = csv.writer(temp_file)
        writer.writerows(csv_content)
        return Path(temp_file.name)


class TestEndToEndPipeline:
    """Integration tests for the complete recommendation pipeline."""

    def test_complete_pipeline(self) -> None:
        """Test the complete pipeline: CSV → Plans → Profile → Scoring → Reasoning."""
        # 1. Load plans from CSV
        csv_path = create_test_csv_with_plans()
        try:
            benefits = load_plans_from_csv(csv_path)
            plans = aggregate_plans_from_benefits(benefits)

            assert len(plans) == 2

            # 2. Create user profile
            user_data = {
                "family_size": 4,
                "children_count": 2,
                "adults_count": 2,
                "required_benefits": ["Basic Dental Care - Adult", "Orthodontia - Child"],
                "preferred_cost_sharing": "Copay",
            }
            user_profile = create_profile_from_dict(user_data)

            assert user_profile.family_size == 4
            assert len(user_profile.required_benefits) == 2

            # 3. Score plans
            orchestrator = ScoringOrchestrator()
            scored_plans = orchestrator.score_plans(plans, user_profile)

            assert len(scored_plans) == 2
            assert all("scores" in result for result in scored_plans)
            assert all("overall" in result["scores"] for result in scored_plans)

            # 4. Build reasoning chains
            builder = ReasoningBuilder()
            for plan in plans:
                reasoning = builder.build_reasoning_chain(plan, user_profile)
                assert reasoning.coverage_analysis is not None
                assert reasoning.cost_analysis is not None
                assert len(reasoning.explanations) == 4

            # 5. Verify plan 1 scores higher (covers both required benefits)
            plan_001_scores = next(
                r["scores"] for r in scored_plans if r["plan_id"] == "PLAN-001"
            )
            plan_002_scores = next(
                r["scores"] for r in scored_plans if r["plan_id"] == "PLAN-002"
            )

            # Plan 1 should have higher coverage score (covers orthodontia)
            assert plan_001_scores["coverage"] > plan_002_scores["coverage"]

        finally:
            csv_path.unlink()

    def test_pipeline_with_missing_benefits(self) -> None:
        """Test pipeline when plan is missing required benefits."""
        csv_path = create_test_csv_with_plans()
        try:
            benefits = load_plans_from_csv(csv_path)
            plans = aggregate_plans_from_benefits(benefits)

            # User requires a benefit that plan 2 doesn't have
            user_data = {
                "family_size": 2,
                "children_count": 0,
                "adults_count": 2,
                "required_benefits": ["Orthodontia - Child"],
            }
            user_profile = create_profile_from_dict(user_data)

            # Score and reason
            orchestrator = ScoringOrchestrator()
            builder = ReasoningBuilder()

            for plan in plans:
                scores = orchestrator.score_plan(plan, user_profile)
                reasoning = builder.build_reasoning_chain(plan, user_profile)

                # Plan 2 should have missing benefits identified
                if plan.plan_id == "PLAN-002":
                    assert "Orthodontia - Child" in reasoning.coverage_analysis.missing_benefits
                    assert len(reasoning.weaknesses) > 0
                    assert scores["coverage"] < 1.0

        finally:
            csv_path.unlink()

    def test_pipeline_cost_preference_matching(self) -> None:
        """Test that cost preferences affect scoring."""
        csv_path = create_test_csv_with_plans()
        try:
            benefits = load_plans_from_csv(csv_path)
            plans = aggregate_plans_from_benefits(benefits)

            # User prefers copays
            user_profile_copay = create_profile_from_dict(
                {
                    "family_size": 2,
                    "children_count": 0,
                    "adults_count": 2,
                    "required_benefits": ["Basic Dental Care - Adult"],
                    "preferred_cost_sharing": "Copay",
                },
            )

            orchestrator = ScoringOrchestrator()

            plan_001_scores = orchestrator.score_plan(
                next(p for p in plans if p.plan_id == "PLAN-001"),
                user_profile_copay,
            )
            plan_002_scores = orchestrator.score_plan(
                next(p for p in plans if p.plan_id == "PLAN-002"),
                user_profile_copay,
            )

            # Plan 2 (with copay) should score higher on cost dimension
            assert plan_002_scores["cost"] > plan_001_scores["cost"]

        finally:
            csv_path.unlink()
