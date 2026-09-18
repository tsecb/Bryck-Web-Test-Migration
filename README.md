# Bryck Web Test Migration

This project contains the migrated Bryck web test suite, built on pytest + Playwright + Allure. The goal is to provide one clean run entry point that handles setup, suite selection, report generation, archive cleanup, and remote execution without manual repeated commands.

## What is included

- One runner: [run_tests.py](run_tests.py)
- Suite-aware execution for one or many suites
- Automatic venv creation and dependency install when needed
- Archive-before-run cleanup of previous data
- One self-contained HTML Allure report per run
- Remote Linux execution via a detached screen session
- Windows-side SSH trigger/status/fetch helper

## Project structure

- [config/config.yaml](config/config.yaml) — runtime config, base URL, credentials, timeouts, reporting paths
- [tests/web/test_web_shipment.py](tests/web/test_web_shipment.py) — shipment suite
- [tests/web/test_system_administration.py](tests/web/test_system_administration.py) — admin/system suite
- [tests/web/test_object_store.py](tests/web/test_object_store.py) — object-store suite
- [tests/web/test_data_management.py](tests/web/test_data_management.py) — data-management checks
- [web_shipment](web_shipment) — page objects, fixtures, services, config models
- [scripts/run_in_screen.sh](scripts/run_in_screen.sh) — starts the run in a detached screen session on the remote Linux runner
- [scripts/remote_control.py](scripts/remote_control.py) — triggers, views status, and fetches the latest report from a remote machine
- [pytest.ini](pytest.ini) — pytest configuration and markers
- [requirements.txt](requirements.txt) — Python dependencies
- [reports/web](reports/web) — output directory for Allure results and generated HTML
- [archive/web](archive/web) — timestamped archive of previous runs

## Setup

From the project root:

```powershell
cd "C:\Users\SanjayJayakumar\Downloads\Bryck Web Test Migration"

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
```

If needed, override the target device in one of these ways:

```powershell
# Option 1: edit config/config.yaml
# Option 2: environment variables
$env:WS_APPLICATION_BASE_URL = "http://192.168.6.35"
$env:WS_CREDENTIALS_USERNAME = "admin"
$env:WS_CREDENTIALS_PASSWORD = "<your-password>"
```

## Local execution

The preferred entry point is the runner in [run_tests.py](run_tests.py). This is the single command you can use from the repo root:

```powershell
python run_tests.py
```

### Run one suite only

```powershell
python run_tests.py --suite web_shipment
python run_tests.py --suite system_administration
python run_tests.py --suite object_store
python run_tests.py --suite data_management
```

### Run multiple suites in one command

```powershell
python run_tests.py --suite web_shipment system_administration
python run_tests.py --suite web_shipment data_management
python run_tests.py --suite all
```

### Advanced filter with pytest markers

```powershell
python run_tests.py --markers "network or storage"
python run_tests.py --markers "smoke and system"
```

### Base URL override without editing config

```powershell
python run_tests.py --base-url http://192.168.6.35
python run_tests.py --suite web_shipment --base-url http://192.168.6.35
```

### Skip preflight check if you really know the device is healthy

```powershell
python run_tests.py --skip-preflight
```

> The default runner performs a fast preflight check before starting the suite. If the device is down, it stops early instead of burning time on slow browser timeouts.

## Remote execution with no extra script to remember

From the remote repo directory, you do not need to pass a special screen flag anymore. The runner now auto-starts the detached `screen` session for Linux remote runs by default:

```bash
cd ~/Bryck-Web-Test-Migration
python run_tests.py --suite web_shipment
```

That command will:

- detect that this is a Linux remote-style run
- replace any existing `web-test` session if one is still alive
- start a fresh screen session automatically
- run the selected suite inside the screen session
- stream all output to `logs/web/runner_<timestamp>.log`
- leave the session available for live inspection with `screen -r web-test`

Examples:

```bash
python run_tests.py --suite system_administration
python run_tests.py --suite object_store
python run_tests.py --suite all
python run_tests.py --markers "network or storage"
```

If you ever want to force the screen behavior explicitly, you can still use `--screen`. If you want to disable the auto-start behavior, set:

```bash
export WS_AUTO_SCREEN=0
```

You do not need to call `scripts/run_in_screen.sh` directly unless you are intentionally using the compatibility wrapper. The clean path is to use the runner itself.

## What the runner does automatically

When you run:

```powershell
python run_tests.py --suite web_shipment
```

it does all of this for you:

1. Creates or reuses the project .venv
2. Installs Python requirements if needed
3. Archives previous report/log artifacts from the last run
4. Runs only the selected suite(s)
5. Generates a fresh single-file HTML report for the current run
6. Keeps old results separate in archive/web so they do not mix with the new output

## Reports and archive behavior

Every new run archives the previous run’s artifacts before generating a new report. The archive folder is under:

- [archive/web](archive/web)

The current report is generated in:

- [reports/web](reports/web)

The single file you should open is the generated Allure HTML report in that folder, for example:

```text
reports/web/allure-report-web-<timestamp>.html
```

This is the one-file report intended to be opened directly in a browser.

## Remote execution

You can run the suite on a separate Linux machine and still use the same project workflow.

### A) Run directly on the remote Linux machine

This is the supported path:

```bash
cd ~/Bryck-Web-Test-Migration
python run_tests.py --suite web_shipment
```

The same runner handles the detached screen session automatically. It:

- kills any stale `web-test` screen session
- starts a fresh detached screen session named `web-test`
- runs the selected suite inside that session
- writes the detailed run output to `logs/web/runner_<timestamp>.log`
- leaves the session available for live inspection with `screen -r web-test`

Useful commands:

```bash
screen -ls
screen -r web-test
tail -f logs/web/runner_*.log
```

### B) Trigger from your Windows machine over SSH

Set the remote environment variables first:

```powershell
$env:WS_REMOTE_HOST = "192.168.6.36"
$env:WS_REMOTE_USER = "bryck"
$env:WS_REMOTE_PASSWORD = "<password>"   # or set WS_REMOTE_KEY_PATH instead
$env:WS_REMOTE_DIR = "~/Bryck-Web-Test-Migration"
```

Then trigger the remote run through the runner itself:

```powershell
python scripts/remote_control.py trigger -- --suite web_shipment
python scripts/remote_control.py trigger -- --suite system_administration
python scripts/remote_control.py trigger -- --suite all
```

This helper now simply delegates to the same remote-safe flow:

```bash
python run_tests.py --screen --suite web_shipment
```

Check the status of the remote run:

```powershell
python scripts/remote_control.py status
```

Download the latest single-file HTML report from the remote machine:

```powershell
python scripts/remote_control.py fetch
```

The fetched report will be placed under:

- [reports/web/fetched](reports/web/fetched)

## Remote trigger examples you can use

```powershell
# Trigger only the shipment suite
python scripts/remote_control.py trigger -- --suite web_shipment

# Trigger only data management checks
python scripts/remote_control.py trigger -- --suite data_management

# Trigger the full set
python scripts/remote_control.py trigger -- --suite all

# Trigger with pytest marker filtering
python scripts/remote_control.py trigger -- --markers "network or storage"
```

## One-line cheat sheet

```powershell
# Local run
python run_tests.py --suite web_shipment

# Remote run from Windows
python scripts/remote_control.py trigger -- --suite web_shipment

# Check status on remote
python scripts/remote_control.py status

# Fetch report from remote
python scripts/remote_control.py fetch
```

## Notes

- The project runner is the supported entry point. Prefer it over raw pytest calls.
- The remote screen session is intentionally single-session and auto-replaced, so it stays clean and avoids stale runner processes.
- Old output is archived before a new run starts, so each run remains isolated.
- The device must be reachable; otherwise the preflight check aborts early to avoid a long slow failure.

## Migration note

This repo was migrated from the legacy web suite into the newer pytest + Playwright + Allure framework. The migration mapping lives in [docs/MIGRATION_MAPPING.md](docs/MIGRATION_MAPPING.md).
