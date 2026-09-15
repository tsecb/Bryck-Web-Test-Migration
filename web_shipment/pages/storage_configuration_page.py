"""Storage configuration page object migrated from legacy web_store format flow."""

from __future__ import annotations

from typing import ClassVar

from playwright.sync_api import expect

from web_shipment.core.models import StorageVariant
from web_shipment.pages.base_page import BasePage


class StorageConfigurationPage(BasePage):
    """Drives format actions for shipment storage-matrix test variants."""

    SELECTORS: ClassVar[dict[str, str]] = {
        "filesystem_dropdown": "#storetypeselect",  # "File System" vs "Block Store"
        "encryption_switch": "#encryptionswitch",
        "key_type_dropdown": "#encryptionuploadoption",  # "AWS KMS" or "Manual upload" - see NOTE below
        "raid_dropdown": "#protectionmode",  # NOTE: same id is reused elsewhere as a read-only summary
        # <span>, but it's a real el-select on this create/format screen (verified against the shipped
        # app bundle) - safe as long as we're on the format wizard, not a "current storage" summary view.
        "io_size_input": "#averageIOSize",
        "dedup_switch": "#dedupswitch",
        "compression_switch": "#compresswitch",
        "data_sync_dropdown": "#formatdatasync",
        "submit_button": "#filestoresubmit",
        "confirm_input": "#filestoreconfirm",  # only appears after submit, needs typed "CONFIRM"
        "confirm_submit_button": "#filestoreconfirmsubmit",
        # NOTE (confirmed live bug, fixed 2026-09-15): "#bryckstatus" is NOT unique - it's
        # reused on BOTH the sidebar "Status" nav <li> AND the actual status-text <span>
        # on the Storage Status page, with the <li> appearing first in the DOM. A plain
        # "#bryckstatus" + .first locator therefore matches the always-visible nav item,
        # not the real status text, making the assertion a near-tautology. Scoping to the
        # span.divTitle class (verified live to uniquely match) fixes this.
        "status_label": "span.divTitle#bryckstatus",
    }

    def configure_variant(self, variant: StorageVariant) -> None:
        """Apply one storage-matrix ``StorageVariant`` through the format form and confirm it."""
        # Each control below is guarded with a `.count() > 0` presence check because
        # some fields only render depending on filesystem/storage-type choice or
        # firmware version, so we skip anything not present instead of failing.
        if self.page.locator(self.selectors["filesystem_dropdown"]).count() > 0:
            self.select_option("filesystem_dropdown", variant.storage_type_label)

        if self.page.locator(self.selectors["encryption_switch"]).count() > 0:
            if variant.encryption:
                self.click("encryption_switch")
                # NOTE (known gap): enabling encryption reveals `key_type_dropdown` with two
                # options - "AWS KMS" (needs a pre-configured AWS connection) or "Manual upload"
                # (needs an actual key file uploaded through a file chooser). Neither can be
                # driven generically from the storage_matrix config without those external
                # secrets/files, so we deliberately leave the app's own default selected here
                # rather than guessing. If your matrix needs to cover this, extend
                # `StorageVariant`/config with the key-type + supporting fixture data first.

        if self.page.locator(self.selectors["raid_dropdown"]).count() > 0:
            self.select_option("raid_dropdown", variant.raid_label)

        self.fill("io_size_input", str(variant.io_size_kb))

        if self.page.locator(self.selectors["dedup_switch"]).count() > 0 and variant.dedup:
            self.click("dedup_switch")
        if self.page.locator(self.selectors["compression_switch"]).count() > 0 and variant.compression:
            self.click("compression_switch")

        if self.page.locator(self.selectors["data_sync_dropdown"]).count() > 0:
            self.select_option("data_sync_dropdown", variant.data_sync)

        self.click("submit_button")
        # Format submission requires a literal "CONFIRM" typed into a second-step
        # dialog before the destructive operation actually runs.
        self.fill("confirm_input", "CONFIRM")
        self.click("confirm_submit_button")

    def assert_storage_status_visible(self) -> None:
        # NOTE (bug fix): this previously omitted `timeout=self.timeout_ms`, silently falling back
        # to Playwright's hardcoded 5s assertion default - far too short for a real format/mount
        # operation to report completion. Now honors the same configured timeout as every other
        # page action (see config/config.yaml timeouts.default_ms).
        expect(self.page.locator(self.selectors["status_label"]).first).to_be_visible(timeout=self.timeout_ms)
