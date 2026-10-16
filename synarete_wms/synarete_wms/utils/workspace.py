import frappe


WORKSPACE_CONTENT = (
    '[{"type":"header","data":{"text":"<span class=\\"h4\\"><b>Warehouse Operations</b></span>","col":12}},'
    '{"type":"shortcut","data":{"shortcut_name":"WMS Site","col":3}},'
    '{"type":"shortcut","data":{"shortcut_name":"Site Work Order","col":3}},'
    '{"type":"shortcut","data":{"shortcut_name":"WMS Material Issue","col":3}},'
    '{"type":"shortcut","data":{"shortcut_name":"HTT Material Receipt","col":3}},'
    '{"type":"shortcut","data":{"shortcut_name":"Engineer Consignment","col":3}},'
    '{"type":"shortcut","data":{"shortcut_name":"Stock Taking Entry","col":3}},'
    '{"type":"header","data":{"text":"<span class=\\"h4\\"><b>ServiceNow Work Orders</b></span>","col":12}},'
    '{"type":"shortcut","data":{"shortcut_name":"ServiceNow Site Work Order","col":3}},'
    '{"type":"shortcut","data":{"shortcut_name":"SNWO Material Transaction","col":3}},'
    '{"type":"shortcut","data":{"shortcut_name":"Maintenance Partner","col":3}},'
    '{"type":"header","data":{"text":"<span class=\\"h4\\"><b>Reports</b></span>","col":12}},'
    '{"type":"shortcut","data":{"shortcut_name":"WMS Stock Summary","col":3}},'
    '{"type":"shortcut","data":{"shortcut_name":"HTT Material Dashboard","col":3}},'
    '{"type":"shortcut","data":{"shortcut_name":"Pending Material Return","col":3}},'
    '{"type":"shortcut","data":{"shortcut_name":"WMS Material Accountability Report","col":3}},'
    '{"type":"shortcut","data":{"shortcut_name":"WMS Site Material Balance","col":3}},'
    '{"type":"shortcut","data":{"shortcut_name":"SNWO Material Traceability","col":3}},'
    '{"type":"shortcut","data":{"shortcut_name":"SNWO MP Material Report","col":3}},'
    '{"type":"shortcut","data":{"shortcut_name":"SNWO Interchange Report","col":3}}]'
)

SNWO_DASHBOARD_CONTENT = (
    '[{"type":"header","data":{"text":"<span class=\\"h4\\"><b>ServiceNow</b></span>","col":12}},'
    '{"type":"shortcut","data":{"shortcut_name":"Open Dashboard","col":4}},'
    '{"type":"shortcut","data":{"shortcut_name":"ServiceNow Site Work Order","col":4}},'
    '{"type":"shortcut","data":{"shortcut_name":"SNWO Material Traceability","col":4}},'
    '{"type":"shortcut","data":{"shortcut_name":"SNWO MP Material Report","col":4}},'
    '{"type":"shortcut","data":{"shortcut_name":"Awaiting Material Issue","col":4}}]'
)

SNWO_DASHBOARD_SHORTCUTS = [
    {
        "label": "Open Dashboard",
        "type": "Page",
        "link_to": "snwo-overview",
        "icon": "dashboard",
    },
    {
        "label": "ServiceNow Site Work Order",
        "type": "DocType",
        "link_to": "ServiceNow Site Work Order",
        "icon": "list",
    },
    {
        "label": "SNWO Material Traceability",
        "type": "Report",
        "link_to": "SNWO Material Traceability",
        "icon": "table",
    },
    {
        "label": "SNWO MP Material Report",
        "type": "Report",
        "link_to": "SNWO MP Material Report",
        "icon": "table",
    },
    {
        "label": "Awaiting Material Issue",
        "type": "Report",
        "link_to": "SNWO Awaiting Material Issue",
        "icon": "list",
    },
]


def ensure_workspace():
    try:
        ensure_servicenow_dashboard_page()
        ensure_servicenow_dashboard_workspace()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "WMS ServiceNow dashboard workspace")

    if frappe.db.exists("Workspace", "Synarete WMS"):
        return

    frappe.get_doc(
        {
            "doctype": "Workspace",
            "name": "Synarete WMS",
            "title": "Synarete WMS",
            "label": "Synarete WMS",
            "module": "Synarete WMS",
            "public": 1,
            "is_hidden": 0,
            "content": WORKSPACE_CONTENT,
        }
    ).insert(ignore_permissions=True)


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

    workspace.module = "Synarete WMS"
    workspace.public = 1
    workspace.is_hidden = 0
    workspace.content = SNWO_DASHBOARD_CONTENT
    workspace.set("shortcuts", [])
    for shortcut in SNWO_DASHBOARD_SHORTCUTS:
        if shortcut["type"] == "Page" and not frappe.db.exists("Page", shortcut["link_to"]):
            continue
        if shortcut["type"] == "DocType" and not frappe.db.exists("DocType", shortcut["link_to"]):
            continue
        if shortcut["type"] == "Report" and not frappe.db.exists("Report", shortcut["link_to"]):
            continue
        workspace.append("shortcuts", shortcut)
    if workspace.is_new():
        workspace.insert(ignore_permissions=True)
    else:
        workspace.save(ignore_permissions=True)
