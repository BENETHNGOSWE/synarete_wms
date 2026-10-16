import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    filters = filters or {}
    columns = [
        {"fieldname": "item_code", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 140},
        {"fieldname": "item_name", "label": _("Item Name"), "fieldtype": "Data", "width": 180},
        {"fieldname": "warehouse", "label": _("Warehouse"), "fieldtype": "Link", "options": "Warehouse", "width": 160},
        {"fieldname": "material_category", "label": _("Category"), "fieldtype": "Data", "width": 110},
        {"fieldname": "actual_qty", "label": _("Actual"), "fieldtype": "Float", "width": 100},
        {"fieldname": "reserved_qty", "label": _("Reserved"), "fieldtype": "Float", "width": 100},
        {"fieldname": "available_qty", "label": _("Available"), "fieldtype": "Float", "width": 100},
        {"fieldname": "minimum_qty", "label": _("Minimum"), "fieldtype": "Float", "width": 100},
        {"fieldname": "stock_status", "label": _("Status"), "fieldtype": "Data", "width": 110},
    ]

    conditions = ["i.disabled = 0"]
    values = {}

    if filters.get("warehouse"):
        conditions.append("b.warehouse = %(warehouse)s")
        values["warehouse"] = filters.get("warehouse")

    if filters.get("material_category"):
        conditions.append("i.custom_wms_material_category = %(material_category)s")
        values["material_category"] = filters.get("material_category")

    data = frappe.db.sql(
        f"""
        SELECT
            b.item_code,
            i.item_name,
            b.warehouse,
            i.custom_wms_material_category AS material_category,
            b.actual_qty,
            b.reserved_qty,
            (b.actual_qty - b.reserved_qty) AS available_qty,
            COALESCE(i.custom_wms_min_stock_level, 0) AS minimum_qty,
            CASE
                WHEN (b.actual_qty - b.reserved_qty) <= 0 THEN 'Out of Stock'
                WHEN (b.actual_qty - b.reserved_qty) <= COALESCE(i.custom_wms_min_stock_level, 0)
                    THEN 'Low Stock'
                ELSE 'In Stock'
            END AS stock_status
        FROM `tabBin` b
        INNER JOIN `tabItem` i ON i.name = b.item_code
        WHERE {' AND '.join(conditions)}
        ORDER BY b.warehouse, b.item_code
        """,
        values,
        as_dict=True,
    )

    return columns, data
