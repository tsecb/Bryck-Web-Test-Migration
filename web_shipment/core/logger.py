"""Structured logger setup for shipment tests."""

from __future__ import annotations

import logging
from pathlib import Path

from pythonjsonlogger import jsonlogger


def get_json_logger(name: str, logs_dir: str) -> logging.Logger:
    """Create a per-test JSON logger for easy ingestion in CI systems."""
    path = Path(logs_dir)
    path.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger

    file_handler = logging.FileHandler(path / f"{name}.jsonl", encoding="utf-8")
    formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger
