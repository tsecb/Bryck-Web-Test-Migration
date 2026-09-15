"""Migrated shipment suite from legacy unittest/selenium to pytest/playwright."""

from __future__ import annotations

import ipaddress
import time

import allure
import pytest

from web_shipment.core.config import Settings
from web_shipment.core.models import StorageVariant
from web_shipment.pages.login_page import LoginPage
from web_shipment.pages.navigation_page import NavigationPage
from web_shipment.pages.network_configuration_page import NetworkConfigurationPage
from web_shipment.pages.storage_configuration_page import StorageConfigurationPage
from web_shipment.services.device_api import DeviceApiClient
from web_shipment.services.host_probe import is_host_up
from web_shipment.services.matrix import build_storage_variants


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Expand the storage test matrix into one parametrized test case per variant.

    Using this hook (instead of a fixture consumed in a for-loop) gives every
    permutation its own pytest/Allure test node with a readable id (see
    ``StorageVariant.id``), so one bad variant fails only its own test node
    and every other combination still gets reported independently. Reads the
    config file directly (no live device call), so it's safe at collection time.
    """
    if "storage_variant" not in metafunc.fixturenames:
        return
    config_path = metafunc.config.getoption("--config")
    matrix = Settings(config_path).get("test_matrix", {})
    variants = build_storage_variants(matrix)
    metafunc.parametrize("storage_variant", variants, ids=[variant.id for variant in variants])


@allure.epic("Web Shipment")
@allure.feature("API Health")
@pytest.mark.shipment
@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.order(0)
def test_device_api_reports_system_info(settings: Settings):
    """Fast, browser-free health check that the device's management API responds.

    Runs before any browser-driven test so a dead/unreachable device fails
    immediately with a clear API error instead of burning time on a slow
    browser navigation timeout first.
    """
    api_client = DeviceApiClient(
        base_url=settings.get("application.api_base_url"),
        verify_ssl=bool(settings.get("application.verify_ssl", False)),
    )
    info = api_client.info()
    assert info, "Device API returned an empty system-info payload"


@allure.epic("Web Shipment")
@allure.feature("Authentication")
@pytest.mark.shipment
@pytest.mark.negative
@pytest.mark.order(1)
def test_login_with_invalid_credentials_is_rejected(guest_page, page_timeout_ms: int):
    """Negative-path check: wrong credentials must not reach the authenticated app shell."""
    LoginPage(guest_page, timeout_ms=page_timeout_ms).login("admin", "not-the-real-password")

    nav = NavigationPage(guest_page, timeout_ms=page_timeout_ms)
    nav.assert_unauthenticated()


@allure.epic("Web Shipment")
@allure.feature("Sanity")
@pytest.mark.shipment
@pytest.mark.smoke
@pytest.mark.order(2)
def test_bryck_presence_check(settings: Settings, context_page, page_timeout_ms: int):
    """Equivalent to legacy test_bryck_check with UI visibility validation."""
    if not settings.get("shipment_suite.run_bryck_check", True):
        pytest.skip("Shipment bryck check disabled in config")

    nav = NavigationPage(context_page, timeout_ms=page_timeout_ms)
    storage = StorageConfigurationPage(context_page, timeout_ms=page_timeout_ms)
    nav.open_storage_format()
    storage.assert_storage_status_visible()


@allure.epic("Web Shipment")
@allure.feature("Storage Configuration")
@pytest.mark.shipment
@pytest.mark.storage
@pytest.mark.order(3)
def test_ui_configure_storage_variant(
    settings: Settings, context_page, page_timeout_ms: int, storage_variant: StorageVariant
):
    """Migrated storage variant matrix from legacy test_ui_configure_all_variants.

    One test node per ``storage_variant`` (see ``pytest_generate_tests`` above)
    instead of one test looping over the whole matrix.
    """
    if not settings.get("shipment_suite.run_storage_matrix", True):
        pytest.skip("Shipment storage matrix disabled in config")

    nav = NavigationPage(context_page, timeout_ms=page_timeout_ms)
    storage = StorageConfigurationPage(context_page, timeout_ms=page_timeout_ms)

    with allure.step(f"Configure variant: {storage_variant.id}"):
        nav.open_storage_format()
        storage.configure_variant(storage_variant)
        # Confirm the UI actually reported completion instead of silently no-oping.
        storage.assert_storage_status_visible()


@allure.epic("Web Shipment")
@allure.feature("Network")
@pytest.mark.shipment
@pytest.mark.network
@pytest.mark.order(4)
def test_ui_network_configure(settings: Settings, context_page, page_timeout_ms: int):
    """Migrated static-IP network configure flow with API-verified rollback."""
    if not settings.get("shipment_suite.run_network_static", True):
        pytest.skip("Shipment static network flow disabled in config")

    api_client = DeviceApiClient(
        base_url=settings.get("application.api_base_url"),
        verify_ssl=bool(settings.get("application.verify_ssl", False)),
    )
    original = api_client.up_interfaces()
    if not original:
        pytest.skip("No UP interfaces found from API")

    nav = NavigationPage(context_page, timeout_ms=page_timeout_ms)
    network = NetworkConfigurationPage(context_page, timeout_ms=page_timeout_ms)

    start_octet = int(settings.get("network.network_test_ip_octet_start", 210))
    for interface_name, old_ip in original.items():
        with allure.step(f"Reconfigure {interface_name} from {old_ip}"):
            ip = ipaddress.ip_address(old_ip)
            replacement = f"{'.'.join(old_ip.split('.')[:3])}.{start_octet}"
            nav.open_network()
            # interface_name must be passed explicitly - the form only ever edits
            # whichever interface is currently selected in its own dropdown, it does
            # not automatically track which interface we're iterating over here.
            network.configure_static(replacement, interface_name=interface_name)

            # Always verify via the read-only management API that the change
            # actually took effect - a UI form can submit "successfully" while
            # silently failing server-side, which a screenshot alone won't catch.
            updated = api_client.up_interfaces()
            assert updated.get(interface_name) == replacement, (
                f"Expected {interface_name} to report {replacement} via API after the UI "
                f"update, got {updated.get(interface_name)!r}"
            )

            if settings.get("network.ping_enabled", False):
                assert is_host_up(replacement, int(settings.get("network.ping_timeout_seconds", 1)))

            nav.open_network()
            network.configure_static(old_ip, interface_name=interface_name)

            restored = api_client.up_interfaces()
            assert restored.get(interface_name) == old_ip, (
                f"Expected {interface_name} to be restored to {old_ip} via API, "
                f"got {restored.get(interface_name)!r}"
            )
            if ip.is_private and settings.get("network.ping_enabled", False):
                assert is_host_up(old_ip, int(settings.get("network.ping_timeout_seconds", 1)))


@allure.epic("Web Shipment")
@allure.feature("Network")
@pytest.mark.shipment
@pytest.mark.network
@pytest.mark.order(5)
def test_ui_network_configure_using_dhcp(settings: Settings, context_page, page_timeout_ms: int):
    """Migrated DHCP network flow from legacy suite with configurable wait."""
    if not settings.get("shipment_suite.run_network_dhcp", True):
        pytest.skip("Shipment DHCP flow disabled in config")

    nav = NavigationPage(context_page, timeout_ms=page_timeout_ms)
    network = NetworkConfigurationPage(context_page, timeout_ms=page_timeout_ms)

    nav.open_network()
    network.enable_dhcp()
    time.sleep(int(settings.get("network.dhcp_wait_seconds", 30)))
