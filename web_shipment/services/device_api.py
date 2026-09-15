"""Minimal API client used for network rollback assertions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class DeviceApiClient:
    """Read-only API client for validating post-UI network state."""

    base_url: str
    verify_ssl: bool
    timeout_seconds: int = 15

    def info(self) -> dict[str, Any]:
        response = requests.get(
            f"{self.base_url.rstrip('/')}/api/v1/system/info",
            timeout=self.timeout_seconds,
            verify=self.verify_ssl,
        )
        response.raise_for_status()
        return response.json().get("result", {})

    def up_interfaces(self) -> dict[str, str]:
        """Return interface-name to ipv4 mapping for UP interfaces."""
        result = self.info()
        interfaces: dict[str, str] = {}
        for item in result.get("server_info", {}).get("ethernet", []):
            if item.get("state") != "UP":
                continue
            ip_obj = item.get("IP") or {}
            address = ip_obj.get("addr")
            if address:
                interfaces[item.get("name", "unknown")] = address
        return interfaces
