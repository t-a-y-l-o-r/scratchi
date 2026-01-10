"""Configuration module for the scratchi package."""

from scratchi.config.settings import get_settings

__all__ = ["get_settings", "settings"]

# Singleton instance of settings
settings = get_settings()
