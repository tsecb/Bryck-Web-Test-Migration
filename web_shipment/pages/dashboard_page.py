"""Dashboard page object (top-level "Dashboard" landing screen).

Migrated from legacy ``ConfigStore.test_ui_dashboard_wizard`` /
``WebStore.test_ui_dashboard_wizard``, which was stubbed with ``pass`` in the
legacy suite (never actually called) even though its Selenium implementation
existed, using absolute ``/html[1]/body[1]/...`` XPaths tied to an older
dashboard layout. The live device's current dashboard has been redesigned
(no per-field ids for bryck/tray/network status), so those exact XPaths no
longer apply - this page instead uses stable, real ids/text confirmed live
on 2026-09-15 and keeps the check simple: assert the mounted status and
usage summary actually rendered, rather than a fragile field-by-field
cross-check against the legacy absolute-XPath layout.
"""

from __future__ import annotations

from typing import ClassVar

from playwright.sync_api import expect

from web_shipment.pages.base_page import BasePage


class DashboardPage(BasePage):
    """Read-only landing dashboard: bryck status, network summary, compute summary."""

    SELECTORS: ClassVar[dict[str, str]] = {
        "network_summary": "#dashnetworktable",
        "monitoring_iframe": "#dashboard-monitoring-iframe",
        # No stable id exists for the "Mounted"/capacity status card (confirmed
        # live) - it's plain text inside the top summary card, so scope by text.
        "mounted_status_text": "text=Mounted",
    }

    def assert_dashboard_loaded(self) -> None:
        """Assert the dashboard's network summary table rendered (proves the page loaded)."""
        expect(self.page.locator(self.selectors["network_summary"]).first).to_be_visible(timeout=self.timeout_ms)

    def assert_mounted_status_visible(self) -> None:
        """Assert the top summary card reports a "Mounted" bryck status.

        NOTE: only meaningful when the bryck is actually mounted going into the
        test - callers should check/establish that precondition themselves
        (e.g. via ``SystemStatusPage``/``StorageConfigurationPage``) rather than
        this page silently mounting/unmounting anything itself.
        """
        expect(self.page.locator(self.selectors["mounted_status_text"]).first).to_be_visible(timeout=self.timeout_ms)
