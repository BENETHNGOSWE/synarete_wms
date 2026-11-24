import json

import frappe
from frappe.tests.utils import FrappeTestCase


class TestWorkspaceNavigation(FrappeTestCase):
    def _workspace_shortcut_labels(self, name):
        workspace = frappe.get_doc("Workspace", name)
        content = json.loads(workspace.content or "[]")
        return {
            block.get("data", {}).get("shortcut_name")
            for block in content
            if isinstance(block, dict) and block.get("type") == "shortcut"
        }

    def _workspace_headings(self, name):
        workspace = frappe.get_doc("Workspace", name)
        content = json.loads(workspace.content or "[]")
        return {
            block.get("data", {}).get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "header"
        }

    def _workspace_targets(self, name):
        workspace = frappe.get_doc("Workspace", name)
        return {(row.type, row.link_to) for row in workspace.shortcuts}

    def test_servicenow_workspace_has_operations_and_reports(self):
        self.assertTrue(frappe.db.exists("Workspace", "ServiceNow Dashboard"))
        labels = self._workspace_shortcut_labels("ServiceNow Dashboard")
        for label in (
            "Open Dashboard",
            "ServiceNow Site Work Order",
            "SNWO Material Transaction",
            "Maintenance Partner",
            "WMS Material Issue",
            "WMS Material Closeout",
            "HTT Material Receipt",
            "WMS HTT Return Batch",
            "Awaiting Material Issue",
            "SNWO Material Traceability",
            "SNWO Material Lifecycle",
            "SNWO Interchange Report",
            "SNWO MP Material Report",
            "HTT Monthly Return Tracker",
        ):
            self.assertIn(label, labels)
        targets = self._workspace_targets("ServiceNow Dashboard")
        self.assertIn(("DocType", "ServiceNow Site Work Order"), targets)
        self.assertIn(("Report", "SNWO Material Lifecycle"), targets)
        headings = self._workspace_headings("ServiceNow Dashboard")
        self.assertTrue(all("padding-bottom: 8px" in value for value in headings))
        self.assertTrue(any("ServiceNow" in value for value in headings))
        self.assertTrue(any("Reports" in value for value in headings))

    def test_wms_workspace_has_grouped_all_report_links(self):
        self.assertTrue(frappe.db.exists("Workspace", "Synarete WMS"))
        labels = self._workspace_shortcut_labels("Synarete WMS")
        reports = {
            "WMS Asset Movement Report",
            "Engineer Consignment Report",
            "HTT Material Dashboard",
            "HTT Monthly Return Tracker",
            "WMS Material Consumption Report",
            "Pending Material Return",
            "WMS Site Material Balance",
            "Site Material Issue Report",
            "SNWO Awaiting Material Issue",
            "SNWO Interchange Report",
            "SNWO Material Lifecycle",
            "SNWO Material Traceability",
            "SNWO MP Material Report",
            "WMS Stock Taking Report",
            "Supplier Delivery Progress",
            "Supplier Outstanding Items",
            "WMS Engineer and Site Stock",
            "WMS Inventory Movement",
            "WMS Inventory Valuation",
            "WMS Material Accountability Report",
            "WMS Monthly Inventory Summary",
            "WMS Stock Reconciliation Exceptions",
            "WMS Stock Summary",
            "WMS Work Order Material Cost",
        }
        self.assertTrue(reports.issubset(labels), f"Missing report links: {reports - labels}")
        for label in (
            "WMS Site",
            "Site Work Order",
            "WMS Material Issue",
            "WMS Material Closeout",
            "HTT Material Receipt",
            "WMS HTT Return Batch",
            "ServiceNow Site Work Order",
        ):
            self.assertIn(label, labels)
        targets = self._workspace_targets("Synarete WMS")
        self.assertIn(("Report", "WMS Stock Summary"), targets)
        self.assertIn(("DocType", "Site Work Order"), targets)
        headings = self._workspace_headings("Synarete WMS")
        self.assertTrue(all("padding-bottom: 8px" in value for value in headings))
        for category in (
            "Warehouse Operations",
            "HTT & Engineer Operations",
            "ServiceNow Work Orders",
            "Reports",
            "Stock & Inventory",
            "Work Orders & Materials",
            "HTT & Consignment Reports",
            "ServiceNow Reports",
            "Purchasing & Suppliers",
        ):
            self.assertTrue(
                any(category in value for value in headings),
                f"Missing workspace category: {category}",
            )
