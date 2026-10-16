import frappe
from frappe.utils import date_diff, today


def get_transaction_balance(htt_receipt, item_code, serial_no=None):
    """Return received + returned - dispatched quantity for a receipt item."""
    conditions = [
        "t.htt_receipt = %(htt_receipt)s",
        "t.item_code = %(item_code)s",
        "t.is_cancelled = 0",
    ]
    values = {
        "htt_receipt": htt_receipt,
        "item_code": item_code,
    }

    if serial_no:
        conditions.append("t.serial_no = %(serial_no)s")
        values["serial_no"] = serial_no

    row = frappe.db.sql(
        f"""
        SELECT COALESCE(SUM(
            CASE
                WHEN t.transaction_type IN ('Receipt', 'Return') THEN t.qty
                WHEN t.transaction_type = 'Dispatch' THEN -t.qty
                ELSE 0
            END
        ), 0) AS balance
        FROM `tabWMS HTT Transaction` t
        WHERE {' AND '.join(conditions)}
        """,
        values,
        as_dict=True,
    )

    return row[0].balance if row else 0


def create_htt_dispatch_transactions(issue):
    """Validate and create HTT dispatch ledger transactions."""
    if not issue.htt_receipt:
        frappe.throw("HTT Material Receipt is required for an HTT issue.")

    receipt = frappe.get_doc("HTT Material Receipt", issue.htt_receipt)

    if receipt.docstatus != 1:
        frappe.throw("The HTT Material Receipt must be submitted first.")

    if issue.customer and receipt.customer != issue.customer:
        frappe.throw("The Customer does not match the HTT Material Receipt.")

    created = []

    for item in issue.items:
        item_type = item.material_type or issue.material_type
        if item_type != "HTT":
            continue

        available = get_transaction_balance(
            htt_receipt=receipt.name,
            item_code=item.item_code,
            serial_no=item.serial_no,
        )

        if item.qty > available:
            frappe.throw(
                f"Cannot dispatch {item.qty} of {item.item_code}. "
                f"Available for this receipt: {available}."
            )

        transaction = frappe.get_doc(
            {
                "doctype": "WMS HTT Transaction",
                "transaction_type": "Dispatch",
                "posting_date": issue.issue_date,
                "customer": receipt.customer,
                "site": issue.site,
                "engineer": issue.engineer,
                "item_code": item.item_code,
                "qty": item.qty,
                "uom": item.uom,
                "serial_no": item.serial_no,
                "htt_receipt": receipt.name,
                "material_issue": issue.name,
                "is_cancelled": 0,
            }
        )
        transaction.insert(ignore_permissions=True)
        created.append(transaction.name)

    update_receipt_dispatch_status(receipt.name)
    return created


def cancel_htt_dispatch_transactions(material_issue):
    transactions = frappe.get_all(
        "WMS HTT Transaction",
        filters={
            "material_issue": material_issue.name,
            "transaction_type": "Dispatch",
            "is_cancelled": 0,
        },
        pluck="name",
    )

    receipts = []
    for transaction_name in transactions:
        receipt_name = frappe.db.get_value(
            "WMS HTT Transaction",
            transaction_name,
            "htt_receipt",
        )
        if receipt_name and receipt_name not in receipts:
            receipts.append(receipt_name)

        frappe.db.set_value(
            "WMS HTT Transaction",
            transaction_name,
            "is_cancelled",
            1,
            update_modified=True,
        )

    for receipt_name in receipts:
        update_receipt_dispatch_status(receipt_name)


def update_receipt_dispatch_status(receipt_name):
    receipt = frappe.get_doc("HTT Material Receipt", receipt_name)
    all_dispatched = True
    any_dispatched = False

    for item in receipt.items:
        dispatched = frappe.db.sql(
            """
            SELECT COALESCE(SUM(qty), 0)
            FROM `tabWMS HTT Transaction`
            WHERE htt_receipt = %s
              AND item_code = %s
              AND transaction_type = 'Dispatch'
              AND is_cancelled = 0
            """,
            (receipt.name, item.item_code),
        )[0][0]

        item.db_set("dispatched_qty", dispatched, update_modified=False)

        if dispatched > 0:
            any_dispatched = True
        if dispatched < item.qty:
            all_dispatched = False

    status = "Dispatched" if all_dispatched else "Partially Dispatched" if any_dispatched else "Pending"
    receipt.db_set("dispatch_status", status, update_modified=True)
    if any_dispatched:
        receipt.db_set("dispatch_date", today(), update_modified=False)
        receipt.db_set("dispatched_by", frappe.session.user, update_modified=False)


def flag_overdue_htt_materials():
    settings = frappe.get_single("WMS Settings")
    threshold = settings.htt_overdue_days or 7

    receipts = frappe.get_all(
        "HTT Material Receipt",
        filters={
            "docstatus": 1,
            "dispatch_status": ["in", ["Pending", "Partially Dispatched"]],
        },
        fields=["name", "receipt_date"],
    )

    for receipt in receipts:
        if not receipt.receipt_date:
            continue

        days_in_warehouse = date_diff(
            today(),
            str(receipt.receipt_date),
        )

        frappe.db.set_value(
            "HTT Material Receipt",
            receipt.name,
            {
                "days_in_warehouse": days_in_warehouse,
                "is_overdue": int(days_in_warehouse >= threshold),
            },
            update_modified=False,
        )
