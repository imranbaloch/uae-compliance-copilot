"""Structured logging setup using structlog, with per-agent context binding."""

from __future__ import annotations

import logging

import structlog


def configure_logging(level: str = "INFO") -> None:
    """Configure structlog + stdlib logging once for the whole process.

    Args:
        level: Logging level name, e.g. ``"DEBUG"``, ``"INFO"``, ``"WARNING"``.
    """
    logging.basicConfig(format="%(message)s", level=getattr(logging, level.upper(), logging.INFO))
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(agent_name: str) -> structlog.BoundLogger:
    """Return a structlog logger pre-bound with the given agent name as context."""
    return structlog.get_logger().bind(agent=agent_name)
