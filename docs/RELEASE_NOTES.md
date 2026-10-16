# Synarete WMS v0.1.51

## Fixes in v0.1.51

- Clicking **ServiceNow Dashboard** in the sidebar now opens the real dashboard page (`/app/servicenow-dashboard`) instead of an empty workspace.
- Workspace shortcuts are repaired on migrate: Open Dashboard, work orders, and reports.
- HTT is unchanged.

# Synarete WMS v0.1.50

## ServiceNow Dashboard in v0.1.50

- Added a searchable **ServiceNow Dashboard** page (search: ServiceNow Dashboard).
- Overview cards: total WOs, received material, completed, on progress, MP qty, not issued, returned.
- Charts: site interchange, consumed vs remaining.
- Date filter, This Month, and Export Report to Excel.
- Uses ServiceNow work-order data only. HTT is unchanged.

# Synarete WMS v0.1.49

## Fixes in v0.1.49

- SNWO Material Traceability **Warehouse Remaining** now shows live ERPNext warehouse stock for MP material (no longer 0 after an MP issue).
- ServiceNow-received material still uses process remaining (received minus issued).
- HTT is unchanged.

# Synarete WMS v0.1.48

## Fixes in v0.1.48

- ServiceNow **Issue MP Stock** now posts a standard ERPNext Material Issue Stock Entry, so warehouse quantity is deducted.
- Completing a ServiceNow work order posts any missing MP stock deductions.
- Existing MP issues from v0.1.47 can be fixed with **Material → Deduct MP Stock**.
- HTT is unchanged.

# Synarete WMS v0.1.47

## ServiceNow Site Work Order in v0.1.47

- Added a separate ServiceNow Site Work Order process. HTT is unchanged and is not mixed with this process.
- Added Maintenance Partner master with Synarete and JD Electronics.
- WMS Site now stores Maintenance Partner and Transition Partner, fetched onto the ServiceNow work order.
- Import/transform auto-fills the eight mandatory fields. Users do not type them.
- Material lifecycle: Created → Material Required → Material Received → Material Issued → Material Consumed → Reconciliation → Completed.
- Material interchange between work orders keeps the original request and records who, when, why, and both work orders.
- MP stock issued to a ServiceNow work order is flagged for client payback on SNWO MP Material Report.
- Reports: SNWO Material Traceability, SNWO Material Lifecycle, SNWO Interchange Report, SNWO MP Material Report.

# Synarete WMS v0.1.46

## Fixes in v0.1.46

- Create Material Issue now loads the exact current approved Site Work Order instead of retaining stale route items or references.
- MP outstanding balances are loaded on the new Material Issue form before submission.
- Selecting Use Outstanding Stock now calculates the net warehouse issue immediately and no longer raises a false zero-limit error.
- HTT dispatch behavior from v0.1.45 is retained.

# Synarete WMS v0.1.45

## Fixes in v0.1.45

- HTT Material Issues now load customer-material lines from the selected submitted HTT Material Receipt.
- HTT dispatch quantity is editable and validated against the receipt custody balance.
- MP-only warehouse and outstanding-stock fields are hidden for HTT issues.
- HTT issues no longer use MP warehouse or outstanding quantity calculations.

# Synarete WMS v0.1.44

## Fixes in v0.1.44

- Outstanding material on a previous issue is now a warning only on a new Site Work Order; staff can submit the request without first recording consumption or return.
- The Stock Manager can decide on the WMS Material Issue whether to use outstanding stock, issue new warehouse stock, or use both.
- Carry-forward and reallocated quantities are included in accountability calculations and Material Consumption balances.
- Added the WMS Material Allocation DocType to the packaged application.
- Added regression coverage for the outstanding-material submission rule.

## Included

- One separate `synarete_wms` Frappe application.
- Main Warehouse and Field Issued Warehouse stock model.
- WMS Site master for telecom sites.
- Site Work Order and material approval process.
- ServiceNow Site Work Order process, interchange, and MP payback tracking.
- MP stock issue and consumption using standard Stock Entry transactions.
- HTT customer-material receipt, dispatch, return, and custody ledger.
- Engineer consignment allocation and consumption reconciliation.
- Material return tracking.
- Monthly service material schedules.
- Stock Taking Entry and Stock Reconciliation creation.
- Delivery Note signature record and optional QR generation.
- Purchase Receipt delivery-phase tracking.
- Asset Movement site and condition integration.
- WMS roles, permissions, and permission query conditions.
- Workflow setup for core WMS processes.
- Scheduler alerts and monthly/weekly jobs.
- WMS reports and workspace shortcuts.
- Static repository validation and Frappe smoke-test scripts.

## Local verification required

This repository was statically validated in the build workspace. The following must be run in the Synarete local Frappe bench before release is considered runtime-verified:

```bash
cd /mnt/d/2026/BENETH/CLIENTS/SYNARATE/synarate-local/apps/synarete_wms
python3 scripts/validate_repo.py

cd /mnt/d/2026/BENETH/CLIENTS/SYNARATE/synarate-local/frappe-setup
bash ../apps/synarete_wms/scripts/local_smoke.sh
```

The local smoke test must confirm installation, migration, app imports, DocTypes, custom fields, workflows, permissions, and end-to-end stock flows.

No production deployment is included in this release.
