"""System > Report page object (bryck diagnostic report generation/download)."""

from __future__ import annotations

from typing import ClassVar

from playwright.sync_api import expect

from web_shipment.pages.base_page import BasePage


class SystemReportPage(BasePage):
    """Drives the diagnostic report list at System > Report.

    NOTE (confirmed live 2026-09-15): the id ``#generatereport`` is reused by
    the app on *two different screens* - it's this page's "Generate Report"
    button, but also the "Add" button on the unrelated External Storage
    screen. Never assume this id is unique app-wide; it's only unique within
    whichever single page is currently mounted, which is fine for Playwright
    (locators are scoped to the current DOM) but would break a naive
    global id-uniqueness assumption.
    """

    SELECTORS: ClassVar[dict[str, str]] = {
        "generate_button": "#generatereport",
        "latest_report_name": "#reportname",
        "download_button": "#reportdownload",
    }

    def assert_page_loaded(self) -> None:
        """Assert the Report screen rendered its "Generate Report" entry point."""
        expect(self.page.locator(self.selectors["generate_button"]).first).to_be_visible(timeout=self.timeout_ms)

    def latest_report_name(self) -> str:
        """Return the filename of the most recently generated report, if any."""
        return self.get_text("latest_report_name")

    def generate_report(self) -> None:
        """Trigger generation of a new diagnostic report.

        This is a real, non-destructive but resource-consuming action (the
        device bundles logs/config into a downloadable archive) - gated by
        ``shipment_suite.run_bryck_report_generation`` in config so it isn't
        triggered on every CI run by default.
        """
        self.click("generate_button")

    def assert_download_control_visible(self) -> None:
        """Assert a downloadable report entry with its download control is visible."""
        expect(self.page.locator(self.selectors["download_button"]).first).to_be_visible(timeout=self.timeout_ms)
