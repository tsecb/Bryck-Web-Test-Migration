"""Bryck Storage > Object Store coverage: Bucket / Access / Configure.

Continues the ``@pytest.mark.order(n)`` sequence started in
``test_web_shipment.py`` and ``test_system_administration.py``.
"""

from __future__ import annotations

import allure
import pytest

from web_shipment.core.config import Settings
from web_shipment.pages.navigation_page import NavigationPage
from web_shipment.pages.object_store_page import ObjectStorePage


@allure.epic("Web Shipment")
@allure.feature("Object Store")
@pytest.mark.shipment
@pytest.mark.object_store
@pytest.mark.order(13)
def test_object_store_bucket_create_dialog_can_be_cancelled(context_page, page_timeout_ms: int, settings: Settings):
    """Exercises the real create-bucket form interaction without persisting a bucket.

    Verified live and mirrored here: CREATE BUCKET starts disabled, becomes
    enabled once a name is typed, and CANCEL reverts cleanly with the bucket
    list unchanged. This is deliberately the "Cancel" path only - this device
    already has real user buckets ("jjejej", "kazuki" as of writing) that
    must never be touched, so no test in this suite creates or deletes a
    bucket for real.
    """
    if not settings.get("shipment_suite.run_object_store_bucket_flow", True):
        pytest.skip("Object Store bucket flow disabled in config")

    nav = NavigationPage(context_page, timeout_ms=page_timeout_ms)
    object_store = ObjectStorePage(context_page, timeout_ms=page_timeout_ms)

    with allure.step("Open Bryck Storage > Object Store > Bucket"):
        nav.open_object_store_bucket()

    with allure.step("Record the current bucket count"):
        bucket_count_before = object_store.bucket_count()

    with allure.step("Open the create-bucket form"):
        object_store.start_create_bucket()
        object_store.assert_create_bucket_submit_disabled()

    with allure.step("Typing a name enables CREATE BUCKET"):
        object_store.type_bucket_name("automation-check-do-not-create")
        object_store.assert_create_bucket_submit_enabled()

    with allure.step("Cancel instead of submitting"):
        object_store.cancel_create_bucket()

    with allure.step("Bucket count is unchanged - nothing was persisted"):
        assert object_store.bucket_count() == bucket_count_before


@allure.epic("Web Shipment")
@allure.feature("Object Store")
@pytest.mark.shipment
@pytest.mark.object_store
@pytest.mark.order(14)
def test_object_store_access_page_loads(context_page, page_timeout_ms: int):
    """Object Store > Access screen renders its entry point without erroring."""
    nav = NavigationPage(context_page, timeout_ms=page_timeout_ms)
    object_store = ObjectStorePage(context_page, timeout_ms=page_timeout_ms)

    with allure.step("Open Bryck Storage > Object Store > Access"):
        nav.open_object_store_access()

    with allure.step("Assert the page rendered"):
        object_store.assert_access_list_visible()


@allure.epic("Web Shipment")
@allure.feature("Object Store")
@pytest.mark.shipment
@pytest.mark.object_store
@pytest.mark.order(15)
def test_object_store_configure_lists_known_interface(context_page, page_timeout_ms: int):
    """Object Store > Configure lists at least the primary management interface.

    ``oob_net0`` is the always-present management interface on this device
    (confirmed live), so its presence in this list is a stable, safe thing to
    assert regardless of whatever other interfaces are currently configured.
    """
    nav = NavigationPage(context_page, timeout_ms=page_timeout_ms)
    object_store = ObjectStorePage(context_page, timeout_ms=page_timeout_ms)

    with allure.step("Open Bryck Storage > Object Store > Configure"):
        nav.open_object_store_configure()

    with allure.step("Assert the known management interface is listed"):
        object_store.assert_configure_lists_interface("oob_net0")
