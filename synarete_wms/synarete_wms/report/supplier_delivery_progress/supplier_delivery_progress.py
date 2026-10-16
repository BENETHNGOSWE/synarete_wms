import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    columns = [
        {"fieldname": "purchase_order", "label": _("Purchase Order"), "fieldtype": "Link", "options": "Purchase Order", "width": 150},
        {"fieldname": "supplier", "label": _("Supplier"), "fieldtype": "Link", "options": "Supplier", "width": 150},
        {"fieldname": "transaction_date", "label": _("PO Date"), "fieldtype": "Date", "width": 100},
        {"fieldname": "item_code", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 130},
        {"fieldname": "item_name", "label": _("Item Name"), "fieldtype": "Data", "width": 180},
        {"fieldname": "ordered_qty", "label": _("Ordered"), "fieldtype": "Float", "width": 100},
        {"fieldname": "received_qty", "label": _("Received"), "fieldtype": "Float", "width": 100},
        {"fieldname": "remaining_qty", "label": _("Remaining"), "fieldtype": "Float", "width": 100},
        {"fieldname": "delivery_count", "label": _("Deliveries"), "fieldtype": "Int", "width": 90},
        {"fieldname": "last_delivery_date", "label": _("Last Delivery"), "fieldtype": "Date", "width": 110},
        {"fieldname": "completion_pct", "label": _("% Complete"), "fieldtype": "Percent", "width": 100},
        {"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 130},
    ]

    conditions = ["po.docstatus = 1"]
    values = {}

    if filters.get("supplier"):
        conditions.append("po.supplier = %(supplier)s")
        values["supplier"] = filters.get("supplier")
    if filters.get("from_date"):
        conditions.append("po.transaction_date >= %(from_date)s")
        values["from_date"] = filters.get("from_date")
    if filters.get("to_date"):
        conditions.append("po.transaction_date <= %(to_date)s")
        values["to_date"] = filters.get("to_date")
    if filters.get("material_type"):
        conditions.append("po.custom_wms_material_type = %(material_type)s")
        values["material_type"] = filters.get("material_type")

    data = frappe.db.sql(
        f"""
        SELECT
            po.name AS purchase_order,
            po.supplier,
            po.transaction_date,
            poi.item_code,
            poi.item_name,
            poi.ordered_qty AS ordered_qty,
            COALESCE(phase.received_qty, 0) AS received_qty,
            GREATEST(
                0,
                poi.ordered_qty - COALESCE(phase.received_qty, 0)
            ) AS remaining_qty,
            COALESCE(phase.delivery_count, 0) AS delivery_count,
            phase.last_delivery_date AS last_delivery_date,
            CASE
                WHEN poi.ordered_qty = 0 THEN 0
                ELSE ROUND(
                    COALESCE(phase.received_qty, 0) / poi.ordered_qty * 100,
                    1
                )
            END AS completion_pct,
            CASE
                WHEN COALESCE(phase.received_qty, 0) >= poi.ordered_qty
                    THEN 'Fully Received'
                WHEN COALESCE(phase.received_qty, 0) > 0
                    THEN 'Partially Received'
                ELSE 'Pending'
            END AS status
        FROM (
            SELECT parent, item_code, item_name, SUM(qty) AS ordered_qty
            FROM `tabPurchase Order Item`
            GROUP BY parent, item_code, item_name
        ) poi
        INNER JOIN `tabPurchase Order` po
            ON po.name = poi.parent
        LEFT JOIN (
            SELECT
                parent,
                item_code,
                SUM(phase_qty) AS received_qty,
                COUNT(DISTINCT purchase_receipt) AS delivery_count,
                MAX(phase_date) AS last_delivery_date
            FROM `tabWMS Delivery Phase`
            WHERE parenttype = 'Purchase Order'
            GROUP BY parent, item_code
        ) phase
            ON phase.parent = po.name
           AND phase.item_code = poi.item_code
        WHERE {' AND '.join(conditions)}
        ORDER BY po.transaction_date DESC, poi.item_code
        """,
        values,
        as_dict=True,
    )

    return columns, data
