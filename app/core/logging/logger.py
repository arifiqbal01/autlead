from __future__ import annotations

import logging
from typing import cast

import structlog

from app.core.config.settings import settings


def configure_logging() -> None:
    """Configure application logging."""

    logging.basicConfig(
        level=settings.log_level,
        format="%(message)s",
    )

    # ---------------------------------------------------------
    # Suppress noisy infrastructure logs
    # ---------------------------------------------------------

    # SQLAlchemy engine SQL statements.
    logging.getLogger(
        "sqlalchemy.engine",
    ).setLevel(
        logging.WARNING,
    )

    # HTTP request/response logging.
    #
    # Important: these logs may contain sensitive query parameters,
    # including API keys.
    logging.getLogger(
        "httpx",
    ).setLevel(
        logging.WARNING,
    )

    logging.getLogger(
        "httpcore",
    ).setLevel(
        logging.WARNING,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(
                logging,
                settings.log_level.upper(),
            ),
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(
    name: str | None = None,
) -> structlog.stdlib.BoundLogger:
    """Return a structured logger."""

    return cast(
        structlog.stdlib.BoundLogger,
        structlog.get_logger(name),
    )