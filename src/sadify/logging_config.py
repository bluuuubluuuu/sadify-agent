from __future__ import annotations

import logging
from typing import TextIO

from sadify.diagnostics import redact_mapping


def configure_logging(level: str = "INFO", *, stream: TextIO | None = None) -> logging.Logger:
    logger = logging.getLogger("sadify")
    logger.setLevel(_level_value(level))

    if not logger.handlers:
        handler = logging.StreamHandler(stream)
        handler.setFormatter(SafeMetadataFormatter())
        logger.addHandler(handler)
    elif stream is not None:
        logger.handlers[0].stream = stream

    logger.propagate = False
    return logger


def _level_value(level: str) -> int:
    return getattr(logging, level.upper(), logging.INFO)


class SafeMetadataFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__("%(asctime)s %(levelname)s %(name)s %(message)s %(metadata)s")

    def format(self, record: logging.LogRecord) -> str:
        if hasattr(record, "metadata") and isinstance(record.metadata, dict):
            record.metadata = redact_mapping(record.metadata)
        elif not hasattr(record, "metadata"):
            record.metadata = {}
        return super().format(record)
