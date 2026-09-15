"""Pytest fixtures and hooks for Playwright web shipment test suite."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import allure
import pytest
from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from web_shipment.core.config import Settings
from web_shipment.core.logger import get_json_logger
from web_shipment.pages.login_page import LoginPage


DEFAULT_CONFIG = "config/config.yaml"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--config",
        action="store",
        default=os.environ.get("WS_CONFIG_FILE", DEFAULT_CONFIG),
        help="Path to config yaml",
    )
    parser.addoption(
        "--base-url",
        action="store",
        default="",
        help="Override application.base_url",
    )


def pytest_configure(config: pytest.Config) -> None:
    cfg = Settings(config.getoption("--config"))
    results_dir = Path(cfg.get("reporting.allure_results_dir", "reports/web/allure-results"))
    results_dir.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session")
def settings(pytestconfig: pytest.Config) -> Settings:
    return Settings(pytestconfig.getoption("--config"))


@pytest.fixture(scope="session")
def base_url(settings: Settings, pytestconfig: pytest.Config) -> str:
    override = pytestconfig.getoption("--base-url")
    return override or settings.get("application.base_url")


@pytest.fixture(scope="session")
def page_timeout_ms(settings: Settings) -> int:
    """Default per-action timeout (ms) shared by all page objects.

    Centralized here so every ``BasePage`` subclass instantiated in tests uses
    the same config-driven value instead of each call site hardcoding one.
    """
    return int(settings.get("timeouts.default_ms", 10000))


@pytest.fixture(scope="session")
def playwright_instance() -> Playwright:
    with sync_playwright() as playwright:
        yield playwright


@pytest.fixture(scope="session")
def browser(playwright_instance: Playwright, settings: Settings) -> Browser:
    engine = settings.get("browser.engine", "chromium")
    launch_kwargs = {
        "headless": bool(settings.get("browser.headless", True)),
        "slow_mo": int(settings.get("browser.slow_mo_ms", 0)),
    }
    browser_obj = getattr(playwright_instance, engine).launch(**launch_kwargs)
    yield browser_obj
    browser_obj.close()


@pytest.fixture
def artifact_logger(request: pytest.FixtureRequest, settings: Settings):
    # Parametrized test ids can contain characters that are illegal in Windows
    # filenames (e.g. "|" from ids like "fs=zfs|enc=True|..."), which raises
    # OSError: [Errno 22] Invalid argument when opening the log file. Strip
    # anything outside a safe allowlist before using it as a filename.
    safe_name = request.node.nodeid.replace("/", "_").replace("::", "__")
    safe_name = re.sub(r'[<>:"/\\|?*\[\]=,]', "_", safe_name)
    safe_name = re.sub(r"_+", "_", safe_name).strip("_")
    logs_dir = settings.get("paths.logs_dir", "logs/web")
    logger = get_json_logger(safe_name, logs_dir)
    logger.info("test_start")
    yield logger
    logger.info("test_end")


def _artifact_dirs(settings: Settings) -> tuple[Path, Path]:
    """Return (traces_dir, screenshots_dir), creating both if they don't exist."""
    traces_dir = Path(settings.get("paths.traces_dir", "traces/web"))
    screenshots_dir = Path(settings.get("paths.screenshots_dir", "screenshots/web"))
    traces_dir.mkdir(parents=True, exist_ok=True)
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    return traces_dir, screenshots_dir


def _new_traced_context(browser: Browser, settings: Settings) -> BrowserContext:
    """Create a browser context with tracing enabled, using the shared viewport/cert config."""
    context = browser.new_context(
        viewport={
            "width": int(settings.get("browser.viewport.width", 1680)),
            "height": int(settings.get("browser.viewport.height", 960)),
        },
        ignore_https_errors=bool(settings.get("browser.ignore_https_errors", True)),
    )
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    return context


def _navigate_to_app(page: Page, base_url: str, settings: Settings) -> None:
    """Load the app and wait until the login form is actually interactive.

    Waits for "domcontentloaded" rather than the default "load": this is a
    live-updating Vue SPA whose background polling/websocket traffic can keep
    the network "busy" indefinitely on a slow link, so the browser's "load"
    event may never fire even though the page is fully usable. Waiting for the
    login form to appear is a much more reliable readiness signal.
    """
    navigation_timeout_ms = int(settings.get("timeouts.navigation_ms", 20000))
    page.goto(base_url, wait_until="domcontentloaded", timeout=navigation_timeout_ms)
    page.wait_for_selector(LoginPage.SELECTORS["username_input"], timeout=navigation_timeout_ms)


def _finalize_context(
    request: pytest.FixtureRequest,
    page: Page,
    context: BrowserContext,
    artifact_logger,
    screenshots_dir: Path,
    traces_dir: Path,
) -> None:
    """Attach a failure screenshot (if the test failed) plus the Playwright trace to Allure."""
    failed = getattr(request.node, "rep_call", None) and request.node.rep_call.failed
    safe_name = request.node.nodeid.replace("/", "_").replace("::", "__")

    if failed:
        screenshot = screenshots_dir / f"{safe_name}_FAILED.png"
        page.screenshot(path=str(screenshot), full_page=True)
        allure.attach.file(str(screenshot), name="failure-screenshot", attachment_type=allure.attachment_type.PNG)
        artifact_logger.error("test_failed", extra={"screenshot": str(screenshot)})

    trace_file = traces_dir / f"{safe_name}.zip"
    context.tracing.stop(path=str(trace_file))
    allure.attach.file(str(trace_file), name="playwright-trace", attachment_type=allure.attachment_type.ZIP)
    context.close()


@pytest.fixture
def context_page(
    request: pytest.FixtureRequest,
    browser: Browser,
    settings: Settings,
    base_url: str,
    page_timeout_ms: int,
    artifact_logger,
) -> Page:
    """An already-authenticated page - the fixture most tests should use."""
    traces_dir, screenshots_dir = _artifact_dirs(settings)
    context = _new_traced_context(browser, settings)

    page = context.new_page()
    page.set_default_timeout(int(settings.get("timeouts.default_ms", 10000)))
    _navigate_to_app(page, base_url, settings)

    # Locators for this flow live on LoginPage itself
    # (see web_shipment/pages/login_page.py), not in config.
    LoginPage(page, timeout_ms=page_timeout_ms).login(
        settings.get("credentials.username"),
        settings.get("credentials.password"),
    )

    yield page

    _finalize_context(request, page, context, artifact_logger, screenshots_dir, traces_dir)


@pytest.fixture
def guest_page(
    request: pytest.FixtureRequest,
    browser: Browser,
    settings: Settings,
    base_url: str,
    artifact_logger,
) -> Page:
    """A page loaded up to the login form but NOT authenticated.

    Use this for negative-path authentication tests (e.g. wrong credentials)
    that must not use the already-logged-in ``context_page`` fixture.
    """
    traces_dir, screenshots_dir = _artifact_dirs(settings)
    context = _new_traced_context(browser, settings)

    page = context.new_page()
    page.set_default_timeout(int(settings.get("timeouts.default_ms", 10000)))
    _navigate_to_app(page, base_url, settings)

    yield page

    _finalize_context(request, page, context, artifact_logger, screenshots_dir, traces_dir)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[Any]):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)
