# BRYCK Web Shipment Playwright Framework

A clean migration of the legacy web shipment suite from selenium/unittest to Playwright + pytest + Allure with trend-ready reporting and shareable report outputs.

## Highlights

- True Page Object Model: each page class under `web_shipment/pages/` owns its own
  `SELECTORS` locator map and interaction methods - `config.yaml` only holds run
  configuration (URLs, credentials, timeouts, matrix), not UI selectors.
- Config-driven storage test matrix, expanded into one parametrized pytest case per
  variant (`test_ui_configure_storage_variant[...]`) so each permutation is reported
  and can fail/pass independently.
- Fast, browser-free API health check (`test_device_api_reports_system_info`) runs
  first so a dead device fails immediately instead of via a slow browser timeout.
- Negative-path authentication test (`test_login_with_invalid_credentials_is_rejected`)
  using a dedicated unauthenticated `guest_page` fixture.
- Network changes are verified through the read-only management API, not just the UI
  form submitting without error.
- Per-test artifacts: screenshot, trace zip, json logs.
- Allure rich metadata: environment, categories, executor.
- Trend chart continuity by preserving history between runs.
- Shareable report folder and zip bundle after each run.
- GitHub Actions workflow for CI artifact publishing.
- Full System ("Administration") coverage: read-only Status, External Storage,
  Cloud Setup, Settings (Timezone/Session Timeout/Date and Time), Alerts (Receiver
  form validation, Email Setup, Notification SNS/SQS), and a view-only Power check
  that intentionally never clicks the real Shutdown control.
- Full Object Store coverage (Bryck Storage > Object Store): a real, safe
  create-bucket-then-cancel flow (never persists a bucket), plus Access and
  Configure screen checks.
- Extensive/full storage-matrix + data-management coverage migrated from the
  legacy full `WebTest` suite (`tests/web/test_data_management.py`): Dashboard
  status, System > Status drive-serial field, System > Report generation,
  Data Transfer (Data Center) add/verify dialogs, External Storage NFS mount
  dialog, a real (config-gated) NFS mount + transfer + verify flow, and the
  Bryck Storage Mount/Unmount hot-pluggable-eject round-trip (opt-in, off by
  default - see "Migration scope" below).
- Every new locator was confirmed against the live device DOM (not guessed from
  static analysis) before being written into a page object.
- **Session-drop fail-safe (two layers)**: the device's session can expire (10 min
  default, configurable in System > Settings) or otherwise log the browser out
  mid-run. (1) `BasePage` wraps every `click`/`fill`/`get_text`/`select_option` in a
  try/except: on a `TimeoutError`, it checks whether the login form has silently
  reappeared and, if so, logs back in with the configured credentials and retries
  that exact step once. (2) At the whole-test level, `pytest.ini` runs with
  `--reruns 1 --only-rerun TimeoutError`, so if recovery mid-test still isn't
  enough, the entire test reruns with a brand-new authenticated `context_page`
  (fresh browser context + fresh login) rather than failing outright. Real
  assertion failures are untouched by either layer - only timeout-shaped failures
  are treated as recoverable.

## Project Structure

```text
Bryck Web Test Migration/
  config/
    config.yaml
  docs/
    MIGRATION_MAPPING.md
  tests/
    conftest.py
    web/
      test_web_shipment.py
      test_system_administration.py
      test_object_store.py
      test_data_management.py
  web_shipment/
    core/
      config.py
      logger.py
      models.py
    pages/
      base_page.py
      login_page.py
      navigation_page.py
      network_configuration_page.py
      storage_configuration_page.py
      system_status_page.py
      object_store_page.py
      settings_page.py
      cloud_setup_page.py
      alerts_page.py
      external_storage_page.py
      power_page.py
      dashboard_page.py
      system_report_page.py
      data_transfer_page.py
      mount_eject_page.py
    services/
      allure_report.py
      device_api.py
      host_probe.py
      matrix.py
  .github/workflows/
    web-shipment-playwright.yml
  pytest.ini
  requirements.txt
  run_tests.py
```

## Install

```powershell
git clone <your-repo-url>
cd "Bryck Web Test Migration"

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
```

Then point the suite at your device. Either edit `config/config.yaml` directly
(`application.base_url`, `credentials.username`/`password`), or leave the
committed defaults alone and override at run time with environment variables
(never commit real credentials):

```powershell
$env:WS_APPLICATION_BASE_URL = "https://<device-ip>"
$env:WS_CREDENTIALS_USERNAME = "admin"
$env:WS_CREDENTIALS_PASSWORD = "<real-password>"
```

## Run

```powershell
# Full migrated shipment suite (all markers tagged `shipment`)
python run_tests.py

# Only a subset, by marker expression
python run_tests.py --markers "shipment and network"

# One-off base URL override without touching config.yaml or env vars
python run_tests.py --base-url https://192.168.0.140

# Equivalent, calling pytest directly (useful for -k, --reruns 0, single tests, etc.)
python -m pytest -m shipment
python -m pytest tests/web/test_data_management.py -v
```

Each run writes fresh output to `reports/web/`, `screenshots/web/`, `traces/web/`,
and `logs/web/` (all git-ignored - see `.gitignore`). Open the HTML report with:

```powershell
python -m pytest ...  # or python run_tests.py
allure open reports/web/allure-html
```

## Report Outputs

- Raw results: reports/web/allure-results
- HTML: reports/web/allure-html
- Shareable folder: reports/web/shareable-report
- Shareable zip: reports/web/allure-report-web-<timestamp>.zip
- Screenshots: screenshots/web
- Traces: traces/web
- Logs: logs/web

## Adding New Test Cases

1. Add or extend a page object under `web_shipment/pages/`: add new locators to that
   page's `SELECTORS` dict and a method that drives them (locators never go in
   `config.yaml`).
2. Add business flow in `tests/web/test_web_shipment.py`, instantiating the page
   object with `timeout_ms=page_timeout_ms`.
3. Reuse existing fixtures from `tests/conftest.py`:
   - `settings` / `page_timeout_ms` - config and shared per-action timeout.
   - `context_page` - an already-authenticated page (most tests should use this).
   - `guest_page` - a page loaded to the login form but NOT authenticated, for
     negative-path auth tests.
4. If the case needs matrix coverage, add values under `test_matrix` in
   `config/config.yaml` - `pytest_generate_tests` in the test module automatically
   expands it into one parametrized test per permutation.
5. Mark new tests with an existing marker (`smoke`, `storage`, `network`, `api`,
   `negative`, `system`, `object_store`, `settings`, `alerts`, `dashboard`, `report`,
   `data_transfer`, `external_storage`, `mount_eject`) or add a new one to
   `pytest.ini`'s `markers` list (required because `--strict-markers` is set).

### Safety rules for new tests (device is real, shared hardware)

- Never click a real "Shutdown"/destructive control from a test - see
  `web_shipment/pages/power_page.py`, which deliberately has no click method for
  its Shutdown button at all.
- Never create/delete/modify real user data (buckets, cloud configs, alert users)
  - prefer an "open form -> assert state -> Cancel" pattern like
    `test_object_store_bucket_create_dialog_can_be_cancelled`.
- When reading a table's row count right after navigating to it, wait for the
  list to settle first (row or empty-state visible) before calling `.count()` -
  see `ObjectStorePage.bucket_count()` for the pattern.

## Migration scope (legacy `WebTest`/`WebTestShipment` -> this suite)

The full legacy Selenium suite (`ci_cd/tests/func/test_web.py` +
`test_web_shipment.py`) was analyzed method-by-method and migrated as follows:

**Migrated (extensive coverage, not just the reduced shipment subset):**

- Full storage-format matrix (`test_ui_configure_storage_variant`), expanded from
  8 to 32 variants by default (encryption x io_size x data_sync x compression) -
  see the `test_matrix` comment block in `config/config.yaml` for how to opt into
  the maximally exhaustive 144-variant legacy matrix (raid5+raid6, 3 io sizes, 3
  data-sync modes).
- Drive serial number field check, dashboard status check, bryck report
  generation, network configure (static + DHCP), Object Store bucket/access/
  configure, and the full System (Administration) section - all as before.
- Data Transfer (Data Center) add-transfer/add-verify dialogs, External Storage
  NFS mount dialog - migrated as safe "open -> assert fields -> Cancel" checks
  by default, plus a real, config-gated NFS mount + transfer + verify flow
  (`test_nfs_mount_and_data_transfer`) for environments with actual NFS
  infrastructure (set `nfs.host`/`nfs.mount_point`/`nfs.export_path` in
  `config.yaml` and `shipment_suite.run_nfs_data_transfer: true`).
- Bryck Storage Mount/Unmount hot-pluggable-eject round-trip
  (`test_bryck_mount_with_hot_pluggable_eject`) - genuinely state-changing (really
  ejects/remounts the live bryck), so it is **off by default**
  (`shipment_suite.run_mount_eject_cycle: false`); opt in deliberately per
  environment.

**Explicitly out of scope (with rationale):**

- **Cloud configure/deconfigure/transfer**: already disabled/commented out in the
  legacy suite itself. Its legacy test fixture data (`web_store.py`) also
  contains what appear to be **real AWS access key/secret and Azure tenant/
  client credentials hardcoded in plaintext** - these were never copied into
  this codebase. **If these credentials are still valid, rotate them.**
- **Legacy dashboard API-vs-UI cross-check** (`test_ui_dashboard_wizard`): already
  stubbed with `pass` in the legacy suite, and its absolute-XPath locators no
  longer match the current (redesigned) dashboard, which has no stable
  per-field ids to check against. Migrated instead as a simpler, always-on
  check (`test_dashboard_shows_mounted_status`).
- **iSCSI bryck-insertion** (`Configuration._test_bryck_inserted`): SSH/iSCSI
  hardware provisioning, not a web UI concern.

## Notes on Allure Trends

Trend charts appear when previous history exists. This framework automatically copies previous report history into new results before HTML generation.

## Legacy Mapping

See docs/MIGRATION_MAPPING.md for test-by-test migration mapping from the old suite.
