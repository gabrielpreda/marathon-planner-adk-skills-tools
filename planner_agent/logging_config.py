"""Logging configuration shared by local ADK runs and Agent Engine."""

from __future__ import annotations

import logging
import os
import sys


def configure_logging() -> int:
    """Configure application logging and return the effective numeric level.

    Agent Engine collects stdout/stderr into Cloud Logging, so a normal
    ``StreamHandler`` works in both local and deployed environments.
    ``PLANNER_LOG_LEVEL`` can be set to DEBUG, INFO, WARNING, or ERROR.
    """
    level_name = os.getenv("PLANNER_LOG_LEVEL", "INFO").upper().strip()
    level = getattr(logging, level_name, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # ADK normally installs its own handler. When running the module directly,
    # install a readable console handler so application logs are still visible.
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s - %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S%z",
            )
        )
        root_logger.addHandler(handler)

    logging.getLogger("planner_agent").setLevel(level)
    return level
