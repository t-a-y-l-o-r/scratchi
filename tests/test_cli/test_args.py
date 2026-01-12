"""Tests for CLI argument parsing."""

import argparse
from pathlib import Path

import pytest

from scratchi.cli.args import parse_args, validate_args


class TestArgParsing:
    """Test cases for argument parsing."""

    def test_parse_args_required_fields(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that required arguments are enforced."""
        # Missing --csv should fail
        with monkeypatch.context() as m:
            m.setattr("sys.argv", ["scratchi", "--family-size", "2"])
            with pytest.raises(SystemExit):
                parse_args()

    def test_validate_args_csv_not_found(self, tmp_path: Path) -> None:
        """Test validation fails for non-existent CSV."""
        args = argparse.Namespace(
            csv=tmp_path / "nonexistent.csv",
            family_size=2,
            adults=None,
            children=0,
            expected_usage="Medium",
            required=[],
            preferred_cost_sharing="Either",
            priority="default",
            top=None,
            format="text",
            explanation_style="detailed",
            output=None,
            quiet=False,
            verbose=False,
        )

        is_valid, error_msg = validate_args(args)
        assert not is_valid
        assert "not found" in error_msg.lower()

    def test_validate_args_family_size_mismatch(self, tmp_path: Path) -> None:
        """Test validation fails for family size mismatch."""
        csv_file = tmp_path / "test.csv"
        csv_file.touch()

        args = argparse.Namespace(
            csv=csv_file,
            family_size=4,
            adults=3,
            children=2,  # 3 + 2 = 5, but family_size is 4
            expected_usage="Medium",
            required=[],
            preferred_cost_sharing="Either",
            priority="default",
            top=None,
            format="text",
            explanation_style="detailed",
            output=None,
            quiet=False,
            verbose=False,
        )

        is_valid, error_msg = validate_args(args)
        assert not is_valid
        assert "mismatch" in error_msg.lower()

    def test_validate_args_auto_calculate_adults(self, tmp_path: Path) -> None:
        """Test that adults are auto-calculated if not specified."""
        csv_file = tmp_path / "test.csv"
        csv_file.touch()

        args = argparse.Namespace(
            csv=csv_file,
            family_size=4,
            adults=None,
            children=2,
            expected_usage="Medium",
            required=[],
            preferred_cost_sharing="Either",
            priority="default",
            top=None,
            format="text",
            explanation_style="detailed",
            output=None,
            quiet=False,
            verbose=False,
        )

        is_valid, error_msg = validate_args(args)
        assert is_valid
        assert args.adults == 2  # Auto-calculated: 4 - 2 = 2

    def test_validate_args_negative_values(self, tmp_path: Path) -> None:
        """Test validation fails for negative values."""
        csv_file = tmp_path / "test.csv"
        csv_file.touch()

        args = argparse.Namespace(
            csv=csv_file,
            family_size=2,
            adults=-1,
            children=0,
            expected_usage="Medium",
            required=[],
            preferred_cost_sharing="Either",
            priority="default",
            top=None,
            format="text",
            explanation_style="detailed",
            output=None,
            quiet=False,
            verbose=False,
        )

        is_valid, error_msg = validate_args(args)
        assert not is_valid
        assert "negative" in error_msg.lower()
