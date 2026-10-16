import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    filters = filters or {}
    columns = [
        {
            "fieldname": "work_order",
            "label": _("Work Order"),
            "fieldtype": "Link",
            "options": "ServiceNow Site Work Order",
            "width": 170,
        },
        {"fieldname": "site", "label": _("Site"), "fieldtype": "Link", "options": "WMS Site", "width": 140},
        {
            "fieldname": "assigned_to",
            "label": _("Assigned Engineer"),
            "fieldtype": "Link",
            "options": "Employee",
            "width": 150,
        },
        {"fieldname": "process_status", "label": _("Process Status"), "fieldtype": "Data", "width": 140},
        {"fieldname": "item_code", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 130},
        {"fieldname": "qty_requested", "label": _("Requested"), "fieldtype": "Float", "width": 100},
        {"fieldname": "qty_received", "label": _("Received"), "fieldtype": "Float", "width": 100},
        {"fieldname": "qty_issued", "label": _("Issued"), "fieldtype": "Float", "width": 100},
        {
            "fieldname": "qty_warehouse_remaining",
            "label": _("Warehouse Remaining"),
            "fieldtype": "Float",
            "width": 150,
        },
        {"fieldname": "qty_to_issue", "label": _("Still To Issue"), "fieldtype": "Float", "width": 120},
    ]

    conditions = [
        "wo.process_status != 'Completed'",
        "IFNULL(wo.awaiting_warehouse_issue, 0) = 1",
    ]
    values = {}
    if filters.get("site"):
        conditions.append("wo.site = %(site)s")
        values["site"] = filters["site"]
    if filters.get("assigned_to"):
        conditions.append("wo.assigned_to = %(assigned_to)s")
        values["assigned_to"] = filters["assigned_to"]

    rows = frappe.db.sql(
        f"""
        SELECT
            wo.name AS work_order,
            wo.site,
            wo.assigned_to,
            wo.process_status,
            item.item_code,
            item.qty_requested,
            item.qty_received,
            item.qty_issued,
            item.qty_warehouse_remaining
        FROM `tabServiceNow Site Work Order` wo
        LEFT JOIN `tabSNWO Material Item` item
            ON item.parent = wo.name
        WHERE {' AND '.join(conditions)}
        ORDER BY wo.modified DESC
        """,
        values,
        as_dict=True,
    )
    data = []
    for row in rows:
        requested = flt(row.qty_requested)
        issued = flt(row.qty_issued)
        warehouse_left = flt(row.qty_warehouse_remaining)
        still = max(warehouse_left, max(0, requested - issued))
        row["qty_to_issue"] = still
        data.append(row)
    return columns, data
