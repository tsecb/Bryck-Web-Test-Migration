"""Data Transfer page object (top-level "Data Transfer" > "Data Center" tab).

Migrated from legacy ``ConfigStore.ui_configure_data_transfer`` /
``WebStore`` transfer-add flow (``#transferaddsrc``/``#transferadddst``/
``#transferaddcheck``/``#transferaddsubmit``/``#path``/``#verifysubmit``),
confirmed live against the current app on 2026-09-15 - all of those ids still
exist and work as-is, this screen has not been redesigned.

NOTE (real app quirk, confirmed live): the "Add" button for the *Transfers*
list and the "Add" button for the *Verify* list share the exact same id,
``#transferdatanew`` - there is no separate id to distinguish them. This
page object resolves that by DOM order (Transfers' Add is always first,
Verify's Add is always second) via explicit ``.nth()`` indexing rather than
``BasePage.click()``'s ``.first``, which would always hit the Transfers one.
"""

from __future__ import annotations

from typing import ClassVar

from playwright.sync_api import expect

from web_shipment.pages.base_page import BasePage

_ADD_BUTTON_SELECTOR = "#transferdatanew"


class DataTransferPage(BasePage):
    """Drives the Data Transfer > Data Center transfer/verify add dialogs."""

    SELECTORS: ClassVar[dict[str, str]] = {
        "add_button": _ADD_BUTTON_SELECTOR,
        "transfers_table": "#transfertable",
        "verify_table": "#verifytable",
        "transfer_source": "#transferaddsrc",
        "transfer_destination": "#transferadddst",
        "transfer_checksum_checkbox": "#transferaddcheck",
        "transfer_submit": "#transferaddsubmit",
        "transfer_cancel": "#transferaddcancel",
        "verify_path": "#path",
        "verify_submit": "#verifysubmit",
        "verify_cancel": "#verifycancel",
    }

    def assert_page_loaded(self) -> None:
        """Assert both the Transfers and Verify list tables rendered."""
        expect(self.page.locator(self.selectors["transfers_table"]).first).to_be_visible(timeout=self.timeout_ms)
        expect(self.page.locator(self.selectors["verify_table"]).first).to_be_visible(timeout=self.timeout_ms)

    def open_add_transfer_dialog(self) -> None:
        """Open the "Add" dialog for the Transfers list (first ``#transferdatanew`` match)."""
        self.page.locator(_ADD_BUTTON_SELECTOR).nth(0).click(timeout=self.timeout_ms)
        expect(self.page.locator(self.selectors["transfer_source"]).first).to_be_visible(timeout=self.timeout_ms)

    def cancel_add_transfer_dialog(self) -> None:
        """Close the Transfers "Add" dialog without submitting anything."""
        self.click("transfer_cancel")

    def submit_transfer(self, source: str, destination: str, verify_checksum: bool = False) -> None:
        """Fill and submit a real transfer job. Only call this against a config-approved,
        safe source/destination (e.g. an intentionally provisioned NFS-mounted test path) -
        never against arbitrary real device data.
        """
        self.fill("transfer_source", source)
        self.fill("transfer_destination", destination)
        if verify_checksum:
            self.click("transfer_checksum_checkbox")
        self.click("transfer_submit")

    def open_add_verify_dialog(self) -> None:
        """Open the "Add" dialog for the Verify list (second ``#transferdatanew`` match)."""
        self.page.locator(_ADD_BUTTON_SELECTOR).nth(1).click(timeout=self.timeout_ms)
        expect(self.page.locator(self.selectors["verify_path"]).first).to_be_visible(timeout=self.timeout_ms)

    def cancel_add_verify_dialog(self) -> None:
        """Close the Verify "Add" dialog without submitting anything."""
        self.click("verify_cancel")

    def submit_verify(self, path: str) -> None:
        """Fill and submit a real data-checksum verification job for ``path``."""
        self.fill("verify_path", path)
        self.click("verify_submit")

    def transfer_row_count(self) -> int:
        """Return how many rows currently exist in the Transfers table (0 if empty)."""
        rows = self.page.locator(f"{self.selectors['transfers_table']} tbody tr")
        return rows.count()

    def verify_row_count(self) -> int:
        """Return how many rows currently exist in the Verify table (0 if empty)."""
        rows = self.page.locator(f"{self.selectors['verify_table']} tbody tr")
        return rows.count()
