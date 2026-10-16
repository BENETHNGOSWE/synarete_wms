# Build status

This file tracks local implementation progress. It is not a production deployment record.

## Implemented in the current workspace

- Persistent-app architecture documentation.
- Minimal app metadata and hooks.
- WMS Settings singleton.
- WMS Site master.
- Site Work Order and child items.
- ServiceNow Site Work Order, Maintenance Partner, SNWO material ledger, interchange, and MP payback reports.
- WMS Material Issue and child items.
- WMS Material Consumption and child items.
- HTT Material Receipt and child items.
- WMS HTT Transaction log.
- Engineer Consignment and child items.
- Material Return Record.
- Monthly Service Schedule and child items.
- Stock Taking Entry and child items.
- Delivery Note Signature and child items.
- WMS Delivery Phase child table.
- Idempotent WMS custom fields and roles setup.
- Main Warehouse to Field Issued stock transfer helper.
- Field Issued material consumption stock issue helper.
- MP/HTT issue and receipt event handlers.
- Asset Movement site/condition update hook.
- Low-stock, overdue-return, HTT-overdue, monthly-suggestion, and consignment-reminder jobs.
- Initial parameterized script reports.
- Initial custom JavaScript for Site Work Order, WMS Material Issue, Purchase Order, Delivery Note, Asset, and Asset Movement.
- WMS Material Consumption and HTT dispatch/return quantity validation.
- Idempotent WMS workflow setup definitions for the core issue/consumption flows.
- Local smoke-test module.
- Idempotent workflow setup for Site Work Order, Material Issue, and Consumption.
- WMS permission-query conditions for site/engineer visibility.
- Site/warehouse workspace metadata.
- Static validation and local smoke-test scripts.

## Still required before the first local installation milestone

- Run the app in the local Frappe bench.
- Validate every DocType JSON through `bench migrate`.
- Confirm controller class discovery for acronym names such as WMS/HTT.
- Confirm that the Frappe version supports the Signature fieldtype.
- Run the idempotent Workflow setup in the local Frappe bench and verify every transition.
- Validate standard DocType client scripts through the local UI.
- Test Stock Reconciliation integration for Stock Taking Entry.
- Test supplier delivery phases with partial receipts and cancellation.
- Test HTT dispatch/return quantity validation, serials, and cancellation.
- Test consignment consumption/replenishment and cancellation.
- Complete remaining dashboard workspace links and report filters.
- Add local end-to-end test data and run automated tests.
- Review permissions with Stock User, Stock Manager, Warehouse Manager, WMS Viewer, and System Manager.
- Export only tested configuration fixtures.
- Run `git diff --check`, static checks, and local migration before the first commit.

## Important

The repository is not ready for production and has not been pushed as a final app. The code must be installed and tested locally before the release commit is prepared.
