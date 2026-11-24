import frappe
from frappe import _

from synarete_wms.synarete_wms.utils.po_receive import get_supplier_outstanding


def execute(filters=None):
    filters = filters or {}
    columns = [
        {
            "fieldname": "purchase_order",
            "label": _("Purchase Order"),
            "fieldtype": "Link",
            "options": "Purchase Order",
            "width": 150,
        },
        {
            "fieldname": "transaction_date",
            "label": _("PO Date"),
            "fieldtype": "Date",
            "width": 100,
        },
        {
            "fieldname": "item_code",
            "label": _("Item"),
            "fieldtype": "Link",
            "options": "Item",
            "width": 140,
        },
        {
            "fieldname": "item_name",
            "label": _("Item Name"),
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "fieldname": "ordered_qty",
            "label": _("Ordered"),
            "fieldtype": "Float",
            "width": 100,
        },
        {
            "fieldname": "received_qty",
            "label": _("Received"),
            "fieldtype": "Float",
            "width": 100,
        },
        {
            "fieldname": "outstanding_qty",
            "label": _("Outstanding"),
            "fieldtype": "Float",
            "width": 110,
        },
    ]

    if not filters.get("supplier"):
        columns.insert(
            1,
            {
                "fieldname": "supplier",
                "label": _("Supplier"),
                "fieldtype": "Link",
                "options": "Supplier",
                "width": 150,
            },
        )
        suppliers = frappe.get_all(
            "Purchase Order",
            filters={"docstatus": 1},
            pluck="supplier",
            distinct=True,
        )
        data = []
        for supplier in suppliers:
            if not supplier:
                continue
            rows = get_supplier_outstanding(
                supplier, item_code=filters.get("item_code")
            )
            for row in rows:
                row["supplier"] = supplier
                data.append(row)
        return columns, data

    data = get_supplier_outstanding(
        filters.get("supplier"),
        item_code=filters.get("item_code"),
    )
    return columns, data
