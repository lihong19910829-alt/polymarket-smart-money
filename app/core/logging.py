import logging
import re
from typing import Any

import structlog

SECRET_PATTERNS = [
    re.compile(r"(bot\d+:[A-Za-z0-9_-]+)"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)=([^&\s]+)"),
]


def redact(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    redacted = value
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub(lambda m: f"{m.group(1)}=***" if len(m.groups()) > 1 else "***", redacted)
    return redacted


def add_redaction(_: Any, __: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    return {key: redact(value) for key, value in event_dict.items()}


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            add_redaction,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )

