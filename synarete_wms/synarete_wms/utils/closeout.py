"""Mandatory material closeout before work-order completion."""

import frappe
from frappe.utils import cint, flt, today

from synarete_wms.synarete_wms.utils.qty_rules import validate_closeout_quantities


def _allow_skip():
    try:
        return cint(
            frappe.db.get_single_value(
                "WMS Settings", "allow_complete_without_closeout"
            )
        )
    except Exception:
        return 0


def _submitted_closeout(work_order_type, work_order):
    if not work_order or not frappe.db.exists("DocType", "WMS Material Closeout"):
        return None
    return frappe.db.get_value(
        "WMS Material Closeout",
        {
            "work_order_type": work_order_type,
            "work_order": work_order,
            "docstatus": 1,
        },
        "name",
    )


def work_order_issued_lines(work_order_type, work_order):
    """Issued / used / returned lines that must be reconciled."""
    lines = []
    if not work_order:
        return lines

    if work_order_type == "Site Work Order":
        rows = frappe.get_all(
            "WMS Material Accountability",
            filters={"site_work_order": work_order},
            fields=[
                "name",
                "item_code",
                "issued_qty",
                "carried_forward_qty",
                "transferred_out_qty",
                "consumed_qty",
                "returned_qty",
                "outstanding_qty",
                "material_issue",
            ],
        )
        for row in rows:
            issued = (
                flt(row.issued_qty)
                + flt(row.carried_forward_qty)
                - flt(row.transferred_out_qty)
            )
            if issued <= 0:
                continue
            item_name = frappe.db.get_value("Item", row.item_code, "item_name")
            lines.append(
                {
                    "item_code": row.item_code,
                    "item_name": item_name,
                    "issued_qty": issued,
                    "previously_used_qty": flt(row.consumed_qty),
                    "previously_returned_qty": flt(row.returned_qty),
                    "used_qty": flt(row.consumed_qty),
                    "returned_unused_qty": flt(row.returned_qty),
                    "accountability": row.name,
                    "material_issue": row.material_issue,
                }
            )
        return lines

    if work_order_type == "ServiceNow Site Work Order":
        from synarete_wms.synarete_wms.utils.servicenow import (
            collect_material_totals,
        )

        totals = collect_material_totals(work_order)
        for current in totals.values():
            issued = flt(current.get("qty_issued"))
            if issued <= 0:
                continue
            consumed = flt(current.get("qty_consumed"))
            returned = flt(current.get("qty_returned"))
            item_code = current.get("item_code")
            item_name = frappe.db.get_value("Item", item_code, "item_name")
            lines.append(
                {
                    "item_code": item_code,
                    "item_name": item_name,
                    "issued_qty": issued,
                    "previously_used_qty": consumed,
                    "previously_returned_qty": returned,
                    "used_qty": consumed,
                    "returned_unused_qty": returned,
                    "accountability": None,
                    "material_issue": None,
                }
            )
    return lines


@frappe.whitelist()
def get_closeout_lines(work_order_type, work_order):
    return work_order_issued_lines(work_order_type, work_order)


def has_issued_materials(work_order_type, work_order):
    return bool(work_order_issued_lines(work_order_type, work_order))


def assert_work_order_reconciled(work_order_type, work_order):
    if _allow_skip():
        return
    if not has_issued_materials(work_order_type, work_order):
        return
    closeout = _submitted_closeout(work_order_type, work_order)
    if closeout:
        return
    frappe.throw(
        "Return Material first. Open Material → Return Material, "
        "enter Used and Unused for every issued item, then Submit. "
        "You can Close the work order after that."
    )


@frappe.whitelist()
def can_complete_work_order(work_order_type, work_order):
    try:
        assert_work_order_reconciled(work_order_type, work_order)
        return {"ok": 1}
    except frappe.ValidationError as exc:
        return {"ok": 0, "message": str(exc)}


def post_closeout_stock(doc):
    """Expense extra used qty; transfer unused Field Issued → Main."""
    settings = frappe.get_single("WMS Settings")
    field_issued = settings.field_issued_warehouse
    main = settings.main_warehouse
    if not field_issued or not main or not settings.company:
        frappe.throw(
            "Set Company, Main Warehouse and Field Issued Warehouse in WMS Settings."
        )

    from synarete_wms.synarete_wms.utils.accountability import (
        add_consumption,
        add_return,
    )
    from synarete_wms.synarete_wms.utils.stock import (
        create_material_issue,
        create_material_transfer,
        get_available_qty,
        get_item_expense_account,
    )

    consume_items = []
    return_items = []
    for row in doc.items or []:
        extra_used = max(
            0, flt(row.used_qty) - flt(row.previously_used_qty)
        )
        extra_return = max(
            0,
            flt(row.returned_unused_qty) - flt(row.previously_returned_qty),
        )
        available = flt(get_available_qty(row.item_code, field_issued))
        if extra_used > 0:
            qty = min(extra_used, available)
            if qty > 0:
                consume_items.append(
                    {
                        "item_code": row.item_code,
                        "qty": qty,
                        "uom": row.uom,
                        "expense_account": get_item_expense_account(
                            row.item_code, settings.company
                        ),
                    }
                )
                available -= qty
            elif doc.work_order_type == "Site Work Order":
                frappe.throw(
                    f"{row.item_code}: no Field Issued stock to expense used qty {extra_used}."
                )
        if extra_return > 0:
            qty = min(extra_return, available)
            if qty > 0:
                return_items.append(
                    {
                        "item_code": row.item_code,
                        "qty": qty,
                        "uom": row.uom,
                    }
                )
            elif doc.work_order_type == "Site Work Order":
                frappe.throw(
                    f"{row.item_code}: no Field Issued stock to return unused qty {extra_return}."
                )

        if doc.work_order_type == "Site Work Order" and row.accountability:
            if extra_used > 0:
                accountability = frappe.get_doc(
                    "WMS Material Accountability", row.accountability
                )
                add_consumption(
                    accountability,
                    extra_used,
                    doc.name,
                    consumption_doctype="WMS Material Closeout",
                )
            if extra_return > 0:
                accountability = frappe.get_doc(
                    "WMS Material Accountability", row.accountability
                )
                add_return(
                    accountability,
                    extra_return,
                    doc.name,
                    return_doctype="WMS Material Closeout",
                )

    consume_entry = None
    return_entry = None
    if consume_items:
        consume_entry = create_material_issue(
            items=consume_items,
            source_warehouse=field_issued,
            company=settings.company,
            reference_doctype=doc.doctype,
            reference_name=doc.name,
            site=doc.site,
            engineer=doc.engineer,
            posting_date=doc.posting_date or today(),
            remarks=f"WMS closeout used material {doc.name}",
        )
    if return_items:
        return_entry = create_material_transfer(
            items=return_items,
            source_warehouse=field_issued,
            target_warehouse=main,
            company=settings.company,
            reference_doctype=doc.doctype,
            reference_name=doc.name,
            site=doc.site,
            engineer=doc.engineer,
        )
    if consume_entry:
        doc.db_set("consume_stock_entry", consume_entry.name, update_modified=False)
    if return_entry:
        doc.db_set("return_stock_entry", return_entry.name, update_modified=False)
