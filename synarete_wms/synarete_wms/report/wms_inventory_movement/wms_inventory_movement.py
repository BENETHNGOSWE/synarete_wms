import frappe
from frappe import _

from synarete_wms.synarete_wms.utils.inventory_reports import (
    aggregate_movement,
    settings_warehouses,
    sle_movement,
)


def execute(filters=None):
    filters = filters or {}
    columns = [
        {"fieldname": "item_code", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 140},
        {"fieldname": "item_name", "label": _("Item Name"), "fieldtype": "Data", "width": 160},
        {"fieldname": "warehouse", "label": _("Warehouse"), "fieldtype": "Link", "options": "Warehouse", "width": 160},
        {"fieldname": "opening_qty", "label": _("Opening Qty"), "fieldtype": "Float", "width": 110},
        {"fieldname": "opening_value", "label": _("Opening Value"), "fieldtype": "Currency", "width": 120},
        {"fieldname": "received_qty", "label": _("Received Qty"), "fieldtype": "Float", "width": 110},
        {"fieldname": "to_field_qty", "label": _("To Field Issued"), "fieldtype": "Float", "width": 120},
        {"fieldname": "returned_qty", "label": _("Returned to Main"), "fieldtype": "Float", "width": 130},
        {"fieldname": "consumed_qty", "label": _("Consumed Qty"), "fieldtype": "Float", "width": 110},
        {"fieldname": "other_qty", "label": _("Other / Adjust"), "fieldtype": "Float", "width": 110},
        {"fieldname": "closing_qty", "label": _("Closing Qty"), "fieldtype": "Float", "width": 110},
        {"fieldname": "closing_value", "label": _("Closing Value"), "fieldtype": "Currency", "width": 120},
    ]

    warehouses = settings_warehouses(frappe)
    opening_rows, period_rows = sle_movement(frappe, filters)
    data = aggregate_movement(opening_rows, period_rows, warehouses)
    data.sort(key=lambda row: (row.get("warehouse") or "", row.get("item_code") or ""))
    return columns, data
