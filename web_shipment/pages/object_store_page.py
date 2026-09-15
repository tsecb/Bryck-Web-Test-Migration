"""Object Store page object: Bucket / Access / Configure sub-tabs.

All three sub-tabs live under Bryck Storage > Object Store and share the same
route (``#/configuration``); only the sidebar selection changes which table is
rendered, so one page object models all three rather than splitting them up.
"""

from __future__ import annotations

from typing import ClassVar

from playwright.sync_api import expect

from web_shipment.pages.base_page import BasePage


class ObjectStorePage(BasePage):
    """Drives the Object Store Bucket/Access/Configure screens."""

    SELECTORS: ClassVar[dict[str, str]] = {
        # Bucket tab
        "add_bucket_button": "#createNewBucket",
        "bucket_name_input": "#createbucketinput",
        "create_bucket_submit": "#createbucketsubmit",
        "create_bucket_cancel": "#createbucketcancel",
        "bucket_list_table": "#objectbucketlist",
        "delete_bucket_action": "#removeobjectbucket",  # NOTE: repeated id, one per row -
        # matches Element-UI's per-row action-column pattern seen elsewhere (e.g.
        # "#nfcmountpoint"), so always scope with .nth()/text filters, never assume unique.
        # Access tab
        "add_access_button": "#createNewAccess",
        "access_list_table": "#objectaccesslist",
        # Configure tab
        "configure_interface_list_table": "#objectinterfacelist",
    }

    def bucket_count(self) -> int:
        """Return how many buckets currently exist, by counting table body rows.

        Waits for the list to actually settle (either a row or the el-table
        empty-state text becomes visible) first - right after navigating to
        this tab the wrapper renders before its async row data has arrived,
        so counting immediately can race and read a stale/empty ``0``.
        """
        table = self.page.locator(self.selectors["bucket_list_table"])
        # CSS comma = "or": matches once either a real row or the empty-state
        # text shows up, whichever the list settles on.
        settled = table.locator("tbody tr, .el-table__empty-text")
        expect(settled.first).to_be_visible(timeout=self.timeout_ms)
        return table.locator("tbody tr").count()

    def start_create_bucket(self) -> None:
        """Click "Add" on the Bucket tab to reveal the create-bucket mini-form."""
        self.click("add_bucket_button")

    def assert_create_bucket_submit_disabled(self) -> None:
        """Assert "CREATE BUCKET" is disabled (e.g. while the name field is empty)."""
        expect(self.page.locator(self.selectors["create_bucket_submit"]).first).to_be_disabled(
            timeout=self.timeout_ms
        )

    def type_bucket_name(self, name: str) -> None:
        """Type a candidate bucket name without submitting the form."""
        self.fill("bucket_name_input", name)

    def assert_create_bucket_submit_enabled(self) -> None:
        """Assert "CREATE BUCKET" becomes enabled once a name has been typed."""
        expect(self.page.locator(self.selectors["create_bucket_submit"]).first).to_be_enabled(timeout=self.timeout_ms)

    def cancel_create_bucket(self) -> None:
        """Cancel the create-bucket form without persisting anything."""
        self.click("create_bucket_cancel")

    def assert_access_list_visible(self) -> None:
        """Assert the Access tab's key-list table (or its empty state) has rendered."""
        expect(self.page.locator(self.selectors["add_access_button"]).first).to_be_visible(timeout=self.timeout_ms)

    def assert_configure_lists_interface(self, interface_name: str) -> None:
        """Assert the Configure tab's interface table lists ``interface_name``.

        Waits for the table to settle (row or empty-state) first - same race
        as ``bucket_count()``: this list's data arrives from an async call
        that can take noticeably longer than the route transition itself.
        """
        table = self.page.locator(self.selectors["configure_interface_list_table"])
        settled = table.locator("tbody tr, .el-table__empty-text")
        expect(settled.first).to_be_visible(timeout=self.timeout_ms)
        expect(table.locator(f"text={interface_name}").first).to_be_visible(timeout=self.timeout_ms)
