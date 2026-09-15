"""Runner for migrated web shipment suite with Allure trend and shareable report support."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from web_shipment.core.config import Settings
from web_shipment.services.allure_report import (
    build_shareable_report,
    cleanup_temp_history,
    generate_allure_html,
    preserve_trend_history,
    write_support_files,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run web shipment playwright suite")
    parser.add_argument("--config", default="config/config.yaml", help="Path to config yaml")
    parser.add_argument("--base-url", default="", help="Override application.base_url")
    parser.add_argument("--markers", default="shipment", help="Pytest markers expression")
    parser.add_argument("--no-report", action="store_true", help="Skip allure html generation")
    parser.add_argument("--open-report", action="store_true", help="Open allure report server after run")
    parser.add_argument("extra", nargs=argparse.REMAINDER, help="Additional pytest args")
    return parser.parse_args()


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
    shareable_dir = Path(settings.get("reporting.shareable_report_dir"))

    history_tmp = preserve_trend_history(results_dir, html_dir)
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
            report_zip = build_shareable_report(html_dir, shareable_dir)
            print(f"Shareable report folder: {shareable_dir}")
            print(f"Shareable report zip: {report_zip}")
        except Exception as exc:
            print(f"Report generation warning: {exc}")

    if args.open_report:
        allure_bin = "allure"
        subprocess.Popen([allure_bin, "open", str(html_dir)])

    cleanup_temp_history(history_tmp)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
