"""
logger.py — centralised structured logging for LBCA backend.

Every module should do:
    from logger import get_logger
    logger = get_logger(__name__)
    logger.info("something happened", extra={"user_id": str(user.id)})

In production the JSON handler writes one JSON object per line to stdout,
which Render captures in its log stream.
In development (LOG_FORMAT=text) it prints a human-readable line.
"""

import logging
import json
import os
import sys
from datetime import datetime, timezone


LOG_LEVEL  = os.getenv("LOG_LEVEL",  "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "json")   # "json" | "text"


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        doc = {
            "ts":      datetime.now(timezone.utc).isoformat(),
            "level":   record.levelname,
            "logger":  record.name,
            "message": record.getMessage(),
        }
        # Merge any extra= fields passed by the caller
        for key, val in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and not key.startswith("_"):
                doc[key] = val
        if record.exc_info:
            doc["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(doc, default=str)


def _build_handler() -> logging.Handler:
    handler = logging.StreamHandler(sys.stdout)
    if LOG_FORMAT == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s  %(levelname)-8s  %(name)s  %(message)s")
        )
    return handler


# Root LBCA logger — all child loggers inherit this handler
_root = logging.getLogger("lbca")
_root.setLevel(LOG_LEVEL)
if not _root.handlers:
    _root.addHandler(_build_handler())


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the 'lbca' namespace."""
    return _root.getChild(name.removeprefix("lbca."))
