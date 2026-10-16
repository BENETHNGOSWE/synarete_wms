import frappe
from frappe import _
from frappe.utils import flt

from synarete_wms.synarete_wms.utils.inventory_reports import (
    aggregate_movement,
    settings_warehouses,
    sle_movement,
)


def execute(filters=None):
    filters = filters or {}
    columns = [
        {"fieldname": "metric", "label": _("Metric"), "fieldtype": "Data", "width": 280},
        {"fieldname": "qty", "label": _("Quantity"), "fieldtype": "Float", "width": 120},
        {"fieldname": "value", "label": _("Value"), "fieldtype": "Currency", "width": 140},
        {"fieldname": "note", "label": _("Note"), "fieldtype": "Data", "width": 420},
    ]

    warehouses = settings_warehouses(frappe)
    opening_rows, period_rows = sle_movement(frappe, filters)
    movement = aggregate_movement(opening_rows, period_rows, warehouses)

    totals = {
        "opening_qty": 0,
        "opening_value": 0,
        "received_qty": 0,
        "received_value": 0,
        "to_field_qty": 0,
        "to_field_value": 0,
        "returned_qty": 0,
        "returned_value": 0,
        "consumed_qty": 0,
        "consumed_value": 0,
        "other_qty": 0,
        "other_value": 0,
        "closing_qty": 0,
        "closing_value": 0,
    }
    for row in movement:
        for key in totals:
            totals[key] += flt(row.get(key))

    outstanding_filters = {"outstanding_qty": [">", 0]}
    if filters.get("engineer"):
        outstanding_filters["engineer"] = filters.get("engineer")
    if filters.get("site"):
        outstanding_filters["site"] = filters.get("site")
    if filters.get("item_code"):
        outstanding_filters["item_code"] = filters.get("item_code")
    outstanding_qty = sum(
        flt(row.outstanding_qty)
        for row in frappe.get_all(
            "WMS Material Accountability",
            filters=outstanding_filters,
            fields=["outstanding_qty"],
        )
    )
    field_bin = frappe.db.sql(
        """
        SELECT SUM(actual_qty) AS qty, SUM(actual_qty * valuation_rate) AS value
        FROM `tabBin`
        WHERE warehouse = %s
        """,
        warehouses.get("field"),
        as_dict=True,
    )
    field_qty = flt(field_bin[0].qty) if field_bin else 0
    field_value = flt(field_bin[0].value) if field_bin else 0

    recon = "OK"
    if outstanding_qty - field_qty > 0.001:
        recon = "Exception: WMS outstanding exceeds Field Issued Bin qty"

    data = [
        {"metric": "Opening inventory (Stock Ledger)", "qty": totals["opening_qty"], "value": totals["opening_value"], "note": "ERPNext SLE before From Date"},
        {"metric": "Stock received", "qty": totals["received_qty"], "value": totals["received_value"], "note": "Purchase Receipt inbound; not expensed"},
        {"metric": "Transferred to Field Issued", "qty": totals["to_field_qty"], "value": totals["to_field_value"], "note": "Material Transfer only — not consumption"},
        {"metric": "Returned to Main Warehouse", "qty": totals["returned_qty"], "value": totals["returned_value"], "note": "Inventory transfer, not expense"},
        {"metric": "Actual consumption expense", "qty": totals["consumed_qty"], "value": totals["consumed_value"], "note": "Material Issue from Field Issued only"},
        {"metric": "Other / adjustments", "qty": totals["other_qty"], "value": totals["other_value"], "note": "Stock Reconciliation and unclassified SLE"},
        {"metric": "Closing inventory (Stock Ledger)", "qty": totals["closing_qty"], "value": totals["closing_value"], "note": "Per-warehouse SLE roll-forward"},
        {"metric": "Field Issued Bin qty / value", "qty": field_qty, "value": field_value, "note": "Physical shared Field Issued Warehouse"},
        {"metric": "WMS engineer outstanding qty", "qty": outstanding_qty, "value": 0, "note": "Custody ledger — reallocations are not receipts"},
        {"metric": "Reconciliation status", "qty": 0, "value": 0, "note": recon},
    ]
    return columns, data
