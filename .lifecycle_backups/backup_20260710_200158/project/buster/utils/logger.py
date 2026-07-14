from __future__ import annotations

from pathlib import Path
from typing import Any
import logging


def get_logger(name: str = "buster") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    Path("logs").mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = logging.FileHandler("logs/buster.log", encoding="utf-8")
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def log_event(name: str, message: str, **data: Any) -> None:
    logger = get_logger(name)
    if data:
        logger.info("%s | %s", message, data)
    else:
        logger.info(message)
