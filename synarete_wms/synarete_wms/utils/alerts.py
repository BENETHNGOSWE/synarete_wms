import frappe
from frappe.utils import today, date_diff


def _users_with_role(role):
    rows = frappe.get_all(
        "Has Role",
        filters={
            "role": role,
            "parenttype": "User",
        },
        pluck="parent",
    )
    return list(dict.fromkeys(rows))


def send_low_stock_alerts():
    low_items = frappe.db.sql(
        """
        SELECT
            b.item_code,
            i.item_name,
            b.warehouse,
            b.actual_qty,
            b.reserved_qty,
            (b.actual_qty - b.reserved_qty) AS available_qty,
            i.custom_wms_min_stock_level AS minimum_qty,
            i.custom_wms_material_category AS material_category
        FROM `tabBin` b
        INNER JOIN `tabItem` i ON i.name = b.item_code
        WHERE i.disabled = 0
          AND i.custom_wms_min_stock_level > 0
          AND (b.actual_qty - b.reserved_qty) <= i.custom_wms_min_stock_level
        ORDER BY available_qty ASC
        LIMIT 100
        """,
        as_dict=True,
    )

    if not low_items:
        return

    recipients = _users_with_role("Stock Manager")
    if not recipients:
        return

    lines = [
        f"{row.item_code} | {row.item_name} | {row.warehouse} | "
        f"available {row.available_qty} | minimum {row.minimum_qty}"
        for row in low_items
    ]

    frappe.sendmail(
        recipients=recipients,
        subject=f"[WMS] Low stock alert - {today()}",
        message="\n".join(lines),
        now=False,
    )


def send_pending_return_report():
    pending = frappe.get_all(
        "Material Return Record",
        filters={
            "return_status": "Pending Return",
            "docstatus": 1,
        },
        fields=[
            "name",
            "site",
            "engineer",
            "material_type",
            "old_item_code",
            "expected_return_date",
        ],
        order_by="expected_return_date asc",
        limit_page_length=100,
    )

    if not pending:
        return

    recipients = _users_with_role("Stock Manager")
    if not recipients:
        return

    lines = []
    for row in pending:
        overdue = 0
        if row.expected_return_date:
            overdue = max(
                0,
                date_diff(today(), str(row.expected_return_date)),
            )
        lines.append(
            f"{row.name} | site {row.site} | engineer {row.engineer} | "
            f"item {row.old_item_code} | days overdue {overdue}"
        )

    frappe.sendmail(
        recipients=recipients,
        subject=f"[WMS] Pending material returns - {today()}",
        message="\n".join(lines),
        now=False,
    )
