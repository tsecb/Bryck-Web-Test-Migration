"""System > Settings page object (Timezone / Session Timeout / Date and Time tabs)."""

from __future__ import annotations

from typing import ClassVar

from playwright.sync_api import expect

from web_shipment.pages.base_page import BasePage


class SettingsPage(BasePage):
    """Read-only view of the three Settings tabs plus their "Change" entry points.

    We only assert the current values render and the "Change" buttons are
    present - we deliberately never click "Change", since doing so opens a
    real edit dialog for timezone/session-timeout/date-time that would alter
    live device behaviour (e.g. session timeout affecting every other test).
    """

    SELECTORS: ClassVar[dict[str, str]] = {
        # Real, stable el-tabs ids (confirmed live) - not auto-generated numbers,
        # so safe to hardcode unlike Element-UI's usual "#tab-1234" style ids.
        "timezone_tab": "#tab-first",
        "session_timeout_tab": "#tab-second",
        "date_time_tab": "#tab-third",
        "current_timezone": "#currentTimezone",
        "change_timezone_button": "#changeTimezone",
        "current_timeout": "#currentTimeout",
        "change_timeout_button": "#changeTimeout",
        "current_date_time": "#currentDateTime",
        "change_date_time_button": "#changeDateTime",
    }

    def open_timezone_tab(self) -> None:
        self.click("timezone_tab")

    def open_session_timeout_tab(self) -> None:
        self.click("session_timeout_tab")

    def open_date_time_tab(self) -> None:
        self.click("date_time_tab")

    def assert_timezone_visible(self) -> None:
        expect(self.page.locator(self.selectors["current_timezone"]).first).to_be_visible(timeout=self.timeout_ms)
        expect(self.page.locator(self.selectors["change_timezone_button"]).first).to_be_visible(
            timeout=self.timeout_ms
        )

    def assert_session_timeout_visible(self) -> None:
        expect(self.page.locator(self.selectors["current_timeout"]).first).to_be_visible(timeout=self.timeout_ms)
        expect(self.page.locator(self.selectors["change_timeout_button"]).first).to_be_visible(timeout=self.timeout_ms)

    def assert_date_time_visible(self) -> None:
        expect(self.page.locator(self.selectors["current_date_time"]).first).to_be_visible(timeout=self.timeout_ms)
        expect(self.page.locator(self.selectors["change_date_time_button"]).first).to_be_visible(
            timeout=self.timeout_ms
        )
