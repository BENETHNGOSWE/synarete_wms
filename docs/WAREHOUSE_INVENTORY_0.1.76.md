# Warehouse inventory upgrade — v0.1.76

Smallest safe changes on the **existing** Site Work Order / WMS Material Issue path. SNWO and HTT behaviour is unchanged except HTT issue lines still skip MP stock math.

## What was already working (kept)

- Purchase Receipt remains the ERPNext receive path. WMS does not post a second GRN or GL.
- Issue is a **Material Transfer** Main → Field Issued (inventory stays an asset).
- Consume is a **Material Issue** from Field Issued (this is the expense).
- Return is a **Material Transfer** Field Issued → Main.
- One shared Field Issued Warehouse. Engineer/site custody stays on **WMS Material Accountability**.
- Use Outstanding Stock still reallocates leftover without a second Stock Entry.

## What changed

### Reuse leftover on the next work order

- Issue form auto-ticks **Use Outstanding Stock** when the engineer already holds the item (can be unticked).
- Intro line shows requested / engineer available / reused / additional from Main.
- Field labels: Engineer Available Stock, Quantity Reused, Additional from Main Warehouse.
- Additional qty cannot exceed Main Warehouse Bin available.
- Second **submitted** MP issue on the same Site Work Order is blocked.

### Accountability and cancellation

- Reallocation locks source rows (`FOR UPDATE`).
- Allocation notes record source and target work orders.
- Cancelling a Material Issue restores reallocated leftover and deletes accountability, unless consume / return / later reallocation already happened.
- Cancelling a Material Return restores outstanding (`reverse_return` was missing).
- Consumption checks Field Issued Bin qty before expensing.
- Completing a Site Work Order still does **not** expense leftover. The outstanding warning now says leftover stays inventory.

### Custodian transfer

- New submittable **WMS Custodian Transfer**: move leftover between engineers/sites with **no** Stock Entry (stock stays in Field Issued). Reverse with a new transfer; cancel is blocked.

### Reports (Synarete WMS)

- WMS Inventory Movement
- WMS Inventory Valuation
- WMS Engineer and Site Stock
- WMS Work Order Material Cost
- WMS Monthly Inventory Summary
- WMS Stock Reconciliation Exceptions (does **not** auto-post adjustments)

### Accounting

- No new GL accounts and no direct SLE/GL writes.
- Transfer remarks now include the WMS document name.
- Consumption Stock Entry remarks include issue + work order.
- Expense account still comes from Company `stock_adjustment_account` / `default_expense_account` (ERPNext config). Warehouse inventory accounts are not overridden.

## Files touched

- `utils/accountability.py`, `utils/stock.py`, `utils/inventory_reports.py`
- `doctype/wms_material_issue/*`, `wms_material_issue_item.json`
- `doctype/wms_material_consumption/wms_material_consumption.py`
- `doctype/material_return_record/material_return_record.py`
- `doctype/site_work_order/site_work_order.py`
- `doctype/wms_custodian_transfer/` (new)
- reports listed above
- `tests/test_inventory_reuse.py`

## Deploy

1. Copy app, `bench migrate`, **restart backend**.
2. Do not rewrite historical SLE/GL.
3. Run **WMS Stock Reconciliation Exceptions** before go-live; fix mismatches with authorized stock taking / returns, not silent adjustments.
4. Smoke: receive → issue 10 → consume 4 → complete WO → new WO for 5 should reuse 5 and transfer 0 from Main → return leftover 1.

HTT, Engineer Consignment, SNWO, delivery notes and signatures were not redesigned.
