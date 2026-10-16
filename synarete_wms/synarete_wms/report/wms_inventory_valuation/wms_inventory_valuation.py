import frappe
from frappe import _

from synarete_wms.synarete_wms.utils.inventory_reports import bin_valuation, settings_warehouses


def execute(filters=None):
    filters = filters or {}
    columns = [
        {"fieldname": "item_code", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 140},
        {"fieldname": "item_name", "label": _("Item Name"), "fieldtype": "Data", "width": 180},
        {"fieldname": "warehouse", "label": _("Warehouse"), "fieldtype": "Link", "options": "Warehouse", "width": 180},
        {"fieldname": "warehouse_role", "label": _("WMS Role"), "fieldtype": "Data", "width": 140},
        {"fieldname": "actual_qty", "label": _("Qty"), "fieldtype": "Float", "width": 100},
        {"fieldname": "valuation_rate", "label": _("Valuation Rate"), "fieldtype": "Currency", "width": 120},
        {"fieldname": "stock_value", "label": _("Stock Value"), "fieldtype": "Currency", "width": 130},
    ]

    warehouses = settings_warehouses(frappe)
    rows = bin_valuation(frappe, filters.get("warehouse"))
    for row in rows:
        if row.warehouse == warehouses.get("main"):
            row["warehouse_role"] = "Main Warehouse"
        elif row.warehouse == warehouses.get("field"):
            row["warehouse_role"] = "Field Issued Warehouse"
        else:
            row["warehouse_role"] = "Other"
    return columns, rows
