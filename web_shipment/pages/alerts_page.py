"""System > Alerts page object: Alerts Receiver / Email Setup / Notification tabs."""

from __future__ import annotations

from typing import ClassVar

from playwright.sync_api import expect

from web_shipment.pages.base_page import BasePage


class AlertsPage(BasePage):
    """Drives the three Alerts sub-screens reachable from the System sidebar."""

    SELECTORS: ClassVar[dict[str, str]] = {
        # Alerts Receiver
        "alert_users_table": "#alertTable",
        "user_name_input": "#user_name",
        "email_input": "#emailId",
        "alert_category_select": "#alert_type",
        # NOTE: real (if slightly odd/reused-looking) id confirmed live - the "ADD"
        # button on this screen genuinely renders with id="upgradesubmit", not
        # something alert-specific. Kept as-is since it's what actually exists.
        "add_alert_user_button": "#upgradesubmit",
        # Email Setup
        "email_list_table": "#emailListList",
        "add_email_button": "text=Add",
        # Notification (SNS/SQS)
        "notification_list_table": "#notificationlisttable",
        "add_notification_button": "#addnotification",
        "subscribers_table": "#subscriberstable",
        "add_subscriber_button": "#addsubscriber",
    }

    def assert_alerts_receiver_loaded(self) -> None:
        """Assert the Alerts Receiver form + table have rendered."""
        expect(self.page.locator(self.selectors["alert_users_table"]).first).to_be_visible(timeout=self.timeout_ms)
        expect(self.page.locator(self.selectors["user_name_input"]).first).to_be_visible(timeout=self.timeout_ms)

    def assert_add_alert_user_disabled(self) -> None:
        """Assert the ADD button is disabled (e.g. required fields incomplete)."""
        expect(self.page.locator(self.selectors["add_alert_user_button"]).first).to_be_disabled(
            timeout=self.timeout_ms
        )

    def fill_alert_user_name(self, name: str) -> None:
        self.fill("user_name_input", name)

    def fill_alert_email(self, email: str) -> None:
        self.fill("email_input", email)

    def assert_email_setup_loaded(self) -> None:
        """Assert the Email Setup list (or its empty state) has rendered."""
        expect(self.page.locator(self.selectors["email_list_table"]).first).to_be_visible(timeout=self.timeout_ms)

    def assert_notification_setup_loaded(self) -> None:
        """Assert both Notification tables (SNS/SQS topics + subscribers) rendered."""
        expect(self.page.locator(self.selectors["notification_list_table"]).first).to_be_visible(
            timeout=self.timeout_ms
        )
        expect(self.page.locator(self.selectors["subscribers_table"]).first).to_be_visible(timeout=self.timeout_ms)
