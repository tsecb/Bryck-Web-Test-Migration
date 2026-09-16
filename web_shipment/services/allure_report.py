"""Allure report generation helpers: clean-slate archiving + a single self-contained HTML report.

Each run is expected to reflect ONLY what that run tested - never a blend with
previous runs. Two things make that true:

1. ``archive_previous_run`` moves every existing results/logs/screenshots/traces
   directory out of the way (into a timestamped folder under ``archive/web/``)
   *before* pytest writes a single new file, run as the very first step of
   ``run_tests.py``. Without this, ``pytest --alluredir`` (see pytest.ini) simply
   appends new result files next to whatever was already there from prior runs,
   which is exactly what silently happened before this change - the report was a
   mix of many runs' results at once.
2. ``generate_allure_html`` renders with Allure's ``--single-file`` option, so the
   entire report (data + history + widgets) is baked into one standalone
   ``index.html`` - no separate ``data/``/``history/`` folders, no local HTTP
   server needed, and nothing left around to accidentally bleed into the next run.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
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


def archive_previous_run(
    paths: dict[str, Path], archive_root: Path, loose_report_glob: tuple[Path, str] | None = None
) -> Path | None:
    """Move every existing (non-empty) directory in ``paths`` into a fresh,
    timestamped folder under ``archive_root`` - e.g. ``archive/web/20260916_101500/
    allure-results/`` - then recreate each original directory empty.

    ``loose_report_glob``, if given as ``(base_dir, glob_pattern)``, also
    sweeps any loose files matching that pattern directly under ``base_dir``
    (e.g. previous runs' standalone ``allure-report-web-*.html`` files sitting
    next to the raw results dirs) into ``archive_dir/reports/``.

    Must run before pytest (or anything else) writes a single new file for the
    current run, so the new run always starts from a genuinely clean slate
    instead of accumulating alongside old results/logs/screenshots/traces.
    Returns the archive folder actually created, or ``None`` if there was
    nothing to archive (e.g. first-ever run).
    """
    stamp = time.strftime("%Y%m%d_%H%M%S")
    archive_dir = archive_root / stamp
    archived_anything = False

    for name, path in paths.items():
        if not path.exists() or not any(path.iterdir()):
            path.mkdir(parents=True, exist_ok=True)
            continue
        archive_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(archive_dir / name))
        path.mkdir(parents=True, exist_ok=True)
        archived_anything = True

    if loose_report_glob is not None:
        base_dir, pattern = loose_report_glob
        matches = list(base_dir.glob(pattern)) if base_dir.exists() else []
        if matches:
            reports_archive = archive_dir / "reports"
            reports_archive.mkdir(parents=True, exist_ok=True)
            for match in matches:
                shutil.move(str(match), str(reports_archive / match.name))
            archived_anything = True

    return archive_dir if archived_anything else None



def generate_allure_html(results_dir: Path, html_dir: Path) -> None:
    """Generate a single self-contained ``index.html`` (data/history/widgets all
    inlined) from the current run's result files only - no local HTTP server
    needed to view it, and nothing left over to leak into the next run.

    Falls back to a normal multi-file report if the installed Allure CLI is too
    old to support ``--single-file`` (added in Allure 2.9), so this still works
    end to end either way; the caller checks which form ``html_dir`` ended up
    in via ``(html_dir / "index.html").exists()``.
    """
    allure_bin = shutil.which("allure")
    if allure_bin is None:
        raise RuntimeError("allure CLI not found in PATH")

    if html_dir.exists():
        shutil.rmtree(html_dir)

    result = subprocess.run(
        [allure_bin, "generate", "--single-file", str(results_dir), "-o", str(html_dir), "--clean"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # Older Allure CLI without --single-file support - retry without it.
        subprocess.run(
            [allure_bin, "generate", str(results_dir), "-o", str(html_dir), "--clean"],
            check=True,
            capture_output=True,
            text=True,
        )


def finalize_single_file_report(html_dir: Path, output_dir: Path) -> Path:
    """Copy the generated report into ``output_dir`` as one clearly-named,
    timestamped, immediately-downloadable file for this run.

    If Allure fell back to a multi-file report (see ``generate_allure_html``),
    copies the whole folder instead and returns its path - callers should check
    ``.is_dir()`` on the result before telling a user to "just open this file".
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    single_file = html_dir / "index.html"

    if single_file.exists():
        destination = output_dir / f"allure-report-web-{stamp}.html"
        shutil.copy2(single_file, destination)
        return destination

    destination = output_dir / f"allure-report-web-{stamp}"
    shutil.copytree(html_dir, destination)
    return destination
