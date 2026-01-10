"""Application settings and configuration."""

import logging
import os
from enum import Enum
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(str, Enum):
    """Logging level options."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """Application settings loaded from environment variables or defaults.

    Settings can be configured via environment variables with the prefix
    'SCRATCHI_'. For example, SCRATCHI_LOG_LEVEL sets the log_level.
    
    The DATA_FILE environment variable (without prefix) can be used to specify
    the CSV file path directly.
    """

    model_config = SettingsConfigDict(
        env_prefix="SCRATCHI_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Logging configuration
    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Logging level for the application",
    )
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format",
    )
    log_date_format: str = Field(
        default="%Y-%m-%d %H:%M:%S",
        description="Date format for log messages",
    )

    # Data paths
    project_root: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent.parent.parent,
        description="Project root directory",
    )
    data_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent.parent.parent / "data",
        description="Directory containing data files",
    )
    default_csv_file: str = Field(
        default="sample.csv",
        description="Default CSV file name to load (used if DATA_FILE not set)",
    )
    data_file: Path | None = Field(
        default=None,
        description="Full path to CSV file (can be set programmatically)",
    )

    # Display configuration
    sample_display_count: int = Field(
        default=3,
        ge=1,
        le=100,
        description="Number of sample items to display",
    )

    @field_validator("project_root", "data_dir", mode="before")
    @classmethod
    def validate_path(cls, value: str | Path) -> Path:
        """Convert string paths to Path objects."""
        if isinstance(value, str):
            return Path(value)
        return value

    @field_validator("data_file", mode="before")
    @classmethod
    def validate_data_file(cls, value: str | Path | None) -> Path | None:
        """Convert string paths to Path objects."""
        if isinstance(value, str):
            return Path(value)
        if isinstance(value, Path):
            return value
        return None

    @field_validator("log_level", mode="before")
    @classmethod
    def validate_log_level(cls, value: str | LogLevel) -> LogLevel:
        """Validate and convert log level string to enum."""
        if isinstance(value, LogLevel):
            return value
        if isinstance(value, str):
            try:
                return LogLevel[value.upper()]
            except KeyError as error:
                raise ValueError(
                    f"Invalid log level: {value}. "
                    f"Must be one of {[level.name for level in LogLevel]}",
                ) from error

    @property
    def csv_path(self) -> Path:
        """Get the full path to the CSV file.
        
        Uses DATA_FILE environment variable if set, otherwise falls back to
        data_dir / default_csv_file.
        """
        # Check DATA_FILE environment variable directly (without prefix)
        env_data_file = os.getenv("DATA_FILE")
        if env_data_file:
            return Path(env_data_file)
        
        # Fall back to configured data_file if set
        if self.data_file is not None:
            return self.data_file
        
        # Default: use data_dir / default_csv_file
        return self.data_dir / self.default_csv_file

    @property
    def logging_level_int(self) -> int:
        """Get the integer logging level for Python's logging module."""
        level_mapping: dict[LogLevel, int] = {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.CRITICAL: logging.CRITICAL,
        }
        return level_mapping[self.log_level]


_settings_instance: Settings | None = None


def get_settings() -> Settings:
    """Get the singleton settings instance.

    Returns:
        Settings instance
    """
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
