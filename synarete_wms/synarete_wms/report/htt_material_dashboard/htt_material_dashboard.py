import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    columns = [
        {"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 150},
        {"fieldname": "site", "label": _("Site"), "fieldtype": "Link", "options": "WMS Site", "width": 150},
        {"fieldname": "item_code", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 130},
        {"fieldname": "transaction_type", "label": _("Transaction"), "fieldtype": "Data", "width": 100},
        {"fieldname": "received_qty", "label": _("Received"), "fieldtype": "Float", "width": 100},
        {"fieldname": "dispatched_qty", "label": _("Dispatched"), "fieldtype": "Float", "width": 100},
        {"fieldname": "returned_qty", "label": _("Returned"), "fieldtype": "Float", "width": 100},
        {"fieldname": "net_custody_qty", "label": _("In Custody"), "fieldtype": "Float", "width": 100},
    ]

    conditions = ["t.is_cancelled = 0"]
    values = {}

    if filters.get("customer"):
        conditions.append("t.customer = %(customer)s")
        values["customer"] = filters.get("customer")
    if filters.get("site"):
        conditions.append("t.site = %(site)s")
        values["site"] = filters.get("site")
    if filters.get("transaction_type"):
        conditions.append("t.transaction_type = %(transaction_type)s")
        values["transaction_type"] = filters.get("transaction_type")

    data = frappe.db.sql(
        f"""
        SELECT
            t.customer,
            t.site,
            t.item_code,
            t.transaction_type,
            SUM(CASE WHEN t.transaction_type = 'Receipt' THEN t.qty ELSE 0 END) AS received_qty,
            SUM(CASE WHEN t.transaction_type = 'Dispatch' THEN t.qty ELSE 0 END) AS dispatched_qty,
            SUM(CASE WHEN t.transaction_type = 'Return' THEN t.qty ELSE 0 END) AS returned_qty,
            SUM(CASE
                WHEN t.transaction_type = 'Receipt' THEN t.qty
                WHEN t.transaction_type = 'Return' THEN -t.qty
                WHEN t.transaction_type = 'Dispatch' THEN -t.qty
                ELSE 0
            END) AS net_custody_qty
        FROM `tabWMS HTT Transaction` t
        WHERE {' AND '.join(conditions)}
        GROUP BY t.customer, t.site, t.item_code, t.transaction_type
        ORDER BY t.customer, t.site, t.item_code
        """,
        values,
        as_dict=True,
    )

    return columns, data
