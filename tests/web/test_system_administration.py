"""System ("Administration") section coverage: status, external storage, cloud
setup, settings, alerts, and a safe (view-only) power screen check.

Continues the ``@pytest.mark.order(n)`` sequence from ``test_web_shipment.py``
(which ends at 5) so the whole suite still runs in one deterministic order
even though these live in a separate file for readability.
"""

from __future__ import annotations

import allure
import pytest

from web_shipment.core.config import Settings
from web_shipment.pages.alerts_page import AlertsPage
from web_shipment.pages.cloud_setup_page import CloudSetupPage
from web_shipment.pages.external_storage_page import ExternalStoragePage
from web_shipment.pages.navigation_page import NavigationPage
from web_shipment.pages.power_page import PowerPage
from web_shipment.pages.settings_page import SettingsPage
from web_shipment.pages.system_status_page import SystemStatusPage


@allure.epic("Web Shipment")
@allure.feature("System Status")
@pytest.mark.shipment
@pytest.mark.system
@pytest.mark.smoke
@pytest.mark.order(6)
def test_system_status_shows_hardware_summary(context_page, page_timeout_ms: int):
    """System > Status must render live hardware/build facts, not an empty shell.

    A blank/loading summary here usually means the device-info API call that
    backs this screen failed silently, so this is a cheap smoke check for
    that upstream dependency in addition to verifying the UI itself.
    """
    nav = NavigationPage(context_page, timeout_ms=page_timeout_ms)
    status = SystemStatusPage(context_page, timeout_ms=page_timeout_ms)

    with allure.step("Open System > Status"):
        nav.open_system_status()

    with allure.step("Assert hardware/build summary is visible"):
        status.assert_summary_visible()

    with allure.step("Assert a build version string was actually reported"):
        assert status.build_version_text(), "Build version text was empty"


@allure.epic("Web Shipment")
@allure.feature("External Storage")
@pytest.mark.shipment
@pytest.mark.system
@pytest.mark.order(7)
def test_external_storage_page_loads(context_page, page_timeout_ms: int):
    """External Storage screen renders its entry point ("Add") without erroring."""
    nav = NavigationPage(context_page, timeout_ms=page_timeout_ms)
    external_storage = ExternalStoragePage(context_page, timeout_ms=page_timeout_ms)

    with allure.step("Open System > External Storage"):
        nav.open_external_storage()

    with allure.step("Assert the page rendered"):
        external_storage.assert_page_loaded()


@allure.epic("Web Shipment")
@allure.feature("Cloud Setup")
@pytest.mark.shipment
@pytest.mark.system
@pytest.mark.order(8)
def test_cloud_setup_page_loads(context_page, page_timeout_ms: int):
    """Cloud Setup screen renders; robust to whatever provider count currently exists.

    Deliberately does not assert a specific provider/username - this device
    may have a real, actively-used cloud connection configured (confirmed
    live: an "aws"/minioadmin entry powering scheduled transfers), and this
    suite must never assume, create, or remove cloud credentials.
    """
    nav = NavigationPage(context_page, timeout_ms=page_timeout_ms)
    cloud_setup = CloudSetupPage(context_page, timeout_ms=page_timeout_ms)

    with allure.step("Open System > Cloud Setup"):
        nav.open_cloud_setup()

    with allure.step("Assert the page rendered"):
        cloud_setup.assert_page_loaded()

    with allure.step("Sanity-check provider row count is non-negative (list is queryable)"):
        assert cloud_setup.configured_provider_count() >= 0


@allure.epic("Web Shipment")
@allure.feature("Settings")
@pytest.mark.shipment
@pytest.mark.system
@pytest.mark.settings
@pytest.mark.order(9)
def test_settings_tabs_show_current_values(context_page, page_timeout_ms: int):
    """All three Settings tabs (Timezone/Session Timeout/Date and Time) load with a value + Change control.

    Never clicks any "Change" button - doing so opens a real edit dialog that
    would alter live device behaviour (e.g. session timeout affects every
    other test in the suite), so this only verifies the read-only summary.
    """
    nav = NavigationPage(context_page, timeout_ms=page_timeout_ms)
    settings_page = SettingsPage(context_page, timeout_ms=page_timeout_ms)

    with allure.step("Open System > Settings"):
        nav.open_settings()

    with allure.step("Timezone tab shows a current value"):
        settings_page.open_timezone_tab()
        settings_page.assert_timezone_visible()

    with allure.step("Session Timeout tab shows a current value"):
        settings_page.open_session_timeout_tab()
        settings_page.assert_session_timeout_visible()

    with allure.step("Date and Time tab shows a current value"):
        settings_page.open_date_time_tab()
        settings_page.assert_date_time_visible()


@allure.epic("Web Shipment")
@allure.feature("Alerts")
@pytest.mark.shipment
@pytest.mark.system
@pytest.mark.alerts
@pytest.mark.order(10)
def test_alerts_receiver_add_user_form_requires_all_fields(context_page, page_timeout_ms: int):
    """Real validation-behaviour test: ADD stays disabled until the form is fully valid.

    Fills User Name + Email but deliberately leaves Alert Category unset, then
    asserts ADD is still disabled - proving the form enforces all three
    required fields client-side. Never actually submits (no alert user is
    created), so it's safe to run repeatedly with no cleanup needed.
    """
    nav = NavigationPage(context_page, timeout_ms=page_timeout_ms)
    alerts = AlertsPage(context_page, timeout_ms=page_timeout_ms)

    with allure.step("Open System > Alerts > Alerts Receiver"):
        nav.open_alerts_receiver()
        alerts.assert_alerts_receiver_loaded()

    with allure.step("ADD starts disabled on an empty form"):
        alerts.assert_add_alert_user_disabled()

    with allure.step("Fill User Name + Email, but leave Alert Category unset"):
        alerts.fill_alert_user_name("automation-check")
        alerts.fill_alert_email("automation-check@example.com")

    with allure.step("ADD must still be disabled (Alert Category is required)"):
        alerts.assert_add_alert_user_disabled()


@allure.epic("Web Shipment")
@allure.feature("Alerts")
@pytest.mark.shipment
@pytest.mark.system
@pytest.mark.alerts
@pytest.mark.order(11)
def test_alerts_email_and_notification_pages_load(context_page, page_timeout_ms: int):
    """Email Setup and Notification (SNS/SQS) screens both render their list tables."""
    nav = NavigationPage(context_page, timeout_ms=page_timeout_ms)
    alerts = AlertsPage(context_page, timeout_ms=page_timeout_ms)

    with allure.step("Open System > Alerts > Email Setup"):
        nav.open_email_setup()
        alerts.assert_email_setup_loaded()

    with allure.step("Open System > Alerts > Notification (SNS/SQS)"):
        nav.open_notification_setup()
        alerts.assert_notification_setup_loaded()


@allure.epic("Web Shipment")
@allure.feature("Power")
@pytest.mark.shipment
@pytest.mark.system
@pytest.mark.order(12)
def test_power_page_renders_without_triggering_shutdown(context_page, page_timeout_ms: int, settings: Settings):
    """System > Power renders its Shutdown control - which this test NEVER clicks.

    This is intentionally the least "thorough" test in the suite: it proves
    navigation/rendering work for this screen while structurally avoiding the
    one real, physically-destructive action available in the entire
    application. ``PowerPage`` itself has no click/shutdown method at all, so
    this can't be "fixed" into a destructive test by future maintainers
    without deliberately adding new code to do so.
    """
    if not settings.get("shipment_suite.run_power_page_check", True):
        pytest.skip("Power page check disabled in config")

    nav = NavigationPage(context_page, timeout_ms=page_timeout_ms)
    power = PowerPage(context_page, timeout_ms=page_timeout_ms)

    with allure.step("Open System > Power"):
        nav.open_power()

    with allure.step("Assert Shutdown control is visible (never clicked)"):
        power.assert_shutdown_button_visible()
