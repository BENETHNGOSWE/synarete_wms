import frappe
from frappe import _
from frappe.utils import flt

from synarete_wms.synarete_wms.utils.inventory_reports import settings_warehouses


def execute(filters=None):
    filters = filters or {}
    columns = [
        {"fieldname": "accountability", "label": _("Accountability"), "fieldtype": "Link", "options": "WMS Material Accountability", "width": 150},
        {"fieldname": "engineer", "label": _("Engineer"), "fieldtype": "Link", "options": "Employee", "width": 140},
        {"fieldname": "site", "label": _("Site"), "fieldtype": "Link", "options": "WMS Site", "width": 140},
        {"fieldname": "item_code", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 130},
        {"fieldname": "site_work_order", "label": _("Original Work Order"), "fieldtype": "Link", "options": "Site Work Order", "width": 150},
        {"fieldname": "material_issue", "label": _("Original Issue"), "fieldtype": "Link", "options": "WMS Material Issue", "width": 150},
        {"fieldname": "issued_qty", "label": _("Issued / Allocated"), "fieldtype": "Float", "width": 120},
        {"fieldname": "carried_forward_qty", "label": _("Carried Forward"), "fieldtype": "Float", "width": 120},
        {"fieldname": "consumed_qty", "label": _("Consumed"), "fieldtype": "Float", "width": 100},
        {"fieldname": "returned_qty", "label": _("Returned"), "fieldtype": "Float", "width": 100},
        {"fieldname": "transferred_out_qty", "label": _("Reallocated Out"), "fieldtype": "Float", "width": 120},
        {"fieldname": "outstanding_qty", "label": _("Available Balance"), "fieldtype": "Float", "width": 120},
        {"fieldname": "age_days", "label": _("Age (Days)"), "fieldtype": "Int", "width": 90},
        {"fieldname": "estimated_value", "label": _("Est. Value (Field Issued rate)"), "fieldtype": "Currency", "width": 160},
        {"fieldname": "accountability_status", "label": _("Status"), "fieldtype": "Data", "width": 140},
        {"fieldname": "last_activity", "label": _("Last Activity"), "fieldtype": "Datetime", "width": 150},
    ]

    conditions = []
    values = {}
    if not filters.get("include_zero"):
        conditions.append("a.outstanding_qty > 0")
    else:
        conditions.append("1 = 1")
    if filters.get("engineer"):
        conditions.append("a.engineer = %(engineer)s")
        values["engineer"] = filters.get("engineer")
    if filters.get("site"):
        conditions.append("a.site = %(site)s")
        values["site"] = filters.get("site")
    if filters.get("item_code"):
        conditions.append("a.item_code = %(item_code)s")
        values["item_code"] = filters.get("item_code")

    data = frappe.db.sql(
        f"""
        SELECT
            a.name AS accountability,
            a.engineer,
            a.site,
            a.item_code,
            a.site_work_order,
            a.material_issue,
            a.issued_qty,
            a.carried_forward_qty,
            a.consumed_qty,
            a.returned_qty,
            a.transferred_out_qty,
            a.outstanding_qty,
            DATEDIFF(CURDATE(), a.creation) AS age_days,
            a.accountability_status,
            a.modified AS last_activity
        FROM `tabWMS Material Accountability` a
        WHERE {' AND '.join(conditions)}
        ORDER BY a.engineer, a.item_code, a.creation
        """,
        values,
        as_dict=True,
    )

    warehouses = settings_warehouses(frappe)
    rates = {}
    if warehouses.get("field"):
        for bin_row in frappe.db.sql(
            """
            SELECT item_code, valuation_rate
            FROM `tabBin`
            WHERE warehouse = %s
            """,
            warehouses["field"],
            as_dict=True,
        ):
            rates[bin_row.item_code] = flt(bin_row.valuation_rate)

    for row in data:
        row["issued_qty"] = flt(row.issued_qty) + flt(row.carried_forward_qty)
        row["estimated_value"] = flt(row.outstanding_qty) * flt(rates.get(row.item_code))

    return columns, data
