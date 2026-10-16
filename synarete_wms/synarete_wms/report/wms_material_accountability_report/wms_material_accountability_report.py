import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    columns = [
        {"fieldname": "accountability", "label": _("Accountability"), "fieldtype": "Link", "options": "WMS Material Accountability", "width": 150},
        {"fieldname": "material_issue", "label": _("Material Issue"), "fieldtype": "Link", "options": "WMS Material Issue", "width": 150},
        {"fieldname": "site_work_order", "label": _("Work Order"), "fieldtype": "Link", "options": "Site Work Order", "width": 150},
        {"fieldname": "site", "label": _("Site"), "fieldtype": "Link", "options": "WMS Site", "width": 140},
        {"fieldname": "engineer", "label": _("Engineer"), "fieldtype": "Link", "options": "Employee", "width": 140},
        {"fieldname": "item_code", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 130},
        {"fieldname": "requested_qty", "label": _("Requested"), "fieldtype": "Float", "width": 90},
        {"fieldname": "issued_qty", "label": _("Issued"), "fieldtype": "Float", "width": 90},
        {"fieldname": "consumed_qty", "label": _("Consumed"), "fieldtype": "Float", "width": 90},
        {"fieldname": "returned_qty", "label": _("Returned"), "fieldtype": "Float", "width": 90},
        {"fieldname": "outstanding_qty", "label": _("Outstanding"), "fieldtype": "Float", "width": 100},
        {"fieldname": "accountability_status", "label": _("Status"), "fieldtype": "Data", "width": 130},
    ]

    conditions = ["(a.outstanding_qty > 0 OR a.accountability_status = 'Fully Accounted')"]
    values = {}

    if filters.get("engineer"):
        conditions.append("a.engineer = %(engineer)s")
        values["engineer"] = filters.get("engineer")
    if filters.get("site"):
        conditions.append("a.site = %(site)s")
        values["site"] = filters.get("site")
    if filters.get("item_code"):
        conditions.append("a.item_code = %(item_code)s")
        values["item_code"] = filters.get("item_code")
    if filters.get("accountability_status"):
        conditions.append("a.accountability_status = %(accountability_status)s")
        values["accountability_status"] = filters.get("accountability_status")

    data = frappe.db.sql(
        f"""
        SELECT
            a.name AS accountability,
            a.material_issue,
            a.site_work_order,
            a.site,
            a.engineer,
            a.item_code,
            a.requested_qty,
            a.issued_qty,
            a.consumed_qty,
            a.returned_qty,
            a.outstanding_qty,
            a.accountability_status
        FROM `tabWMS Material Accountability` a
        WHERE {' AND '.join(conditions)}
        ORDER BY a.modified DESC
        """,
        values,
        as_dict=True,
    )

    return columns, data
