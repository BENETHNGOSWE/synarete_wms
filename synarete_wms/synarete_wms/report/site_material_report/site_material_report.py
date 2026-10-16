import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    columns = [
        {"fieldname": "material_issue", "label": _("Material Issue"), "fieldtype": "Link", "options": "WMS Material Issue", "width": 150},
        {"fieldname": "site", "label": _("Site"), "fieldtype": "Link", "options": "WMS Site", "width": 150},
        {"fieldname": "engineer", "label": _("Engineer"), "fieldtype": "Link", "options": "Employee", "width": 140},
        {"fieldname": "issue_date", "label": _("Issue Date"), "fieldtype": "Date", "width": 100},
        {"fieldname": "item_code", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 130},
        {"fieldname": "item_name", "label": _("Item Name"), "fieldtype": "Data", "width": 180},
        {"fieldname": "qty", "label": _("Quantity"), "fieldtype": "Float", "width": 100},
        {"fieldname": "material_type", "label": _("Type"), "fieldtype": "Data", "width": 80},
    ]

    conditions = ["wmi.docstatus = 1"]
    values = {}

    if filters.get("site"):
        conditions.append("wmi.site = %(site)s")
        values["site"] = filters.get("site")
    if filters.get("engineer"):
        conditions.append("wmi.engineer = %(engineer)s")
        values["engineer"] = filters.get("engineer")
    if filters.get("from_date"):
        conditions.append("wmi.issue_date >= %(from_date)s")
        values["from_date"] = filters.get("from_date")
    if filters.get("to_date"):
        conditions.append("wmi.issue_date <= %(to_date)s")
        values["to_date"] = filters.get("to_date")

    data = frappe.db.sql(
        f"""
        SELECT
            wmi.name AS material_issue,
            wmi.site,
            wmi.engineer,
            wmi.issue_date,
            item.item_code,
            item.item_name,
            item.qty,
            COALESCE(item.material_type, wmi.material_type) AS material_type
        FROM `tabWMS Material Issue` wmi
        INNER JOIN `tabWMS Material Issue Item` item
            ON item.parent = wmi.name
        WHERE {' AND '.join(conditions)}
        ORDER BY wmi.issue_date DESC, item.item_code
        """,
        values,
        as_dict=True,
    )

    return columns, data
