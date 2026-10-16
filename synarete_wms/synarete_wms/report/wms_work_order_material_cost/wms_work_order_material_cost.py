import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    filters = filters or {}
    columns = [
        {"fieldname": "site_work_order", "label": _("Work Order"), "fieldtype": "Link", "options": "Site Work Order", "width": 150},
        {"fieldname": "site", "label": _("Site"), "fieldtype": "Link", "options": "WMS Site", "width": 130},
        {"fieldname": "engineer", "label": _("Engineer"), "fieldtype": "Link", "options": "Employee", "width": 130},
        {"fieldname": "item_code", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 130},
        {"fieldname": "requested_qty", "label": _("Requested"), "fieldtype": "Float", "width": 100},
        {"fieldname": "approved_qty", "label": _("Approved"), "fieldtype": "Float", "width": 100},
        {"fieldname": "carried_forward_qty", "label": _("Reused"), "fieldtype": "Float", "width": 90},
        {"fieldname": "issued_qty", "label": _("New from Main"), "fieldtype": "Float", "width": 110},
        {"fieldname": "consumed_qty", "label": _("Consumed"), "fieldtype": "Float", "width": 100},
        {"fieldname": "returned_qty", "label": _("Returned"), "fieldtype": "Float", "width": 90},
        {"fieldname": "outstanding_qty", "label": _("Outstanding"), "fieldtype": "Float", "width": 110},
        {"fieldname": "consumption_cost", "label": _("Consumption Cost"), "fieldtype": "Currency", "width": 140},
        {"fieldname": "wo_status", "label": _("WO Status"), "fieldtype": "Data", "width": 120},
    ]

    conditions = ["1 = 1"]
    values = {}
    if filters.get("site"):
        conditions.append("a.site = %(site)s")
        values["site"] = filters.get("site")
    if filters.get("engineer"):
        conditions.append("a.engineer = %(engineer)s")
        values["engineer"] = filters.get("engineer")
    if filters.get("site_work_order"):
        conditions.append("a.site_work_order = %(site_work_order)s")
        values["site_work_order"] = filters.get("site_work_order")
    if filters.get("from_date"):
        conditions.append("wo.creation >= %(from_date)s")
        values["from_date"] = filters.get("from_date")
    if filters.get("to_date"):
        conditions.append("wo.creation <= %(to_date)s")
        values["to_date"] = filters.get("to_date")

    data = frappe.db.sql(
        f"""
        SELECT
            a.site_work_order,
            a.site,
            a.engineer,
            a.item_code,
            a.requested_qty,
            a.approved_qty,
            a.carried_forward_qty,
            a.issued_qty,
            a.consumed_qty,
            a.returned_qty,
            a.outstanding_qty,
            a.last_consumption,
            wo.status AS wo_status
        FROM `tabWMS Material Accountability` a
        LEFT JOIN `tabSite Work Order` wo ON wo.name = a.site_work_order
        WHERE {' AND '.join(conditions)}
        ORDER BY a.site_work_order, a.item_code
        """,
        values,
        as_dict=True,
    )

    costs = {}
    names = [row.last_consumption for row in data if row.last_consumption]
    if names:
        for se in frappe.db.sql(
            """
            SELECT parent, item_code, qty, basic_rate, amount
            FROM `tabStock Entry Detail`
            WHERE parent IN (
                SELECT stock_entry FROM `tabWMS Material Consumption`
                WHERE name IN %(names)s AND IFNULL(stock_entry, '') != ''
            )
            """,
            {"names": names},
            as_dict=True,
        ):
            costs[(se.parent, se.item_code)] = costs.get((se.parent, se.item_code), 0) + flt(se.amount)

    consumption_map = {}
    if names:
        for row in frappe.get_all(
            "WMS Material Consumption",
            filters={"name": ["in", names]},
            fields=["name", "stock_entry"],
        ):
            consumption_map[row.name] = row.stock_entry

    for row in data:
        stock_entry = consumption_map.get(row.last_consumption)
        row["consumption_cost"] = 0
        if stock_entry:
            row["consumption_cost"] = flt(costs.get((stock_entry, row.item_code)))
            if not row["consumption_cost"] and flt(row.consumed_qty):
                rate = frappe.db.get_value(
                    "Stock Entry Detail",
                    {"parent": stock_entry, "item_code": row.item_code},
                    "basic_rate",
                )
                row["consumption_cost"] = flt(rate) * flt(row.consumed_qty)

    return columns, data
