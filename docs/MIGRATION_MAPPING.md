# Legacy to Playwright Mapping

This document maps the old shipment web suite from ci_cd to the new framework.

## Source

- Legacy suite: tests/func/test_web_shipment.py
- Legacy helpers: tests/func/config_store.py, tests/func/web_store.py

## Migrated Cases

1. test_bryck_check -> test_bryck_presence_check
2. test_ui_configure_all_variants -> test_ui_configure_storage_variant (32-variant matrix by default; see config/config.yaml for the full 144-variant legacy matrix)
3. test_ui_network_configure -> test_ui_network_configure
4. test_ui_network_configure_using_dhcp -> test_ui_network_configure_using_dhcp
5. test_ui_system_page_drive_serial_no_check -> test_drive_serial_number_field_renders (tests/web/test_data_management.py)
6. test_dashboard_wizard (stubbed/no-op in legacy) -> test_dashboard_shows_mounted_status (simplified, real check against the redesigned dashboard)
7. test_ui_generate_bryck_report -> test_generate_bryck_report
8. ConfigStore.check_ui_data_transfer (transfer/verify add dialogs) -> test_data_transfer_add_dialog_can_be_cancelled + test_nfs_mount_and_data_transfer (real path, config-gated)
9. WebStore.add_nfs_server -> test_external_storage_add_mount_dialog_can_be_cancelled + ExternalStoragePage.add_nfs_mount (real path, config-gated)
10. ConfigStore.\_test_ui_bryck_mount_with_hot_pluggable_eject -> test_bryck_mount_with_hot_pluggable_eject (opt-in, off by default: shipment_suite.run_mount_eject_cycle)
11. WebStore.bucket_create / bucket_delete -> test_object_store_bucket_create_dialog_can_be_cancelled (cancel-only; real buckets on this device are never touched)

## Not Migrated (with rationale)

- Cloud configure/deconfigure/transfer (WebStore.cloud_ui_configure/cloud_ui_deconfigure/cloud_data_transfer): already disabled/commented out in the legacy suite. SECURITY NOTE: the legacy fixture data for this hardcodes what look like real AWS access key/secret and Azure tenant/client credentials in plaintext - not copied here; rotate them if still valid.
- Configuration.\_test_bryck_inserted: SSH/iSCSI hardware provisioning, not a web UI concern - out of scope for a Playwright UI suite.

## What Changed

- unittest + selenium + sleep replaced by pytest + playwright waits.
- hard-coded loops moved to config-driven matrix in config/config.yaml.
- mixed utility calls replaced by clean page objects and service helpers.
- exit() based failure flow replaced by assertion-driven pytest failures.
- report generation standardized with Allure metadata, trend history, and shareable bundle.

## Folder Boundaries

- web_shipment/pages: only UI interactions.
- web_shipment/services: API, matrix generation, report helpers.
- web_shipment/core: config and structured logging.
- tests/web: business-level test intent only.
