import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    columns = [
        {"fieldname": "site", "label": _("Site"), "fieldtype": "Link", "options": "WMS Site", "width": 150},
        {"fieldname": "engineer", "label": _("Engineer"), "fieldtype": "Link", "options": "Employee", "width": 140},
        {"fieldname": "item_code", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 140},
        {"fieldname": "issued_qty", "label": _("Issued"), "fieldtype": "Float", "width": 100},
        {"fieldname": "consumed_qty", "label": _("Consumed"), "fieldtype": "Float", "width": 100},
        {"fieldname": "returned_qty", "label": _("Returned"), "fieldtype": "Float", "width": 100},
        {"fieldname": "outstanding_qty", "label": _("With Site/Engineer"), "fieldtype": "Float", "width": 125},
        {"fieldname": "accountability_status", "label": _("Status"), "fieldtype": "Data", "width": 130},
    ]

    conditions = ["a.outstanding_qty > 0"]
    values = {}

    if filters.get("include_fully_accounted"):
        conditions = ["1 = 1"]
    if filters.get("site"):
        conditions.append("a.site = %(site)s")
        values["site"] = filters.get("site")
    if filters.get("engineer"):
        conditions.append("a.engineer = %(engineer)s")
        values["engineer"] = filters.get("engineer")
    if filters.get("item_code"):
        conditions.append("a.item_code = %(item_code)s")
        values["item_code"] = filters.get("item_code")

    data = frappe.db.sql(
        f"""
        SELECT
            a.site,
            a.engineer,
            a.item_code,
            a.issued_qty,
            a.consumed_qty,
            a.returned_qty,
            a.outstanding_qty,
            a.accountability_status
        FROM `tabWMS Material Accountability` a
        WHERE {' AND '.join(conditions)}
        ORDER BY a.site, a.engineer, a.item_code
        """,
        values,
        as_dict=True,
    )

    return columns, data
