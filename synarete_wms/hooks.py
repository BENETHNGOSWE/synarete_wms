app_name = "synarete_wms"
app_title = "Synarete WMS"
app_publisher = "Eveneth Beneth"
app_description = "Warehouse Management System for Synarete Engineering Limited"
app_email = "benethemmanueli1701@gmail.com"
app_license = "MIT"
app_version = "0.1.82"

required_apps = ["frappe", "erpnext", "hrms"]

app_include_js = [
    "/assets/synarete_wms/js/snwo_desk.js",
    "/assets/synarete_wms/js/snwo_overview.js",
]

# Register the Desk module after the WMS Site DocType exists.
# `config/desktop.py` supplies the module entry.

doctype_js = {
    "Delivery Note": "public/js/delivery_note.js",
    "Purchase Order": "public/js/purchase_order.js",
    "Asset": "public/js/asset.js",
    "Asset Movement": "public/js/asset_movement.js",
}

after_migrate = [
    "synarete_wms.synarete_wms.utils.setup.after_migrate",
]

# Standard DocType hooks are registered only for implemented modules.
# Stock handlers deliberately do not commit transactions themselves.
permission_query_conditions = {
    "Site Work Order": "synarete_wms.synarete_wms.utils.permissions.site_work_order_permission_query",
    "ServiceNow Site Work Order": "synarete_wms.synarete_wms.utils.permissions.servicenow_work_order_permission_query",
    "SNWO Material Transaction": "synarete_wms.synarete_wms.utils.permissions.snwo_material_transaction_permission_query",
    "WMS Material Issue": "synarete_wms.synarete_wms.utils.permissions.material_issue_permission_query",
    "WMS Material Consumption": "synarete_wms.synarete_wms.utils.permissions.material_consumption_permission_query",
    "Engineer Consignment": "synarete_wms.synarete_wms.utils.permissions.consignment_permission_query",
}

has_permission = {
    "ServiceNow Site Work Order": "synarete_wms.synarete_wms.utils.permissions.servicenow_work_order_has_permission",
    "SNWO Material Transaction": "synarete_wms.synarete_wms.utils.permissions.snwo_material_transaction_has_permission",
}

scheduler_events = {
    "daily": [
        "synarete_wms.synarete_wms.utils.alerts.send_low_stock_alerts",
        "synarete_wms.synarete_wms.utils.htt.flag_overdue_htt_materials",
        "synarete_wms.synarete_wms.utils.servicenow.update_days_open",
    ],
    "weekly": [
        "synarete_wms.synarete_wms.utils.alerts.send_pending_return_report",
    ],
    "monthly": [
        "synarete_wms.synarete_wms.utils.monthly.generate_monthly_suggestions",
        "synarete_wms.synarete_wms.utils.consignment.send_reconciliation_reminder",
    ],
}

doc_events = {
    "Purchase Receipt": {
        "on_submit": "synarete_wms.synarete_wms.utils.stock.on_purchase_receipt_submit",
    },
    "Delivery Note": {
        "before_submit": "synarete_wms.synarete_wms.utils.delivery.prevent_wms_delivery_note_submit",
        "on_submit": "synarete_wms.synarete_wms.utils.stock.on_delivery_note_submit",
        "on_cancel": "synarete_wms.synarete_wms.utils.stock.on_delivery_note_cancel",
    },
    "Stock Entry": {
        "on_submit": "synarete_wms.synarete_wms.utils.stock.on_stock_entry_submit",
        "on_cancel": "synarete_wms.synarete_wms.utils.stock.on_stock_entry_cancel",
    },
    "Asset Movement": {
        "on_submit": "synarete_wms.synarete_wms.utils.asset.on_asset_movement_submit",
    },
}

fixtures = []
