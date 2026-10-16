import frappe
from frappe.utils import add_days, today


def send_reconciliation_reminder():
    cutoff = add_days(today(), -30)

    consignments = frappe.get_all(
        "Engineer Consignment",
        filters={
            "docstatus": 1,
            "status": "Active",
            "last_reconciliation_date": ["<", cutoff],
        },
        fields=["name", "engineer", "last_reconciliation_date"],
        limit_page_length=200,
    )

    if not consignments:
        return

    recipients = frappe.get_all(
        "Has Role",
        filters={
            "role": "Stock Manager",
            "parenttype": "User",
        },
        pluck="parent",
    )

    if not recipients:
        return

    lines = []
    for row in consignments:
        lines.append(
            f"{row.name} | engineer {row.engineer} | "
            f"last reconciliation {row.last_reconciliation_date or 'Never'}"
        )

    frappe.sendmail(
        recipients=list(dict.fromkeys(recipients)),
        subject="[WMS] Engineer consignment reconciliation reminder",
        message="\n".join(lines),
        now=False,
    )
