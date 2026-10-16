import frappe
from frappe import _
from frappe.utils import date_diff, today


def execute(filters=None):
    filters = filters or {}
    columns = [
        {"fieldname": "name", "label": _("Return Record"), "fieldtype": "Link", "options": "Material Return Record", "width": 150},
        {"fieldname": "site", "label": _("Site"), "fieldtype": "Link", "options": "WMS Site", "width": 150},
        {"fieldname": "engineer", "label": _("Engineer"), "fieldtype": "Link", "options": "Employee", "width": 130},
        {"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 130},
        {"fieldname": "material_type", "label": _("Type"), "fieldtype": "Data", "width": 80},
        {"fieldname": "old_item_code", "label": _("Item to Return"), "fieldtype": "Link", "options": "Item", "width": 140},
        {"fieldname": "old_serial_no", "label": _("Serial No"), "fieldtype": "Data", "width": 120},
        {"fieldname": "return_status", "label": _("Status"), "fieldtype": "Data", "width": 120},
        {"fieldname": "expected_return_date", "label": _("Expected Return"), "fieldtype": "Date", "width": 130},
        {"fieldname": "days_overdue", "label": _("Days Overdue"), "fieldtype": "Int", "width": 110},
    ]

    conditions = [
        "mrr.docstatus = 1",
        "mrr.return_status = 'Pending Return'",
    ]
    values = {}

    if filters.get("site"):
        conditions.append("mrr.site = %(site)s")
        values["site"] = filters.get("site")
    if filters.get("engineer"):
        conditions.append("mrr.engineer = %(engineer)s")
        values["engineer"] = filters.get("engineer")
    if filters.get("material_type"):
        conditions.append("mrr.material_type = %(material_type)s")
        values["material_type"] = filters.get("material_type")

    data = frappe.db.sql(
        f"""
        SELECT
            mrr.name,
            mrr.site,
            mrr.engineer,
            mrr.customer,
            mrr.material_type,
            mrr.old_item_code,
            mrr.old_serial_no,
            mrr.return_status,
            mrr.expected_return_date
        FROM `tabMaterial Return Record` mrr
        WHERE {' AND '.join(conditions)}
        ORDER BY mrr.expected_return_date ASC
        """,
        values,
        as_dict=True,
    )

    for row in data:
        if row.expected_return_date:
            row.days_overdue = max(
                0,
                date_diff(today(), str(row.expected_return_date)),
            )
        else:
            row.days_overdue = 0

    return columns, data
