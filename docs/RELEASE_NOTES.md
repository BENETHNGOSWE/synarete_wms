# Synarete WMS v0.1.97

## Work Order material approval, reconciliation, and closeout fixes

- Site Work Order approval now persists reviewer/date and each approved quantity. A blank/zero quantity defaults to the requested quantity; a lower approved amount is preserved, and negative or above-request quantities are rejected. MP issue submission is blocked until the linked Site Work Order is approved.
- Closeout quantities are explicitly cumulative. The closeout form distinguishes prior used/returned quantities and explains that **Used** is consumed while **Unused** is physically returned to Main Warehouse. A prior return cannot be silently reduced; if it is erroneous, correct/cancel the source record before submitting a closeout.
- Fixed the `WCL-...` accountability reference: closeout consumption and returns now link through the typed `last_closeout` field rather than the `last_return` Material Return Record link.
- ServiceNow `Reconcile` now validates against remaining unconsumed issued quantity, blocks zero/negative and over-balance entries, and directs used material to **Consume**. The form pre-fills the remaining unused amount and the ServiceNow Work Order only offers **Reconcile Unused** when such balance exists. Site Work Order and ServiceNow closeout entry paths are unified under **Return Material**.
- Regression coverage added for approval quantity normalization, issue approval gates, reconciliation boundaries, fully consumed closeout quantities, and typed closeout references.

**Historical data:** this release does not rewrite old ServiceNow transactions or deployed records. If an earlier Reconcile/return was recorded incorrectly, review and correct that source transaction using the site's normal cancellation/correction process before closeout. No production database was available for verification.

# Synarete WMS v0.1.96

## Show Engineer names in the Site Work Order list

- The Site Work Order list now displays the linked Employee's readable name instead of the Employee ID.
- The Employee ID remains available on the form; a read-only display field is populated on save and existing Site Work Orders are backfilled after migration.
- No Work Order approval, assignment, closeout, stock, or GL behavior changes.

# Synarete WMS v0.1.95

## Workspace heading spacing

- Added a small 8px bottom gap after section headings in both the **Synarete WMS** and **ServiceNow Dashboard** workspaces to separate headings from their links and improve readability.
- No access, workflow, stock, or GL behavior changed.

# Synarete WMS v0.1.94

## Discoverable WMS and ServiceNow workspaces

- Refreshed the **ServiceNow Dashboard** workspace with direct links to its dashboard, Work Orders, material transactions, Maintenance Partner records, related warehouse actions, and all ServiceNow reports.
- Populated the **Synarete WMS** workspace with user-facing warehouse, HTT, engineer, and ServiceNow actions.
- Added all 24 distinct WMS reports to the Synarete WMS workspace, grouped under Stock & Inventory, Work Orders & Materials, HTT & Consignment, ServiceNow, and Purchasing & Suppliers.
- Workspace navigation is refreshed by the app's after-migrate setup. No Work Order workflow, stock posting, or GL behavior is changed.

# Synarete WMS v0.1.93

## Bulk approvals and HTT monthly return visibility

- Added **Approve Selected** to the Site Work Order and ServiceNow Site Work Order lists. The Site action processes only **Pending Stock Review** orders through the existing WMS workflow and self-approval check. The ServiceNow action uses each selected order's existing WMS **Approve** workflow transition, including its role/condition checks. Both actions report per-order failures; imports are never approved automatically and individual approval remains available.
- Added a separate warehouse **WMS HTT Return Batch** for recording bulk delivery of **Used** or **Faulty** HTT items back to the client. It does not update Work Orders, create Stock Entries, or post GL.
- Added **HTT Monthly Return Tracker**: for completed Site and imported ServiceNow Work Orders, shows HTT-supplied, returned-used/faulty, pending quantities, report deadline (15th), return deadline (25th), and countdown/overdue state. No grace period is applied.
- Added an explicit optional ServiceNow Work Order link for HTT-only WMS Material Issues and included those jobs in the tracker; imported MP-only or ordinary ServiceNow material rows are never inferred to be HTT.
- ServiceNow completion date uses Actual WO Date, then Closed At, then the existing local completion audit date; missing dates are shown without an invented deadline.
- Work Order opening-to-closing workflow and individual approval are unchanged.

# Synarete WMS v0.1.92

**Close Work Order** on Approved / Issued / In Progress. Status becomes **Closed**. If material was issued and not returned, it asks you to Return Material first.

# Synarete WMS v0.1.91

Return table shows **Item** name, not a locked Issued Item link. Server fills issued lines so Save is not blocked. Intro banner removed.

# Synarete WMS v0.1.90

## Material return form

- **Return Material** opens the return of **issued items only** (no blank New Item).
- **Used** = consumed/damaged, not sent to warehouse. **Unused** = back to Main.
- All issued qty can be Used (workflow still requires this return).
- If Used + Unused &lt; Issued (e.g. 6 of 10), **reason is required**.

# Synarete WMS v0.1.89

## Receive Batch no longer needs a broken Core DocType

Receive Batch posts a **Purchase Receipt** directly. About was still 0.1.87 and `WMS PO Receive Batch` had been registered under **Core**, so Frappe looked for `frappe.core.doctype.wms_po_receive_batch`. Copy the full 9-file app folder and migrate.

# Synarete WMS v0.1.88

## Demo feedback: PO batches, supplier outstanding, mandatory closeout

- **Receive Batch** on a submitted Purchase Order (not HTT). Enter this batch qty. PO stays **Partially Received** until remaining is 0, then **WMS Receive Status = Completed**. History is WMS Delivery Phases (qty, date, user, Purchase Receipt). Over-receive blocked unless WMS Settings **Allow PO Over-Receive**.
- Warehouse receive creates a **Purchase Receipt** (stock in, SRBNB — not Creditors, not a new PO, WMS still does not pay suppliers).
- New PO shows **previous outstanding** from the same supplier for the same item. New ordered qty is **not** increased. Receive leftover on the original PO. Report: **Supplier Outstanding Items**.
- **WMS Material Closeout** is required before Complete on Site Work Order and ServiceNow Site Work Order when material was issued. **Issued = Used + Returned unused**. Used is consumed (item default expense; engineer does not pick GL). Unused transfers Field Issued → Main. HTT unchanged.

# Synarete WMS v0.1.87

## SNWO MP Issue matches Site Work Order

- **Issue MP Stock** is a **transfer** Main → Field Issued (still **1040010** / inventory). It does **not** expense the full issued qty.
- **Consume** expenses **only consumed qty** from Field Issued. Leftover stays inventory (engineer) until consume or return.
- Same idea as warehouse Site Work Order. HTT unchanged.

# Synarete WMS v0.1.86

## Consume submit error

- Engineer Submit no longer queries Item `expense_account` (that field is on **Item Default**, not Item). Fixes `Field not permitted in query: expense_account`.
- Expense GL is filled only for warehouse on **Pending Verification / Approve**.

# Synarete WMS v0.1.85

## Two-step consume (qty then expense GL)

- Engineer **Submit** consume = request only (**Pending Verification**). No stock, no GL.
- Warehouse **Approve** must choose **Expense Account** per item (prefilled from Item default). Then inventory is credited and that expense is debited.
- Warehouse Submit no longer jumps straight to Consumed.
- HTT / SNWO / payment / PO unchanged.

# Synarete WMS v0.1.84

## Inventory vs expense (no supplier payment)

- **WMS Settings:** Consume Expense Account and Opening Stock Adjustment Account (use `5010010 - CONSUMABLES - SEL`).
- Consume Stock Entry uses that expense account (not forced COGS). Receive and Issue still stay on warehouse inventory (`1040010`).
- Opening / already-expensed stock: put remaining qty on inventory and credit the opening adjustment (expense) account — never the supplier.
- HTT, SNWO, dual-path 0.1.83 unchanged.

# Synarete WMS v0.1.83

## Warehouse and engineer can both raise work orders

- Warehouse **or** engineer can create **Site Work Order** and **ServiceNow Site Work Order**.
- Engineer is **required**. Warehouse must assign who will do the job. That engineer sees the WO when they log in, even if warehouse already issued, consumed, or closed it.
- Warehouse can run the full chain: create → submit → approve (see setting) → issue → consume → close.
- **WMS Settings → Allow Self-Approve** (default **No**): the user who created a Site Work Order cannot Approve it. Another Warehouse/Stock Manager Approves. Tick **Yes** if one warehouse user must do every step.
- ServiceNow **import** still works. Warehouse may also create a ServiceNow WO by hand if it is not in ERPNext yet.
- HTT is unchanged. ServiceNow Receive/Interchange is still not on warehouse Site Work Order.

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
