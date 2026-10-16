"""Idempotent workflow definitions owned by Synarete WMS."""

import frappe


WORKFLOWS = [
    {
        "name": "Site Work Order Workflow",
        "document_type": "Site Work Order",
        "state_field": "status",
        "states": [
            ("Draft", 0, "Stock User"),
            ("Pending Stock Review", 0, "Stock Manager"),
            ("Approved", 0, "Stock Manager"),
            ("Rejected", 0, "Stock User"),
            ("Issued", 0, "Stock User"),
            ("In Progress", 0, "Stock User"),
            ("Completed", 1, "Stock User"),
            ("Cancelled", 2, "Stock Manager"),
        ],
        "transitions": [
            ("Draft", "Submit", "Pending Stock Review", "Stock User", None),
            ("Draft", "Submit", "Pending Stock Review", "Employee", None),
            ("Pending Stock Review", "Approve", "Approved", "Stock Manager", None),
            ("Pending Stock Review", "Reject", "Rejected", "Stock Manager", None),
            ("Approved", "Mark Issued", "Issued", "Stock Manager", None),
            ("Issued", "Start Work", "In Progress", "Stock User", None),
            ("In Progress", "Complete", "Completed", "Stock User", None),
            ("Approved", "Reject", "Rejected", "Stock Manager", None),
        ],
    },
    {
        "name": "WMS Material Issue Workflow",
        "document_type": "WMS Material Issue",
        # Same as SNWO Material Transaction: an active workflow hid Submit
        # from warehouse users. Stock posting is on_submit of the DocType.
        "is_active": 0,
        "state_field": "status",
        "states": [
            ("Draft", 0, "Stock User"),
            ("Issued", 1, "Stock Manager"),
            ("Cancelled", 2, "Stock Manager"),
        ],
        "transitions": [
            ("Draft", "Submit", "Issued", "Stock Manager", None),
            ("Draft", "Submit", "Issued", "Warehouse Manager", None),
            ("Draft", "Submit", "Issued", "Stock User", None),
            ("Issued", "Cancel", "Cancelled", "Stock Manager", None),
            ("Issued", "Cancel", "Cancelled", "Warehouse Manager", None),
        ],
    },
    {
        "name": "SNWO Material Transaction Workflow",
        "document_type": "SNWO Material Transaction",
        # Standard Submit is used instead. A Frappe workflow here hid Submit
        # from engineers (only Stock Manager could edit Draft).
        "is_active": 0,
        "state_field": "status",
        "states": [
            ("Draft", 0, "Employee"),
            ("Submitted", 1, "Stock Manager"),
            ("Cancelled", 2, "Stock Manager"),
        ],
        "transitions": [
            ("Draft", "Submit", "Submitted", "Stock Manager", None),
            ("Draft", "Submit", "Submitted", "Warehouse Manager", None),
            ("Draft", "Submit", "Submitted", "WMS Engineer", None),
            ("Draft", "Submit", "Submitted", "Stock User", None),
            ("Draft", "Submit", "Submitted", "Employee", None),
            ("Submitted", "Cancel", "Cancelled", "Stock Manager", None),
            ("Submitted", "Cancel", "Cancelled", "Warehouse Manager", None),
        ],
    },
    {
        "name": "WMS Material Consumption Workflow",
        "document_type": "WMS Material Consumption",
        "state_field": "status",
        "states": [
            ("Draft", 0, "Employee"),
            ("Pending Verification", 0, "Stock Manager"),
            ("Consumed", 1, "Stock Manager"),
            ("Rejected", 0, "Employee"),
            ("Cancelled", 2, "Stock Manager"),
        ],
        "transitions": [
            ("Draft", "Submit", "Pending Verification", "Employee", None),
            ("Draft", "Submit", "Pending Verification", "Stock User", None),
            ("Draft", "Submit", "Consumed", "Stock Manager", None),
            ("Draft", "Submit", "Consumed", "Warehouse Manager", None),
            ("Pending Verification", "Approve", "Consumed", "Stock Manager", None),
            ("Pending Verification", "Approve", "Consumed", "Warehouse Manager", None),
            ("Pending Verification", "Reject", "Rejected", "Stock Manager", None),
            ("Pending Verification", "Reject", "Rejected", "Warehouse Manager", None),
            ("Consumed", "Cancel", "Cancelled", "Stock Manager", None),
            ("Consumed", "Cancel", "Cancelled", "Warehouse Manager", None),
        ],
    },
]


def _condition_key(value):
    return (value or "").replace(" ", "").replace("'", '"')


def _ensure_workflow_state(state_name):
    if frappe.db.exists("Workflow State", state_name):
        return

    frappe.get_doc(
        {
            "doctype": "Workflow State",
            "workflow_state_name": state_name,
        }
    ).insert(ignore_permissions=True)


def _ensure_workflow_action(action_name):
    if frappe.db.exists("Workflow Action Master", action_name):
        return

    frappe.get_doc(
        {
            "doctype": "Workflow Action Master",
            "workflow_action_name": action_name,
        }
    ).insert(ignore_permissions=True)


def ensure_workflows():
    for definition in WORKFLOWS:
        if not frappe.db.exists("DocType", definition["document_type"]):
            continue
        for state, _doc_status, _allow_edit in definition["states"]:
            _ensure_workflow_state(state)

        actions = []
        for _state, action, _next_state, _allowed, _condition in definition["transitions"]:
            if action not in actions:
                actions.append(action)

        for action in actions:
            _ensure_workflow_action(action)

        workflow_name = frappe.db.exists("Workflow", definition["name"])

        if workflow_name:
            doc = frappe.get_doc("Workflow", workflow_name)
        else:
            doc = frappe.new_doc("Workflow")
            doc.workflow_name = definition["name"]
            doc.document_type = definition["document_type"]
            doc.workflow_state_field = definition["state_field"]
            doc.is_active = definition.get("is_active", 1)
            doc.module = "Synarete WMS"

        desired_state_names = []
        for state, _doc_status, _allow_edit in definition["states"]:
            desired_state_names.append(state)

        if definition["document_type"] in (
            "WMS Material Issue",
            "WMS Material Consumption",
            "SNWO Material Transaction",
        ):
            doc.set(
                "states",
                [
                    row
                    for row in doc.states
                    if row.state in desired_state_names
                ],
            )

            desired_transition_keys = []
            for state, action, next_state, allowed, condition in definition["transitions"]:
                desired_transition_keys.append(
                    (
                        state,
                        action,
                        next_state,
                        allowed,
                        _condition_key(condition),
                    )
                )

            doc.set(
                "transitions",
                [
                    row
                    for row in doc.transitions
                    if (
                        row.state,
                        row.action,
                        row.next_state,
                        row.allowed,
                        _condition_key(row.condition),
                    ) in desired_transition_keys
                ],
            )

        existing_states = {}
        for row in doc.states:
            existing_states[row.state] = row

        for state, doc_status, allow_edit in definition["states"]:
            if state in existing_states:
                row = existing_states[state]
                row.doc_status = doc_status
                row.update_field = definition["state_field"]
                row.update_value = state
                row.allow_edit = allow_edit
            else:
                doc.append(
                    "states",
                    {
                        "state": state,
                        "doc_status": doc_status,
                        "update_field": definition["state_field"],
                        "update_value": state,
                        "allow_edit": allow_edit,
                    },
                )

        if definition["document_type"] == "Site Work Order":
            valid_transitions = []
            for row in doc.transitions:
                if (
                    row.state == "Approved"
                    and row.next_state == "Cancelled"
                ):
                    continue
                valid_transitions.append(row)
            doc.set("transitions", valid_transitions)

        for state, action, next_state, allowed, condition in definition["transitions"]:
            exists = False
            target_condition = _condition_key(condition)
            allow_self_approval = (
                (
                    definition["document_type"] == "Site Work Order"
                    and state == "Draft"
                    and action == "Submit"
                    and next_state == "Pending Stock Review"
                )
                or (
                    definition["document_type"] == "WMS Material Issue"
                    and state == "Draft"
                    and action == "Submit"
                    and next_state == "Issued"
                )
                or (
                    definition["document_type"] == "WMS Material Consumption"
                    and state == "Draft"
                    and action == "Submit"
                    and next_state in ["Pending Verification", "Consumed"]
                )
                or (
                    definition["document_type"] == "SNWO Material Transaction"
                    and state == "Draft"
                    and action == "Submit"
                    and next_state == "Submitted"
                )
            )

            for row in doc.transitions:
                if (
                    row.state == state
                    and row.action == action
                    and row.next_state == next_state
                    and row.allowed == allowed
                    and _condition_key(row.condition) == target_condition
                ):
                    exists = True
                    row.allow_self_approval = int(allow_self_approval)
                    break

            if not exists:
                doc.append(
                    "transitions",
                    {
                        "state": state,
                        "action": action,
                        "next_state": next_state,
                        "allowed": allowed,
                        "condition": condition,
                        "allow_self_approval": int(allow_self_approval),
                    },
                )

        doc.is_active = definition.get("is_active", 1)
        doc.save(ignore_permissions=True)


def ensure_wms_workflows():
    ensure_workflows()
