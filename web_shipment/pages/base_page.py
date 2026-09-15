"""Base page object for the Page Object Model (POM).

Every concrete page (LoginPage, NavigationPage, ...) declares its own
``SELECTORS`` class attribute - a ``{logical_name: css_or_text_selector}``
dict - right next to the code that uses it. This base class only supplies
the shared, reusable interaction helpers (click/fill/select/etc.) that look
up a locator by its logical name and drive it through Playwright with a
consistent timeout, so subclasses stay small and declarative.
"""

from __future__ import annotations

import os
from typing import ClassVar

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from web_shipment.core.config import Settings

#: Same default this repo's tests/conftest.py falls back to for --config, so the
#: auto-relogin fail-safe below reads the same credentials the suite is using
#: even though individual page objects are never explicitly given a Settings.
_DEFAULT_CONFIG_FILE = "config/config.yaml"

#: Tracks which pages (by id) are mid-recovery, keyed by ``id(page)`` rather than
#: the page object itself so we never depend on Playwright's ``Page`` supporting
#: weak references or arbitrary attribute assignment. Guards against infinite
#: recursion if the login form itself is broken/unreachable (a real failure,
#: not a recoverable session drop) - see ``BasePage._relogin``.
_relogin_in_progress_page_ids: set[int] = set()


class BasePage:
    """Common Playwright interaction helpers shared by every page object.

    Subclasses MUST override ``SELECTORS`` with their own locator map.
    """

    #: Logical-name -> CSS/text selector map. Overridden by each subclass.
    SELECTORS: ClassVar[dict[str, str]] = {}

    #: A selector that reliably only appears on the login form - used to detect
    #: "we got silently bounced back to login" without importing LoginPage at
    #: module scope (LoginPage itself extends BasePage, so that would be circular).
    _LOGIN_MARKER_SELECTOR: ClassVar[str] = "#username"

    def __init__(self, page: Page, timeout_ms: int = 10000, settings: Settings | None = None) -> None:
        self.page = page
        self.selectors = self.SELECTORS
        self.timeout_ms = timeout_ms
        self._settings = settings

    def _resolve_settings(self) -> Settings:
        """Lazily load the same config file the running suite is using.

        Only needed by the auto-relogin fail-safe below - callers never have to
        pass ``settings`` explicitly for normal page-object usage.
        """
        if self._settings is None:
            self._settings = Settings(os.environ.get("WS_CONFIG_FILE", _DEFAULT_CONFIG_FILE))
        return self._settings

    def _looks_logged_out(self) -> bool:
        """Fast, best-effort check for the login form having reappeared."""
        try:
            return self.page.locator(self._LOGIN_MARKER_SELECTOR).first.is_visible()
        except Exception:
            return False

    def _relogin(self) -> None:
        """Re-authenticate with the configured credentials after an unexpected session drop.

        Guarded by ``_relogin_in_progress_page_ids`` so a genuinely broken/
        unreachable login form raises a clear error instead of recursing
        forever (``LoginPage.login`` itself calls ``self.fill``/``self.click``,
        which are wrapped by the very same fail-safe this method is part of).
        """
        page_id = id(self.page)
        if page_id in _relogin_in_progress_page_ids:
            raise RuntimeError(
                "Auto-relogin already in progress for this page - the login form "
                "itself appears unreachable/broken, not just an expired session."
            )

        from web_shipment.pages.login_page import LoginPage  # local import: avoids a circular import

        _relogin_in_progress_page_ids.add(page_id)
        try:
            settings = self._resolve_settings()
            LoginPage(self.page, timeout_ms=self.timeout_ms).login(
                settings.get("credentials.username"),
                settings.get("credentials.password"),
            )
        finally:
            _relogin_in_progress_page_ids.discard(page_id)

    def _run_with_relogin_failsafe(self, action):
        """Run a zero-arg Playwright action; auto-recover exactly once from a mid-test logout.

        The device's session can expire (default 10 minutes - see System >
        Settings) or drop for other reasons mid-run, which silently bounces
        every subsequent locator back to the login form. Without this, that
        surfaces as a confusing raw ``TimeoutError`` deep inside some unrelated
        click/fill instead of a clear "session expired, logged back in" story.
        This is a single, bounded retry (log back in, then re-run the exact
        same action once) - it deliberately does not loop, so a genuinely
        broken locator still fails fast instead of hanging twice as long.
        """
        try:
            return action()
        except PlaywrightTimeoutError:
            if not self._looks_logged_out():
                raise
            self._relogin()
            return action()

    def click(self, key: str) -> None:
        """Click the first match of the locator registered under ``key``."""
        selector = self.selectors[key]
        self._run_with_relogin_failsafe(lambda: self.page.locator(selector).first.click(timeout=self.timeout_ms))

    def fill(self, key: str, value: str) -> None:
        """Fill the first match of the locator registered under ``key``."""
        selector = self.selectors[key]
        self._run_with_relogin_failsafe(
            lambda: self.page.locator(selector).first.fill(value, timeout=self.timeout_ms)
        )

    def is_visible(self, key: str) -> bool:
        """Return whether the locator registered under ``key`` is visible."""
        selector = self.selectors[key]
        return self.page.locator(selector).first.is_visible(timeout=self.timeout_ms)

    def get_text(self, key: str) -> str:
        """Return the trimmed inner text of the locator registered under ``key``."""
        selector = self.selectors[key]
        return self._run_with_relogin_failsafe(
            lambda: self.page.locator(selector).first.inner_text(timeout=self.timeout_ms).strip()
        )

    def select_option(self, key: str, option_text: str) -> None:
        """Open an Element UI dropdown and choose the visible option matching ``option_text``.

        The app's dropdowns (`el-select`) are a read-only text input that toggles a
        nearby `.el-select-dropdown__item` list via inline `display:none`, rather than
        a native `<select>`, so a plain Playwright `select_option()` call cannot be used.
        """
        selector = self.selectors[key]

        def _select_visible_option() -> None:
            self.page.locator(selector).first.click(timeout=self.timeout_ms)
            option = self.page.locator(".el-select-dropdown__item:visible", has_text=option_text).first
            option.click(timeout=self.timeout_ms)

        self._run_with_relogin_failsafe(_select_visible_option)

