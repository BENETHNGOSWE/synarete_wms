# Warehouse / WMS module — current implementation

This document describes **only** the existing warehouse WMS path:

**Site Work Order → approve → WMS Material Issue (Main Warehouse → Field Issued Warehouse) → consume / return → complete.**

It is **not** the ServiceNow Site Work Order (SNWO) process. SNWO is a separate module. HTT (customer-owned custody) is mentioned only where the same doctypes branch into HTT; HTT does not post Synarete-owned stock in the same way as MP.

Sources are the app files under `synarete_wms/synarete_wms/`. Anything not present in those files is marked **not verified**.

---

## 1. What this module is for

The warehouse module tracks **company-owned MP stock** from the moment it sits in **Main Warehouse** until it is either:

- still sitting in **Field Issued Warehouse** (issued to a job / engineer but not yet consumed or returned), or
- **expensed** out of stock by a Material Issue Stock Entry (consumption), or
- **returned** to Main Warehouse.

It also keeps an application-level ledger, **WMS Material Accountability**, of how much of each issue is still “with” an engineer (outstanding), so a later work order can optionally reuse that outstanding instead of taking more from Main Warehouse.

---

## 2. Masters and settings (must exist first)

| Doctype | Path | Role |
|---|---|---|
| **WMS Settings** (single) | `doctype/wms_settings/wms_settings.json` | Company, Main Warehouse, Field Issued Warehouse, optional internal delivery customer, HTT settings |
| **WMS Site** | `doctype/wms_site/` | Telecom site; linked from work orders and issues |
| **Item** (ERPNext) | ERPNext | Stock items with a valuation rate in a Bin |
| **Warehouse** (ERPNext) | ERPNext | Physical Main Warehouse and virtual/physical Field Issued Warehouse |
| **Employee** (HRMS) | HRMS | Engineer on the work order |
| **Company** (ERPNext) | ERPNext | Used on every Stock Entry |

`WMS Settings` required fields (from JSON): `company`, `main_warehouse`, `field_issued_warehouse`.

Stock helpers: `synarete_wms/synarete_wms/utils/stock.py`.

Without a **valuation rate** on the source Bin, `create_material_transfer` throws and no Stock Entry is created.

---

## 3. End-to-end MP flow (as implemented)

```text
ERPNext stock in Main Warehouse
        │  (how it got there is mostly ERPNext: Purchase Receipt, Stock Reconciliation, etc.)
        ▼
Site Work Order  (request: site, engineer, items, qty)
        │  workflow: Draft → Submit → Pending Stock Review
        ▼
Stock Manager Approve  → status Approved
        │
        ▼
WMS Material Issue  (from Approved WO)
        │  on_submit: Stock Entry type Material Transfer
        │  Main Warehouse → Field Issued Warehouse  (only qty > 0 new issue)
        │  plus WMS Material Accountability row(s)
        ▼
Field Issued Warehouse holds the qty
        │
        ├─► WMS Material Consumption
        │     Stock Entry type Material Issue  (out of Field Issued)
        │     accountability.consumed_qty += qty
        │
        ├─► Material Return Record  (normal return)
        │     Stock Entry type Material Transfer
        │     Field Issued → Main Warehouse
        │     accountability.returned_qty += qty
        │
        └─► Material Return Record  (Replacement)
              Transfer old item Field Issued → Main
              Transfer new item Main → Field Issued
        ▼
Site Work Order workflow: Issued → In Progress → Completed
        │
        └── Completing the WO does NOT move leftover Field Issued stock
            and does NOT close accountability. Unused qty stays outstanding
            until consumed, returned, or reallocated to a later issue.
```

---

## 4. How stock enters Main Warehouse (receive)

The WMS app **does not** implement a dedicated “WMS Goods Receipt” doctype for MP.

Verified inbound paths that affect Main Warehouse Bin qty:

1. **ERPNext Purchase Receipt** (standard). Hook `on_purchase_receipt_submit` in `utils/stock.py` only updates custom fields on **Purchase Order** (`custom_wms_delivery_phases`, totals). It does **not** create WMS documents. Stock itself is posted by ERPNext’s Purchase Receipt.
2. **Stock Taking Entry** → on submit creates ERPNext **Stock Reconciliation** (`create_stock_reconciliation` in `utils/stock.py`). That can increase or decrease Bin qty.
3. **Material Return Record** (MP) transfers qty **back** from Field Issued to Main Warehouse.

**Not verified:** opening stock, stock entries created by hand in ERPNext, or manufacturing. Those would show in Bin/Stock Ledger if they exist, but they are not coded in this app.

---

## 5. Site Work Order (request)

**Doctype:** `Site Work Order`  
**Files:** `doctype/site_work_order/site_work_order.py`, `.json`, `.js`  
**Child:** `Site Work Order Item` (`item_code`, `qty`, `approved_qty`, `uom`, `source_warehouse`, `material_type`)

Important parent fields: `site` (WMS Site), `engineer` (Employee), `work_type`, `planned_date`, `material_type` (`MP` / `HTT` / `Both`), `status`, `outstanding_material_notice`, `material_issue` (link filled after an issue is submitted).

### Validate (`site_work_order.py`)

- At least one material row; qty > 0; source warehouse required.
- Calls `get_open_balance(engineer, item_code)` from `utils/accountability.py`.
- If the engineer already has **outstanding_qty > 0** on `WMS Material Accountability` for that item, sets `outstanding_material_notice` and shows an **orange warning**. Submission is **not** blocked.

### Submit

- Document is submittable (`is_submittable: 1`).
- `on_submit`: if status is Draft, sets status to **Pending Stock Review**.
- UI (`site_work_order.js`) uses `apply_wms_workflow` with action `Submit` rather than relying only on the standard Submit button.

### Workflow

Defined in `utils/workflows.py` as **Site Work Order Workflow** (`state_field`: `status`):

| From | Action | To | Allowed role |
|---|---|---|---|
| Draft | Submit | Pending Stock Review | Stock User, Employee |
| Pending Stock Review | Approve | Approved | Stock Manager |
| Pending Stock Review | Reject | Rejected | Stock Manager |
| Approved | Mark Issued | Issued | Stock Manager |
| Approved | Reject | Rejected | Stock Manager |
| Issued | Start Work | In Progress | Stock User |
| In Progress | Complete | Completed | Stock User |

Workflow API: `utils/workflow_api.py` (`apply_wms_workflow`).

**Approve does not move stock.** It only changes `status`.

When status is **Approved**, the form adds **Create Material Issue**, which opens `WMS Material Issue` with `site`, `engineer`, `site_work_order`, `material_type`.

**Completed** only changes workflow status. There is **no** `on_update`/`on_change` in `site_work_order.py` that returns leftover stock or writes accountability.

---

## 6. WMS Material Issue (Main → Field Issued)

**Doctype:** `WMS Material Issue`  
**Files:** `doctype/wms_material_issue/wms_material_issue.py`, `.json`, `.js`  
**Child:** `WMS Material Issue Item`

Header fields used for MP: `site`, `engineer`, `site_work_order` (required when `material_type` is MP), `source_warehouse`, `target_warehouse`, `stock_entry`, `delivery_note`, `status`.

### Validate (MP)

- Site and engineer must match the Site Work Order.
- Item rows copy `requested_qty` / `approved_qty` from the WO child if the item matches.
- `previous_outstanding_qty` = `get_open_balance(engineer, item_code)` excluding this issue.
- `warehouse_stock_qty` = Bin `actual_qty - reserved_qty` at `source_warehouse`.
- If **Use Outstanding Stock** (`use_outstanding`): `outstanding_applied_qty = min(previous outstanding, approved_qty)`. Physical new issue `qty` cannot exceed `approved_qty - outstanding_applied_qty`.
- `fulfilled_qty = outstanding_applied_qty + qty`.
- Source and target warehouses required and must differ.

So the system **already has a hook to reuse unused engineer stock** on a **new** issue, if the manager ticks Use Outstanding Stock. That reuse is **accountability reallocation**, not a second Stock Entry for the carried-forward qty (see below).

### on_submit (MP)

1. If `stock_entry` already set, return (prevents a second Stock Entry on re-entry).
2. For each MP row with **qty > 0**, append to a transfer list.
3. `create_material_transfer` (`utils/stock.py`):
   - ERPNext **Stock Entry**, `stock_entry_type = "Material Transfer"`
   - `s_warehouse` = source (Main), `t_warehouse` = target (Field Issued)
   - `basic_rate` from Bin valuation_rate (throws if 0)
   - insert + submit
4. Link stored on `WMS Material Issue.stock_entry`.
5. `create_for_material_issue` (`utils/accountability.py`) creates **WMS Material Accountability** per item (skipped if a row already exists for that issue item).
6. If `outstanding_applied_qty > 0`, `reallocate_outstanding` reduces older accountability `transferred_out_qty` and creates **WMS Material Allocation** documents. **No extra Stock Entry** for the carried-forward qty — stock is assumed already in Field Issued.
7. Printable Delivery Note + Delivery Note Signature helpers.
8. Sets `Site Work Order.material_issue` to this issue name.
9. Status **Issued**.

**Carried-forward qty is not transferred again in ERPNext.** Only `item.qty` (new warehouse issue) hits Stock Ledger.

### on_cancel

`cancel_linked_stock_entry` cancels the linked Stock Entry. Accountability rows are **not** deleted in this file (**not verified** whether cancel reverses allocations).

### Workflow

**WMS Material Issue Workflow**: Draft → Submit → Issued (Stock Manager or Warehouse Manager). This is in addition to `on_submit` posting stock.

---

## 7. Tracking quantities (two layers)

### Layer A — ERPNext inventory (Bin / Stock Ledger / GL)

| Event | Stock Entry type | Warehouses | Bin effect | GL (as coded / ERPNext) |
|---|---|---|---|---|
| WMS Material Issue (new qty) | Material Transfer | Main → Field Issued | Main −qty, Field Issued +qty | Transfer: value stays in stock. The app does **not** set `purpose`/`expense_account` on transfers. Exact GL lines are whatever ERPNext posts for Material Transfer for that company. **Not verified beyond that.** |
| WMS Material Consumption | Material Issue | Field Issued out | Field Issued −qty | App sets `purpose = "Material Issue"`, `from_warehouse`, and `expense_account` = Company `stock_adjustment_account` or `default_expense_account` if those fields exist. ERPNext then posts SLE + GL (typically stock credit, expense debit). **Exact accounts depend on Company / Item / Warehouse accounts in ERPNext, not listed in this app.** |
| Material Return (normal) | Material Transfer | Field Issued → Main | reverse of issue | Same as other transfers |
| Replacement return | Two transfers | old: Field→Main; new: Main→Field | as above | Transfers |
| Engineer Consignment submit | Material Transfer | Main → Field Issued | same as issue | Transfer |
| Stock Taking Entry | Stock Reconciliation | named warehouse | set to physical qty | ERPNext Stock Reconciliation GL |

Stock Ledger / Stock Balance reports are ERPNext’s, driven by submitted Stock Entries / Reconciliations / Purchase Receipts.

### Layer B — WMS Material Accountability (application ledger)

**Doctype:** `WMS Material Accountability` (not submittable)  
**File:** `utils/accountability.py`  
**Created by:** `create_for_material_issue`

Per **material issue item**:

```text
outstanding_qty = issued_qty + carried_forward_qty
                 − consumed_qty − returned_qty − transferred_out_qty
```

Status: Awaiting Consumption / Partially Accounted / Fully Accounted.

`get_open_balance(engineer, item_code)` **sums outstanding_qty > 0 across all accountability rows for that engineer and item**, regardless of site or work order. That sum is the “engineer still holds this item” figure used on Site Work Order warnings and on the next issue’s Use Outstanding Stock.

This is **not** a per-site warehouse and **not** a Bin. Field Issued Warehouse is shared; engineer/site ownership is only this doctype (plus consignment child rows).

---

## 8. Consumption (expense)

**Doctype:** `WMS Material Consumption`  
**Files:** `doctype/wms_material_consumption/wms_material_consumption.py`

- Requires a submitted `WMS Material Issue` with status Issued.
- Engineer and site must match the issue.
- Each line must have an accountability record; consume qty cannot exceed `outstanding_qty`.
- Optional `engineer_consignment`: consume qty also cannot exceed consignment remaining.

**on_submit:**

- `create_material_issue` from **Field Issued Warehouse** (settings).
- `add_consumption` on accountability.
- If consignment linked, increment `consumed_qty` / decrement `remaining_qty` on consignment items.
- Status Consumed.
- Guard: if `stock_entry` already set, skip posting.

**Workflow** (`WMS Material Consumption Workflow`): employees can Submit to **Pending Verification**; Stock Manager / Warehouse Manager can Submit straight to **Consumed** or Approve the pending doc. Stock posting happens in `on_submit` of the DocType (when the document is submitted). **Not verified** whether the “Pending Verification” path submits the document (`docstatus=1`) before Approve; the Python `on_submit` is what posts stock.

**on_cancel:** cancel Stock Entry; `reverse_consumption`.

This is the point at which inventory **leaves** Field Issued and is **expensed** (Material Issue), as opposed to merely moved.

---

## 9. Returns and replacement

**Doctype:** `Material Return Record`  
**File:** `doctype/material_return_record/material_return_record.py`

MP requires `material_issue`. Qty cannot exceed accountability `outstanding_qty`.

- **New Installation** (normal return): `new_item_code` is the returned item. Transfer Field Issued → Main. `add_return` on accountability.
- **Replacement:** transfer `old_item_code` Field Issued → Main, then transfer `new_item_code` Main → Field Issued. Return qty is applied to accountability for the **old** item when `installation_type == Replacement`.

HTT branch writes `WMS HTT Transaction` type Return and does **not** call `create_material_transfer` in `_submit_htt_return`.

---

## 10. Engineer consignment (parallel path)

**Doctype:** `Engineer Consignment`  
**File:** `doctype/engineer_consignment/engineer_consignment.py`

Submit transfers `allocated_qty` Main → Field Issued (same helper as material issue). Remaining = allocated − consumed, updated when a **WMS Material Consumption** points at this consignment.

This is **not** required for the Site Work Order happy path. Consumption can run with only `material_issue`.

---

## 11. Completing the work order and unused stock

Verified in `site_work_order.py` and `workflows.py`:

- **Complete** is a workflow action: In Progress → Completed (Stock User).
- No stock entry, no accountability close, no auto-return.

**What happens to unused stock**

- ERPNext: qty remains in **Field Issued Warehouse** (one warehouse for all engineers/sites unless you created extra warehouses — the code always uses `WMS Settings.field_issued_warehouse` for consume/return).
- WMS: leftover stays as `WMS Material Accountability.outstanding_qty` for that **engineer + item** (and original issue / site / WO links on that row).

**Can it be reused on another work order?**

- **Yes, if** the next `WMS Material Issue` for the **same engineer and item** has **Use Outstanding Stock** checked. Then `reallocate_outstanding` moves outstanding from older accountability rows onto the new issue via `carried_forward_qty` / `WMS Material Allocation`, and **does not** take that portion from Main Warehouse.
- **No automatic reuse** by site. `get_open_balance` filters **engineer + item only**, not site.
- Completing WO A does not free stock for WO B by itself.

**Expense only what was consumed**

- Already true for **GL/stock**: only `WMS Material Consumption` posts Material Issue (expense). Issue and return are transfers.
- **Not true** as a close-out: leftover can sit in Field Issued indefinitely, still valued as stock, still outstanding on the engineer, until someone consumes or returns it.

---

## 12. Duplicate / incorrect balance controls (what exists)

| Control | Where |
|---|---|
| Do not post a second Stock Entry if `stock_entry` is already set | Issue, Consumption, Consignment `on_submit` |
| Cancel linked Stock Entry on cancel | `cancel_linked_stock_entry` |
| New issue qty ≤ approved − outstanding applied | `wms_material_issue.py` |
| Consume / return ≤ outstanding | accountability helpers |
| Skip creating a second accountability row for the same issue item | `create_for_material_issue` |
| Valuation rate required on transfer | `create_material_transfer` |
| Source ≠ target warehouse | issue validate + transfer helper |
| Site/engineer must match WO / issue | issue, consumption, return |
| One Site Work Order field `material_issue` | overwritten to the latest submitted issue name (does **not** block a second issue document) |

**Not verified:** a unique constraint forbidding two `WMS Material Issue` documents against the same Site Work Order. The WO only stores **one** `material_issue` link; a second issue could still be submitted and would replace that link.

**Not verified:** Field Issued Bin qty is always equal to the sum of accountability outstanding. Nothing in code reconciles Bin vs accountability except human process / stock taking.

---

## 13. Doctype relationship map

```text
WMS Settings ── company, main_warehouse, field_issued_warehouse

WMS Site ◄──── Site Work Order.site
Employee ◄──── Site Work Order.engineer

Site Work Order
   └── Site Work Order Item (requested materials)
   └── material_issue ──► WMS Material Issue   (set on issue submit)

WMS Material Issue
   └── WMS Material Issue Item
   └── stock_entry ──► Stock Entry (Material Transfer)
   └── on_submit creates WMS Material Accountability (1 per item)
   └── delivery_note / delivery_signature (helpers)

WMS Material Accountability
   ├── material_issue, material_issue_item, site_work_order, site, engineer, item_code
   ├── last_consumption ──► WMS Material Consumption
   ├── last_return ──► Material Return Record
   └── last_allocation ──► WMS Material Allocation
         (source_accountability → target_material_issue)

WMS Material Consumption
   └── material_issue (required)
   └── stock_entry ──► Stock Entry (Material Issue from Field Issued)
   └── optional engineer_consignment

Material Return Record
   └── material_issue (required for MP)
   └── stock_entry, issue_stock_entry ──► Stock Entry (transfers)

Engineer Consignment
   └── stock_entry ──► Stock Entry (Main → Field Issued)
```

ERPNext **Bin** / **Stock Ledger Entry** / **GL Entry** are created by submitting those Stock Entries (and Purchase Receipt / Stock Reconciliation), not by custom SQL in WMS.

---

## 14. Important code paths

| Concern | File |
|---|---|
| WO validate, outstanding warning, submit status | `doctype/site_work_order/site_work_order.py` |
| WO buttons | `doctype/site_work_order/site_work_order.js` |
| Issue validate + stock + accountability | `doctype/wms_material_issue/wms_material_issue.py` |
| Consume stock + accountability | `doctype/wms_material_consumption/wms_material_consumption.py` |
| Return / replacement transfers | `doctype/material_return_record/material_return_record.py` |
| Outstanding math, reallocation | `utils/accountability.py` |
| Create/cancel Stock Entry | `utils/stock.py` |
| Workflow definitions | `utils/workflows.py` |
| Workflow actions from UI | `utils/workflow_api.py` |
| Purchase Receipt → PO phases | `utils/stock.py` `on_purchase_receipt_submit` |
| Consignment | `doctype/engineer_consignment/engineer_consignment.py` |

---

## 15. Current limitations (from code)

1. **Field Issued is one warehouse.** Engineer/site tracking is accountability, not Bin. Stock Balance for Field Issued is pooled.
2. **Outstanding is by engineer + item**, not by site. Reuse on a later WO is the same engineer, any site, if Use Outstanding Stock is ticked.
3. **Completing a Site Work Order does not** return, expense, or freeze leftover qty.
4. **Expense happens only on consumption** (Material Issue SE). Issued-but-unused remains on the balance sheet as stock in Field Issued.
5. **Carried-forward outstanding does not move ERPNext stock again.** If Field Issued Bin was already reduced (e.g. stock taking or a consume on the old job), reallocating outstanding can **desync** Bin vs accountability.
6. **No coded job to auto-return leftovers** after Complete.
7. **Second material issue** on the same WO is not clearly forbidden; the WO link stores one name.
8. **Issue cancel** does not show accountability reversal in `wms_material_issue.py`.
9. **Valuation rate 0** blocks transfers.
10. **HTT** on the same Issue doctype is a different branch (ledger, not Main/Field transfer for HTT lines).

---

## 16. What would need to change for the future model

*(Review notes only — not implemented.)*

Goal: track unused stock by **engineer and/or site**, reuse it on later work orders, and **expense only qty actually consumed**.

| Need | Today | Would need |
|---|---|---|
| Unused after WO complete | Stays in Field Issued + outstanding on engineer | Explicit close-out: return to Main, or keep as tagged leftover, or force consume. Workflow Complete is not enough. |
| Track leftover by engineer/site | Accountability has engineer, site, WO, but Bin does not | Either extra warehouses / bins per engineer or site, **or** treat accountability as the source of truth and add reports/reconciliation vs Field Issued Bin |
| Reuse on a future WO | Use Outstanding Stock + reallocate (engineer+item only) | UI/default to apply leftover; possibly filter by site; possibly a transfer document between WOs that updates both accountability **and** Bin if you split warehouses |
| Expense only consumed | Already: consume = Material Issue SE | Keep issue as transfer; do not post Material Issue on WO issue; add a period-end or WO-close check that outstanding must be 0 or returned |
| Prevent wrong balances | Qty caps vs outstanding; no Bin↔accountability reconcile | Reconcile report; block consume if Field Issued Bin < outstanding; reverse accountability on issue cancel |

---

## 17. Out of scope / not this document

- **ServiceNow Site Work Order**, SNWO Material Transaction, interchange, SNWO MP Issue (separate module).
- **HTT** full custody lifecycle (except where WMS Material Issue / Return branches).
- Live Chart of Accounts mappings in the customer’s ERPNext company (not in this repository).

---

*Generated from synarete_wms source as of app version 0.1.75. No code was changed for this document.*
