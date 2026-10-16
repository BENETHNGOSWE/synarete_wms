import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    columns = [
        {"fieldname": "movement", "label": _("Asset Movement"), "fieldtype": "Link", "options": "Asset Movement", "width": 150},
        {"fieldname": "asset", "label": _("Asset"), "fieldtype": "Link", "options": "Asset", "width": 130},
        {"fieldname": "movement_type", "label": _("Movement Type"), "fieldtype": "Data", "width": 140},
        {"fieldname": "origin_site", "label": _("Origin Site"), "fieldtype": "Link", "options": "WMS Site", "width": 140},
        {"fieldname": "destination_site", "label": _("Destination Site"), "fieldtype": "Link", "options": "WMS Site", "width": 140},
        {"fieldname": "engineer", "label": _("Engineer"), "fieldtype": "Link", "options": "Employee", "width": 140},
        {"fieldname": "transaction_date", "label": _("Date"), "fieldtype": "Date", "width": 100},
    ]

    conditions = ["am.docstatus = 1"]
    values = {}

    if filters.get("movement_type"):
        conditions.append("am.custom_wms_movement_type = %(movement_type)s")
        values["movement_type"] = filters.get("movement_type")
    if filters.get("engineer"):
        conditions.append("am.custom_wms_engineer = %(engineer)s")
        values["engineer"] = filters.get("engineer")
    if filters.get("from_date"):
        conditions.append("am.transaction_date >= %(from_date)s")
        values["from_date"] = filters.get("from_date")
    if filters.get("to_date"):
        conditions.append("am.transaction_date <= %(to_date)s")
        values["to_date"] = filters.get("to_date")

    data = frappe.db.sql(
        f"""
        SELECT
            am.name AS movement,
            asset_row.asset,
            am.custom_wms_movement_type AS movement_type,
            am.custom_wms_origin_site AS origin_site,
            am.custom_wms_destination_site AS destination_site,
            am.custom_wms_engineer AS engineer,
            am.transaction_date
        FROM `tabAsset Movement` am
        INNER JOIN `tabAsset Movement Item` asset_row
            ON asset_row.parent = am.name
        WHERE {' AND '.join(conditions)}
        ORDER BY am.transaction_date DESC
        """,
        values,
        as_dict=True,
    )

    return columns, data
