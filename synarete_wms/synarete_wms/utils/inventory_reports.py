"""Shared queries for warehouse inventory reports.

ERPNext Stock Ledger / Bin / GL are the quantity and valuation source.
WMS Material Accountability is the engineer/site custody source.
Reallocation between work orders is never treated as a receipt or expense.
"""

from frappe.utils import flt, getdate


def settings_warehouses(frappe):
    settings = frappe.get_single("WMS Settings")
    return {
        "company": settings.company,
        "main": settings.main_warehouse,
        "field": settings.field_issued_warehouse,
    }


def bin_valuation(frappe, warehouse=None):
    values = {}
    conditions = ["1 = 1"]
    if warehouse:
        conditions.append("b.warehouse = %(warehouse)s")
        values["warehouse"] = warehouse

    return frappe.db.sql(
        f"""
        SELECT
            b.item_code,
            i.item_name,
            b.warehouse,
            b.actual_qty,
            b.valuation_rate,
            (b.actual_qty * b.valuation_rate) AS stock_value
        FROM `tabBin` b
        INNER JOIN `tabItem` i ON i.name = b.item_code
        WHERE {' AND '.join(conditions)}
        ORDER BY b.warehouse, b.item_code
        """,
        values,
        as_dict=True,
    )


def sle_movement(frappe, filters):
    values = {
        "from_date": filters.get("from_date"),
        "to_date": filters.get("to_date"),
    }
    conditions = ["sle.docstatus < 2"]
    if filters.get("from_date"):
        conditions.append("sle.posting_date >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("sle.posting_date <= %(to_date)s")
    if filters.get("item_code"):
        conditions.append("sle.item_code = %(item_code)s")
        values["item_code"] = filters.get("item_code")
    if filters.get("warehouse"):
        conditions.append("sle.warehouse = %(warehouse)s")
        values["warehouse"] = filters.get("warehouse")
    if filters.get("company"):
        conditions.append("sle.company = %(company)s")
        values["company"] = filters.get("company")

    opening_conditions = ["sle.docstatus < 2"]
    opening_values = dict(values)
    if filters.get("from_date"):
        opening_conditions.append("sle.posting_date < %(from_date)s")
    else:
        opening_conditions.append("1 = 0")
    if filters.get("item_code"):
        opening_conditions.append("sle.item_code = %(item_code)s")
    if filters.get("warehouse"):
        opening_conditions.append("sle.warehouse = %(warehouse)s")
    if filters.get("company"):
        opening_conditions.append("sle.company = %(company)s")

    opening_rows = frappe.db.sql(
        f"""
        SELECT
            sle.item_code,
            sle.warehouse,
            SUM(sle.actual_qty) AS qty,
            SUM(sle.stock_value_difference) AS value
        FROM `tabStock Ledger Entry` sle
        WHERE {' AND '.join(opening_conditions)}
        GROUP BY sle.item_code, sle.warehouse
        """,
        opening_values,
        as_dict=True,
    )

    period_rows = frappe.db.sql(
        f"""
        SELECT
            sle.item_code,
            i.item_name,
            sle.warehouse,
            sle.voucher_type,
            sle.voucher_no,
            sle.actual_qty,
            sle.stock_value_difference,
            se.purpose AS stock_entry_purpose,
            se.stock_entry_type
        FROM `tabStock Ledger Entry` sle
        LEFT JOIN `tabItem` i ON i.name = sle.item_code
        LEFT JOIN `tabStock Entry` se
            ON sle.voucher_type = 'Stock Entry' AND se.name = sle.voucher_no
        WHERE {' AND '.join(conditions)}
        """,
        values,
        as_dict=True,
    )
    return opening_rows, period_rows


def classify_movement(row, warehouses):
    qty = flt(row.get("actual_qty"))
    value = flt(row.get("stock_value_difference"))
    voucher = row.get("voucher_type")
    purpose = (row.get("stock_entry_purpose") or row.get("stock_entry_type") or "")
    warehouse = row.get("warehouse")

    bucket = "other"
    if voucher == "Purchase Receipt" and qty > 0:
        bucket = "received"
    elif "Material Receipt" in purpose and qty > 0:
        # Dummy / warehouse receive via Stock Entry, not Purchase Receipt.
        bucket = "received"
    elif voucher == "Purchase Receipt" and qty < 0:
        bucket = "other"
    elif voucher == "Stock Reconciliation":
        bucket = "other"
    elif "Material Issue" in purpose and qty < 0:
        bucket = "consumed"
    elif "Material Transfer" in purpose:
        if warehouse == warehouses.get("field") and qty > 0:
            bucket = "to_field"
        elif warehouse == warehouses.get("main") and qty > 0:
            bucket = "returned"
        elif warehouse == warehouses.get("main") and qty < 0:
            bucket = "to_field"
        elif warehouse == warehouses.get("field") and qty < 0:
            bucket = "returned"
        else:
            bucket = "other"
    return bucket, qty, value


def empty_movement():
    return {
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


def aggregate_movement(opening_rows, period_rows, warehouses):
    data = {}

    def key(item_code, warehouse):
        return (item_code, warehouse)

    for row in opening_rows:
        k = key(row.item_code, row.warehouse)
        slot = data.setdefault(k, empty_movement())
        slot["item_code"] = row.item_code
        slot["warehouse"] = row.warehouse
        slot["opening_qty"] += flt(row.qty)
        slot["opening_value"] += flt(row.value)

    for row in period_rows:
        k = key(row.item_code, row.warehouse)
        slot = data.setdefault(k, empty_movement())
        slot["item_code"] = row.item_code
        slot["item_name"] = row.get("item_name")
        slot["warehouse"] = row.warehouse
        bucket, qty, value = classify_movement(row, warehouses)
        if bucket == "received":
            slot["received_qty"] += qty
            slot["received_value"] += value
        elif bucket == "to_field":
            slot["to_field_qty"] += abs(qty)
            slot["to_field_value"] += abs(value)
        elif bucket == "returned":
            slot["returned_qty"] += abs(qty)
            slot["returned_value"] += abs(value)
        elif bucket == "consumed":
            slot["consumed_qty"] += abs(qty)
            slot["consumed_value"] += abs(value)
        else:
            slot["other_qty"] += qty
            slot["other_value"] += value

    rows = []
    for slot in data.values():
        slot["closing_qty"] = (
            flt(slot["opening_qty"])
            + flt(slot["received_qty"])
            + flt(slot["other_qty"])
            - flt(slot["consumed_qty"])
        )
        # Transfers between Main and Field Issued net to zero company-wide
        # but this report is per warehouse, so apply in/out:
        if slot["warehouse"] == warehouses.get("main"):
            slot["closing_qty"] = (
                flt(slot["opening_qty"])
                + flt(slot["received_qty"])
                + flt(slot["returned_qty"])
                - flt(slot["to_field_qty"])
                + flt(slot["other_qty"])
            )
        elif slot["warehouse"] == warehouses.get("field"):
            slot["closing_qty"] = (
                flt(slot["opening_qty"])
                + flt(slot["to_field_qty"])
                - flt(slot["returned_qty"])
                - flt(slot["consumed_qty"])
                + flt(slot["other_qty"])
            )
        if slot["warehouse"] == warehouses.get("main"):
            slot["closing_value"] = (
                flt(slot["opening_value"])
                + flt(slot["received_value"])
                + flt(slot["returned_value"])
                - flt(slot["to_field_value"])
                + flt(slot["other_value"])
            )
        elif slot["warehouse"] == warehouses.get("field"):
            slot["closing_value"] = (
                flt(slot["opening_value"])
                + flt(slot["to_field_value"])
                - flt(slot["returned_value"])
                - flt(slot["consumed_value"])
                + flt(slot["other_value"])
            )
        else:
            slot["closing_value"] = (
                flt(slot["opening_value"])
                + flt(slot["received_value"])
                + flt(slot["other_value"])
                - flt(slot["consumed_value"])
            )
        rows.append(slot)
    return rows


def report_as_of_date(filters):
    return getdate(filters.get("to_date")) if filters.get("to_date") else None
