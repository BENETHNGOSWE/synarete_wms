# Workspace Navigation — v0.1.94

This release makes the two Synarete WMS workspaces useful as navigation hubs. Both are refreshed by the app's `after_migrate` setup; the UI links remain subject to each user's existing DocType, Report, and Page permissions.

## ServiceNow Dashboard workspace

The top **ServiceNow** section links to the ServiceNow Dashboard page, ServiceNow Site Work Orders, SNWO Material Transactions, and Maintenance Partners. **Related Warehouse Actions** provides links to WMS Material Issue, WMS Material Closeout, HTT Material Receipt, and WMS HTT Return Batch.

The **Reports** section lists all ServiceNow reports:

- Awaiting Material Issue (SNWO Awaiting Material Issue report)
- SNWO Material Traceability
- SNWO Material Lifecycle
- SNWO Interchange Report
- SNWO MP Material Report
- HTT Monthly Return Tracker (for explicitly linked HTT dispatches)

## Synarete WMS workspace

The main **Synarete WMS** workspace now lists Warehouse Operations, HTT & Engineer Operations, and ServiceNow Work Order shortcuts. Its Reports section is grouped into Stock & Inventory, Work Orders & Materials, HTT & Consignment, ServiceNow, and Purchasing & Suppliers. All 24 distinct reports shipped with this app are linked from the workspace.

## Applying the navigation update

After installing the updated app source, run the site's normal `bench migrate` command so the `after_migrate` hook refreshes both Workspace records, then hard-refresh Desk. If custom workspace content was added manually to either app-managed workspace, save a copy first: the app refreshes these navigation layouts to the shipped grouped layout.

This is a navigation-only update. It does not add Work Order steps, alter approval rules, or change stock/GL posting behavior.
