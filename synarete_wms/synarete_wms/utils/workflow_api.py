import frappe
from frappe.utils import today

from synarete_wms.synarete_wms.utils.qty_rules import (
    normalize_approved_quantity,
)


SUPPORTED_DOCTYPES = {
    "Site Work Order",
    "WMS Material Issue",
    "WMS Material Consumption",
}

WORKFLOW_NAMES = {
    "Site Work Order": "Site Work Order Workflow",
    "WMS Material Issue": "WMS Material Issue Workflow",
    "WMS Material Consumption": "WMS Material Consumption Workflow",
}


def _prepare_site_work_order_approval(document):
    """Persist reviewed quantities and reviewer metadata on explicit approval."""
    for row in document.materials or []:
        try:
            row.approved_qty = normalize_approved_quantity(
                row.qty,
                row.approved_qty,
            )
        except ValueError as exc:
            frappe.throw(f"{row.item_code}: {exc}")

    document.reviewed_by = frappe.session.user
    document.review_date = today()


@frappe.whitelist()
def apply_wms_workflow(doc, action):
    """Apply a WMS transition while preserving Frappe role checks."""
    parsed_doc = frappe.parse_json(doc) if isinstance(doc, str) else doc
    doctype = parsed_doc.get("doctype") if isinstance(parsed_doc, dict) else None
    name = parsed_doc.get("name") if isinstance(parsed_doc, dict) else None

    if doctype not in SUPPORTED_DOCTYPES:
        frappe.throw("Unsupported WMS workflow document.")
    if not name:
        frappe.throw("A saved WMS document is required.")

    previous_ignore_permissions = frappe.flags.get("ignore_permissions")
    frappe.flags.ignore_permissions = True

    try:
        document = frappe.get_doc(doctype, name)
        workflow_name = WORKFLOW_NAMES.get(doctype)

        if not workflow_name or not frappe.db.exists(
            "Workflow",
            workflow_name,
        ):
            frappe.throw(
                f"WMS workflow record is missing for {doctype}."
            )

        workflow = frappe.get_doc("Workflow", workflow_name)

        if not workflow.is_active:
            frappe.throw(
                f"WMS workflow is inactive for {doctype}."
            )
        current_state = document.get(workflow.workflow_state_field)
        roles = set(frappe.get_roles(frappe.session.user))
        transition = None
        manager_roles = {
            "Stock Manager",
            "Warehouse Manager",
            "System Manager",
        }

        for candidate in workflow.transitions:
            if candidate.state != current_state:
                continue
            if candidate.action != action:
                continue
            if candidate.allowed not in roles:
                continue
            if candidate.condition:
                if not frappe.safe_eval(
                    candidate.condition,
                    {"doc": document.as_dict()},
                ):
                    continue

            if transition is None:
                transition = candidate

            # If a manager is finalizing a consumption or issue, prefer
            # the submitted/final state over the employee verification path.
            if (
                roles.intersection(manager_roles)
                and candidate.next_state in ["Consumed", "Issued"]
            ):
                transition = candidate
                break

        if not transition:
            frappe.throw(
                f"No permitted '{action}' transition from {current_state}."
            )

        # Submit / Issue / Complete may be done by the same warehouse user.
        # Only Approve is gated by WMS Settings.allow_self_approve (default No).
        if doctype == "Site Work Order" and action == "Approve":
            from synarete_wms.synarete_wms.utils.permissions import (
                assert_can_approve_site_work_order,
            )

            assert_can_approve_site_work_order(document)
            _prepare_site_work_order_approval(document)

        if doctype == "WMS Material Consumption" and action == "Approve":
            document._require_expense_accounts()

        if doctype == "Site Work Order" and action in ("Complete", "Close Work Order"):
            from synarete_wms.synarete_wms.utils.closeout import (
                assert_work_order_reconciled,
            )

            assert_work_order_reconciled("Site Work Order", document.name)

        next_state = None
        for state in workflow.states:
            if state.state == transition.next_state:
                next_state = state
                break

        if not next_state:
            frappe.throw(
                f"Workflow state not found: {transition.next_state}"
            )

        document.set(workflow.workflow_state_field, next_state.state)

        if next_state.update_field:
            document.set(
                next_state.update_field,
                next_state.update_value,
            )

        old_docstatus = int(document.docstatus or 0)
        new_docstatus = int(next_state.doc_status or 0)

        if old_docstatus == 0 and new_docstatus == 0:
            document.save(ignore_permissions=True)
        elif old_docstatus == 0 and new_docstatus == 1:
            document.submit()
        elif old_docstatus == 1 and new_docstatus == 1:
            document.save(ignore_permissions=True)
        elif old_docstatus == 1 and new_docstatus == 2:
            document.cancel()
        else:
            frappe.throw(
                f"Illegal workflow status change {old_docstatus} -> {new_docstatus}."
            )

        document.add_comment("Workflow", next_state.state)
        return document.as_dict()

    finally:
        frappe.flags.ignore_permissions = previous_ignore_permissions


@frappe.whitelist()
def bulk_approve_site_work_orders(work_orders):
    """Approve selected Site Work Orders using the existing per-WO workflow.

    The individual Approve action remains available. Every selected order is
    reloaded and validated independently; ineligible orders stay unchanged.
    """
    names = frappe.parse_json(work_orders) if isinstance(work_orders, str) else work_orders
    if not isinstance(names, (list, tuple)) or not names:
        frappe.throw("Select at least one Site Work Order to approve.")

    unique_names = []
    for name in names:
        name = str(name or "").strip()
        if name and name not in unique_names:
            unique_names.append(name)
    if not unique_names:
        frappe.throw("Select at least one Site Work Order to approve.")
    if len(unique_names) > 200:
        frappe.throw("Approve no more than 200 Site Work Orders at a time.")

    if "Stock Manager" not in set(frappe.get_roles(frappe.session.user)):
        frappe.throw("Only a Stock Manager with the existing Approve permission can use bulk approval.")

    approved = []
    failed = []
    for index, name in enumerate(unique_names):
        savepoint = f"wms_bulk_swo_approve_{index}"
        frappe.db.savepoint(savepoint)
        try:
            if not frappe.db.exists("Site Work Order", name):
                frappe.throw(f"Site Work Order {name} was not found.")

            document = frappe.get_doc("Site Work Order", name)
            if int(document.docstatus or 0) != 0:
                frappe.throw(f"{name} is not a draft work order awaiting approval.")
            if document.status != "Pending Stock Review":
                frappe.throw(
                    f"{name} is {document.status or 'without a status'}, not Pending Stock Review."
                )

            apply_wms_workflow(
                {"doctype": "Site Work Order", "name": name},
                "Approve",
            )
            approved.append(name)
        except Exception as exc:
            frappe.db.rollback(save_point=savepoint)
            failed.append({"name": name, "reason": str(exc).splitlines()[0]})

    return {"approved": approved, "failed": failed}


@frappe.whitelist()
def bulk_approve_servicenow_work_orders(work_orders):
    """Run the existing active ServiceNow Work Order Approve transition per selection.

    This endpoint does not add an approval state or auto-approve imports. Each
    order is passed to Frappe's normal workflow engine, which enforces the
    active transition, its allowed roles, and its conditions independently.
    """
    names = frappe.parse_json(work_orders) if isinstance(work_orders, str) else work_orders
    if not isinstance(names, (list, tuple)) or not names:
        frappe.throw("Select at least one ServiceNow Work Order to approve.")

    unique_names = []
    for name in names:
        name = str(name or "").strip()
        if name and name not in unique_names:
            unique_names.append(name)
    if not unique_names:
        frappe.throw("Select at least one ServiceNow Work Order to approve.")
    if len(unique_names) > 200:
        frappe.throw("Approve no more than 200 ServiceNow Work Orders at a time.")

    from frappe.model.workflow import apply_workflow

    approved = []
    failed = []
    for index, name in enumerate(unique_names):
        savepoint = f"wms_bulk_snwo_approve_{index}"
        frappe.db.savepoint(savepoint)
        try:
            if not frappe.db.exists("ServiceNow Site Work Order", name):
                frappe.throw(f"ServiceNow Work Order {name} was not found.")

            document = frappe.get_doc("ServiceNow Site Work Order", name)
            apply_workflow(document.as_dict(), "Approve")
            approved.append(name)
        except Exception as exc:
            frappe.db.rollback(save_point=savepoint)
            failed.append({"name": name, "reason": str(exc).splitlines()[0]})

    return {"approved": approved, "failed": failed}
