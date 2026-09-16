"""Runner for the migrated web shipment suite.

Every invocation starts from a clean slate: the previous run's allure results,
HTML, logs, screenshots, and traces are archived (never silently mixed into
the new run - see ``archive_previous_run``), then the suite runs, then a
single self-contained HTML report is generated for THIS run only.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import webbrowser
from pathlib import Path

import requests

from web_shipment.core.config import Settings
from web_shipment.services.allure_report import (
    archive_previous_run,
    finalize_single_file_report,
    generate_allure_html,
    write_support_files,
)

# Pytest's own navigation timeout can be minutes long (see config.yaml
# timeouts.navigation_ms - bumped up for slow mount/format operations), and
# --reruns 1 doubles that. If the device/network is simply down, letting each
# test discover that on its own would take hours (this is exactly what
# happened on 2026-09-15/16: ~90 tests all failed the same way, one at a
# time). This check fails the whole run in seconds instead.
PREFLIGHT_TIMEOUT_SECONDS = 10


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run web shipment playwright suite")
    parser.add_argument("--config", default="config/config.yaml", help="Path to config yaml")
    parser.add_argument("--base-url", default="", help="Override application.base_url")
    parser.add_argument("--markers", default="shipment", help="Pytest markers expression")
    parser.add_argument("--no-report", action="store_true", help="Skip allure html generation")
    parser.add_argument("--open-report", action="store_true", help="Open the generated report in a browser after the run")
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help="Skip the fast device-reachability check and go straight to pytest "
        "(not recommended - a down device will then take a very long time to fail via pytest's own timeouts/reruns)",
    )
    parser.add_argument("extra", nargs=argparse.REMAINDER, help="Additional pytest args")
    return parser.parse_args()


def preflight_check(base_url: str, verify_ssl: bool) -> str | None:
    """Fast reachability check against the device. Returns an error message
    string if the device looks unreachable, or None if it's fine.

    This intentionally does NOT use Playwright/a browser - just a short-timeout
    plain HTTP request - so an unreachable device is reported in ~10s instead
    of minutes, before any browser/pytest machinery even starts.
    """
    try:
        requests.get(base_url, timeout=PREFLIGHT_TIMEOUT_SECONDS, verify=verify_ssl)
    except requests.exceptions.RequestException as exc:
        return f"{type(exc).__name__}: {exc}"
    return None


def run_pytest(settings: Settings, base_url: str, markers: str, extra_args: list[str]) -> int:
    env = {**os.environ, "WS_CONFIG_FILE": str(settings.config_file)}
    command = [sys.executable, "-m", "pytest", "-m", markers]
    if base_url:
        command += ["--base-url", base_url]
    if extra_args:
        command += extra_args

    print("Running:", " ".join(command))
    result = subprocess.run(command, env=env)
    return result.returncode


def main() -> int:
    args = parse_args()
    settings = Settings(args.config)

    base_url = args.base_url or settings.get("application.base_url")
    results_dir = Path(settings.get("reporting.allure_results_dir"))
    html_dir = Path(settings.get("reporting.allure_html_dir"))
    single_file_dir = Path(settings.get("reporting.single_file_report_dir", "reports/web"))
    archive_root = Path(settings.get("reporting.archive_dir", "archive/web"))
    logs_dir = Path(settings.get("paths.logs_dir"))
    screenshots_dir = Path(settings.get("paths.screenshots_dir"))
    traces_dir = Path(settings.get("paths.traces_dir"))
    verify_ssl = bool(settings.get("application.verify_ssl", True))

    # Step -1 (fail fast): make sure the device is even reachable before
    # doing anything else. Without this, an unreachable device means every
    # single test fails the slow way (full navigation_ms timeout x reruns),
    # which can take hours instead of seconds - see run_tests.py's docstring.
    if not args.skip_preflight:
        print(f"Checking device reachability: {base_url} (timeout={PREFLIGHT_TIMEOUT_SECONDS}s)...")
        error = preflight_check(base_url, verify_ssl)
        if error:
            print(
                f"\nABORTING - device unreachable at {base_url}: {error}\n"
                "This is a network/device problem, not a test bug - the suite was NOT run "
                "(no point burning hours failing every test the slow way). Check the device is "
                "powered on and reachable from this machine, then re-run. Use --skip-preflight "
                "to bypass this check if you're sure the device is actually fine.\n"
            )
            return 1
        print("Device is reachable - proceeding.")

    # Step 0: clean slate. Must happen before pytest (or anything else) writes
    # a single new file for this run - see archive_previous_run's docstring.
    archived_to = archive_previous_run(
        {
            "allure-results": results_dir,
            "allure-html": html_dir,
            "logs": logs_dir,
            "screenshots": screenshots_dir,
            "traces": traces_dir,
        },
        archive_root,
        loose_report_glob=(single_file_dir, "allure-report-web-*"),
    )
    if archived_to:
        print(f"Archived previous run's results/logs/screenshots/traces to: {archived_to}")

    write_support_files(
        results_dir=results_dir,
        base_url=base_url,
        browser=settings.get("browser.engine", "chromium"),
        headless=bool(settings.get("browser.headless", True)),
    )

    code = run_pytest(settings, base_url, args.markers, args.extra)

    if not args.no_report:
        try:
            generate_allure_html(results_dir, html_dir)
            report_path = finalize_single_file_report(html_dir, single_file_dir)
            if report_path.is_dir():
                print(f"Report (multi-file - older Allure CLI without --single-file support): {report_path}")
            else:
                print(f"Single-file HTML report (this run only): {report_path}")
            if args.open_report:
                webbrowser.open(report_path.as_uri() if report_path.is_file() else (report_path / "index.html").as_uri())
        except Exception as exc:
            print(f"Report generation warning: {exc}")

    return code




if __name__ == "__main__":
    raise SystemExit(main())
