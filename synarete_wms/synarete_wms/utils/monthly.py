import frappe
from frappe.utils import get_first_day, today


def generate_monthly_suggestions():
    month_start = get_first_day(today())

    sites = frappe.get_all(
        "WMS Site",
        filters={"status": "Active"},
        pluck="name",
    )

    items = frappe.get_all(
        "Item",
        filters={
            "disabled": 0,
            "custom_wms_is_monthly_service": 1,
        },
        fields=["name", "item_name", "stock_uom"],
    )

    if not sites or not items:
        return

    for site in sites:
        existing = frappe.db.exists(
            "Monthly Service Schedule",
            {
                "site": site,
                "month_year": month_start,
                "docstatus": ["!=", 2],
            },
        )

        if existing:
            continue

        schedule = frappe.new_doc("Monthly Service Schedule")
        schedule.site = site
        schedule.month_year = month_start
        schedule.status = "Suggested"

        for item in items:
            schedule.append(
                "items",
                {
                    "item_code": item.name,
                    "item_name": item.item_name,
                    "is_fixed_qty": 1,
                    "qty": 1,
                    "uom": item.stock_uom,
                    "issued_qty": 0,
                    "balance_qty": 1,
                },
            )

        schedule.insert(ignore_permissions=True)
