"""System > Power page object.

SAFETY CRITICAL: this screen has one control - a real "Shutdown" button
(id="shutdown") that powers off the physical device. Nothing in this file,
and no test built on top of it, may ever call ``.click()`` on that button.
The only supported operation is asserting it is present/visible, which
proves navigation and rendering work without touching the hardware.
"""

from __future__ import annotations

from typing import ClassVar

from playwright.sync_api import expect

from web_shipment.pages.base_page import BasePage


class PowerPage(BasePage):
    """Read-only verification of the System > Power screen.

    Deliberately does NOT expose a ``shutdown()`` / ``click_shutdown()``
    method - only presence/visibility assertions are provided, by design,
    to make it structurally impossible for a test to accidentally power off
    the device through this page object.
    """

    SELECTORS: ClassVar[dict[str, str]] = {
        "shutdown_button": "#shutdown",
    }

    def assert_shutdown_button_visible(self) -> None:
        """Assert the Power screen rendered with its Shutdown control present.

        NEVER click this locator from a test - see module docstring.
        """
        expect(self.page.locator(self.selectors["shutdown_button"]).first).to_be_visible(timeout=self.timeout_ms)
