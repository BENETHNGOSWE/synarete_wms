"""Warehouse Receive Batch against ERPNext Purchase Orders.

Does not create Purchase Orders or credit Creditors. New goods go through
Purchase Receipt so stock is debited and SRBNB is credited. HTT POs are
excluded (use HTT Material Receipt).
"""

import frappe
from frappe.utils import cint, flt, getdate, today

from synarete_wms.synarete_wms.utils.qty_rules import (
    expected_delivery,
    receive_status,
    remaining_qty,
    validate_batch_qty,
)


def _can_receive():
    roles = set(frappe.get_roles())
    return bool(
        roles
        & {
            "System Manager",
            "Warehouse Manager",
            "Stock Manager",
        }
    )


def _po_item_received(row):
    return flt(row.get("received_qty") or row.received_qty)


def _refresh_po_totals(po):
    total_ordered = 0
    total_received = 0
    for item in po.items or []:
        total_ordered += flt(item.qty)
        total_received += _po_item_received(item)

    if po.meta.get_field("custom_wms_total_ordered_qty"):
        po.custom_wms_total_ordered_qty = total_ordered
    if po.meta.get_field("custom_wms_total_received_qty"):
        po.custom_wms_total_received_qty = total_received
    if po.meta.get_field("custom_wms_remaining_qty"):
        po.custom_wms_remaining_qty = remaining_qty(total_ordered, total_received)
    if po.meta.get_field("custom_wms_receive_status"):
        po.custom_wms_receive_status = receive_status(total_ordered, total_received)
    return total_ordered, total_received


def get_item_outstanding_on_po(po, item_code, po_detail=None):
    ordered = 0
    received = 0
    for row in po.items or []:
        if po_detail and row.name != po_detail:
            continue
        if not po_detail and row.item_code != item_code:
            continue
        ordered += flt(row.qty)
        received += _po_item_received(row)
        if po_detail:
            break
    return remaining_qty(ordered, received)


@frappe.whitelist()
def get_supplier_outstanding(supplier, exclude_po=None, item_code=None):
    """Outstanding qty on other submitted POs for the same supplier (and item)."""
    if not supplier:
        return []

    values = {"supplier": supplier}
    conditions = [
        "po.docstatus = 1",
        "po.status not in ('Closed', 'Cancelled')",
        "po.supplier = %(supplier)s",
        "IFNULL(po.custom_wms_material_type, '') != 'HTT'",
    ]
    if exclude_po:
        conditions.append("po.name != %(exclude_po)s")
        values["exclude_po"] = exclude_po
    if item_code:
        conditions.append("poi.item_code = %(item_code)s")
        values["item_code"] = item_code

    rows = frappe.db.sql(
        f"""
        SELECT
            po.name AS purchase_order,
            po.transaction_date,
            poi.name AS po_detail,
            poi.item_code,
            poi.item_name,
            poi.qty AS ordered_qty,
            IFNULL(poi.received_qty, 0) AS received_qty,
            GREATEST(0, poi.qty - IFNULL(poi.received_qty, 0)) AS outstanding_qty
        FROM `tabPurchase Order Item` poi
        INNER JOIN `tabPurchase Order` po ON po.name = poi.parent
        WHERE {' AND '.join(conditions)}
          AND poi.qty - IFNULL(poi.received_qty, 0) > 0.000001
        ORDER BY po.transaction_date ASC, po.name ASC
        """,
        values,
        as_dict=True,
    )
    return rows


def outstanding_notice_for_po(po):
    if not po.supplier:
        return "", []
    rows = get_supplier_outstanding(po.supplier, exclude_po=po.name)
    if not rows:
        return "", []

    by_item = {}
    for row in rows:
        by_item.setdefault(row.item_code, 0)
        by_item[row.item_code] += flt(row.outstanding_qty)

    lines = []
    for item in po.items or []:
        previous = flt(by_item.get(item.item_code) or 0)
        if previous <= 0:
            continue
        summary = expected_delivery(item.qty, previous)
        lines.append(
            f"{item.item_code}: new order {summary['new_order_qty']}, "
            f"previous outstanding {summary['previous_outstanding_qty']}, "
            f"supplier expected to deliver {summary['total_expected_delivery']}. "
            "The new PO quantity is not increased."
        )
    notice = "\n".join(lines)
    return notice, rows


def on_purchase_order_validate(doc, method=None):
    if getattr(doc, "custom_wms_material_type", None) == "HTT":
        return
    _refresh_po_totals(doc)
    notice, _rows = outstanding_notice_for_po(doc)
    if doc.meta.get_field("custom_wms_supplier_outstanding"):
        doc.custom_wms_supplier_outstanding = notice or None
    if notice and doc.docstatus == 0:
        frappe.msgprint(
            notice.replace("\n", "<br>"),
            title="Previous outstanding from this supplier",
            indicator="orange",
        )


@frappe.whitelist()
def get_po_receive_preview(purchase_order):
    if not _can_receive():
        frappe.throw("Only a Warehouse or Stock Manager can receive a PO batch.")
    po = frappe.get_doc("Purchase Order", purchase_order)
    if po.docstatus != 1:
        frappe.throw("Submit the Purchase Order before receiving a batch.")
    if getattr(po, "custom_wms_material_type", None) == "HTT":
        frappe.throw("HTT Purchase Orders use HTT Material Receipt, not Receive Batch.")

    settings = frappe.get_single("WMS Settings")
    items = []
    for row in po.items or []:
        ordered = flt(row.qty)
        received = _po_item_received(row)
        items.append(
            {
                "po_detail": row.name,
                "item_code": row.item_code,
                "item_name": row.item_name,
                "uom": row.uom,
                "ordered_qty": ordered,
                "previously_received_qty": received,
                "outstanding_qty": remaining_qty(ordered, received),
                "batch_qty": 0,
                "rate": flt(row.rate),
            }
        )

    previous = get_supplier_outstanding(po.supplier, exclude_po=po.name)
    previous_by_item = {}
    for row in previous:
        previous_by_item.setdefault(row.item_code, 0)
        previous_by_item[row.item_code] += flt(row.outstanding_qty)

    for item in items:
        item["previous_po_outstanding_qty"] = flt(
            previous_by_item.get(item["item_code"]) or 0
        )
        summary = expected_delivery(
            item["ordered_qty"],
            item["previous_po_outstanding_qty"],
        )
        item["total_expected_delivery"] = summary["total_expected_delivery"]

    total_ordered, total_received = _refresh_po_totals(po)
    return {
        "purchase_order": po.name,
        "supplier": po.supplier,
        "company": po.company,
        "warehouse": settings.main_warehouse,
        "receive_status": receive_status(total_ordered, total_received),
        "total_ordered_qty": total_ordered,
        "total_received_qty": total_received,
        "remaining_qty": remaining_qty(total_ordered, total_received),
        "allow_over_receive": cint(
            getattr(settings, "allow_po_over_receive", 0)
        ),
        "items": items,
        "previous_outstanding": previous,
    }


@frappe.whitelist()
def submit_po_receive_batch(purchase_order, items, warehouse=None, posting_date=None):
    if not _can_receive():
        frappe.throw("Only a Warehouse or Stock Manager can receive a PO batch.")

    items = frappe.parse_json(items) if isinstance(items, str) else items
    po = frappe.get_doc("Purchase Order", purchase_order)
    if po.docstatus != 1:
        frappe.throw("Submit the Purchase Order before receiving a batch.")
    if getattr(po, "custom_wms_material_type", None) == "HTT":
        frappe.throw("HTT Purchase Orders use HTT Material Receipt, not Receive Batch.")

    settings = frappe.get_single("WMS Settings")
    warehouse = warehouse or settings.main_warehouse
    if not warehouse:
        frappe.throw("Set Main Warehouse in WMS Settings.")
    allow_over = cint(getattr(settings, "allow_po_over_receive", 0))

    posting_date = getdate(posting_date) if posting_date else today()
    lines = []
    po_by_detail = {row.name: row for row in po.items}
    for raw in items or []:
        qty = flt(raw.get("batch_qty"))
        if qty <= 0:
            continue
        po_detail = raw.get("po_detail")
        po_row = po_by_detail.get(po_detail)
        if not po_row:
            frappe.throw(f"PO item {po_detail} was not found on {po.name}.")
        outstanding = remaining_qty(po_row.qty, _po_item_received(po_row))
        error = validate_batch_qty(qty, outstanding, allow_over=allow_over)
        if error:
            frappe.throw(f"{po_row.item_code}: {error}")
        lines.append(
            {
                "po_detail": po_detail,
                "item_code": po_row.item_code,
                "item_name": po_row.item_name,
                "uom": po_row.uom,
                "qty": qty,
                "rate": flt(po_row.rate),
            }
        )

    if not lines:
        frappe.throw("Enter a quantity greater than zero for at least one item.")

    receipt = _create_purchase_receipt(
        po=po,
        warehouse=warehouse,
        posting_date=posting_date,
        lines=lines,
        company=po.company or settings.company,
    )

    return {
        "batch": None,
        "purchase_receipt": receipt.name,
        "receive_status": frappe.db.get_value(
            "Purchase Order", po.name, "custom_wms_receive_status"
        )
        or receive_status(
            sum(flt(row.qty) for row in po.items),
            sum(_po_item_received(row) for row in frappe.get_doc("Purchase Order", po.name).items),
        ),
    }


def _create_purchase_receipt(po, warehouse, posting_date, lines, company):
    receipt = frappe.new_doc("Purchase Receipt")
    receipt.supplier = po.supplier
    receipt.company = company
    receipt.posting_date = posting_date or today()
    if receipt.meta.get_field("set_posting_time"):
        receipt.set_posting_time = 1
    receipt.set_warehouse = warehouse
    if receipt.meta.get_field("remarks"):
        receipt.remarks = f"WMS Receive Batch for {po.name}"

    for row in lines:
        receipt.append(
            "items",
            {
                "item_code": row["item_code"],
                "item_name": row.get("item_name"),
                "qty": row["qty"],
                "uom": row.get("uom"),
                "warehouse": warehouse,
                "purchase_order": po.name,
                "purchase_order_item": row.get("po_detail"),
                "rate": flt(row.get("rate")),
            },
        )

    receipt.insert(ignore_permissions=True)
    receipt.submit()
    return receipt


def apply_delivery_phase(po, receipt_name, posting_date, supplier, item_code, phase_qty):
    ordered = 0
    for row in po.items:
        if row.item_code == item_code:
            ordered += flt(row.qty)

    previous = 0
    for phase in po.get("custom_wms_delivery_phases") or []:
        if phase.item_code == item_code:
            previous += flt(phase.phase_qty)

    cumulative = previous + flt(phase_qty)
    po.append(
        "custom_wms_delivery_phases",
        {
            "item_code": item_code,
            "phase_date": posting_date or today(),
            "ordered_qty": ordered,
            "phase_qty": flt(phase_qty),
            "cumulative_qty": cumulative,
            "remaining_qty": remaining_qty(ordered, cumulative),
            "purchase_receipt": receipt_name,
            "supplier": supplier,
            "received_by": frappe.session.user,
        },
    )


def on_purchase_receipt_submit(doc, method=None):
    purchase_order = doc.get("purchase_order")
    if not purchase_order and doc.items:
        purchase_order = doc.items[0].get("purchase_order")
    if not purchase_order or not frappe.db.exists("Purchase Order", purchase_order):
        return

    po = frappe.get_doc("Purchase Order", purchase_order)
    if not po.meta.get_field("custom_wms_delivery_phases"):
        return

    existing = [
        phase.purchase_receipt
        for phase in po.get("custom_wms_delivery_phases") or []
        if phase.purchase_receipt
    ]
    if doc.name in existing:
        _refresh_po_totals(po)
        po.flags.ignore_validate_update_after_submit = True
        po.save(ignore_permissions=True)
        return

    received_by_item = {}
    for item in doc.items:
        received_by_item[item.item_code] = received_by_item.get(
            item.item_code, 0
        ) + flt(item.qty)

    for item_code, phase_qty in received_by_item.items():
        apply_delivery_phase(
            po,
            doc.name,
            doc.posting_date,
            doc.supplier,
            item_code,
            phase_qty,
        )

    _refresh_po_totals(po)
    po.flags.ignore_validate_update_after_submit = True
    po.save(ignore_permissions=True)


def on_purchase_receipt_cancel(doc, method=None):
    purchase_order = doc.get("purchase_order")
    if not purchase_order and doc.items:
        purchase_order = doc.items[0].get("purchase_order")
    if not purchase_order or not frappe.db.exists("Purchase Order", purchase_order):
        return

    po = frappe.get_doc("Purchase Order", purchase_order)
    kept = []
    for phase in po.get("custom_wms_delivery_phases") or []:
        if phase.purchase_receipt != doc.name:
            kept.append(phase.as_dict())
    po.set("custom_wms_delivery_phases", [])
    for row in kept:
        po.append("custom_wms_delivery_phases", row)
    _refresh_po_totals(po)
    po.flags.ignore_validate_update_after_submit = True
    po.save(ignore_permissions=True)
