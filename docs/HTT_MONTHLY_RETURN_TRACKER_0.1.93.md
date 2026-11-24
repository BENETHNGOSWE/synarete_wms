# HTT Monthly Return Tracker — v0.1.93

This is a separate visibility and warehouse recording layer. It does **not** change how a Site Work Order or ServiceNow Site Work Order is opened, issued, closed, or reconciled.

## Monthly cycle

- The cycle month selected in the report is the month containing the deadlines.
- The report lists completed Site Work Orders and completed imported ServiceNow Work Orders from the **previous calendar month**.
- Client report deadline: **15th** of the selected cycle month.
- HTT used/faulty material return window: **20th–25th** of the selected cycle month, with final delivery due by the **25th**. Pending quantity is overdue from the 26th; there is no grace period.
- Example: August completion dates appear in the September cycle, with report due September 15 and return due September 25.

## Report

Open **HTT Monthly Return Tracker** and select a date in the deadline month. It displays the Work Order, requested/completion dates, HTT issue and issue date, item, quantity supplied, quantities returned as Used and Faulty, total returned, pending quantity, last return date, deadlines, and days remaining.

The return obligation quantity is taken from actual submitted HTT dispatch transactions. Only submitted **WMS HTT Return Batch** records count as returned to the client. The report does not inspect whether an engineer submitted a closeout and does not use the engineer closeout as evidence that HTT received material.

The report uses explicit HTT issue links. For a Site Work Order, the submitted WMS Material Issue is linked through its Site Work Order field. To track an imported ServiceNow job, set the optional **ServiceNow Work Order (HTT tracking)** field on its HTT-only WMS Material Issue. The issue's site (and engineer, when assigned) must match the ServiceNow job. This link exists only for reporting and does not alter the ServiceNow Work Order process. Ordinary ServiceNow material transactions and MP-only quantities are never inferred to be HTT.

For ServiceNow jobs, the completion date is taken from **Actual WO Date**, then **Closed At**; if neither is populated, the existing local completion audit date is used when available. Site Work Orders use their existing **Completion Date**, then the existing completion-status audit date. A completed HTT job with no usable date is shown as **Completion Date Missing** with no invented deadline; those unassigned rows are not included in the selected cycle's pending-unit summary. This release does not change a Work Order close action to set a date.

## Bulk client return record

Use **WMS HTT Return Batch** once for a warehouse-to-client bulk delivery. Add one row per Work Order / HTT issue / item, select condition **Used** or **Faulty**, enter quantity, and record the client delivery date/reference. New or unused items cannot be counted as returned. A batch can include multiple Work Orders.

A return row must refer to a submitted HTT Material Issue linked to exactly one Site Work Order or ServiceNow Work Order. Total submitted returns cannot exceed the quantity dispatched for that issue/item. The record is for return reporting only: it does not update any Work Order, create a Stock Entry, post GL, or change the HTT custody ledger.

## Bulk approval

On the **Site Work Order** or **ServiceNow Site Work Order** list, select the records and use **Approve Selected**. The Site Work Order action accepts only **Pending Stock Review** and uses the existing workflow/self-approval checks. The ServiceNow action calls the existing WMS **Approve** workflow transition separately for each selection, so its active roles and conditions remain authoritative. If a selected imported job has no active **Approve** transition or fails its condition, it stays unchanged and is listed as not approved. Imports are not auto-approved. Individual approval remains available on both forms.

## Reminder behavior

The report shows the calendar-day countdown to the 15th and 25th. This release provides in-report visibility; it does not send email reminders or record the actual date a client report was sent.
