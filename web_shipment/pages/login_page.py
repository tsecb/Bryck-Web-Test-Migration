"""Login page object for the BRYCK web console."""

from __future__ import annotations

from typing import ClassVar

from web_shipment.pages.base_page import BasePage


class LoginPage(BasePage):
    """Performs the login flow, including an optional cert-acceptance banner."""

    SELECTORS: ClassVar[dict[str, str]] = {
        # Some deployments show a self-signed cert acknowledgement banner
        # before the login form; not present on every host, hence optional.
        "accept_button": "text=I Accept",
        "username_input": "#username",
        "password_input": "#password",
        "submit_button": "#login",
    }

    def login(self, username: str, password: str) -> None:
        """Dismiss the optional cert banner (if present), then submit credentials."""
        accept_selector = self.selectors["accept_button"]
        if self.page.locator(accept_selector).count() > 0:
            self.page.locator(accept_selector).first.click(timeout=2000)

        self.fill("username_input", username)
        self.fill("password_input", password)
        self.click("submit_button")
