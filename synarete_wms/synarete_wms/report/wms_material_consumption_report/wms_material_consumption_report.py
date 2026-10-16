import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    columns = [
        {"fieldname": "consumption", "label": _("Consumption"), "fieldtype": "Link", "options": "WMS Material Consumption", "width": 150},
        {"fieldname": "site", "label": _("Site"), "fieldtype": "Link", "options": "WMS Site", "width": 150},
        {"fieldname": "engineer", "label": _("Engineer"), "fieldtype": "Link", "options": "Employee", "width": 140},
        {"fieldname": "consumption_date", "label": _("Date"), "fieldtype": "Date", "width": 100},
        {"fieldname": "item_code", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 130},
        {"fieldname": "item_name", "label": _("Item Name"), "fieldtype": "Data", "width": 180},
        {"fieldname": "qty", "label": _("Quantity"), "fieldtype": "Float", "width": 100},
        {"fieldname": "uom", "label": _("UOM"), "fieldtype": "Link", "options": "UOM", "width": 80},
    ]

    conditions = ["wmc.docstatus = 1"]
    values = {}

    if filters.get("site"):
        conditions.append("wmc.site = %(site)s")
        values["site"] = filters.get("site")
    if filters.get("engineer"):
        conditions.append("wmc.engineer = %(engineer)s")
        values["engineer"] = filters.get("engineer")
    if filters.get("from_date"):
        conditions.append("wmc.consumption_date >= %(from_date)s")
        values["from_date"] = filters.get("from_date")
    if filters.get("to_date"):
        conditions.append("wmc.consumption_date <= %(to_date)s")
        values["to_date"] = filters.get("to_date")

    data = frappe.db.sql(
        f"""
        SELECT
            wmc.name AS consumption,
            wmc.site,
            wmc.engineer,
            wmc.consumption_date,
            item.item_code,
            item.item_name,
            item.qty,
            item.uom
        FROM `tabWMS Material Consumption` wmc
        INNER JOIN `tabWMS Material Consumption Item` item
            ON item.parent = wmc.name
        WHERE {' AND '.join(conditions)}
        ORDER BY wmc.consumption_date DESC, item.item_code
        """,
        values,
        as_dict=True,
    )

    return columns, data
