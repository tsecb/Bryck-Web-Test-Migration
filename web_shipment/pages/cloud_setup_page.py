"""System > Cloud Setup page object (read-only list of configured cloud providers)."""

from __future__ import annotations

from typing import ClassVar

from playwright.sync_api import expect

from web_shipment.pages.base_page import BasePage


class CloudSetupPage(BasePage):
    """Read-only view of configured cloud (e.g. AWS/S3-compatible) connections.

    We intentionally never automate "Add"/"Remove config" here - cloud
    credentials are sensitive and, per this device's live state, at least one
    real cloud connection is actively used for scheduled transfers (this is
    exactly what made Unmount fail with a 409 during exploration), so mutating
    it from an automated test would be unsafe.
    """

    SELECTORS: ClassVar[dict[str, str]] = {
        "add_button": "text=Add",
        "providers_table": "#cloudtransfertable",
    }

    def assert_page_loaded(self) -> None:
        """Assert the Cloud Setup screen rendered (header + Add button)."""
        expect(self.page.locator(self.selectors["add_button"]).first).to_be_visible(timeout=self.timeout_ms)

    def configured_provider_count(self) -> int:
        """Return how many cloud provider rows are currently configured."""
        return self.page.locator(f"{self.selectors['providers_table']} tbody tr").count()
