"""Allure report generation helpers with trend preservation and shareable output."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path


def write_support_files(results_dir: Path, base_url: str, browser: str, headless: bool) -> None:
    """Write environment, categories, and executor metadata for richer Allure pages."""
    results_dir.mkdir(parents=True, exist_ok=True)
    now = time.strftime("%Y-%m-%dT%H:%M:%S")

    (results_dir / "environment.properties").write_text(
        "\n".join(
            [
                "Target.Environment=Shipment-Lab",
                f"Target.BaseURL={base_url}",
                "Suite=Web Shipment",
                "Framework=pytest + Playwright + Allure",
                f"Browser={browser}",
                f"Headless={headless}",
                f"RunDate={now}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    categories = [
        {
            "name": "Locator regressions",
            "matchedStatuses": ["failed", "broken"],
            "messageRegex": ".*(Timeout|strict mode violation|No node found).*",
        },
        {
            "name": "Backend/API instability",
            "matchedStatuses": ["failed", "broken"],
            "messageRegex": ".*(500|502|503|ConnectionError|ReadTimeout).*",
        },
        {
            "name": "Assertion failures",
            "matchedStatuses": ["failed"],
        },
    ]
    (results_dir / "categories.json").write_text(json.dumps(categories, indent=2), encoding="utf-8")

    executor = {
        "name": "GitHub Actions" if os.environ.get("GITHUB_ACTIONS") else "Local Runner",
        "type": "github" if os.environ.get("GITHUB_ACTIONS") else "local",
        "buildName": f"Web Shipment - {now}",
    }
    (results_dir / "executor.json").write_text(json.dumps(executor, indent=2), encoding="utf-8")


def preserve_trend_history(results_dir: Path, html_dir: Path) -> Path | None:
    """Copy old history out and place it into current results to keep trends alive."""
    history_src = html_dir / "history"
    if not history_src.exists():
        return None

    temp_dir = Path(tempfile.mkdtemp(prefix="allure_history_"))
    shutil.copytree(history_src, temp_dir / "history")
    history_dst = results_dir / "history"
    if history_dst.exists():
        shutil.rmtree(history_dst)
    shutil.copytree(temp_dir / "history", history_dst)
    return temp_dir


def generate_allure_html(results_dir: Path, html_dir: Path) -> None:
    """Generate static Allure HTML from result files."""
    allure_bin = shutil.which("allure")
    if allure_bin is None:
        raise RuntimeError("allure CLI not found in PATH")

    subprocess.run(
        [allure_bin, "generate", str(results_dir), "-o", str(html_dir), "--clean"],
        check=True,
        capture_output=True,
        text=True,
    )


def build_shareable_report(html_dir: Path, shareable_dir: Path) -> Path:
    """Create a portable folder plus zip archive from generated allure-html."""
    if shareable_dir.exists():
        shutil.rmtree(shareable_dir)
    shutil.copytree(html_dir, shareable_dir)

    readme = shareable_dir / "HOW_TO_OPEN.txt"
    readme.write_text(
        "Open this report using an HTTP server, not file://.\n"
        "Examples:\n"
        "  python -m http.server 9090\n"
        "Then browse http://localhost:9090\n",
        encoding="utf-8",
    )

    ps1 = shareable_dir / "open_report.ps1"
    ps1.write_text(
        "python -m http.server 9090\n",
        encoding="utf-8",
    )

    archive_base = shareable_dir.parent / f"allure-report-web-{time.strftime('%Y-%m-%d_%H-%M-%S')}"
    archive_path = shutil.make_archive(str(archive_base), "zip", root_dir=shareable_dir)
    return Path(archive_path)


def cleanup_temp_history(temp_dir: Path | None) -> None:
    """Remove temporary trend-history staging directory."""
    if temp_dir and temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
