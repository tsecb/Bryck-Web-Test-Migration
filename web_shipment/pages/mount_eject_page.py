"""Bryck Storage Mount/Unmount (hot-pluggable eject) page object.

Migrated from legacy ``ConfigStore._test_ui_bryck_mount_with_hot_pluggable_eject`` /
``WebStore._bryck_mount`` / ``WebStore._bryck_eject``.

This is a genuinely state-changing flow (it actually unmounts/remounts the
live bryck), so it is deliberately gated behind
``shipment_suite.run_mount_eject_cycle`` (default ``false``) in
``tests/web/test_data_management.py`` - unlike the read-only pages in this
package, callers should treat every method here as mutating real device
state and always leave the device back in its original mounted state.
"""

from __future__ import annotations

from typing import ClassVar

from playwright.sync_api import expect

from web_shipment.pages.base_page import BasePage

_ENCRYPTED_STATUS_TEXT = "Bryck is Encrypted"


class MountEjectPage(BasePage):
    """Drives the Bryck Storage > Mount and > Unmount screens."""

    SELECTORS: ClassVar[dict[str, str]] = {
        "encryption_key_status": "#encryptionkey",
        "mount_submit": "#mountsubmit",
        "eject_submit": "#ejectsubmit",
    }

    def is_encryption_key_required(self) -> bool:
        """Return True if the Mount screen is prompting for an encryption key.

        NOTE: this device (confirmed live) has encryption disabled, so this
        branch is defensive/best-effort - if a caller's device has an
        encrypted bryck, they must supply their own key-selection handling
        (AWS KMS vs manual upload) before calling ``mount()``; this page
        deliberately does not guess a key type or upload a file on the
        caller's behalf (mirrors the same conservative stance
        ``StorageConfigurationPage.configure_variant`` takes for encryption).
        """
        locator = self.page.locator(self.selectors["encryption_key_status"]).first
        if locator.count() == 0:
            return False
        return _ENCRYPTED_STATUS_TEXT in locator.inner_text(timeout=self.timeout_ms)

    def mount(self) -> None:
        """Submit the Mount form (bryck must not already be mounted)."""
        self.click("mount_submit")

    def eject(self) -> None:
        """Submit the Unmount (hot-pluggable eject) form."""
        self.click("eject_submit")
