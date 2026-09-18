"""Runner for the migrated web shipment suite.

Every invocation starts from a clean slate: the previous run's allure results,
HTML, logs, screenshots, and traces are archived (never silently mixed into
the new run - see ``archive_previous_run``), then the suite runs, then a
single self-contained HTML report is generated for THIS run only.

The runner also handles the standard local workflow end-to-end:
- ensure .venv exists and install requirements if needed
- allow a single command to target one or many suites via ``--suite``
- keep the legacy ``--markers`` workflow working for advanced custom runs
- start a remote detached ``screen`` session automatically when ``--screen`` is passed
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import time
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

SUITE_FILES: dict[str, list[str]] = {
    "web_shipment": ["tests/web/test_web_shipment.py"],
    "system_administration": ["tests/web/test_system_administration.py"],
    "object_store": ["tests/web/test_object_store.py"],
    "data_management": ["tests/web/test_data_management.py"],
    "all": ["tests/web/test_web_shipment.py", "tests/web/test_system_administration.py", "tests/web/test_object_store.py", "tests/web/test_data_management.py"],
}

SUITE_ALIASES: dict[str, str] = {
    "shipment": "web_shipment",
    "webshipment": "web_shipment",
    "web-shipment": "web_shipment",
    "system": "system_administration",
    "system_admin": "system_administration",
    "admin": "system_administration",
    "object-store": "object_store",
    "object_store": "object_store",
    "data-management": "data_management",
    "data_management": "data_management",
    "all": "all",
}


def log_step(message: str) -> None:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{stamp}] {message}", flush=True)


def resolve_suite_names(values: list[str] | None) -> list[str]:
    if not values:
        return ["all"]

    out: list[str] = []
    for item in values:
        key = item.strip().lower().replace("-", "_").replace(" ", "_")
        resolved = SUITE_ALIASES.get(key, key)
        if resolved not in SUITE_FILES:
            raise SystemExit(
                f"Unknown suite '{item}'. Available suites: {', '.join(sorted(SUITE_FILES))}. "
                "You can also pass pytest marker expressions via --markers."
            )
        out.append(resolved)
    return out


def python_executable_for_venv(project_root: Path) -> Path:
    if os.name == "nt":
        return project_root / ".venv" / "Scripts" / "python.exe"
    return project_root / ".venv" / "bin" / "python"


def ensure_virtualenv(project_root: Path) -> Path:
    py_exe = python_executable_for_venv(project_root)
    if py_exe.exists():
        return py_exe

    print(f".venv not found at {py_exe}. Creating it from scratch...")
    subprocess.run([sys.executable, "-m", "venv", str(project_root / ".venv")], check=True)
    subprocess.run([str(py_exe), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], check=True)
    subprocess.run([str(py_exe), "-m", "pip", "install", "-r", str(project_root / "requirements.txt")], check=True)
    return py_exe

# Pytest's own navigation timeout can be minutes long (see config.yaml
# timeouts.navigation_ms - bumped up for slow mount/format operations), and
# --reruns 1 doubles that. If the device/network is simply down, letting each
# test discover that on its own would take hours (this is exactly what
# happened on 2026-09-15/16: ~90 tests all failed the same way, one at a
# time). This check fails the whole run in seconds instead.
PREFLIGHT_TIMEOUT_SECONDS = 10


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Bryck web shipment suite")
    parser.add_argument("--config", default="config/config.yaml", help="Path to config yaml")
    parser.add_argument("--base-url", default="", help="Override application.base_url")
    parser.add_argument(
        "--suite",
        "--suites",
        nargs="+",
        default=None,
        help="Run one or multiple suite groups: web_shipment, system_administration, object_store, data_management, all",
    )
    parser.add_argument("--markers", default="", help="Optional pytest marker expression, e.g. 'network or storage'. If omitted, suite selection is used.")
    parser.add_argument("--no-report", action="store_true", help="Skip allure html generation")
    parser.add_argument("--open-report", action="store_true", help="Open the generated report in a browser after the run")
    parser.add_argument(
        "--screen",
        action="store_true",
        help="Force a detached screen session. On Linux remote runs this is automatic by default; set WS_AUTO_SCREEN=0 to disable the auto behavior.",
    )
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help="Skip the fast device-reachability check and go straight to pytest "
        "(not recommended - a down device will then take a very long time to fail via pytest's own timeouts/reruns)",
    )
    parser.add_argument("--skip-venv-setup", action="store_true", help="Skip automatic .venv creation and dependency install")
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


def pytest_targets_from_suite(suite_names: list[str]) -> list[str]:
    targets: list[str] = []
    for suite_name in suite_names:
        for target in SUITE_FILES[suite_name]:
            targets.append(target)
    return targets


def run_pytest(settings: Settings, base_url: str, markers: str, suite_names: list[str], extra_args: list[str], python_exe: Path) -> int:
    env = {**os.environ, "WS_CONFIG_FILE": str(settings.config_file)}
    command = [str(python_exe), "-m", "pytest"]
    normalized_extra = [arg for arg in extra_args if arg != "--"]

    if suite_names:
        command += pytest_targets_from_suite(suite_names)
    if markers:
        command += ["-m", markers]
    if base_url:
        command += ["--base-url", base_url]
    if normalized_extra:
        command += normalized_extra

    log_step(f"Pytest command: {' '.join(command)}")
    log_step(f"Target suites: {suite_names}")
    log_step(f"Marker expression: {markers or '(none)'}")
    log_step(f"Extra pytest args: {normalized_extra if normalized_extra else '(none)'}")
    result = subprocess.run(command, env=env)
    log_step(f"Pytest finished with exit code {result.returncode}")
    return result.returncode


def start_screen_session(project_root: Path, args: argparse.Namespace) -> int:
    """Launch a detached screen session that runs this same command, teeing all
    output to logs/web/runner_<timestamp>.log. This is the remote-friendly entry
    point: from the remote directory, the user just runs `python run_tests.py ...
    --screen` and the runner handles the screen management for them."""
    try:
        subprocess.run(["screen", "-ls"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print("screen is not installed on this machine; cannot start a detached session.")
        return 1

    log_dir = project_root / "logs" / "web"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    runner_log = log_dir / f"runner_{stamp}.log"

    screen_name = "web-test"
    original_args = []
    for key, value in vars(args).items():
        if key == "screen":
            continue
        if key == "extra":
            original_args.extend(value)
            continue
        if value is None or value is False:
            continue
        if isinstance(value, list):
            original_args.extend(str(v) for v in value)
        else:
            original_args.extend([f"--{key.replace('_', '-')}", str(value)])

    command_tokens = [sys.executable, str(project_root / "run_tests.py")]
    for item in original_args:
        command_tokens.append(item)
    command_string = " ".join(shlex.quote(str(part)) for part in command_tokens)

    print(f"==> Starting detached screen session '{screen_name}'")
    print(f"==> Runner log: {runner_log}")
    print(f"==> Command: {command_string}")

    existing = subprocess.run(
        ["bash", "-lc", f"screen -ls 2>/dev/null | grep -oE '[0-9]+\\.{screen_name}[[:space:]]' | awk '{{print $1}}' || true"],
        capture_output=True,
        text=True,
        check=False,
    )
    if existing.stdout.strip():
        for pid_name in existing.stdout.splitlines():
            if not pid_name.strip():
                continue
            subprocess.run(["screen", "-S", pid_name, "-X", "quit"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            pid = pid_name.split(".", 1)[0]
            try:
                os.kill(int(pid), 9)
            except (ProcessLookupError, ValueError):
                pass
        subprocess.run(["screen", "-wipe"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    screen_launcher = (
        f"cd {shlex.quote(str(project_root))} && "
        f"exec bash -lc {shlex.quote(command_string)} 2>&1 | tee {shlex.quote(str(runner_log))}"
    )
    screen_cmd = ["screen", "-dmS", screen_name, "bash", "-lc", screen_launcher]
    result = subprocess.run(screen_cmd, check=False)
    if result.returncode == 0:
        print(f"==> Session started. Attach with: screen -r {screen_name}")
        print(f"==> Tail the live log with: tail -f {runner_log}")
        return 0
    print(f"==> Failed to start the screen session for {screen_name}")
    return result.returncode


def main() -> int:
    args = parse_args()
    project_root = Path(__file__).resolve().parent

    auto_screen = (
        sys.platform.startswith("linux")
        and os.environ.get("WS_AUTO_SCREEN", "1") not in {"0", "false", "False"}
    )
    if args.screen or auto_screen:
        return start_screen_session(project_root, args)

    log_step(f"Beginning Bryck web test run from {project_root}")
    log_step(f"User arguments: suite={args.suite}, markers={args.markers}, base_url={args.base_url}, extra={args.extra}")

    if not args.skip_venv_setup:
        log_step("Ensuring project virtual environment and dependencies are present")
        python_exe = ensure_virtualenv(project_root)
    else:
        python_exe = python_executable_for_venv(project_root)
    log_step(f"Using Python executable: {python_exe}")

    suite_names = resolve_suite_names(args.suite)
    markers = args.markers.strip()
    if not markers:
        if suite_names == ["all"]:
            markers = "shipment"
        elif len(suite_names) == 1:
            if suite_names[0] == "web_shipment":
                markers = "shipment"
            elif suite_names[0] == "system_administration":
                markers = "system"
            elif suite_names[0] == "object_store":
                markers = "object_store"
            elif suite_names[0] == "data_management":
                markers = "dashboard or report or data_transfer or external_storage or mount_eject"
            else:
                markers = "shipment"

    settings = Settings(args.config)

    base_url = args.base_url or settings.get("application.base_url")
    log_step(f"Resolved base URL: {base_url}")
    log_step(f"Resolved suite list: {suite_names}")
    log_step(f"Resolved marker filter: {markers or '(none)'}")
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
        log_step(f"Checking device reachability: {base_url} (timeout={PREFLIGHT_TIMEOUT_SECONDS}s)")
        error = preflight_check(base_url, verify_ssl)
        if error:
            log_step(f"ABORTING - device unreachable at {base_url}: {error}")
            print(
                f"\nABORTING - device unreachable at {base_url}: {error}\n"
                "This is a network/device problem, not a test bug - the suite was NOT run "
                "(no point burning hours failing every test the slow way). Check the device is "
                "powered on and reachable from this machine, then re-run. Use --skip-preflight "
                "to bypass this check if you're sure the device is actually fine.\n"
            )
            return 1
        log_step("Device reachability check passed - proceeding")

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
        log_step(f"Archived previous run data to: {archived_to}")
    else:
        log_step("No previous run data to archive; starting fresh")

    write_support_files(
        results_dir=results_dir,
        base_url=base_url,
        browser=settings.get("browser.engine", "chromium"),
        headless=bool(settings.get("browser.headless", True)),
    )
    log_step(f"Reporting directories initialized: results={results_dir}, html={html_dir}, single-file={single_file_dir}")

    code = run_pytest(settings, base_url, markers, suite_names, args.extra, python_exe)

    if not args.no_report:
        try:
            log_step("Generating Allure HTML report from the current run results")
            generate_allure_html(results_dir, html_dir)
            report_path = finalize_single_file_report(html_dir, single_file_dir)
            if report_path.is_dir():
                log_step(f"Allure report (multi-file fallback): {report_path}")
            else:
                log_step(f"Single-file HTML report (this run only): {report_path}")
            if args.open_report:
                webbrowser.open(report_path.as_uri() if report_path.is_file() else (report_path / "index.html").as_uri())
        except Exception as exc:
            log_step(f"Report generation warning: {exc}")

    log_step(f"Run complete with exit code {code}")
    return code




if __name__ == "__main__":
    raise SystemExit(main())
