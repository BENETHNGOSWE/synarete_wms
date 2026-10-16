import frappe
from frappe import _
from frappe.utils import flt

from synarete_wms.synarete_wms.utils.stock import get_available_qty


def execute(filters=None):
    filters = filters or {}
    columns = [
        {"fieldname": "work_order", "label": _("Original Work Order"), "fieldtype": "Link", "options": "ServiceNow Site Work Order", "width": 160},
        {"fieldname": "site", "label": _("Site"), "fieldtype": "Link", "options": "WMS Site", "width": 120},
        {"fieldname": "item_code", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 130},
        {"fieldname": "part_name", "label": _("Part Name"), "fieldtype": "Data", "width": 140},
        {"fieldname": "qty_requested", "label": _("Requested"), "fieldtype": "Float", "width": 100},
        {"fieldname": "qty_received", "label": _("Received"), "fieldtype": "Float", "width": 100},
        {"fieldname": "qty_issued", "label": _("Issued To WO"), "fieldtype": "Float", "width": 110},
        {"fieldname": "qty_consumed", "label": _("Consumed"), "fieldtype": "Float", "width": 100},
        {"fieldname": "qty_remaining", "label": _("Remaining"), "fieldtype": "Float", "width": 100},
        {"fieldname": "qty_warehouse_remaining", "label": _("Warehouse Remaining"), "fieldtype": "Float", "width": 150},
        {"fieldname": "qty_interchanged_out", "label": _("Interchanged Out"), "fieldtype": "Float", "width": 130},
        {"fieldname": "qty_interchanged_in", "label": _("Interchanged In"), "fieldtype": "Float", "width": 130},
        {"fieldname": "qty_mp_issued", "label": _("MP Issued"), "fieldtype": "Float", "width": 100},
        {"fieldname": "process_status", "label": _("Process Status"), "fieldtype": "Data", "width": 140},
    ]

    conditions = ["1=1"]
    values = {}
    if filters.get("work_order"):
        conditions.append("wo.name = %(work_order)s")
        values["work_order"] = filters.get("work_order")
    if filters.get("site"):
        conditions.append("wo.site = %(site)s")
        values["site"] = filters.get("site")
    if filters.get("item_code"):
        conditions.append("item.item_code = %(item_code)s")
        values["item_code"] = filters.get("item_code")

    data = frappe.db.sql(
        f"""
        SELECT
            wo.name AS work_order,
            wo.site,
            item.item_code,
            item.part_name,
            item.qty_requested,
            item.qty_received,
            item.qty_issued,
            item.qty_consumed,
            item.qty_remaining,
            item.qty_warehouse_remaining,
            item.qty_interchanged_out,
            item.qty_interchanged_in,
            item.qty_mp_issued,
            wo.process_status
        FROM `tabServiceNow Site Work Order` wo
        INNER JOIN `tabSNWO Material Item` item
            ON item.parent = wo.name
        WHERE {' AND '.join(conditions)}
        ORDER BY wo.modified DESC, item.idx
        """,
        values,
        as_dict=True,
    )

    _apply_live_mp_warehouse_stock(data)
    return columns, data


def _apply_live_mp_warehouse_stock(data):
    """For MP issues, Warehouse Remaining is live Bin qty, not SN process remaining."""
    if not data:
        return

    main_warehouse = frappe.db.get_single_value("WMS Settings", "main_warehouse")
    mp_rows = frappe.db.sql(
        """
        SELECT
            t.issued_to_work_order AS work_order,
            t.original_work_order,
            item.item_code,
            t.warehouse,
            t.posting_date,
            t.creation
        FROM `tabSNWO Material Transaction` t
        INNER JOIN `tabSNWO Material Transaction Item` item
            ON item.parent = t.name
        WHERE t.docstatus = 1
          AND (t.is_mp_stock = 1 OR t.transaction_type = 'MP Issue')
        ORDER BY t.posting_date DESC, t.creation DESC
        """,
        as_dict=True,
    )

    warehouse_by_wo_item = {}
    for row in mp_rows:
        work_order = row.work_order or row.original_work_order
        key = (work_order, row.item_code)
        if key not in warehouse_by_wo_item:
            warehouse_by_wo_item[key] = row.warehouse or main_warehouse

    stock_cache = {}
    for row in data:
        if flt(row.get("qty_mp_issued")) <= 0:
            continue
        warehouse = warehouse_by_wo_item.get(
            (row.work_order, row.item_code)
        ) or main_warehouse
        cache_key = (row.item_code, warehouse)
        if cache_key not in stock_cache:
            stock_cache[cache_key] = _current_warehouse_qty(row.item_code, warehouse)
        row["qty_warehouse_remaining"] = stock_cache[cache_key]


def _current_warehouse_qty(item_code, warehouse=None):
    if not item_code:
        return 0
    if warehouse:
        return flt(get_available_qty(item_code, warehouse))
    total = frappe.db.sql(
        """
        SELECT SUM(actual_qty - IFNULL(reserved_qty, 0))
        FROM `tabBin`
        WHERE item_code = %s
        """,
        item_code,
    )
    return flt(total[0][0] if total else 0)
