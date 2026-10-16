import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    filters = filters or {}
    columns = [
        {"fieldname": "month_year", "label": _("Month"), "fieldtype": "Date", "width": 100},
        {"fieldname": "warehouse", "label": _("Warehouse"), "fieldtype": "Link", "options": "Warehouse", "width": 150},
        {"fieldname": "item_code", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 130},
        {"fieldname": "item_name", "label": _("Item Name"), "fieldtype": "Data", "width": 180},
        {"fieldname": "material_type", "label": _("Type"), "fieldtype": "Data", "width": 80},
        {"fieldname": "system_qty", "label": _("System Qty"), "fieldtype": "Float", "width": 110},
        {"fieldname": "physical_qty", "label": _("Physical Qty"), "fieldtype": "Float", "width": 110},
        {"fieldname": "variance", "label": _("Variance"), "fieldtype": "Float", "width": 100},
        {"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 110},
    ]

    conditions = ["ste.docstatus = 1"]
    values = {}

    if filters.get("warehouse"):
        conditions.append("ste.warehouse = %(warehouse)s")
        values["warehouse"] = filters.get("warehouse")
    if filters.get("month_year"):
        conditions.append("ste.month_year = %(month_year)s")
        values["month_year"] = filters.get("month_year")
    if filters.get("material_type"):
        conditions.append("sti.material_type = %(material_type)s")
        values["material_type"] = filters.get("material_type")

    data = frappe.db.sql(
        f"""
        SELECT
            ste.month_year,
            ste.warehouse,
            sti.item_code,
            sti.item_name,
            sti.material_type,
            sti.system_qty,
            sti.physical_qty,
            sti.variance,
            ste.status
        FROM `tabStock Taking Entry` ste
        INNER JOIN `tabStock Taking Item` sti ON sti.parent = ste.name
        WHERE {' AND '.join(conditions)}
        ORDER BY ste.month_year DESC, sti.item_code
        """,
        values,
        as_dict=True,
    )

    return columns, data
