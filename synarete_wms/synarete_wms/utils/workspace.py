import json

import frappe


# Workspaces are refreshed after migrate so users can discover the main WMS and
# ServiceNow actions without having to remember DocType or report names.
WMS_WORKSPACE_SECTIONS = [
    (
        "Warehouse Operations",
        [
            {"label": "WMS Site", "type": "DocType", "link_to": "WMS Site", "icon": "list"},
            {"label": "Site Work Order", "type": "DocType", "link_to": "Site Work Order", "icon": "list"},
            {"label": "WMS Material Issue", "type": "DocType", "link_to": "WMS Material Issue", "icon": "list"},
            {"label": "WMS Material Consumption", "type": "DocType", "link_to": "WMS Material Consumption", "icon": "list"},
            {"label": "WMS Material Closeout", "type": "DocType", "link_to": "WMS Material Closeout", "icon": "list"},
            {"label": "Material Return Record", "type": "DocType", "link_to": "Material Return Record", "icon": "list"},
            {"label": "WMS Material Allocation", "type": "DocType", "link_to": "WMS Material Allocation", "icon": "list"},
            {"label": "WMS Custodian Transfer", "type": "DocType", "link_to": "WMS Custodian Transfer", "icon": "list"},
            {"label": "WMS PO Receive Batch", "type": "DocType", "link_to": "WMS PO Receive Batch", "icon": "list"},
            {"label": "Stock Taking Entry", "type": "DocType", "link_to": "Stock Taking Entry", "icon": "list"},
            {"label": "WMS Settings", "type": "DocType", "link_to": "WMS Settings", "icon": "list"},
        ],
    ),
    (
        "HTT & Engineer Operations",
        [
            {"label": "HTT Material Receipt", "type": "DocType", "link_to": "HTT Material Receipt", "icon": "list"},
            {"label": "WMS HTT Return Batch", "type": "DocType", "link_to": "WMS HTT Return Batch", "icon": "list"},
            {"label": "WMS HTT Transaction", "type": "DocType", "link_to": "WMS HTT Transaction", "icon": "list"},
            {"label": "Engineer Consignment", "type": "DocType", "link_to": "Engineer Consignment", "icon": "list"},
        ],
    ),
    (
        "ServiceNow Work Orders",
        [
            {"label": "Open Dashboard", "type": "Page", "link_to": "snwo-overview", "icon": "dashboard"},
            {"label": "ServiceNow Site Work Order", "type": "DocType", "link_to": "ServiceNow Site Work Order", "icon": "list"},
            {"label": "SNWO Material Transaction", "type": "DocType", "link_to": "SNWO Material Transaction", "icon": "list"},
            {"label": "Maintenance Partner", "type": "DocType", "link_to": "Maintenance Partner", "icon": "list"},
        ],
    ),
    ("Reports", []),
    (
        "Stock & Inventory",
        [
            {"label": "WMS Stock Summary", "type": "Report", "link_to": "WMS Stock Summary", "icon": "table"},
            {"label": "WMS Inventory Movement", "type": "Report", "link_to": "WMS Inventory Movement", "icon": "table"},
            {"label": "WMS Inventory Valuation", "type": "Report", "link_to": "WMS Inventory Valuation", "icon": "table"},
            {"label": "WMS Monthly Inventory Summary", "type": "Report", "link_to": "WMS Monthly Inventory Summary", "icon": "table"},
            {"label": "WMS Stock Taking Report", "type": "Report", "link_to": "WMS Stock Taking Report", "icon": "table"},
            {"label": "WMS Stock Reconciliation Exceptions", "type": "Report", "link_to": "WMS Stock Reconciliation Exceptions", "icon": "table"},
            {"label": "WMS Asset Movement Report", "type": "Report", "link_to": "WMS Asset Movement Report", "icon": "table"},
            {"label": "WMS Engineer and Site Stock", "type": "Report", "link_to": "WMS Engineer and Site Stock", "icon": "table"},
        ],
    ),
    (
        "Work Orders & Materials",
        [
            {"label": "Site Material Issue Report", "type": "Report", "link_to": "Site Material Issue Report", "icon": "table"},
            {"label": "WMS Material Accountability Report", "type": "Report", "link_to": "WMS Material Accountability Report", "icon": "table"},
            {"label": "WMS Site Material Balance", "type": "Report", "link_to": "WMS Site Material Balance", "icon": "table"},
            {"label": "WMS Material Consumption Report", "type": "Report", "link_to": "WMS Material Consumption Report", "icon": "table"},
            {"label": "WMS Work Order Material Cost", "type": "Report", "link_to": "WMS Work Order Material Cost", "icon": "table"},
            {"label": "Pending Material Return", "type": "Report", "link_to": "Pending Material Return", "icon": "table"},
        ],
    ),
    (
        "HTT & Consignment Reports",
        [
            {"label": "HTT Material Dashboard", "type": "Report", "link_to": "HTT Material Dashboard", "icon": "table"},
            {"label": "HTT Monthly Return Tracker", "type": "Report", "link_to": "HTT Monthly Return Tracker", "icon": "table"},
            {"label": "Engineer Consignment Report", "type": "Report", "link_to": "Engineer Consignment Report", "icon": "table"},
        ],
    ),
    (
        "ServiceNow Reports",
        [
            {"label": "SNWO Awaiting Material Issue", "type": "Report", "link_to": "SNWO Awaiting Material Issue", "icon": "table"},
            {"label": "SNWO Material Traceability", "type": "Report", "link_to": "SNWO Material Traceability", "icon": "table"},
            {"label": "SNWO Material Lifecycle", "type": "Report", "link_to": "SNWO Material Lifecycle", "icon": "table"},
            {"label": "SNWO Interchange Report", "type": "Report", "link_to": "SNWO Interchange Report", "icon": "table"},
            {"label": "SNWO MP Material Report", "type": "Report", "link_to": "SNWO MP Material Report", "icon": "table"},
        ],
    ),
    (
        "Purchasing & Suppliers",
        [
            {"label": "Supplier Delivery Progress", "type": "Report", "link_to": "Supplier Delivery Progress", "icon": "table"},
            {"label": "Supplier Outstanding Items", "type": "Report", "link_to": "Supplier Outstanding Items", "icon": "table"},
        ],
    ),
]


SNWO_DASHBOARD_SECTIONS = [
    (
        "ServiceNow",
        [
            {"label": "Open Dashboard", "type": "Page", "link_to": "snwo-overview", "icon": "dashboard"},
            {"label": "ServiceNow Site Work Order", "type": "DocType", "link_to": "ServiceNow Site Work Order", "icon": "list"},
            {"label": "SNWO Material Transaction", "type": "DocType", "link_to": "SNWO Material Transaction", "icon": "list"},
            {"label": "Maintenance Partner", "type": "DocType", "link_to": "Maintenance Partner", "icon": "list"},
        ],
    ),
    (
        "Related Warehouse Actions",
        [
            {"label": "WMS Material Issue", "type": "DocType", "link_to": "WMS Material Issue", "icon": "list"},
            {"label": "WMS Material Closeout", "type": "DocType", "link_to": "WMS Material Closeout", "icon": "list"},
            {"label": "HTT Material Receipt", "type": "DocType", "link_to": "HTT Material Receipt", "icon": "list"},
            {"label": "WMS HTT Return Batch", "type": "DocType", "link_to": "WMS HTT Return Batch", "icon": "list"},
        ],
    ),
    ("Reports", []),
    (
        "ServiceNow Reports",
        [
            {"label": "Awaiting Material Issue", "type": "Report", "link_to": "SNWO Awaiting Material Issue", "icon": "table"},
            {"label": "SNWO Material Traceability", "type": "Report", "link_to": "SNWO Material Traceability", "icon": "table"},
            {"label": "SNWO Material Lifecycle", "type": "Report", "link_to": "SNWO Material Lifecycle", "icon": "table"},
            {"label": "SNWO Interchange Report", "type": "Report", "link_to": "SNWO Interchange Report", "icon": "table"},
            {"label": "SNWO MP Material Report", "type": "Report", "link_to": "SNWO MP Material Report", "icon": "table"},
        ],
    ),
    (
        "HTT Return Tracking",
        [
            {"label": "HTT Monthly Return Tracker", "type": "Report", "link_to": "HTT Monthly Return Tracker", "icon": "table"},
        ],
    ),
]


def ensure_workspace():
    """Create or refresh the WMS workspaces and their discoverable navigation links."""
    try:
        ensure_servicenow_dashboard_page()
        ensure_servicenow_dashboard_workspace()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "WMS ServiceNow dashboard workspace")

    ensure_wms_workspace()


def _target_exists(shortcut):
    target_type = shortcut.get("type")
    target = shortcut.get("link_to")
    if not target_type or not target:
        return False
    if target_type == "DocType":
        return bool(frappe.db.exists("DocType", target))
    if target_type == "Report":
        return bool(frappe.db.exists("Report", target))
    if target_type == "Page":
        return bool(frappe.db.exists("Page", target))
    return False


def _workspace_content(sections):
    content = []
    for heading, shortcuts in sections:
        content.append(
            {
                "type": "header",
                "data": {
                    "text": f'<div style="padding-bottom: 8px;"><span class="h4"><b>{heading}</b></span></div>',
                    "col": 12,
                },
            }
        )
        for shortcut in shortcuts:
            if _target_exists(shortcut):
                content.append(
                    {
                        "type": "shortcut",
                        "data": {
                            "shortcut_name": shortcut["label"],
                            "col": shortcut.get("col", 4),
                        },
                    }
                )
    return json.dumps(content)


def _set_workspace_shortcuts(workspace, sections):
    workspace.set("shortcuts", [])
    seen = set()
    for _heading, shortcuts in sections:
        for shortcut in shortcuts:
            key = (shortcut.get("type"), shortcut.get("link_to"))
            if key in seen or not _target_exists(shortcut):
                continue
            seen.add(key)
            workspace.append(
                "shortcuts",
                {
                    "label": shortcut["label"],
                    "type": shortcut["type"],
                    "link_to": shortcut["link_to"],
                    "icon": shortcut.get("icon", "list"),
                },
            )


def ensure_wms_workspace():
    if frappe.db.exists("Workspace", "Synarete WMS"):
        workspace = frappe.get_doc("Workspace", "Synarete WMS")
    else:
        workspace = frappe.new_doc("Workspace")
        workspace.name = "Synarete WMS"
        workspace.title = "Synarete WMS"
        workspace.label = "Synarete WMS"
        workspace.module = "Synarete WMS"
        workspace.public = 1
        workspace.is_hidden = 0

    workspace.title = "Synarete WMS"
    workspace.label = "Synarete WMS"
    workspace.module = "Synarete WMS"
    workspace.public = 1
    workspace.is_hidden = 0
    workspace.content = _workspace_content(WMS_WORKSPACE_SECTIONS)
    _set_workspace_shortcuts(workspace, WMS_WORKSPACE_SECTIONS)
    if workspace.is_new():
        workspace.insert(ignore_permissions=True)
    else:
        workspace.save(ignore_permissions=True)


def ensure_servicenow_dashboard_page():
    if frappe.db.exists("Page", "snwo-overview"):
        return
    page = frappe.get_doc(
        {
            "doctype": "Page",
            "page_name": "snwo-overview",
            "title": "ServiceNow Dashboard",
            "module": "Synarete WMS",
            "standard": "Yes",
        }
    )
    for role in (
        "System Manager",
        "Stock Manager",
        "Warehouse Manager",
        "WMS Viewer",
        "Stock User",
    ):
        page.append("roles", {"role": role})
    page.insert(ignore_permissions=True)


def ensure_servicenow_dashboard_workspace():
    if frappe.db.exists("Workspace", "ServiceNow Dashboard"):
        workspace = frappe.get_doc("Workspace", "ServiceNow Dashboard")
    else:
        workspace = frappe.new_doc("Workspace")
        workspace.name = "ServiceNow Dashboard"
        workspace.title = "ServiceNow Dashboard"
        workspace.label = "ServiceNow Dashboard"
        workspace.module = "Synarete WMS"
        workspace.public = 1
        workspace.is_hidden = 0

    workspace.title = "ServiceNow Dashboard"
    workspace.label = "ServiceNow Dashboard"
    workspace.module = "Synarete WMS"
    workspace.public = 1
    workspace.is_hidden = 0
    workspace.content = _workspace_content(SNWO_DASHBOARD_SECTIONS)
    _set_workspace_shortcuts(workspace, SNWO_DASHBOARD_SECTIONS)
    if workspace.is_new():
        workspace.insert(ignore_permissions=True)
    else:
        workspace.save(ignore_permissions=True)
