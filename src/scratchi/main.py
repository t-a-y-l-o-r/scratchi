"""Main module for the scratchi package."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def main() -> int:
    """Main entry point for the application.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    logger.info("Hello from scratchi!")
    logger.debug(f"Python version: {sys.version}")
    logger.debug(f"Working directory: {Path.cwd()}")
    return 0


if __name__ == "__main__":
    # Configure logging at the application entry point
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    sys.exit(main())
