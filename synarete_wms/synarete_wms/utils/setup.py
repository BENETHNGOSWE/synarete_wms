import frappe


WMS_ROLES = [
    "Stock User",
    "Stock Manager",
    "Warehouse Manager",
    "WMS Viewer",
    "WMS Engineer",
]


def after_migrate():
    ensure_roles()
    ensure_custom_fields()
    ensure_snwo_engineer_link_permissions()
    ensure_snwo_status_and_list_sort()
    ensure_workflows()
    ensure_workspace()
    ensure_print_formats()
    ensure_maintenance_partners()
    refresh_snwo_quantities()


def refresh_snwo_quantities():
    if not frappe.db.exists("DocType", "ServiceNow Site Work Order"):
        return
    from synarete_wms.synarete_wms.utils.servicenow import refresh_work_order_balances

    names = frappe.get_all("ServiceNow Site Work Order", pluck="name")
    for name in names:
        try:
            refresh_work_order_balances(name)
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"SNWO qty refresh {name}")


def ensure_roles():
    for role_name in WMS_ROLES:
        if not frappe.db.exists("Role", role_name):
            frappe.get_doc(
                {
                    "doctype": "Role",
                    "role_name": role_name,
                    "desk_access": 1,
                }
            ).insert(ignore_permissions=True)


def ensure_snwo_engineer_link_permissions():
    """WMS Engineer must read Item/Site so Part Code and Site links work."""
    from frappe.permissions import add_permission, update_permission_property

    grants = [
        ("Item", ["read", "select", "export"]),
        ("WMS Site", ["read", "select"]),
        ("Maintenance Partner", ["read", "select"]),
        ("Employee", ["read", "select"]),
        ("UOM", ["read", "select"]),
        ("Warehouse", ["read", "select"]),
    ]
    for doctype, rights in grants:
        if not frappe.db.exists("DocType", doctype):
            continue
        try:
            add_permission(doctype, "WMS Engineer", 0)
            for right in rights:
                update_permission_property(
                    doctype, "WMS Engineer", 0, right, 1, validate=False
                )
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"WMS Engineer permission {doctype}",
            )
    frappe.clear_cache()


def ensure_snwo_status_and_list_sort():
    """Awaiting Material default, no New status, newest WO first in the list."""
    if not frappe.db.exists("DocType", "ServiceNow Site Work Order"):
        return

    options = (
        "Awaiting Material\nOpen\nWork in Progress\nPending\nOn Hold\n"
        "Resolved\nClosed Complete\nClosed Incomplete\nClosed Rejected\nCancelled"
    )
    fieldname = frappe.db.get_value(
        "DocField",
        {"parent": "ServiceNow Site Work Order", "fieldname": "status"},
        "name",
    )
    if fieldname:
        frappe.db.set_value("DocField", fieldname, "options", options, update_modified=False)
        frappe.db.set_value(
            "DocField", fieldname, "default", "Awaiting Material", update_modified=False
        )
    frappe.db.set_value(
        "DocType",
        "ServiceNow Site Work Order",
        {
            "sort_field": "creation",
            "sort_order": "DESC",
        },
        update_modified=False,
    )
    frappe.db.sql(
        """
        DELETE FROM `tabProperty Setter`
        WHERE doc_type = 'ServiceNow Site Work Order'
          AND field_name = 'status'
          AND property IN ('options', 'default')
        """
    )
    frappe.db.sql(
        """
        UPDATE `tabServiceNow Site Work Order`
        SET status = 'Awaiting Material'
        WHERE status = 'New'
        """
    )
    frappe.clear_cache(doctype="ServiceNow Site Work Order")


def ensure_workflows():
    required_doctypes = [
        "Site Work Order",
        "WMS Material Issue",
        "WMS Material Consumption",
    ]

    missing = []
    for doctype in required_doctypes:
        if not frappe.db.exists("DocType", doctype):
            missing.append(doctype)

    if missing:
        frappe.logger("synarete_wms").warning(
            "WMS workflows deferred; missing DocTypes: %s",
            ", ".join(missing),
        )
        return

    from synarete_wms.synarete_wms.utils.workflows import ensure_wms_workflows
    ensure_wms_workflows()


def ensure_workspace():
    from synarete_wms.synarete_wms.utils.workspace import ensure_workspace as _ensure_workspace
    try:
        _ensure_workspace()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "WMS workspace setup")


def ensure_print_formats():
    from synarete_wms.synarete_wms.utils.print_formats import ensure_print_formats as _ensure_print_formats
    _ensure_print_formats()


def ensure_maintenance_partners():
    from synarete_wms.synarete_wms.utils.servicenow import (
        ensure_maintenance_partners as _ensure_partners,
    )

    if not frappe.db.exists("DocType", "Maintenance Partner"):
        return
    _ensure_partners()


def ensure_custom_fields():
    from synarete_wms.synarete_wms.utils.custom_fields import CUSTOM_FIELDS
    from frappe.custom.doctype.custom_field.custom_field import (
        create_custom_fields,
    )

    create_custom_fields(CUSTOM_FIELDS, update=True)
    frappe.clear_cache()
