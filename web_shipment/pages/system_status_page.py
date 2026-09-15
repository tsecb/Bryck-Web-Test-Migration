"""System ("Administration" > "Status") read-only summary page object."""

from __future__ import annotations

from typing import ClassVar

from playwright.sync_api import expect

from web_shipment.pages.base_page import BasePage


class SystemStatusPage(BasePage):
    """Read-only hardware/build summary shown at System > Status.

    Every id here was confirmed live via DOM inspection - there is nothing to
    submit on this screen, it just displays current device facts, so the only
    thing worth asserting is that the values actually rendered (as opposed to
    an empty/loading shell, which would indicate a broken API call upstream).
    """

    SELECTORS: ClassVar[dict[str, str]] = {
        "network_table": "#networktable",
        "serial_number": "#bryckserialnumber",
        "capacity": "#bryckcapacity",
        "bryck_state": "#bryckstate",
        "build_version": "#buildversion",
        "build_date": "#builddate",
    }

    def assert_summary_visible(self) -> None:
        """Assert the hardware/build summary panel has rendered with real content."""
        for key in ("network_table", "serial_number", "capacity", "bryck_state", "build_version", "build_date"):
            expect(self.page.locator(self.selectors[key]).first).to_be_visible(timeout=self.timeout_ms)

    def build_version_text(self) -> str:
        """Return the currently reported firmware/build version string."""
        return self.get_text("build_version")

    def serial_number_text(self) -> str:
        """Return the reported drive serial number.

        Migrated from legacy ``ConfigStore.ui_system_page_drive_serial_check`` /
        ``WebStore.get_drive_serial_no`` (``//span[@id='bryckserialnumber']``).
        NOTE (confirmed live 2026-09-15): on this particular unit the device
        genuinely reports the literal text ``"None"`` here (a null serial
        number causes a caught renderer error in the app's own JS, visible as
        a console warning, not a crash) - so callers should assert the field
        is *present/visible* rather than assert it's a real-looking serial
        string, since "None" may be a legitimate (if unfortunate) device state
        rather than a test/automation bug.
        """
        return self.get_text("serial_number")
