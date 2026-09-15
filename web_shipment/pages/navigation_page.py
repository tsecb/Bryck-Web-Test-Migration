"""Global navigation page object for BRYCK web top-level menus."""

from __future__ import annotations

from typing import ClassVar

from playwright.sync_api import expect

from web_shipment.pages.base_page import BasePage


class NavigationPage(BasePage):
    """Drives the persistent top navigation bar and both section sidebars.

    All ids below were confirmed against the *live* device DOM (not just the
    compiled JS bundle) via ``page.$$eval('[id]', ...)`` on 2026-09-15, one
    section/tab at a time, so this is the authoritative map of what actually
    exists - see ``/memories/repo/bryck-web-device.md`` for the full trail.
    """

    SELECTORS: ClassVar[dict[str, str]] = {
        # --- Top-level menu bar ---
        "dashboard": "#dashboard",               # top-level menu labelled "Dashboard"
        "configuration": "#configuration",       # top-level menu labelled "Bryck Storage"
        "data": "#data",                         # top-level menu labelled "Data Transfer"
        "administration": "#administration",     # top-level menu labelled "System"
        # Application/Messages/Analysis/Bryck AI exist too (#application, #logging,
        # #monitoring, #bryckai) but are out of scope for this suite (camera ingest,
        # log viewer, Grafana dashboards, and an always-disabled AI tab) - not
        # modeled as page objects.
        # --- Data Transfer ("#data") sidebar ---
        "data_center_page": "#transferadd",       # "Data Center" - transfers/verify (this is
        # also the default view when #data is opened, but click explicitly for clarity).
        # --- Bryck Storage ("Configuration") sidebar ---
        "storage_status_page": "#bryckstatus",        # NOTE: id is duplicated with the
        # read-only status <span> inside the page itself - see storage_configuration_page.py.
        "storage_format_page": "#bryckformat",        # "Format" - disabled while mounted
        "storage_unmount_page": "#bryckeject",        # "Unmount"
        "storage_mount_page": "#bryckmount",          # "Mount" - disabled while mounted
        "storage_erase_page": "#bryckerase",          # "Erase" - disabled while mounted
        "object_store_bucket_page": "#objbucket",     # Object Store > Bucket
        "object_store_access_page": "#objaccess",     # Object Store > Access
        "object_store_configure_page": "#objinterface",  # Object Store > Configure
        # --- System ("Administration") sidebar ---
        "system_status_page": "#systemstatus",
        "network_page": "#systemnetwork",
        "external_storage_page": "#external-storage",
        "cloud_setup_page": "#cloud-configration",   # NOTE: real id has this legacy typo too
        "system_upgrade_page": "#systemupgrade",
        "alerts_receiver_page": "#alertconfig",
        "email_setup_page": "#emailconfig",
        "notification_setup_page": "#notificationconfig",
        "settings_page": "#setting",
        "system_report_page": "#systemreport",
        "system_power_page": "#systempower",
    }

    def open_dashboard(self) -> None:
        """Open the top-level Dashboard screen."""
        self.click("dashboard")

    def open_configuration(self) -> None:
        """Open the Configuration ("Bryck Storage") top-level menu."""
        self.click("configuration")

    def open_data_transfer(self) -> None:
        """Navigate to Data Transfer > Data Center (transfers + verify lists)."""
        self.click("data")
        self.click("data_center_page")

    def open_administration(self) -> None:
        """Open the Administration ("System") top-level menu."""
        self.click("administration")

    def open_storage_format(self) -> None:
        """Navigate to the storage/shipment format screen."""
        self.open_configuration()
        self.click("storage_format_page")

    def open_storage_status(self) -> None:
        """Navigate to the read-only Bryck Storage status/summary screen."""
        self.open_configuration()
        self.click("storage_status_page")

    def open_storage_mount(self) -> None:
        """Navigate to Bryck Storage > Mount (disabled while already mounted)."""
        self.open_configuration()
        self.click("storage_mount_page")

    def open_storage_unmount(self) -> None:
        """Navigate to Bryck Storage > Unmount (hot-pluggable eject)."""
        self.open_configuration()
        self.click("storage_unmount_page")

    def open_object_store_bucket(self) -> None:
        """Navigate to Bryck Storage > Object Store > Bucket."""
        self.open_configuration()
        self.click("object_store_bucket_page")

    def open_object_store_access(self) -> None:
        """Navigate to Bryck Storage > Object Store > Access."""
        self.open_configuration()
        self.click("object_store_access_page")

    def open_object_store_configure(self) -> None:
        """Navigate to Bryck Storage > Object Store > Configure."""
        self.open_configuration()
        self.click("object_store_configure_page")

    def open_network(self) -> None:
        """Navigate to the network configuration screen."""
        self.open_administration()
        self.click("network_page")

    def open_system_status(self) -> None:
        """Navigate to the read-only System status/summary screen."""
        self.open_administration()
        self.click("system_status_page")

    def open_external_storage(self) -> None:
        """Navigate to System > External Storage."""
        self.open_administration()
        self.click("external_storage_page")

    def open_cloud_setup(self) -> None:
        """Navigate to System > Cloud Setup."""
        self.open_administration()
        self.click("cloud_setup_page")

    def open_alerts_receiver(self) -> None:
        """Navigate to System > Alerts > Alerts Receiver."""
        self.open_administration()
        self.click("alerts_receiver_page")

    def open_email_setup(self) -> None:
        """Navigate to System > Alerts > Email Setup."""
        self.open_administration()
        self.click("email_setup_page")

    def open_notification_setup(self) -> None:
        """Navigate to System > Alerts > Notification (SNS/SQS)."""
        self.open_administration()
        self.click("notification_setup_page")

    def open_settings(self) -> None:
        """Navigate to System > Settings (Timezone / Session Timeout / Date and Time)."""
        self.open_administration()
        self.click("settings_page")

    def open_system_report(self) -> None:
        """Navigate to System > Report (bryck diagnostic report generation/download)."""
        self.open_administration()
        self.click("system_report_page")

    def open_power(self) -> None:
        """Navigate to System > Power.

        NOTE: this only opens the page to verify it renders. Never click the
        "Shutdown" button there in an automated test - it is genuinely
        destructive against real hardware, unlike every other flow in this suite.
        """
        self.open_administration()
        self.click("system_power_page")

    def assert_unauthenticated(self) -> None:
        """Assert the authenticated app shell (top nav) never becomes visible.

        Used by negative login tests: polls for up to ``timeout_ms`` so a
        slow-but-eventual redirect isn't mistaken for successful rejection.
        """
        expect(self.page.locator(self.selectors["configuration"]).first).not_to_be_visible(timeout=self.timeout_ms)
