"""Standard ERPNext stock integration for Synarete WMS."""

import frappe
from frappe.utils import flt, today

from synarete_wms.synarete_wms.utils.common import get_configured_warehouses


def create_material_transfer(
    items,
    source_warehouse,
    target_warehouse,
    company,
    reference_doctype=None,
    reference_name=None,
    site=None,
    engineer=None,
):
    if not items:
        frappe.throw("At least one stock item is required.")

    if source_warehouse == target_warehouse:
        frappe.throw("Source and target warehouses must be different.")

    stock_entry = frappe.new_doc("Stock Entry")
    stock_entry.stock_entry_type = "Material Transfer"
    stock_entry.company = company
    stock_entry.posting_date = today()
    if reference_doctype and reference_name and stock_entry.meta.get_field("remarks"):
        stock_entry.remarks = f"{reference_doctype} {reference_name}"

    if hasattr(stock_entry, "custom_wms_site"):
        stock_entry.custom_wms_site = site
    if hasattr(stock_entry, "custom_wms_engineer"):
        stock_entry.custom_wms_engineer = engineer
    if (
        reference_doctype == "WMS Material Issue"
        and stock_entry.meta.get_field("custom_wms_material_issue")
        and reference_name
    ):
        stock_entry.custom_wms_material_issue = reference_name

    for item in items:
        qty = flt(item.get("qty"))
        if qty <= 0:
            frappe.throw(
                f"Quantity must be greater than zero for item {item.get('item_code')}."
            )

        row = stock_entry.append(
            "items",
            {
                "item_code": item.get("item_code"),
                "qty": qty,
                "uom": item.get("uom"),
                "s_warehouse": source_warehouse,
                "t_warehouse": target_warehouse,
                "serial_no": item.get("serial_no"),
                "batch_no": item.get("batch_no"),
            },
        )

        basic_rate = flt(item.get("basic_rate"))
        if not basic_rate:
            basic_rate = flt(
                frappe.db.get_value(
                    "Bin",
                    {
                        "item_code": item.get("item_code"),
                        "warehouse": source_warehouse,
                    },
                    "valuation_rate",
                )
            )

        if basic_rate > 0:
            row.basic_rate = basic_rate
        else:
            frappe.throw(
                f"No valuation rate found for {item.get('item_code')} "
                f"in {source_warehouse}. Receive or issue valued stock first."
            )

    stock_entry.insert(ignore_permissions=True)
    stock_entry.submit()
    return stock_entry


def create_material_issue(
    items,
    source_warehouse,
    company,
    reference_doctype=None,
    reference_name=None,
    site=None,
    engineer=None,
    posting_date=None,
    remarks=None,
):
    if not items:
        frappe.throw("At least one stock item is required.")

    stock_entry = frappe.new_doc("Stock Entry")
    stock_entry.company = company
    stock_entry.purpose = "Material Issue"
    stock_entry.stock_entry_type = "Material Issue"
    stock_entry.from_warehouse = source_warehouse
    stock_entry.posting_date = posting_date or today()
    if stock_entry.meta.get_field("set_posting_time"):
        stock_entry.set_posting_time = 1
    if remarks and stock_entry.meta.get_field("remarks"):
        stock_entry.remarks = remarks
    expense_account = frappe.get_cached_value(
        "Company", company, "stock_adjustment_account"
    ) or frappe.get_cached_value("Company", company, "default_expense_account")
    if expense_account and stock_entry.meta.get_field("expense_account"):
        stock_entry.expense_account = expense_account

    if stock_entry.meta.get_field("custom_wms_site"):
        stock_entry.custom_wms_site = site
    if stock_entry.meta.get_field("custom_wms_engineer"):
        stock_entry.custom_wms_engineer = engineer

    for item in items:
        qty = flt(item.get("qty"))
        if qty <= 0:
            frappe.throw(
                f"Quantity must be greater than zero for item {item.get('item_code')}."
            )

        item_code = item.get("item_code")
        row = stock_entry.append(
            "items",
            {
                "item_code": item_code,
                "qty": qty,
                "uom": item.get("uom"),
                "s_warehouse": source_warehouse,
                "serial_no": item.get("serial_no"),
                "batch_no": item.get("batch_no"),
            },
        )
        if expense_account and row.meta.get_field("expense_account"):
            row.expense_account = expense_account

        basic_rate = flt(item.get("basic_rate"))
        if not basic_rate:
            basic_rate = flt(
                frappe.db.get_value(
                    "Bin",
                    {
                        "item_code": item_code,
                        "warehouse": source_warehouse,
                    },
                    "valuation_rate",
                )
            )
        if not basic_rate:
            basic_rate = flt(
                frappe.db.get_value(
                    "Item",
                    item_code,
                    "valuation_rate",
                )
            ) or flt(frappe.db.get_value("Item", item_code, "standard_rate"))

        if basic_rate > 0:
            row.basic_rate = basic_rate
        else:
            # Still deduct qty so Stock Balance moves. Demo / zero-rate items
            # must not leave warehouse qty unchanged after an MP issue.
            if row.meta.get_field("allow_zero_valuation_rate"):
                row.allow_zero_valuation_rate = 1
            if stock_entry.meta.get_field("set_posting_time"):
                stock_entry.set_posting_time = 1

    stock_entry.insert(ignore_permissions=True)
    stock_entry.submit()
    return stock_entry


def create_stock_reconciliation(
    warehouse,
    items,
    company,
    posting_date=None,
    reference_name=None,
):
    if not items:
        frappe.throw("At least one stock reconciliation item is required.")

    reconciliation = frappe.new_doc("Stock Reconciliation")
    reconciliation.company = company
    reconciliation.posting_date = posting_date or today()

    if reconciliation.meta.get_field("purpose"):
        reconciliation.purpose = "Stock Reconciliation"

    for item in items:
        row = reconciliation.append(
            "items",
            {
                "item_code": item.get("item_code"),
                "warehouse": warehouse,
                "qty": flt(item.get("physical_qty")),
                "valuation_rate": flt(item.get("valuation_rate")),
                "serial_no": item.get("serial_no"),
                "batch_no": item.get("batch_no"),
            },
        )

        if reference_name and reconciliation.meta.get_field("remarks"):
            reconciliation.remarks = f"Created from WMS Stock Taking Entry {reference_name}"

    reconciliation.insert(ignore_permissions=True)
    reconciliation.submit()
    return reconciliation


def cancel_linked_stock_entry(stock_entry_name):
    if not stock_entry_name:
        return

    if not frappe.db.exists("Stock Entry", stock_entry_name):
        return

    stock_entry = frappe.get_doc("Stock Entry", stock_entry_name)
    if stock_entry.docstatus == 1:
        stock_entry.cancel()


def on_purchase_receipt_submit(doc, method=None):
    """Update Purchase Order delivery totals after a Purchase Receipt."""
    purchase_order = doc.get("purchase_order")
    if not purchase_order and doc.items:
        purchase_order = doc.items[0].get("purchase_order")

    if not purchase_order:
        return

    po = frappe.get_doc("Purchase Order", purchase_order)
    if not po.meta.get_field("custom_wms_total_received_qty"):
        return

    existing_receipts = []
    for phase in po.get("custom_wms_delivery_phases") or []:
        if phase.purchase_receipt:
            existing_receipts.append(phase.purchase_receipt)

    if doc.name in existing_receipts:
        return

    ordered_by_item = {}
    item_names = {}

    for item in po.items:
        ordered_by_item[item.item_code] = (
            ordered_by_item.get(item.item_code, 0) + flt(item.qty)
        )
        item_names[item.item_code] = item.item_name

    received_by_item = {}
    for item in doc.items:
        received_by_item[item.item_code] = (
            received_by_item.get(item.item_code, 0) + flt(item.qty)
        )

    total_ordered = 0
    total_received = 0

    for item_code in ordered_by_item:
        total_ordered += ordered_by_item[item_code]

        received_so_far = 0
        for phase in po.get("custom_wms_delivery_phases") or []:
            if phase.item_code == item_code:
                received_so_far += flt(phase.phase_qty)

        total_received += received_so_far

    for item_code in received_by_item:
        if item_code not in ordered_by_item:
            frappe.throw(
                f"Item {item_code} was not found on Purchase Order {po.name}."
            )

        phase_qty = received_by_item[item_code]
        previous_received = 0

        for phase in po.get("custom_wms_delivery_phases") or []:
            if phase.item_code == item_code:
                previous_received += flt(phase.phase_qty)

        cumulative = previous_received + phase_qty
        remaining = max(0, ordered_by_item[item_code] - cumulative)

        po.append(
            "custom_wms_delivery_phases",
            {
                "item_code": item_code,
                "phase_date": doc.posting_date or today(),
                "ordered_qty": ordered_by_item[item_code],
                "phase_qty": phase_qty,
                "cumulative_qty": cumulative,
                "remaining_qty": remaining,
                "purchase_receipt": doc.name,
                "supplier": doc.supplier,
            },
        )

        total_received += phase_qty

    po.custom_wms_total_ordered_qty = total_ordered
    po.custom_wms_total_received_qty = total_received
    po.custom_wms_remaining_qty = max(0, total_ordered - total_received)

    po.flags.ignore_validate_update_after_submit = True
    po.save(ignore_permissions=True)


def on_delivery_note_submit(doc, method=None):
    """Update linked WMS records and create a signature record."""
    issue_name = doc.get("custom_wms_material_issue")
    if issue_name and frappe.db.exists("WMS Material Issue", issue_name):
        issue = frappe.get_doc("WMS Material Issue", issue_name)
        if issue.status != "Issued":
            issue.db_set("status", "Issued")

    engineer = doc.get("custom_wms_engineer")
    if not engineer:
        return

    existing = frappe.db.exists(
        "Delivery Note Signature",
        {"delivery_note": doc.name},
    )
    if existing:
        return

    signature = frappe.new_doc("Delivery Note Signature")
    signature.delivery_note = doc.name
    signature.engineer = engineer
    signature.site = doc.get("custom_wms_site")
    signature.status = "Pending"
    signature.issue_date = doc.posting_date or today()
    signature.warehouse_officer = frappe.session.user

    for item in doc.items:
        signature.append(
            "items",
            {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty": item.qty,
                "uom": item.uom,
            },
        )

    signature.insert(ignore_permissions=True)

    try:
        from synarete_wms.synarete_wms.utils.signature import generate_qr_file
        qr_path = generate_qr_file(doc)
        if qr_path:
            signature.db_set("qr_code", qr_path, update_modified=False)
            doc.db_set("custom_wms_qr_code", qr_path, update_modified=False)
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Synarete WMS QR generation",
        )


def on_delivery_note_cancel(doc, method=None):
    """Reverse WMS Delivery Note links on cancellation."""
    issue_name = doc.get("custom_wms_material_issue")
    if issue_name and frappe.db.exists("WMS Material Issue", issue_name):
        issue = frappe.get_doc("WMS Material Issue", issue_name)
        if issue.status == "Issued":
            issue.db_set("status", "Approved")


def on_stock_entry_submit(doc, method=None):
    """Reserved extension point for WMS stock-entry reconciliation."""
    return None


def on_stock_entry_cancel(doc, method=None):
    """Reserved extension point for WMS stock-entry reconciliation."""
    return None


@frappe.whitelist()
def get_available_qty(item_code, warehouse):
    """Return actual quantity minus reserved quantity."""
    bin_data = frappe.db.get_value(
        "Bin",
        {"item_code": item_code, "warehouse": warehouse},
        ["actual_qty", "reserved_qty"],
        as_dict=True,
    )

    if not bin_data:
        return 0

    return flt(bin_data.actual_qty) - flt(bin_data.reserved_qty)


@frappe.whitelist()
def get_stock_summary(warehouse=None, material_type=None):
    """Return a safe stock summary for WMS dashboards."""
    filters = {"is_group": 0, "disabled": 0}
    if warehouse:
        filters["name"] = warehouse

    warehouses = frappe.get_all("Warehouse", filters=filters, pluck="name")
    result = []

    for warehouse_name in warehouses:
        bins = frappe.get_all(
            "Bin",
            filters={"warehouse": warehouse_name},
            fields=[
                "item_code",
                "actual_qty",
                "reserved_qty",
                "projected_qty",
                "valuation_rate",
            ],
        )

        for bin_row in bins:
            item = frappe.db.get_value(
                "Item",
                bin_row.item_code,
                [
                    "item_name",
                    "custom_wms_material_category",
                    "custom_wms_min_stock_level",
                ],
                as_dict=True,
            )

            if not item:
                continue

            category = item.custom_wms_material_category
            if material_type and category != material_type:
                continue

            available = flt(bin_row.actual_qty) - flt(bin_row.reserved_qty)
            minimum = flt(item.custom_wms_min_stock_level)

            result.append(
                {
                    "warehouse": warehouse_name,
                    "item_code": bin_row.item_code,
                    "item_name": item.item_name,
                    "material_type": category,
                    "actual_qty": bin_row.actual_qty,
                    "reserved_qty": bin_row.reserved_qty,
                    "available_qty": available,
                    "projected_qty": bin_row.projected_qty,
                    "valuation_rate": bin_row.valuation_rate,
                    "minimum_qty": minimum,
                    "is_low_stock": available <= minimum,
                }
            )

    return result
