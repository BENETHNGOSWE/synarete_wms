"""ServiceNow Site Work Order helpers.

HTT remains a separate process. This module only serves ServiceNow work
orders, their material lifecycle, interchange, and MP payback tracking.
"""

from __future__ import annotations

from datetime import datetime

import frappe
from frappe.utils import cint, flt, get_datetime, getdate, now_datetime, nowdate


CLOSED_STATUSES = {
    "Closed Complete",
    "Closed Incomplete",
    "Closed Rejected",
}

STATUS_ALIASES = {
    "new": "Awaiting Material",
    "open": "Open",
    "work in progress": "Work in Progress",
    "work_in_progress": "Work in Progress",
    "in progress": "Work in Progress",
    "in_progress": "Work in Progress",
    "pending": "Pending",
    "on hold": "On Hold",
    "on_hold": "On Hold",
    "awaiting material": "Awaiting Material",
    "awaiting_material": "Awaiting Material",
    "resolved": "Resolved",
    "closed complete": "Closed Complete",
    "closed_complete": "Closed Complete",
    "closed incomplete": "Closed Incomplete",
    "closed_incomplete": "Closed Incomplete",
    "closed rejected": "Closed Rejected",
    "closed_rejected": "Closed Rejected",
    "closed": "Closed Complete",
    "cancelled": "Cancelled",
    "canceled": "Cancelled",
}

PRIORITY_ALIASES = {
    "0": "0 - Very Critical",
    "0 - very critical": "0 - Very Critical",
    "very critical": "0 - Very Critical",
    "1": "1 - Critical",
    "1 - critical": "1 - Critical",
    "critical": "1 - Critical",
    "2": "2 - High",
    "2 - high": "2 - High",
    "high": "2 - High",
    "3": "3 - Moderate",
    "3 - moderate": "3 - Moderate",
    "moderate": "3 - Moderate",
    "4": "4 - Low",
    "4 - low": "4 - Low",
    "low": "4 - Low",
}

PROCESS_STATUSES = [
    "Created",
    "Material Required",
    "Material Received",
    "Material Issued",
    "Material Consumed",
    "Reconciliation",
    "Completed",
]


def normalize_status(value):
    if not value:
        return "Awaiting Material"
    text = str(value).strip()
    return STATUS_ALIASES.get(text.lower(), text)


def status_group_for(status):
    return "Closed" if normalize_status(status) in CLOSED_STATUSES else "Open"


def is_pending_for(status):
    return 0 if status_group_for(status) == "Closed" else 1


def normalize_priority(value):
    if value in (None, ""):
        return None
    text = str(value).strip()
    return PRIORITY_ALIASES.get(text.lower(), text)


def normalize_order_type(value):
    if not value:
        return "Service"
    text = str(value).strip().lower()
    if text in ("material", "materials", "part", "parts"):
        return "Material"
    return "Service"


def parse_servicenow_datetime(value):
    """Convert ServiceNow datetime values to ISO ``YYYY-MM-DD HH:MM:SS``."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")

    text = str(value).strip()
    if not text:
        return None

    for fmt in (
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%d-%m-%Y",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(text.replace("Z", ""), fmt).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        except ValueError:
            continue

    parsed = get_datetime(text)
    if parsed:
        return parsed.strftime("%Y-%m-%d %H:%M:%S")
    return None


def parse_servicenow_date(value):
    parsed = parse_servicenow_datetime(value)
    return parsed[:10] if parsed else None


def compute_days_open(created_on, is_pending, as_of=None):
    if not created_on or not cint(is_pending):
        return 0
    start = getdate(created_on)
    end = getdate(as_of or nowdate())
    if not start or not end:
        return 0
    return max(0, (end - start).days)


def parse_fault_fields(row):
    row = row or {}
    short_description = row.get("short_description") or ""
    fault_code = row.get("fault_code") or row.get("u_fault_code")
    if not fault_code:
        prefix = row.get("u_fault_code_prefix") or ""
        code = row.get("u_fault_code") or ""
        fault_code = f"{prefix}{code}".strip() or None
    if not fault_code and short_description:
        token = str(short_description).split(" ", 1)[0].strip()
        if token and any(character.isdigit() for character in token):
            fault_code = token

    return {
        "fault_code": fault_code,
        "fault_group": row.get("fault_group") or row.get("u_fault_group"),
        "fault": row.get("fault") or row.get("u_fault"),
        "fault_category": row.get("fault_category") or row.get("u_fault_category"),
    }


def first_value(row, *keys):
    for key in keys:
        if row.get(key) not in (None, ""):
            return row.get(key)
    return None


def transform_servicenow_row(row):
    """Map a ServiceNow payload into ServiceNow Site Work Order values.

    Mandatory fields are always auto-filled. Callers must not require a
    user to type them.
    """
    row = dict(row or {})
    status = normalize_status(
        first_value(row, "status", "state", "u_state") or "New"
    )
    created_on = parse_servicenow_datetime(
        first_value(row, "created_on", "sys_created_on", "sys_created_on_display")
    ) or now_datetime().strftime("%Y-%m-%d %H:%M:%S")
    is_pending = is_pending_for(status)
    faults = parse_fault_fields(row)
    order_type = normalize_order_type(
        first_value(row, "order_type", "u_type", "type")
    )
    part_code = first_value(row, "part_code", "u_part_code")
    quantity = flt(first_value(row, "quantity", "u_quantity") or 0)

    transformed = {
        "doctype": "ServiceNow Site Work Order",
        "swo_number": str(
            first_value(row, "swo_number", "number", "sys_id", "u_number") or ""
        ).strip(),
        "site": first_value(row, "site", "u_site"),
        "status": status,
        "status_group": status_group_for(status),
        "is_pending": is_pending,
        "days_open": compute_days_open(created_on, is_pending),
        "order_type": order_type,
        "created_on": created_on,
        "source_system": first_value(row, "source_system") or "ServiceNow",
        "priority": normalize_priority(first_value(row, "priority", "u_priority")),
        "short_description": first_value(row, "short_description"),
        "fault_code": faults["fault_code"],
        "fault_group": faults["fault_group"],
        "fault": faults["fault"],
        "fault_category": faults["fault_category"],
        "part_code": part_code,
        "part_name": first_value(row, "part_name", "u_part"),
        "part_category": first_value(row, "part_category", "u_part_category"),
        "part_group": first_value(row, "part_group", "u_part_group"),
        "quantity": quantity,
        "assigned_to": first_value(row, "assigned_to"),
        "created_by": first_value(row, "created_by", "sys_created_by"),
        "opened_at": parse_servicenow_datetime(first_value(row, "opened_at")),
        "closed_at": parse_servicenow_datetime(first_value(row, "closed_at")),
        "actual_wo_date": parse_servicenow_date(
            first_value(row, "actual_wo_date", "u_actual_wo_date")
        ),
        "due_date": parse_servicenow_date(first_value(row, "due_date")),
        "description": first_value(row, "description"),
        "work_notes": first_value(row, "work_notes"),
        "is_solar_asset": cint(
            first_value(row, "is_solar_asset", "x_htaht_helios_mob_solar_asset") or 0
        ),
        "is_transformer_asset": cint(
            first_value(
                row,
                "is_transformer_asset",
                "x_htaht_helios_mob_transformer_asset",
            )
            or 0
        ),
        "u_escalated_by_tenant": first_value(row, "u_escalated_by_tenant"),
        "u_p0p4tab": cint(first_value(row, "u_p0p4tab") or 0),
        "process_status": "Created",
    }

    if order_type == "Material" and (part_code or quantity):
        transformed["process_status"] = "Material Required"

    return transformed


def apply_derived_fields(doc):
    if not doc.source_system:
        doc.source_system = "ServiceNow"
    if not doc.status:
        doc.status = "Awaiting Material"
    elif doc.status == "New":
        doc.status = "Awaiting Material"
    doc.status = normalize_status(doc.status)
    doc.status_group = status_group_for(doc.status)
    doc.is_pending = is_pending_for(doc.status)
    if not doc.created_on:
        doc.created_on = now_datetime()
    if not doc.order_type:
        doc.order_type = "Service"
    doc.days_open = compute_days_open(doc.created_on, doc.is_pending)
    if doc.site:
        if not doc.maintenance_partner:
            doc.maintenance_partner = frappe.db.get_value(
                "WMS Site", doc.site, "maintenance_partner"
            )
        if not doc.transition_partner:
            doc.transition_partner = frappe.db.get_value(
                "WMS Site", doc.site, "transition_partner"
            )
    if doc.part_code and not doc.part_name:
        doc.part_name = frappe.db.get_value("Item", doc.part_code, "item_name")
    if doc.is_new() and not doc.assigned_to:
        from synarete_wms.synarete_wms.utils.permissions import current_employee

        doc.assigned_to = current_employee()


def ensure_material_row_from_header(doc):
    if doc.order_type != "Material":
        return
    if not doc.part_code and not flt(doc.quantity):
        return

    existing = None
    for row in doc.materials or []:
        if row.item_code == doc.part_code or (
            not row.item_code and row.part_name == doc.part_name
        ):
            existing = row
            break

    if existing is None:
        existing = doc.append("materials", {})
        existing.item_code = doc.part_code
        existing.part_name = doc.part_name
        existing.part_category = doc.part_category
        existing.part_group = doc.part_group
        existing.material_source = "ServiceNow Request"

    if flt(doc.quantity) and flt(existing.qty_requested) == 0:
        existing.qty_requested = flt(doc.quantity)
    if not existing.part_name:
        existing.part_name = doc.part_name
    if not existing.part_category:
        existing.part_category = doc.part_category
    if not existing.part_group:
        existing.part_group = doc.part_group


def _blank_totals():
    return {
        "qty_requested": 0,
        "qty_received": 0,
        "qty_issued": 0,
        "qty_consumed": 0,
        "qty_interchanged_out": 0,
        "qty_interchanged_in": 0,
        "qty_mp_issued": 0,
        "qty_issued_from_received": 0,
        "qty_remaining": 0,
        "qty_warehouse_remaining": 0,
    }


def _item_key(item_code):
    return item_code or ""


def _canonical_item_code(item_code, item_name=None, work_order=None):
    """Map a transaction line onto the work-order item code.

    Receive lines sometimes store only item_name (or a blank item_code).
    Issue/Consume then look up a different key and see warehouse remaining 0
    even though the work order still shows remaining qty.
    """
    code = (item_code or "").strip()
    if code:
        return code
    name = (item_name or "").strip()
    if name and frappe.db.exists("Item", name):
        return name
    if work_order:
        rows = frappe.get_all(
            "SNWO Material Item",
            filters={"parent": work_order},
            fields=["item_code", "part_name"],
        )
        if name:
            for row in rows:
                if (row.part_name or "").strip() == name and row.item_code:
                    return row.item_code
        filled = [row.item_code for row in rows if row.item_code]
        if len(filled) == 1:
            return filled[0]
        if len(rows) == 1 and rows[0].item_code:
            return rows[0].item_code
    return name or code


def _warehouse_available(work_order, item_code, item_name=None):
    totals = collect_material_totals(work_order)
    key = _canonical_item_code(item_code, item_name, work_order)
    live = flt(totals.get(_item_key(key), {}).get("qty_warehouse_remaining"))
    stored = flt(
        frappe.db.get_value(
            "SNWO Material Item",
            {"parent": work_order, "item_code": key or item_code},
            "qty_warehouse_remaining",
        )
    )
    rows = frappe.db.sql(
        """
        SELECT MAX(qty_warehouse_remaining)
        FROM `tabSNWO Material Item`
        WHERE parent = %s
          AND (
                item_code = %s
                OR part_name = %s
                OR IFNULL(item_code, '') = ''
          )
        """,
        (work_order, item_code, item_name or item_code),
    )
    stored_max = flt(rows[0][0] if rows else 0)
    return max(live, stored, stored_max)


def collect_material_totals(work_order):
    totals = {}

    def bucket(item_code):
        key = _item_key(item_code)
        if key not in totals:
            totals[key] = _blank_totals()
            totals[key]["item_code"] = item_code
        return totals[key]

    if not work_order:
        return totals

    transactions = frappe.db.sql(
        """
        SELECT name
        FROM `tabSNWO Material Transaction`
        WHERE docstatus = 1
          AND (
                original_work_order = %(wo)s
                OR received_for_work_order = %(wo)s
                OR issued_to_work_order = %(wo)s
          )
        """,
        {"wo": work_order},
        as_dict=True,
    )

    for txn_row in transactions:
        txn = frappe.get_doc("SNWO Material Transaction", txn_row.name)
        for row in txn.items or []:
            item_code = _canonical_item_code(
                row.item_code,
                getattr(row, "item_name", None),
                work_order,
            )
            qty = flt(row.qty)
            if txn.transaction_type == "Request" and txn.original_work_order == work_order:
                bucket(item_code)["qty_requested"] += qty
            elif txn.transaction_type == "Receive" and (
                txn.received_for_work_order == work_order
                or txn.original_work_order == work_order
            ):
                bucket(item_code)["qty_received"] += qty
            elif txn.transaction_type in ("Issue", "Interchange", "MP Issue"):
                issued_to = txn.issued_to_work_order or txn.original_work_order
                original = txn.original_work_order
                received_for = txn.received_for_work_order or original
                is_mp = cint(txn.is_mp_stock) or txn.transaction_type == "MP Issue"
                if issued_to == work_order:
                    bucket(item_code)["qty_issued"] += qty
                    if is_mp:
                        bucket(item_code)["qty_mp_issued"] += qty
                    if cint(txn.is_interchange) and original and original != work_order:
                        bucket(item_code)["qty_interchanged_in"] += qty
                if original == work_order and issued_to and issued_to != work_order:
                    bucket(item_code)["qty_interchanged_out"] += qty
                if received_for == work_order and not is_mp:
                    bucket(item_code)["qty_issued_from_received"] += qty
            elif txn.transaction_type == "Consume" and (
                txn.issued_to_work_order == work_order
                or txn.original_work_order == work_order
            ):
                bucket(item_code)["qty_consumed"] += qty

    for current in totals.values():
        current["qty_warehouse_remaining"] = max(
            0,
            current["qty_received"]
            - current["qty_issued_from_received"]
            + current["qty_interchanged_in"],
        )
        # Warehouse interchange (received then sent to another SWO) is not
        # issued-on-site, so it must not reduce Qty Remaining.
        # Interchange of stock that was already issued to this SWO must.
        # A return (Interchanged In) restocks warehouse remaining, so it is
        # not also counted as issued remaining.
        self_from_warehouse = max(
            0,
            current["qty_issued"]
            - current["qty_interchanged_in"]
            - current["qty_mp_issued"],
        )
        sent_from_warehouse = min(
            current["qty_interchanged_out"],
            max(0, current["qty_received"] - self_from_warehouse),
        )
        sent_from_issued = max(
            0, current["qty_interchanged_out"] - sent_from_warehouse
        )
        current["qty_remaining"] = max(
            0,
            current["qty_issued"]
            - current["qty_consumed"]
            - sent_from_issued
            - current["qty_interchanged_in"],
        )

    return totals


@frappe.whitelist()
def recalculate_work_order_qty(work_order):
    refresh_work_order_balances(work_order)
    return work_order


def refresh_work_order_balances(work_order):
    if not work_order:
        return
    doc = frappe.get_doc("ServiceNow Site Work Order", work_order)
    totals = collect_material_totals(work_order)
    seen = set()

    for row in doc.materials or []:
        current = totals.get(
            _item_key(
                _canonical_item_code(row.item_code, row.part_name, work_order)
            ),
            _blank_totals(),
        )
        requested = max(flt(row.qty_requested), flt(current["qty_requested"]))
        row.qty_requested = requested
        row.qty_received = flt(current["qty_received"])
        row.qty_issued = flt(current["qty_issued"])
        row.qty_consumed = flt(current["qty_consumed"])
        row.qty_interchanged_out = flt(current["qty_interchanged_out"])
        row.qty_interchanged_in = flt(current["qty_interchanged_in"])
        row.qty_mp_issued = flt(current["qty_mp_issued"])
        row.qty_remaining = flt(current["qty_remaining"])
        row.qty_warehouse_remaining = flt(current["qty_warehouse_remaining"])
        seen.add(_item_key(row.item_code))

    for item_code, current in totals.items():
        if item_code in seen:
            continue
        if not any(flt(current.get(field) or 0) for field in current if field != "item_code"):
            continue
        row = doc.append("materials", {})
        row.item_code = current.get("item_code")
        row.material_source = "ServiceNow Request"
        row.qty_requested = flt(current["qty_requested"])
        row.qty_received = flt(current["qty_received"])
        row.qty_issued = flt(current["qty_issued"])
        row.qty_consumed = flt(current["qty_consumed"])
        row.qty_interchanged_out = flt(current["qty_interchanged_out"])
        row.qty_interchanged_in = flt(current["qty_interchanged_in"])
        row.qty_mp_issued = flt(current["qty_mp_issued"])
        row.qty_remaining = flt(current["qty_remaining"])
        row.qty_warehouse_remaining = flt(current["qty_warehouse_remaining"])

    doc.mp_material_used = 1 if any(flt(row.qty_mp_issued) for row in doc.materials) else 0
    apply_awaiting_material(doc)
    doc.interchange_count = frappe.db.sql(
        """
        SELECT COUNT(DISTINCT name)
        FROM `tabSNWO Material Transaction`
        WHERE docstatus = 1
          AND is_interchange = 1
          AND (original_work_order = %(wo)s OR issued_to_work_order = %(wo)s)
        """,
        {"wo": work_order},
    )[0][0] or 0
    last_interchange = frappe.db.sql(
        """
        SELECT MAX(posting_date)
        FROM `tabSNWO Material Transaction`
        WHERE docstatus = 1
          AND is_interchange = 1
          AND (original_work_order = %(wo)s OR issued_to_work_order = %(wo)s)
        """,
        {"wo": work_order},
    )
    doc.last_interchange_on = last_interchange[0][0] if last_interchange else None
    doc.process_status = derive_process_status(doc)
    doc.days_open = compute_days_open(doc.created_on, doc.is_pending)
    doc.save(ignore_permissions=True)


def _needs_warehouse_issue(doc):
    """True until warehouse has received and issued the requested qty.

    Covers new Material WOs (nothing received yet) and received-but-not-issued.
    """
    if doc.process_status == "Completed":
        return False
    requested = 0
    issued = 0
    warehouse_left = 0
    for row in doc.materials or []:
        requested += flt(row.qty_requested)
        issued += flt(row.qty_issued)
        warehouse_left += flt(row.qty_warehouse_remaining)
    if doc.order_type == "Material":
        requested = max(requested, flt(doc.quantity))
    if warehouse_left > 0:
        return True
    return requested > issued + 0.0001


def apply_awaiting_material(doc):
    """Orange warehouse queue: new WOs and anything still to receive/issue."""
    if doc.process_status == "Completed":
        if doc.meta.has_field("awaiting_warehouse_issue"):
            doc.awaiting_warehouse_issue = 0
        return

    if not doc.status or doc.status == "New":
        doc.status = "Awaiting Material"

    needs = _needs_warehouse_issue(doc)
    if doc.status == "Awaiting Material":
        needs = True
        requested = 0
        issued = 0
        warehouse_left = 0
        for row in doc.materials or []:
            requested += flt(row.qty_requested)
            issued += flt(row.qty_issued)
            warehouse_left += flt(row.qty_warehouse_remaining)
        if doc.order_type == "Material":
            requested = max(requested, flt(doc.quantity))
        fully_issued = (
            requested > 0
            and issued + 0.0001 >= requested
            and warehouse_left <= 0
        )
        if fully_issued:
            needs = False
            doc.status = "Open"

    if doc.meta.has_field("awaiting_warehouse_issue"):
        doc.awaiting_warehouse_issue = 1 if needs else 0
    doc.status_group = status_group_for(doc.status)
    doc.is_pending = is_pending_for(doc.status)


def derive_process_status(doc):
    if doc.process_status == "Completed":
        return "Completed"
    if doc.process_status == "Reconciliation":
        if any(flt(row.qty_consumed) for row in doc.materials or []):
            return "Reconciliation"
    has_request = any(flt(row.qty_requested) for row in doc.materials or []) or (
        doc.order_type == "Material" and flt(doc.quantity)
    )
    has_received = any(flt(row.qty_received) for row in doc.materials or [])
    has_issued = any(flt(row.qty_issued) for row in doc.materials or [])
    has_consumed = any(flt(row.qty_consumed) for row in doc.materials or [])
    has_recon = frappe.db.exists(
        "SNWO Material Transaction",
        {
            "docstatus": 1,
            "transaction_type": "Reconcile",
            "original_work_order": doc.name,
        },
    )
    if has_recon:
        return "Reconciliation"
    if has_consumed:
        return "Material Consumed"
    if has_issued:
        return "Material Issued"
    if has_received:
        return "Material Received"
    if has_request:
        return "Material Required"
    return "Created"


def validate_transaction(doc):
    from synarete_wms.synarete_wms.utils.permissions import enforce_snwo_transaction_role

    enforce_snwo_transaction_role(doc)
    if not doc.items:
        frappe.throw("Add at least one material line.")
    if not doc.original_work_order:
        frappe.throw("Original Work Order is required. The original request is never deleted.")
    if not doc.posting_date:
        doc.posting_date = nowdate()
    if not doc.performed_by:
        doc.performed_by = frappe.session.user

    original = doc.original_work_order
    issued_to = doc.issued_to_work_order or original
    received_for = doc.received_for_work_order or original
    doc.issued_to_work_order = issued_to
    doc.received_for_work_order = received_for

    if doc.transaction_type == "MP Issue":
        doc.is_mp_stock = 1
    if doc.transaction_type == "Interchange":
        doc.is_interchange = 1

    if (
        issued_to == original
        and doc.transaction_type in ("Issue", "Interchange")
        and not cint(doc.is_mp_stock)
    ):
        doc.is_interchange = 0
        if doc.transaction_type == "Interchange":
            doc.transaction_type = "Issue"

    if issued_to != original and doc.transaction_type in ("Issue", "Interchange", "MP Issue"):
        doc.is_interchange = 1
        doc.transaction_type = (
            "MP Issue" if cint(doc.is_mp_stock) else "Interchange"
        )
        if not (doc.interchange_reason or "").strip():
            frappe.throw(
                "Reason for interchange is required when material is issued "
                "to a different ServiceNow Work Order."
            )

    if cint(doc.is_mp_stock) and doc.transaction_type == "Issue":
        doc.transaction_type = "MP Issue"

    if is_mp_transaction(doc):
        if not doc.warehouse:
            settings = frappe.get_single("WMS Settings")
            doc.warehouse = settings.main_warehouse
        if not doc.warehouse:
            frappe.throw(
                "Warehouse is required to deduct MP stock from the stock ledger."
            )
        if cint(doc.docstatus) != 1 and not doc.get("stock_entry"):
            from synarete_wms.synarete_wms.utils.stock import get_available_qty

            for row in doc.items:
                available = flt(get_available_qty(row.item_code, doc.warehouse))
                if flt(row.qty) > available + 0.0001:
                    frappe.throw(
                        f"Cannot issue {flt(row.qty)} of {row.item_code} from MP stock. "
                        f"Available in {doc.warehouse} is {available}."
                    )

    for row in doc.items:
        if flt(row.qty) <= 0:
            frappe.throw(f"Quantity must be greater than zero for {row.item_code}.")
        row.original_work_order = original
        row.received_for_work_order = received_for
        row.issued_to_work_order = issued_to
        row.is_interchange = cint(doc.is_interchange)
        row.is_mp_stock = cint(doc.is_mp_stock)

    if doc.transaction_type in ("Issue", "Interchange") and not cint(doc.is_mp_stock):
        source_totals = (
            collect_material_totals(original) if cint(doc.is_interchange) else {}
        )
        for row in doc.items:
            warehouse_left = _warehouse_available(
                received_for,
                row.item_code,
                getattr(row, "item_name", None),
            )
            issued_left = 0
            available = warehouse_left
            if cint(doc.is_interchange):
                key = _canonical_item_code(
                    row.item_code,
                    getattr(row, "item_name", None),
                    original,
                )
                issued_left = flt(
                    source_totals.get(_item_key(key), {}).get("qty_remaining")
                )
                available = warehouse_left + issued_left
            if flt(row.qty) > available + 0.0001:
                frappe.throw(
                    f"Cannot issue {flt(row.qty)} of {row.item_code}. "
                    f"Available to interchange/issue is {available} "
                    f"(warehouse remaining on {received_for}: {warehouse_left}"
                    + (
                        f", remaining on {original}: {issued_left}"
                        if cint(doc.is_interchange)
                        else ""
                    )
                    + ")."
                )

    if doc.transaction_type == "Consume":
        totals = collect_material_totals(issued_to)
        for row in doc.items:
            key = _canonical_item_code(
                row.item_code,
                getattr(row, "item_name", None),
                issued_to,
            )
            remaining = flt(totals.get(_item_key(key), {}).get("qty_remaining"))
            warehouse_left = flt(
                totals.get(_item_key(key), {}).get("qty_warehouse_remaining")
            )
            if flt(row.qty) > remaining + 0.0001:
                extra = ""
                if warehouse_left:
                    extra = (
                        f" There are still {warehouse_left} remaining in warehouse for this "
                        "work order. Issue that quantity to this same work order first "
                        "(Material → Issue Material, Issued To = this SWO), then Consume."
                    )
                frappe.throw(
                    f"Cannot consume {flt(row.qty)} of {row.item_code}. "
                    f"Remaining issued quantity on {issued_to} is {remaining}.{extra}"
                )


def is_mp_transaction(doc):
    return cint(getattr(doc, "is_mp_stock", 0)) or doc.transaction_type == "MP Issue"


def post_mp_stock_issue(doc, force=False):
    """Deduct company MP stock from the warehouse stock ledger."""
    if not force and not is_mp_transaction(doc):
        return None
    if doc.get("stock_entry"):
        return doc.stock_entry
    if cint(doc.docstatus) == 2:
        return None

    settings = frappe.get_single("WMS Settings")
    warehouse = doc.warehouse or settings.main_warehouse
    if not warehouse:
        frappe.throw("Set the Warehouse on the MP issue, or Main Warehouse in WMS Settings.")
    if not settings.company:
        frappe.throw("Set Company in WMS Settings before issuing MP stock.")

    work_order = doc.issued_to_work_order or doc.original_work_order
    engineer = frappe.db.get_value(
        "ServiceNow Site Work Order",
        work_order,
        "assigned_to",
    )

    items = []
    for row in doc.items or []:
        item_code = _canonical_item_code(
            row.item_code,
            getattr(row, "item_name", None),
            work_order,
        )
        if not item_code:
            frappe.throw(
                f"{doc.name}: item code is missing on a material line. "
                "Warehouse stock was not deducted."
            )
        items.append(
            {
                "item_code": item_code,
                "qty": row.qty,
                "uom": row.uom,
            }
        )
    if not items:
        frappe.throw(f"{doc.name} has no material lines to deduct from warehouse stock.")

    from synarete_wms.synarete_wms.utils.stock import create_material_issue

    stock_entry = create_material_issue(
        items=items,
        source_warehouse=warehouse,
        company=settings.company,
        reference_doctype=doc.doctype,
        reference_name=doc.name,
        site=doc.site,
        engineer=engineer,
        posting_date=doc.posting_date,
        remarks=(
            f"ServiceNow MP issue {doc.name} for work order {work_order}. "
            "Client payback stock."
        ),
    )
    doc.db_set("stock_entry", stock_entry.name, update_modified=False)
    doc.db_set("warehouse", warehouse, update_modified=False)
    if not cint(doc.is_mp_stock):
        doc.db_set("is_mp_stock", 1, update_modified=False)
        doc.is_mp_stock = 1
    return stock_entry.name


def post_missing_mp_stock(work_order):
    """Post stock deductions for submitted MP issues that have none yet."""
    if not work_order:
        return []
    names = frappe.db.sql(
        """
        SELECT name
        FROM `tabSNWO Material Transaction`
        WHERE docstatus = 1
          AND (is_mp_stock = 1 OR transaction_type = 'MP Issue')
          AND IFNULL(stock_entry, '') = ''
          AND (
                original_work_order = %(wo)s
                OR issued_to_work_order = %(wo)s
          )
        """,
        {"wo": work_order},
        as_dict=True,
    )
    posted = []
    for row in names or []:
        posted.append(
            post_mp_stock_issue(frappe.get_doc("SNWO Material Transaction", row.name))
        )
    return posted


def related_work_orders(doc):
    names = [
        doc.original_work_order,
        doc.received_for_work_order,
        doc.issued_to_work_order,
    ]
    unique = []
    for name in names:
        if name and name not in unique:
            unique.append(name)
    return unique


@frappe.whitelist()
def upsert_servicenow_work_order(payload):
    """Create or update a ServiceNow Site Work Order from a mapped payload.

    Mandatory fields are auto-filled by the transform. Existing material
    request quantities are never deleted.
    """
    if isinstance(payload, str):
        payload = frappe.parse_json(payload)
    transformed = transform_servicenow_row(payload)
    if not transformed.get("swo_number"):
        frappe.throw("ServiceNow WO ID is required for import.")
    if not transformed.get("site"):
        frappe.throw("Site is required for import and must match a WMS Site.")

    site = transformed["site"]
    if not frappe.db.exists("WMS Site", site):
        site_name = frappe.db.get_value("WMS Site", {"site_code": site}, "name")
        if not site_name:
            frappe.throw(f"WMS Site {site} was not found. Import the site first.")
        transformed["site"] = site_name

    if transformed.get("part_code") and not frappe.db.exists("Item", transformed["part_code"]):
        # Keep the ServiceNow part description even when the Item master is
        # not yet created. The Link field cannot store an unknown Item.
        transformed["part_name"] = transformed.get("part_name") or transformed["part_code"]
        transformed["part_code"] = None

    if transformed.get("assigned_to") and not frappe.db.exists(
        "Employee", transformed["assigned_to"]
    ):
        employee = frappe.db.get_value(
            "Employee",
            {"user_id": transformed["assigned_to"]},
            "name",
        )
        transformed["assigned_to"] = employee

    existing = frappe.db.exists(
        "ServiceNow Site Work Order", transformed["swo_number"]
    ) or frappe.db.exists(
        "ServiceNow Site Work Order", {"swo_number": transformed["swo_number"]}
    )

    if existing:
        doc = frappe.get_doc("ServiceNow Site Work Order", existing)
        for field, value in transformed.items():
            if field in ("doctype", "materials", "process_status"):
                continue
            if value in (None, ""):
                continue
            doc.set(field, value)
    else:
        doc = frappe.get_doc(transformed)

    apply_derived_fields(doc)
    ensure_material_row_from_header(doc)
    if not doc.process_status:
        doc.process_status = "Created"
    if existing:
        doc.save(ignore_permissions=True)
    else:
        doc.insert(ignore_permissions=True)
    return doc.name


@frappe.whitelist()
def import_servicenow_work_orders(rows):
    if isinstance(rows, str):
        rows = frappe.parse_json(rows)
    created = []
    for row in rows or []:
        created.append(upsert_servicenow_work_order(row))
    return created


def update_days_open():
    orders = frappe.get_all(
        "ServiceNow Site Work Order",
        filters={"is_pending": 1},
        fields=["name", "created_on", "is_pending"],
    )
    for order in orders:
        days = compute_days_open(order.created_on, order.is_pending)
        frappe.db.set_value(
            "ServiceNow Site Work Order",
            order.name,
            "days_open",
            days,
            update_modified=False,
        )


def ensure_maintenance_partners():
    for partner_name in ("Synarete", "JD Electronics"):
        if frappe.db.exists("Maintenance Partner", partner_name):
            continue
        if frappe.db.exists("Maintenance Partner", {"partner_name": partner_name}):
            continue
        frappe.get_doc(
            {
                "doctype": "Maintenance Partner",
                "partner_name": partner_name,
            }
        ).insert(ignore_permissions=True)


@frappe.whitelist()
def complete_work_order(name):
    from synarete_wms.synarete_wms.utils.permissions import can_run_snwo_engineer_ops

    if not can_run_snwo_engineer_ops():
        frappe.throw("You cannot complete this ServiceNow work order.")
    from synarete_wms.synarete_wms.utils.permissions import can_issue_snwo_material

    if can_issue_snwo_material():
        post_missing_mp_stock(name)
    doc = frappe.get_doc("ServiceNow Site Work Order", name)
    doc.process_status = "Completed"
    doc.save(ignore_permissions=True)
    return doc.name


@frappe.whitelist()
def deduct_mp_stock(work_order=None, transaction=None):
    """Fix already submitted MP issues that did not reduce warehouse stock."""
    from synarete_wms.synarete_wms.utils.permissions import can_issue_snwo_material

    if not can_issue_snwo_material():
        frappe.throw("Only a Warehouse Manager can deduct MP warehouse stock.")
    if transaction:
        doc = frappe.get_doc("SNWO Material Transaction", transaction)
        posted = post_mp_stock_issue(doc, force=True)
        return {"stock_entry": posted, "transaction": doc.name}
    if work_order:
        posted = post_missing_mp_stock(work_order)
        return {"stock_entries": posted, "work_order": work_order}
    return post_all_missing_mp_stock()


@frappe.whitelist()
def post_all_missing_mp_stock():
    """Deduct warehouse stock for every submitted MP issue with no Stock Entry."""
    names = frappe.db.sql(
        """
        SELECT name
        FROM `tabSNWO Material Transaction`
        WHERE docstatus = 1
          AND (is_mp_stock = 1 OR transaction_type = 'MP Issue')
          AND IFNULL(stock_entry, '') = ''
        """,
        as_dict=True,
    )
    posted = []
    for row in names or []:
        posted.append(
            post_mp_stock_issue(frappe.get_doc("SNWO Material Transaction", row.name))
        )
    return posted
