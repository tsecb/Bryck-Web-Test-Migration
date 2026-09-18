"""Compatibility checks for the live BRYCK API contract."""

from __future__ import annotations

import requests

from web_shipment.services.device_api import DeviceApiClient


def test_device_api_falls_back_to_legacy_path(monkeypatch):
    """The deployed device may reject the modern v1 route before succeeding on the legacy path."""
    calls: list[str] = []

    def fake_get(url: str, **kwargs):
        calls.append(url)

        class FakeResponse:
            def __init__(self, status_code: int, payload):
                self.status_code = status_code
                self._payload = payload

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise requests.exceptions.HTTPError(f"{self.status_code} Server Error")

            def json(self):
                return self._payload

        if url.endswith("/api/v1/system/info"):
            return FakeResponse(500, {"success": False, "result": {}})
        if url.endswith("/api/system/info"):
            return FakeResponse(
                200,
                {
                    "result": {
                        "server_info": {
                            "ethernet": [{"name": "oob_net0", "state": "UP", "IP": {"addr": "192.168.6.30"}}]
                        }
                    }
                },
            )
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr("web_shipment.services.device_api.requests.get", fake_get)

    client = DeviceApiClient(base_url="http://192.168.6.35", verify_ssl=False)
    info = client.info()

    assert info["server_info"]["ethernet"][0]["name"] == "oob_net0"
    assert calls[0].endswith("/api/v1/system/info")
    assert calls[1].endswith("/api/system/info")
