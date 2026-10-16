# ServiceNow Site Work Order

This process is separate from HTT. HTT receipts, dispatch, and custody are unchanged.

## Purpose

Manage a ServiceNow Work Order and its material lifecycle:

```text
Work Order Created
→ Material Required
→ Material Received
→ Material Issued
→ Material Consumed
→ Reconciliation
→ Work Order Completed
```

## Masters

- `Maintenance Partner` with exactly two records: **Synarete** and **JD Electronics**.
- `WMS Site` now has Maintenance Partner and Transition Partner. Those values are fetched onto the work order.

## Import

Mandatory fields are auto-filled. Users must not type them.

| Field | Source |
| --- | --- |
| swo_number | ServiceNow WO ID |
| site | u_site → WMS Site |
| status | normalised ServiceNow state |
| status_group | Closed when status is Closed Complete, Closed Incomplete, or Closed Rejected |
| is_pending | 1 when not closed |
| order_type | Material if u_type=Material, otherwise Service |
| created_on | sys_created_on converted from DD-MM-YYYY HH:MM to ISO |
| source_system | ServiceNow |

Call:

```python
frappe.call(
    "synarete_wms.synarete_wms.utils.servicenow.import_servicenow_work_orders",
    rows=[...],
)
```

## Interchange

Material requested for Work Order A may be issued to Work Order B.

- The original material request is never changed or deleted.
- The issue is marked Interchange.
- Reason, who, and when are stored.
- The relationship between the two work orders is kept on `SNWO Material Transaction`.

Traceability for every movement:

Original Work Order → Requested → Received → Actual Issued Work Order → Consumed

## MP stock

If a site work order is raised after material is already in the warehouse, warehouse staff can issue MP stock (`Issue MP Stock`).

On submit, the system creates a **Stock Entry (Material Issue)** from the selected warehouse (default: WMS Settings Main Warehouse). The stock balance for that item decreases immediately.

Those quantities also appear on **SNWO MP Material Report** because the client must pay Synarete back.

If an older MP issue has no Stock Entry, open the work order and click **Material → Deduct MP Stock**.

## Reports

- SNWO Material Traceability
- SNWO Material Lifecycle
- SNWO Interchange Report
- SNWO MP Material Report
