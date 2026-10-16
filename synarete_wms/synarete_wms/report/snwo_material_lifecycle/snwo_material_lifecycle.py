import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    columns = [
        {"fieldname": "posting_date", "label": _("When"), "fieldtype": "Date", "width": 110},
        {"fieldname": "transaction", "label": _("Transaction"), "fieldtype": "Link", "options": "SNWO Material Transaction", "width": 160},
        {"fieldname": "transaction_type", "label": _("Type"), "fieldtype": "Data", "width": 110},
        {"fieldname": "item_code", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 130},
        {"fieldname": "qty", "label": _("Quantity"), "fieldtype": "Float", "width": 100},
        {"fieldname": "original_work_order", "label": _("Originally Requested By"), "fieldtype": "Link", "options": "ServiceNow Site Work Order", "width": 180},
        {"fieldname": "received_for_work_order", "label": _("Received For"), "fieldtype": "Link", "options": "ServiceNow Site Work Order", "width": 150},
        {"fieldname": "issued_to_work_order", "label": _("Actually Issued To"), "fieldtype": "Link", "options": "ServiceNow Site Work Order", "width": 160},
        {"fieldname": "is_interchange", "label": _("Interchange"), "fieldtype": "Check", "width": 100},
        {"fieldname": "is_mp_stock", "label": _("MP Stock"), "fieldtype": "Check", "width": 90},
        {"fieldname": "interchange_reason", "label": _("Reason"), "fieldtype": "Data", "width": 180},
        {"fieldname": "performed_by", "label": _("Who"), "fieldtype": "Link", "options": "User", "width": 140},
    ]

    conditions = ["t.docstatus = 1"]
    values = {}
    if filters.get("work_order"):
        conditions.append(
            "(t.original_work_order = %(work_order)s "
            "OR t.received_for_work_order = %(work_order)s "
            "OR t.issued_to_work_order = %(work_order)s)"
        )
        values["work_order"] = filters.get("work_order")
    if filters.get("from_date"):
        conditions.append("t.posting_date >= %(from_date)s")
        values["from_date"] = filters.get("from_date")
    if filters.get("to_date"):
        conditions.append("t.posting_date <= %(to_date)s")
        values["to_date"] = filters.get("to_date")

    data = frappe.db.sql(
        f"""
        SELECT
            t.posting_date,
            t.name AS transaction,
            t.transaction_type,
            item.item_code,
            item.qty,
            t.original_work_order,
            t.received_for_work_order,
            t.issued_to_work_order,
            t.is_interchange,
            t.is_mp_stock,
            t.interchange_reason,
            t.performed_by
        FROM `tabSNWO Material Transaction` t
        INNER JOIN `tabSNWO Material Transaction Item` item
            ON item.parent = t.name
        WHERE {' AND '.join(conditions)}
        ORDER BY t.posting_date, t.creation
        """,
        values,
        as_dict=True,
    )
    return columns, data
