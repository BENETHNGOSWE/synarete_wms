import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    columns = [
        {"fieldname": "consignment", "label": _("Consignment"), "fieldtype": "Link", "options": "Engineer Consignment", "width": 150},
        {"fieldname": "engineer", "label": _("Engineer"), "fieldtype": "Link", "options": "Employee", "width": 140},
        {"fieldname": "engineer_name", "label": _("Engineer Name"), "fieldtype": "Data", "width": 170},
        {"fieldname": "item_code", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 130},
        {"fieldname": "item_name", "label": _("Item Name"), "fieldtype": "Data", "width": 180},
        {"fieldname": "allocated_qty", "label": _("Allocated"), "fieldtype": "Float", "width": 100},
        {"fieldname": "consumed_qty", "label": _("Consumed"), "fieldtype": "Float", "width": 100},
        {"fieldname": "remaining_qty", "label": _("Remaining"), "fieldtype": "Float", "width": 100},
        {"fieldname": "uom", "label": _("UOM"), "fieldtype": "Link", "options": "UOM", "width": 80},
        {"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 100},
    ]

    conditions = ["ec.docstatus = 1"]
    values = {}

    if filters.get("engineer"):
        conditions.append("ec.engineer = %(engineer)s")
        values["engineer"] = filters.get("engineer")
    if filters.get("status"):
        conditions.append("ec.status = %(status)s")
        values["status"] = filters.get("status")

    data = frappe.db.sql(
        f"""
        SELECT
            ec.name AS consignment,
            ec.engineer,
            e.employee_name AS engineer_name,
            eci.item_code,
            eci.item_name,
            eci.allocated_qty,
            eci.consumed_qty,
            eci.remaining_qty,
            eci.uom,
            ec.status
        FROM `tabEngineer Consignment` ec
        INNER JOIN `tabEngineer Consignment Item` eci
            ON eci.parent = ec.name
        LEFT JOIN `tabEmployee` e
            ON e.name = ec.engineer
        WHERE {' AND '.join(conditions)}
        ORDER BY ec.engineer, eci.item_code
        """,
        values,
        as_dict=True,
    )

    return columns, data
