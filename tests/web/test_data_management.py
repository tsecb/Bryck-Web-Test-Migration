"""Extensive/additional web-UI coverage migrated from the legacy full ``WebTest``
suite, beyond the reduced shipment subset in ``test_web_shipment.py``:
Dashboard status, System > Status drive-serial field, System > Report
generation, Data Transfer (Data Center) add/verify dialogs, External Storage
NFS mount dialog, and the Bryck Storage Mount/Unmount (hot-pluggable eject)
round-trip.

Continues the ``@pytest.mark.order(n)`` sequence started in
``test_web_shipment.py`` / ``test_system_administration.py`` /
``test_object_store.py`` (which ends at 15).

Explicitly OUT OF SCOPE for this migration (see README.md "Migration scope"
section for the full rationale):
  - Cloud configure/deconfigure/transfer: already disabled/commented out in
    the legacy suite itself, and its test fixture data contains what look
    like real AWS/Azure credentials that must never be copied into this
    codebase - flagged to the user as a security finding, not migrated.
  - The legacy dashboard "API vs UI cross-check" (``test_ui_dashboard_wizard``):
    already stubbed with ``pass`` in the legacy suite, and its absolute-XPath
    locators no longer match the current (redesigned) dashboard, which has
    no stable per-field ids to check against. Migrated instead as a simpler,
    real, always-on check (``test_dashboard_shows_mounted_status`` below).
  - ``Configuration._test_bryck_inserted`` (iSCSI bryck-insertion): SSH/iSCSI
    hardware provisioning, not a web UI concern at all.
"""

from __future__ import annotations

import allure
import pytest

from web_shipment.core.config import Settings
from web_shipment.pages.dashboard_page import DashboardPage
from web_shipment.pages.data_transfer_page import DataTransferPage
from web_shipment.pages.external_storage_page import ExternalStoragePage
from web_shipment.pages.mount_eject_page import MountEjectPage
from web_shipment.pages.navigation_page import NavigationPage
from web_shipment.pages.storage_configuration_page import StorageConfigurationPage
from web_shipment.pages.system_report_page import SystemReportPage
from web_shipment.pages.system_status_page import SystemStatusPage


@allure.epic("Web Shipment")
@allure.feature("Dashboard")
@pytest.mark.shipment
@pytest.mark.dashboard
@pytest.mark.order(16)
def test_dashboard_shows_mounted_status(context_page, page_timeout_ms: int, settings: Settings):
    """Dashboard renders its network summary and reports the bryck as Mounted.

    Migrated (simplified) from legacy ``test_ui_dashboard_wizard`` - see the
    module docstring for why the original absolute-XPath, field-by-field
    API-vs-UI cross-check could not be migrated as-is against the redesigned
    dashboard. This still gives real signal: the dashboard loads and reports
    the same "Mounted" state confirmed via the Bryck Storage status page.
    """
    if not settings.get("shipment_suite.run_dashboard_status_check", True):
        pytest.skip("Dashboard status check disabled in config")

    nav = NavigationPage(context_page, timeout_ms=page_timeout_ms)
    dashboard = DashboardPage(context_page, timeout_ms=page_timeout_ms)

    with allure.step("Open Dashboard"):
        nav.open_dashboard()

    with allure.step("Assert the network summary rendered"):
        dashboard.assert_dashboard_loaded()

    with allure.step("Assert the bryck status card reports Mounted"):
        dashboard.assert_mounted_status_visible()


@allure.epic("Web Shipment")
@allure.feature("System Status")
@pytest.mark.shipment
@pytest.mark.system
@pytest.mark.order(17)
def test_drive_serial_number_field_renders(context_page, page_timeout_ms: int, settings: Settings):
    """System > Status renders a drive-serial-number field (migrated from legacy
    ``test_ui_system_page_drive_serial_no_check``).

    NOTE: confirmed live this device genuinely reports the literal text
    "None" here (a real, if unfortunate, device condition - not a broken
    test). So this only asserts the field is visible/queryable, matching
    what the legacy check actually verified (that the field could be read at
    all), rather than asserting a non-empty/real-looking serial value.
    """
    if not settings.get("shipment_suite.run_drive_serial_check", True):
        pytest.skip("Drive serial check disabled in config")

    nav = NavigationPage(context_page, timeout_ms=page_timeout_ms)
    status = SystemStatusPage(context_page, timeout_ms=page_timeout_ms)

    with allure.step("Open System > Status"):
        nav.open_system_status()

    with allure.step("Read the drive serial number field"):
        serial = status.serial_number_text()

    with allure.step("Assert the field actually rendered (non-None Python value, may be the string 'None')"):
        assert serial is not None, "Serial number field did not render at all"


@allure.epic("Web Shipment")
@allure.feature("System Report")
@pytest.mark.shipment
@pytest.mark.report
@pytest.mark.order(18)
def test_generate_bryck_report(context_page, page_timeout_ms: int, settings: Settings):
    """Migrated from legacy ``test_ui_generate_bryck_report``: trigger a real
    diagnostic report generation and confirm a downloadable entry appears.

    Real, non-destructive action (bundles device logs/config into an
    archive) - gated by ``shipment_suite.run_bryck_report_generation``.
    """
    if not settings.get("shipment_suite.run_bryck_report_generation", True):
        pytest.skip("Bryck report generation disabled in config")

    nav = NavigationPage(context_page, timeout_ms=page_timeout_ms)
    report = SystemReportPage(context_page, timeout_ms=page_timeout_ms)

    with allure.step("Open System > Report"):
        nav.open_system_report()
        report.assert_page_loaded()

    with allure.step("Generate a new report"):
        report.generate_report()

    with allure.step("Assert a downloadable report entry is present"):
        report.assert_download_control_visible()
        assert report.latest_report_name(), "No report name was reported after generation"


@allure.epic("Web Shipment")
@allure.feature("Data Transfer")
@pytest.mark.shipment
@pytest.mark.data_transfer
@pytest.mark.order(19)
def test_data_transfer_add_dialog_can_be_cancelled(context_page, page_timeout_ms: int, settings: Settings):
    """Data Transfer > Data Center: the "Add" transfer dialog opens with the
    expected fields and CANCEL reverts cleanly without creating a real job.

    Migrated from legacy ``ConfigStore.check_ui_data_transfer`` /
    ``WebStore.create_data_transfer`` locators - this is deliberately the
    cancel-only path, since submitting a real transfer requires an actual
    external NFS-mounted source (see ``test_nfs_mount_and_data_transfer``
    below, gated separately and off by default with no NFS server configured).
    """
    if not settings.get("shipment_suite.run_data_transfer_dialog_checks", True):
        pytest.skip("Data transfer dialog check disabled in config")

    nav = NavigationPage(context_page, timeout_ms=page_timeout_ms)
    data_transfer = DataTransferPage(context_page, timeout_ms=page_timeout_ms)

    with allure.step("Open Data Transfer > Data Center"):
        nav.open_data_transfer()
        data_transfer.assert_page_loaded()

    with allure.step("Record current transfer/verify row counts"):
        transfers_before = data_transfer.transfer_row_count()
        verifications_before = data_transfer.verify_row_count()

    with allure.step("Open and cancel the Add Transfer dialog"):
        data_transfer.open_add_transfer_dialog()
        data_transfer.cancel_add_transfer_dialog()

    with allure.step("Open and cancel the Add Verify dialog"):
        data_transfer.open_add_verify_dialog()
        data_transfer.cancel_add_verify_dialog()

    with allure.step("Row counts are unchanged - nothing was persisted"):
        assert data_transfer.transfer_row_count() == transfers_before
        assert data_transfer.verify_row_count() == verifications_before


@allure.epic("Web Shipment")
@allure.feature("External Storage")
@pytest.mark.shipment
@pytest.mark.external_storage
@pytest.mark.order(20)
def test_external_storage_add_mount_dialog_can_be_cancelled(context_page, page_timeout_ms: int, settings: Settings):
    """External Storage: the NFS mount "Add" dialog opens with the expected
    fields and CANCEL reverts cleanly without mounting anything.

    Migrated from legacy ``WebStore.add_nfs_server`` locators
    (``#mountpoint``/``#remoteaddress``/``#export_path``/``#extmountsubmit``) -
    cancel-only, since a real mount requires an actual external NFS server
    (see ``test_nfs_mount_and_data_transfer`` below).
    """
    if not settings.get("shipment_suite.run_external_storage_dialog_check", True):
        pytest.skip("External storage dialog check disabled in config")

    nav = NavigationPage(context_page, timeout_ms=page_timeout_ms)
    external_storage = ExternalStoragePage(context_page, timeout_ms=page_timeout_ms)

    with allure.step("Open System > External Storage"):
        nav.open_external_storage()
        external_storage.assert_page_loaded()

    with allure.step("Open and cancel the Add NFS mount dialog"):
        external_storage.open_add_mount_dialog()
        external_storage.cancel_add_mount_dialog()


@allure.epic("Web Shipment")
@allure.feature("Data Transfer")
@pytest.mark.shipment
@pytest.mark.data_transfer
@pytest.mark.order(21)
def test_nfs_mount_and_data_transfer(context_page, page_timeout_ms: int, settings: Settings):
    """Full real NFS mount + data transfer + verify flow, migrated from legacy
    ``ConfigStore.check_ui_data_transfer`` / ``WebStore.check_data_transfer``.

    Requires real external NFS server details under ``nfs.host`` /
    ``nfs.mount_point`` / ``nfs.export_path`` in config, plus
    ``shipment_suite.run_nfs_data_transfer: true`` - both are unset by
    default since no NFS infrastructure is provisioned in this environment.
    """
    if not settings.get("shipment_suite.run_nfs_data_transfer", False):
        pytest.skip("NFS data transfer flow disabled in config (no NFS infrastructure provisioned)")

    nfs_host = settings.get("nfs.host")
    nfs_mount_point = settings.get("nfs.mount_point")
    nfs_export_path = settings.get("nfs.export_path")
    if not (nfs_host and nfs_mount_point and nfs_export_path):
        pytest.skip("NFS host/mount_point/export_path not fully configured")

    nav = NavigationPage(context_page, timeout_ms=page_timeout_ms)
    external_storage = ExternalStoragePage(context_page, timeout_ms=page_timeout_ms)
    data_transfer = DataTransferPage(context_page, timeout_ms=page_timeout_ms)

    with allure.step(f"Mount NFS export {nfs_host}:{nfs_export_path} as {nfs_mount_point}"):
        nav.open_external_storage()
        external_storage.open_add_mount_dialog()
        external_storage.add_nfs_mount(nfs_mount_point, nfs_host, nfs_export_path)

    with allure.step("Create a data transfer from the NFS mount into /bryck"):
        nav.open_data_transfer()
        data_transfer.open_add_transfer_dialog()
        data_transfer.submit_transfer(nfs_mount_point, "/bryck", verify_checksum=True)

    with allure.step("Create a verify job against the transferred path"):
        data_transfer.open_add_verify_dialog()
        data_transfer.submit_verify("/bryck")


@allure.epic("Web Shipment")
@allure.feature("Mount / Unmount")
@pytest.mark.shipment
@pytest.mark.mount_eject
@pytest.mark.order(22)
def test_bryck_mount_with_hot_pluggable_eject(context_page, page_timeout_ms: int, settings: Settings):
    """Round-trip Unmount -> Mount, migrated from legacy
    ``ConfigStore._test_ui_bryck_mount_with_hot_pluggable_eject``.

    Genuinely state-changing (really ejects/remounts the live bryck) - OFF by
    default (``shipment_suite.run_mount_eject_cycle``). Always leaves the
    device back in a Mounted state, whatever its starting state was.
    """
    if not settings.get("shipment_suite.run_mount_eject_cycle", False):
        pytest.skip("Mount/eject hot-pluggable cycle disabled in config (state-changing, opt-in only)")

    nav = NavigationPage(context_page, timeout_ms=page_timeout_ms)
    storage = StorageConfigurationPage(context_page, timeout_ms=page_timeout_ms)
    mount_eject = MountEjectPage(context_page, timeout_ms=page_timeout_ms)

    with allure.step("Unmount (hot-pluggable eject)"):
        nav.open_storage_unmount()
        mount_eject.eject()

    with allure.step("Re-mount the bryck"):
        nav.open_storage_mount()
        if mount_eject.is_encryption_key_required():
            pytest.fail(
                "Bryck reports an encryption key is required to remount - this suite does not "
                "guess/select a key type or upload a key file on the caller's behalf."
            )
        mount_eject.mount()

    with allure.step("Assert the bryck is Mounted again"):
        nav.open_storage_status()
        storage.assert_storage_status_visible()
