import frappe


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

        if (
            document.owner == frappe.session.user
            and not int(transition.allow_self_approval or 0)
        ):
            frappe.throw("Self approval is not allowed")

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
