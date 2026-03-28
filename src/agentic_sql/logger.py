import json
import logging
import sys
from datetime import datetime, timezone


_STDLIB_KEYS = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys())


class _JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON for structured log aggregators."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Include only extra fields explicitly passed by callers (e.g. request_id, duration_ms)
        for key, value in record.__dict__.items():
            if key not in _STDLIB_KEYS and not key.startswith("_"):
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    """Call once at application startup to configure root logger."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JSONFormatter())

    root = logging.getLogger()
    root.setLevel(level)
    # Avoid duplicate handlers if called more than once
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
