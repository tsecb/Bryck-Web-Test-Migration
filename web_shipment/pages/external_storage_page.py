"""System > External Storage page object (NFS mount add flow).

Migrated from legacy ``ConfigStore.ui_configure_nfs`` /
``WebStore`` NFS-mount flow. NOTE (confirmed live 2026-09-15): this screen's
"Add" button reuses the id ``#generatereport`` - the exact same id as the
System > Report page's "Generate Report" button (a real app quirk, each id
is only unique within whichever single page is currently mounted). The
mount-form fields themselves (``#mountpoint``/``#remoteaddress``/
``#export_path``/``#extmountsubmit``/``#extmountcancel``) are unique and
match the legacy locators exactly.
"""

from __future__ import annotations

from typing import ClassVar

from playwright.sync_api import expect

from web_shipment.pages.base_page import BasePage


class ExternalStoragePage(BasePage):
    """Drives the System > External Storage NFS mount list + add dialog."""

    SELECTORS: ClassVar[dict[str, str]] = {
        "add_button": "#generatereport",
        "mount_point": "#mountpoint",
        "remote_address": "#remoteaddress",
        "export_path": "#export_path",
        "mount_submit": "#extmountsubmit",
        "mount_cancel": "#extmountcancel",
    }

    def assert_page_loaded(self) -> None:
        """Assert the External Storage screen rendered its "Add" entry point."""
        expect(self.page.locator(self.selectors["add_button"]).first).to_be_visible(timeout=self.timeout_ms)

    def open_add_mount_dialog(self) -> None:
        """Open the NFS mount "Add" dialog."""
        self.click("add_button")
        expect(self.page.locator(self.selectors["mount_point"]).first).to_be_visible(timeout=self.timeout_ms)

    def cancel_add_mount_dialog(self) -> None:
        """Close the NFS mount "Add" dialog without submitting anything."""
        self.click("mount_cancel")

    def add_nfs_mount(self, mount_point: str, remote_address: str, export_path: str) -> None:
        """Fill and submit a real NFS mount. Only call this with config-provisioned,
        real NFS server details - never with guessed/placeholder values, since a
        real mount attempt will be made against ``remote_address``.
        """
        self.fill("mount_point", mount_point)
        self.fill("remote_address", remote_address)
        self.fill("export_path", export_path)
        self.click("mount_submit")
