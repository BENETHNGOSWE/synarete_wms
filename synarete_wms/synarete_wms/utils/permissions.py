import frappe

from frappe.utils import cint


MANAGER_ROLES = {
    "System Manager",
    "Warehouse Manager",
    "Stock Manager",
}

ISSUE_ROLES = {
    "System Manager",
    "Warehouse Manager",
    "Stock Manager",
}

ENGINEER_ROLES = {
    "Stock User",
    "Employee",
    "WMS Engineer",
}

ISSUE_TRANSACTION_TYPES = {
    "Receive",
    "Issue",
    "MP Issue",
    "Interchange",
}


def _roles(user=None):
    return set(frappe.get_roles(user or frappe.session.user))


def _is_manager(user=None):
    return bool(_roles(user) & MANAGER_ROLES)


def can_issue_snwo_material(user=None):
    """Warehouse Manager / Stock Manager / System Manager may issue stock."""
    return bool(_roles(user) & ISSUE_ROLES)


def can_run_snwo_engineer_ops(user=None):
    """Create WOs, request, consume, complete. System Manager always can."""
    roles = _roles(user)
    if roles & {"System Manager"}:
        return True
    return bool(roles & ENGINEER_ROLES) or can_issue_snwo_material(user)


def current_employee(user=None):
    user = user or frappe.session.user
    employee = frappe.db.get_value(
        "Employee",
        {"user_id": user, "status": "Active"},
        "name",
    )
    if employee:
        return employee
    return frappe.db.get_value("Employee", {"user_id": user}, "name")


def _employee_condition(doctype, user=None):
    user = user or frappe.session.user
    if _is_manager(user):
        return ""

    employee = current_employee(user)
    if not employee:
        return "1=0"

    escaped = frappe.db.escape(employee)
    return f"`tab{doctype}`.engineer = {escaped}"


def site_work_order_permission_query(user=None):
    user = user or frappe.session.user

    if _is_manager(user):
        return ""

    conditions = []
    escaped_user = frappe.db.escape(user)
    conditions.append(f"`tabSite Work Order`.owner = {escaped_user}")
    conditions.append(f"`tabSite Work Order`.requested_by = {escaped_user}")

    employee = current_employee(user)
    if employee:
        conditions.append(
            f"`tabSite Work Order`.engineer = {frappe.db.escape(employee)}"
        )

    return "(" + " OR ".join(conditions) + ")"


def servicenow_work_order_permission_query(user=None):
    user = user or frappe.session.user

    if _is_manager(user):
        return ""

    conditions = []
    escaped_user = frappe.db.escape(user)
    conditions.append(f"`tabServiceNow Site Work Order`.owner = {escaped_user}")

    employee = current_employee(user)
    if employee:
        conditions.append(
            f"`tabServiceNow Site Work Order`.assigned_to = {frappe.db.escape(employee)}"
        )

    return "(" + " OR ".join(conditions) + ")"


def servicenow_work_order_has_permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user
    if _is_manager(user):
        return True
    if permission_type in ("create", "share"):
        return True
    if doc is None or isinstance(doc, str):
        return True
    if not getattr(doc, "name", None) or doc.is_new():
        return True
    if doc.owner == user:
        return True
    employee = current_employee(user)
    if employee and doc.assigned_to == employee:
        return True
    return False


def snwo_material_transaction_permission_query(user=None):
    user = user or frappe.session.user
    if _is_manager(user):
        return ""

    escaped_user = frappe.db.escape(user)
    conditions = [f"`tabSNWO Material Transaction`.owner = {escaped_user}"]
    employee = current_employee(user)
    assigned = f"`tabServiceNow Site Work Order`.owner = {escaped_user}"
    if employee:
        assigned += (
            f" OR `tabServiceNow Site Work Order`.assigned_to = {frappe.db.escape(employee)}"
        )
    wo_filter = (
        "SELECT name FROM `tabServiceNow Site Work Order` WHERE " + assigned
    )
    for field in (
        "original_work_order",
        "issued_to_work_order",
        "received_for_work_order",
    ):
        conditions.append(
            f"`tabSNWO Material Transaction`.{field} IN ({wo_filter})"
        )
    return "(" + " OR ".join(conditions) + ")"


def snwo_material_transaction_has_permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user
    if _is_manager(user):
        return True
    if permission_type in ("create", "share"):
        return True
    if doc is None or isinstance(doc, str):
        return True
    if not getattr(doc, "name", None) or doc.is_new():
        return True
    if doc.owner == user:
        return True
    employee = current_employee(user)
    for field in (
        "original_work_order",
        "issued_to_work_order",
        "received_for_work_order",
    ):
        work_order = getattr(doc, field, None)
        if not work_order:
            continue
        meta = frappe.db.get_value(
            "ServiceNow Site Work Order",
            work_order,
            ["owner", "assigned_to"],
            as_dict=True,
        )
        if not meta:
            continue
        if meta.owner == user or (employee and meta.assigned_to == employee):
            return True
    return False


def enforce_snwo_transaction_role(doc):
    """Engineers may request/consume/reconcile. Only warehouse roles may issue."""
    txn_type = doc.transaction_type
    if txn_type in ISSUE_TRANSACTION_TYPES and not can_issue_snwo_material():
        frappe.throw(
            "Only a Warehouse Manager can issue materials "
            f"({txn_type}). Request the material, then wait for warehouse to issue."
        )
    if txn_type == "MP Issue" or cint(getattr(doc, "is_mp_stock", 0)):
        if not can_issue_snwo_material():
            frappe.throw(
                "Only a Warehouse Manager can issue MP stock from the warehouse."
            )


def material_issue_permission_query(user=None):
    return _employee_condition("WMS Material Issue", user)


def material_consumption_permission_query(user=None):
    return _employee_condition("WMS Material Consumption", user)


def consignment_permission_query(user=None):
    return _employee_condition("Engineer Consignment", user)


def has_wms_permission(user=None):
    return bool(
        _roles(user)
        & {
            "Stock User",
            "Stock Manager",
            "Warehouse Manager",
            "WMS Viewer",
            "WMS Engineer",
            "System Manager",
        }
    )
