from __future__ import annotations

import logging


def configure_logging(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("sadify")
    logger.setLevel(_level_value(level))

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s %(message)s"
            )
        )
        logger.addHandler(handler)

    logger.propagate = False
    return logger


def _level_value(level: str) -> int:
    return getattr(logging, level.upper(), logging.INFO)
