"""Configuration reader with environment overrides for shipment tests."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


class Settings:
    """Load YAML settings and resolve dotted-key access with env overrides."""

    def __init__(self, config_file: str) -> None:
        self.config_file = Path(config_file)
        if not self.config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")
        self._data = yaml.safe_load(self.config_file.read_text(encoding="utf-8")) or {}

    def get(self, dotted_key: str, default: Any = None) -> Any:
        env_key = f"WS_{dotted_key.replace('.', '_').upper()}"
        if env_key in os.environ:
            return self._coerce_env_value(os.environ[env_key])

        node: Any = self._data
        for key in dotted_key.split("."):
            if not isinstance(node, dict):
                return default
            node = node.get(key, default)
        return node

    @staticmethod
    def _coerce_env_value(value: str) -> Any:
        lowered = value.lower().strip()
        if lowered in {"true", "false"}:
            return lowered == "true"
        if lowered.isdigit():
            return int(lowered)
        return value
