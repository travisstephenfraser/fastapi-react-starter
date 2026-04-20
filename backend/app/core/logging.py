"""Structured logging via structlog. JSON to stdout in prod; pretty console in dev.

SENSITIVE_FIELDS is a denylist (not an allowlist) of keys whose values are redacted
regardless of where they appear in the event dict. Extend the tuple, don't replace it.
"""

from __future__ import annotations

import logging
import re
import sys
from typing import Any

import structlog

from app.core.config import settings

# Deny by default. New secret-ish key surfaces should match one of these patterns.
SENSITIVE_FIELDS: tuple[str, ...] = (
    "password",
    "token",
    "secret",
    "authorization",
    "cookie",
    "apikey",
    "api_key",
    "service_role",
    "private",
)

_SENSITIVE_RE = re.compile("|".join(SENSITIVE_FIELDS), re.IGNORECASE)


def _redact(_: Any, __: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    for k in list(event_dict.keys()):
        if _SENSITIVE_RE.search(k):
            event_dict[k] = "[REDACTED]"
    return event_dict


def configure_logging() -> None:
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=settings.log_level,
    )

    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _redact,
    ]
    if settings.structlog_json:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level)
        ),
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger()
