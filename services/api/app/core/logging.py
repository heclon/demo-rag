"""Structured logging via structlog.

Events carry key/value fields rather than interpolated strings — `agent.routed`
logs `strategy` and `reasoning` as real fields, so watching the agent decide is
just `docker compose logs -f api`.

Rendering is console-friendly because this is a local demo and those routing
decisions are meant to be read as they happen. Swapping in
`structlog.processors.JSONRenderer()` is the one-line change that makes the same
fields queryable by a log aggregator.
"""

from __future__ import annotations

import logging
import sys

import structlog

from app.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)

    # Human-readable colourized logs — this is a local demo, and the agent's
    # routing decisions are meant to be readable in the terminal as they happen.
    renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
