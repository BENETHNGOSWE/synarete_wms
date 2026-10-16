import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    columns = [
        {"fieldname": "posting_date", "label": _("Date"), "fieldtype": "Date", "width": 110},
        {"fieldname": "transaction", "label": _("Transaction"), "fieldtype": "Link", "options": "SNWO Material Transaction", "width": 160},
        {"fieldname": "work_order", "label": _("ServiceNow Work Order"), "fieldtype": "Link", "options": "ServiceNow Site Work Order", "width": 170},
        {"fieldname": "site", "label": _("Site"), "fieldtype": "Link", "options": "WMS Site", "width": 120},
        {"fieldname": "item_code", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 130},
        {"fieldname": "item_name", "label": _("Item Name"), "fieldtype": "Data", "width": 150},
        {"fieldname": "qty", "label": _("MP Qty Issued"), "fieldtype": "Float", "width": 120},
        {"fieldname": "warehouse", "label": _("Warehouse"), "fieldtype": "Link", "options": "Warehouse", "width": 140},
        {"fieldname": "performed_by", "label": _("Performed By"), "fieldtype": "Link", "options": "User", "width": 140},
        {"fieldname": "notes", "label": _("Notes"), "fieldtype": "Data", "width": 180},
    ]

    conditions = [
        "t.docstatus = 1",
        "(t.is_mp_stock = 1 OR t.transaction_type = 'MP Issue')",
    ]
    values = {}
    if filters.get("from_date"):
        conditions.append("t.posting_date >= %(from_date)s")
        values["from_date"] = filters.get("from_date")
    if filters.get("to_date"):
        conditions.append("t.posting_date <= %(to_date)s")
        values["to_date"] = filters.get("to_date")
    if filters.get("site"):
        conditions.append("t.site = %(site)s")
        values["site"] = filters.get("site")
    if filters.get("work_order"):
        conditions.append("t.issued_to_work_order = %(work_order)s")
        values["work_order"] = filters.get("work_order")

    data = frappe.db.sql(
        f"""
        SELECT
            t.posting_date,
            t.name AS transaction,
            t.issued_to_work_order AS work_order,
            t.site,
            item.item_code,
            item.item_name,
            item.qty,
            t.warehouse,
            t.performed_by,
            t.notes
        FROM `tabSNWO Material Transaction` t
        INNER JOIN `tabSNWO Material Transaction Item` item
            ON item.parent = t.name
        WHERE {' AND '.join(conditions)}
        ORDER BY t.posting_date, t.name
        """,
        values,
        as_dict=True,
    )
    return columns, data
