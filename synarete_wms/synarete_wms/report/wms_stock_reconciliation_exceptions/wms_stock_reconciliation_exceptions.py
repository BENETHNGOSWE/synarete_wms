import frappe
from frappe import _
from frappe.utils import flt

from synarete_wms.synarete_wms.utils.inventory_reports import settings_warehouses


def execute(filters=None):
    filters = filters or {}
    columns = [
        {"fieldname": "severity", "label": _("Severity"), "fieldtype": "Data", "width": 90},
        {"fieldname": "exception_type", "label": _("Exception"), "fieldtype": "Data", "width": 220},
        {"fieldname": "reference_doctype", "label": _("Doctype"), "fieldtype": "Data", "width": 180},
        {"fieldname": "reference_name", "label": _("Document"), "fieldtype": "Dynamic Link", "options": "reference_doctype", "width": 180},
        {"fieldname": "item_code", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 130},
        {"fieldname": "detail", "label": _("Detail"), "fieldtype": "Small Text", "width": 420},
    ]

    item_filter = filters.get("item_code")
    rows = []
    warehouses = settings_warehouses(frappe)
    field_wh = warehouses.get("field")

    outstanding = frappe.db.sql(
        """
        SELECT item_code, SUM(outstanding_qty) AS qty
        FROM `tabWMS Material Accountability`
        WHERE outstanding_qty != 0
        GROUP BY item_code
        """,
        as_dict=True,
    )
    outstanding_map = {row.item_code: flt(row.qty) for row in outstanding}

    bins = {}
    if field_wh:
        for row in frappe.db.sql(
            """
            SELECT item_code, actual_qty
            FROM `tabBin`
            WHERE warehouse = %s
            """,
            field_wh,
            as_dict=True,
        ):
            bins[row.item_code] = flt(row.actual_qty)

    for item_code, qty in outstanding_map.items():
        if item_filter and item_code != item_filter:
            continue
        if qty < 0:
            rows.append(_row("High", "Negative outstanding", "Item", item_code, item_code, f"Outstanding {qty}"))
        physical = bins.get(item_code, 0)
        if qty - physical > 0.001:
            rows.append(
                _row(
                    "High",
                    "Outstanding exceeds Field Issued Bin",
                    "Item",
                    item_code,
                    item_code,
                    f"WMS outstanding {qty} > Bin {physical} in {field_wh}. Do not auto-adjust.",
                )
            )

    missing_issue = frappe.db.sql(
        """
        SELECT a.name, a.item_code, a.material_issue
        FROM `tabWMS Material Accountability` a
        LEFT JOIN `tabWMS Material Issue` i ON i.name = a.material_issue
        WHERE i.name IS NULL OR i.docstatus != 1
        """,
        as_dict=True,
    )
    for row in missing_issue:
        if item_filter and row.item_code != item_filter:
            continue
        rows.append(
            _row(
                "High",
                "Accountability without submitted Issue",
                "WMS Material Accountability",
                row.name,
                row.item_code,
                f"Linked issue {row.material_issue}",
            )
        )

    dupes = frappe.db.sql(
        """
        SELECT material_issue, material_issue_item, COUNT(*) AS cnt
        FROM `tabWMS Material Accountability`
        WHERE IFNULL(material_issue_item, '') != ''
        GROUP BY material_issue, material_issue_item
        HAVING COUNT(*) > 1
        """,
        as_dict=True,
    )
    for row in dupes:
        rows.append(
            _row(
                "High",
                "Duplicate accountability rows",
                "WMS Material Issue",
                row.material_issue,
                None,
                f"Item row {row.material_issue_item} has {row.cnt} accountability records",
            )
        )

    consume = frappe.db.sql(
        """
        SELECT name, material_issue
        FROM `tabWMS Material Consumption`
        WHERE docstatus = 1 AND IFNULL(stock_entry, '') = ''
        """,
        as_dict=True,
    )
    for row in consume:
        rows.append(
            _row(
                "High",
                "Submitted consumption missing Stock Entry",
                "WMS Material Consumption",
                row.name,
                None,
                f"Issue {row.material_issue}",
            )
        )

    issues = frappe.db.sql(
        """
        SELECT name, site_work_order
        FROM `tabWMS Material Issue`
        WHERE docstatus = 1
          AND material_type IN ('MP', 'Both')
          AND IFNULL(stock_entry, '') = ''
          AND name IN (
              SELECT material_issue FROM `tabWMS Material Accountability`
              WHERE issued_qty > 0
          )
        """,
        as_dict=True,
    )
    for row in issues:
        rows.append(
            _row(
                "Medium",
                "Submitted issue missing Stock Entry",
                "WMS Material Issue",
                row.name,
                None,
                "Has newly issued qty but no linked transfer. Reused-only issues are OK.",
            )
        )

    old_open = frappe.db.sql(
        """
        SELECT a.name, a.item_code, a.site_work_order, a.outstanding_qty, wo.status
        FROM `tabWMS Material Accountability` a
        INNER JOIN `tabSite Work Order` wo ON wo.name = a.site_work_order
        WHERE wo.status = 'Completed' AND a.outstanding_qty > 0
        """,
        as_dict=True,
    )
    for row in old_open:
        if item_filter and row.item_code != item_filter:
            continue
        rows.append(
            _row(
                "Medium",
                "Completed work order with leftover stock",
                "WMS Material Accountability",
                row.name,
                row.item_code,
                f"{row.site_work_order} still holds {row.outstanding_qty}. Reuse or return; do not auto-expense.",
            )
        )

    return columns, rows


def _row(severity, exception_type, doctype, name, item_code, detail):
    return {
        "severity": severity,
        "exception_type": exception_type,
        "reference_doctype": doctype,
        "reference_name": name,
        "item_code": item_code,
        "detail": detail,
    }
