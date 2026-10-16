import frappe
from frappe.utils import flt, today


def compute_issue_split(approved_qty, previous_outstanding, use_outstanding):
    """Split a request into reused Field Issued qty vs new Main Warehouse qty.

    Reused quantity never creates a Stock Entry. Additional quantity is the
    only amount transferred Main → Field Issued.
    """
    approved = flt(approved_qty)
    previous = max(0, flt(previous_outstanding))
    if use_outstanding:
        applied = min(previous, approved)
    else:
        applied = 0
    additional = max(0, approved - applied)
    return applied, additional


def get_open_balance(engineer, item_code, exclude_material_issue=None):
    if not engineer or not item_code:
        return 0

    rows = frappe.get_all(
        "WMS Material Accountability",
        filters={
            "engineer": engineer,
            "item_code": item_code,
            "outstanding_qty": [">", 0],
        },
        fields=["name", "outstanding_qty", "material_issue"],
    )

    total = 0
    for row in rows:
        if exclude_material_issue and row.material_issue == exclude_material_issue:
            continue
        total += flt(row.outstanding_qty)
    return total


@frappe.whitelist()
def get_engineer_item_outstanding(engineer, item_code):
    """Return the current field-held balance for a new issue form."""
    return get_open_balance(engineer, item_code)


@frappe.whitelist()
def get_issue_reuse_preview(engineer, item_code, approved_qty, use_outstanding=1):
    """Requested / available / reused / additional-from-Main preview."""
    previous = get_open_balance(engineer, item_code)
    use_flag = str(use_outstanding) not in ("0", "false", "False", "")
    applied, additional = compute_issue_split(approved_qty, previous, use_flag)
    return {
        "previous_outstanding_qty": previous,
        "outstanding_applied_qty": applied,
        "additional_qty": additional,
        "approved_qty": flt(approved_qty),
    }


def get_accountability(material_issue, material_issue_item=None, item_code=None):
    filters = {"material_issue": material_issue}

    if material_issue_item:
        filters["material_issue_item"] = material_issue_item
    elif item_code:
        filters["item_code"] = item_code

    rows = frappe.get_all(
        "WMS Material Accountability",
        filters=filters,
        fields="*",
        limit_page_length=20,
    )

    if len(rows) == 1:
        return frappe.get_doc("WMS Material Accountability", rows[0].name)
    if len(rows) > 1:
        frappe.throw(
            "More than one accountability record matches this material. "
            "Select the exact Material Issue Item row."
        )
    return None


def refresh_accountability(accountability):
    total_available = (
        flt(accountability.issued_qty)
        + flt(accountability.carried_forward_qty)
    )
    accounted = (
        flt(accountability.consumed_qty)
        + flt(accountability.returned_qty)
        + flt(accountability.transferred_out_qty)
    )

    accountability.outstanding_qty = max(0, total_available - accounted)

    if accountability.outstanding_qty <= 0:
        accountability.accountability_status = "Fully Accounted"
    elif accounted == 0:
        accountability.accountability_status = "Awaiting Consumption"
    else:
        accountability.accountability_status = "Partially Accounted"


@frappe.whitelist()
def get_accountability_summary(material_issue, material_issue_item=None, item_code=None):
    accountability = get_accountability(
        material_issue,
        material_issue_item,
        item_code,
    )
    if not accountability:
        return None

    return {
        "name": accountability.name,
        "requested_qty": accountability.requested_qty,
        "approved_qty": accountability.approved_qty,
        "issued_qty": accountability.issued_qty,
        "carried_forward_qty": accountability.carried_forward_qty,
        "transferred_out_qty": accountability.transferred_out_qty,
        "consumed_qty": accountability.consumed_qty,
        "returned_qty": accountability.returned_qty,
        "outstanding_qty": accountability.outstanding_qty,
        "accountability_status": accountability.accountability_status,
    }


def reallocate_outstanding(issue, item, quantity):
    remaining = flt(quantity)
    if remaining <= 0:
        return 0

    # Lock matching rows so two simultaneous issues cannot consume the
    # same leftover twice.
    frappe.db.sql(
        """
        SELECT name FROM `tabWMS Material Accountability`
        WHERE engineer = %s
          AND item_code = %s
          AND outstanding_qty > 0
        ORDER BY creation ASC
        FOR UPDATE
        """,
        (issue.engineer, item.item_code),
    )

    sources = frappe.get_all(
        "WMS Material Accountability",
        filters={
            "engineer": issue.engineer,
            "item_code": item.item_code,
            "outstanding_qty": [">", 0],
        },
        fields=["name", "outstanding_qty"],
        order_by="creation asc",
    )

    total_reallocated = 0

    for source_row in sources:
        if remaining <= 0:
            break

        source = frappe.get_doc(
            "WMS Material Accountability",
            source_row.name,
        )
        available = flt(source.outstanding_qty)
        allocated = min(available, remaining)

        if allocated <= 0:
            continue

        allocation = frappe.get_doc(
            {
                "doctype": "WMS Material Allocation",
                "source_accountability": source.name,
                "target_material_issue": issue.name,
                "target_material_issue_item": item.name,
                "engineer": issue.engineer,
                "site": issue.site,
                "item_code": item.item_code,
                "quantity": allocated,
                "allocation_date": issue.issue_date or today(),
                "notes": (
                    f"Reused on {issue.site_work_order or issue.name} "
                    f"from {source.site_work_order or source.material_issue}"
                ),
            }
        )
        allocation.insert(ignore_permissions=True)

        source.transferred_out_qty = flt(source.transferred_out_qty) + allocated
        source.last_allocation = allocation.name
        refresh_accountability(source)
        source.save(ignore_permissions=True)

        remaining -= allocated
        total_reallocated += allocated

    if remaining > 0:
        frappe.throw(
            f"Only {total_reallocated} outstanding units could be reallocated "
            f"for {item.item_code}; requested {quantity}."
        )

    return total_reallocated


def create_for_material_issue(issue):
    created = []

    for item in issue.items:
        existing = frappe.get_all(
            "WMS Material Accountability",
            filters={
                "material_issue": issue.name,
                "material_issue_item": item.name,
            },
            pluck="name",
            limit_page_length=1,
        )
        if existing:
            continue

        requested = flt(item.requested_qty) or flt(item.qty)
        approved = flt(item.approved_qty) or requested
        carried_forward = flt(item.outstanding_applied_qty)

        if carried_forward > 0:
            reallocate_outstanding(issue, item, carried_forward)

        accountability = frappe.get_doc(
            {
                "doctype": "WMS Material Accountability",
                "material_issue": issue.name,
                "material_issue_item": item.name,
                "site_work_order": issue.site_work_order,
                "site": issue.site,
                "engineer": issue.engineer,
                "item_code": item.item_code,
                "requested_qty": requested,
                "approved_qty": approved,
                "issued_qty": flt(item.qty),
                "carried_forward_qty": carried_forward,
                "transferred_out_qty": 0,
                "consumed_qty": 0,
                "returned_qty": 0,
                "outstanding_qty": flt(item.qty) + carried_forward,
                "accountability_status": "Awaiting Consumption",
            }
        )
        refresh_accountability(accountability)
        accountability.insert(ignore_permissions=True)
        created.append(accountability.name)

        item.db_set(
            "accountability",
            accountability.name,
            update_modified=False,
        )

    return created


def reverse_for_material_issue(issue):
    """Undo accountability created by a cancelled WMS Material Issue.

    Blocks cancel when any of the issued qty has already been consumed,
    returned, or reallocated to a later work order.
    """
    records = frappe.get_all(
        "WMS Material Accountability",
        filters={"material_issue": issue.name},
        fields=[
            "name",
            "item_code",
            "consumed_qty",
            "returned_qty",
            "transferred_out_qty",
        ],
    )

    for row in records:
        if flt(row.consumed_qty) > 0:
            frappe.throw(
                f"Cannot cancel Material Issue {issue.name}: {row.item_code} "
                f"already has consumed quantity {row.consumed_qty}."
            )
        if flt(row.returned_qty) > 0:
            frappe.throw(
                f"Cannot cancel Material Issue {issue.name}: {row.item_code} "
                f"already has returned quantity {row.returned_qty}."
            )
        if flt(row.transferred_out_qty) > 0:
            frappe.throw(
                f"Cannot cancel Material Issue {issue.name}: {row.item_code} "
                "was reallocated to another work order. Reverse that "
                "allocation first."
            )

    allocations = frappe.get_all(
        "WMS Material Allocation",
        filters={"target_material_issue": issue.name},
        fields=["name", "source_accountability", "quantity"],
    )

    for row in allocations:
        source = frappe.get_doc(
            "WMS Material Accountability",
            row.source_accountability,
        )
        source.transferred_out_qty = max(
            0,
            flt(source.transferred_out_qty) - flt(row.quantity),
        )
        refresh_accountability(source)
        source.save(ignore_permissions=True)
        frappe.delete_doc(
            "WMS Material Allocation",
            row.name,
            ignore_permissions=True,
            force=True,
        )

    for row in records:
        frappe.delete_doc(
            "WMS Material Accountability",
            row.name,
            ignore_permissions=True,
            force=True,
        )


def add_consumption(accountability, quantity, consumption_name):
    quantity = flt(quantity)
    available = flt(accountability.outstanding_qty)
    if quantity <= 0:
        frappe.throw("Consumed quantity must be greater than zero.")
    if quantity > available:
        frappe.throw(
            f"Consumed quantity exceeds outstanding quantity for {accountability.item_code}. "
            f"Outstanding: {available}."
        )

    accountability.consumed_qty = flt(accountability.consumed_qty) + quantity
    accountability.last_consumption = consumption_name
    refresh_accountability(accountability)
    accountability.save(ignore_permissions=True)


def reverse_consumption(accountability, quantity):
    quantity = flt(quantity)
    accountability.consumed_qty = max(
        0,
        flt(accountability.consumed_qty) - quantity,
    )
    refresh_accountability(accountability)
    accountability.save(ignore_permissions=True)


def add_return(accountability, quantity, return_name):
    quantity = flt(quantity)
    available = flt(accountability.outstanding_qty)
    if quantity <= 0:
        frappe.throw("Returned quantity must be greater than zero.")
    if quantity > available:
        frappe.throw(
            f"Returned quantity exceeds outstanding quantity for {accountability.item_code}. "
            f"Outstanding: {available}."
        )

    accountability.returned_qty = flt(accountability.returned_qty) + quantity
    accountability.last_return = return_name
    refresh_accountability(accountability)
    accountability.save(ignore_permissions=True)


def reverse_return(accountability, quantity):
    quantity = flt(quantity)
    accountability.returned_qty = max(
        0,
        flt(accountability.returned_qty) - quantity,
    )
    refresh_accountability(accountability)
    accountability.save(ignore_permissions=True)


def transfer_custodian(source_accountability, target_engineer, target_site, quantity, transfer_name=None):
    """Move leftover Field Issued custody between engineers. No Stock Entry."""
    quantity = flt(quantity)
    if quantity <= 0:
        frappe.throw("Transfer quantity must be greater than zero.")

    frappe.db.sql(
        """
        SELECT name FROM `tabWMS Material Accountability`
        WHERE name = %s
        FOR UPDATE
        """,
        (source_accountability,),
    )

    source = frappe.get_doc("WMS Material Accountability", source_accountability)
    if quantity > flt(source.outstanding_qty):
        frappe.throw(
            f"Transfer quantity exceeds outstanding quantity for {source.item_code}. "
            f"Outstanding: {source.outstanding_qty}."
        )
    if source.engineer == target_engineer and source.site == target_site:
        frappe.throw("Source and target custodian / site must be different.")

    source.transferred_out_qty = flt(source.transferred_out_qty) + quantity
    refresh_accountability(source)
    source.save(ignore_permissions=True)

    target = frappe.get_doc(
        {
            "doctype": "WMS Material Accountability",
            "material_issue": source.material_issue,
            "material_issue_item": source.material_issue_item,
            "site_work_order": source.site_work_order,
            "site": target_site or source.site,
            "engineer": target_engineer,
            "item_code": source.item_code,
            "requested_qty": 0,
            "approved_qty": 0,
            "issued_qty": 0,
            "carried_forward_qty": quantity,
            "transferred_out_qty": 0,
            "consumed_qty": 0,
            "returned_qty": 0,
            "outstanding_qty": quantity,
            "accountability_status": "Awaiting Consumption",
        }
    )
    refresh_accountability(target)
    target.insert(ignore_permissions=True)

    allocation = frappe.get_doc(
        {
            "doctype": "WMS Material Allocation",
            "source_accountability": source.name,
            "target_material_issue": source.material_issue,
            "target_material_issue_item": target.name,
            "engineer": target_engineer,
            "site": target.site,
            "item_code": source.item_code,
            "quantity": quantity,
            "allocation_date": today(),
            "notes": f"Custodian transfer {transfer_name or ''} {source.engineer} → {target_engineer}",
        }
    )
    allocation.insert(ignore_permissions=True)
    source.db_set("last_allocation", allocation.name, update_modified=False)
    return target.name
