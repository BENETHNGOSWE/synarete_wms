import frappe


DEFAULT_ROLES = ["Stock User", "Stock Manager", "Warehouse Manager", "WMS Viewer"]


def get_settings():
    return frappe.get_single("WMS Settings")


def get_active_employee(user=None):
    user = user or frappe.session.user
    return frappe.db.get_value(
        "Employee",
        {"user_id": user, "status": "Active"},
        "name",
    )


def get_user_roles(user=None):
    user = user or frappe.session.user
    return set(frappe.get_roles(user))


def has_any_role(roles, user=None):
    return bool(get_user_roles(user) & set(roles))


def require_any_role(roles, user=None):
    if not has_any_role(roles, user):
        frappe.throw(
            "You do not have permission for this WMS operation."
        )


def get_warehouse(name):
    if not name:
        return None
    if not frappe.db.exists("Warehouse", name):
        frappe.throw(f"Warehouse does not exist: {name}")
    return name


def get_configured_warehouses():
    settings = get_settings()
    return {
        "main": get_warehouse(settings.main_warehouse),
        "field_issued": get_warehouse(settings.field_issued_warehouse),
    }
