import frappe
from frappe.tests.utils import FrappeTestCase


class TestWMSSmoke(FrappeTestCase):
    def test_required_doctypes_exist(self):
        doctypes = [
            "WMS Settings",
            "WMS Site",
            "Site Work Order",
            "Maintenance Partner",
            "ServiceNow Site Work Order",
            "SNWO Material Transaction",
            "WMS Material Issue",
            "WMS Material Accountability",
            "WMS Material Allocation",
            "WMS Material Consumption",
            "HTT Material Receipt",
            "WMS HTT Transaction",
            "Engineer Consignment",
            "Material Return Record",
            "WMS PO Receive Batch",
            "WMS Material Closeout",
            "WMS HTT Return Batch",
            "WMS HTT Return Batch Item",
            "Monthly Service Schedule",
            "Stock Taking Entry",
            "Delivery Note Signature",
        ]

        for doctype in doctypes:
            self.assertTrue(
                frappe.db.exists("DocType", doctype),
                f"Missing DocType: {doctype}",
            )

        self.assertTrue(
            frappe.db.exists("Report", "HTT Monthly Return Tracker"),
            "Missing Report: HTT Monthly Return Tracker",
        )

    def test_htt_tracking_supports_both_work_order_types(self):
        issue_meta = frappe.get_meta("WMS Material Issue")
        return_item_meta = frappe.get_meta("WMS HTT Return Batch Item")
        self.assertIsNotNone(issue_meta.get_field("servicenow_work_order"))
        self.assertIsNotNone(return_item_meta.get_field("servicenow_work_order"))

    def test_site_work_order_list_uses_employee_name(self):
        field = frappe.get_meta("Site Work Order").get_field("engineer_name")
        self.assertIsNotNone(field)
        self.assertEqual(field.fetch_from, "engineer.employee_name")
        self.assertEqual(field.label, "Engineer Name")
        self.assertTrue(field.in_list_view)

    def test_site_work_order_review_and_issue_approval_fields(self):
        work_order_meta = frappe.get_meta("Site Work Order")
        self.assertIsNotNone(work_order_meta.get_field("reviewed_by"))
        self.assertIsNotNone(work_order_meta.get_field("review_date"))
        item_meta = frappe.get_meta("Site Work Order Item")
        self.assertIsNotNone(item_meta.get_field("approved_qty"))

    def test_closeout_reference_fields_match_their_doctypes(self):
        meta = frappe.get_meta("WMS Material Accountability")
        self.assertEqual(meta.get_field("last_return").options, "Material Return Record")
        self.assertEqual(meta.get_field("last_closeout").options, "WMS Material Closeout")

    def test_site_work_order_approve_transitions_cover_warehouse_roles(self):
        from synarete_wms.synarete_wms.utils.workflows import WORKFLOWS

        definition = next(
            item for item in WORKFLOWS if item["document_type"] == "Site Work Order"
        )
        allowed = {
            row[3]
            for row in definition["transitions"]
            if row[0] == "Pending Stock Review" and row[1] == "Approve"
        }
        self.assertEqual(
            allowed,
            {"Stock Manager", "Warehouse Manager", "System Manager"},
        )

    def test_wms_site_meta(self):
        meta = frappe.get_meta("WMS Site")
        self.assertIsNotNone(meta.get_field("site_code"))
        self.assertIsNotNone(meta.get_field("site_name"))
        self.assertIsNotNone(meta.get_field("status"))

    def test_wms_roles_exist_after_setup(self):
        for role in [
            "Stock User",
            "Stock Manager",
            "Warehouse Manager",
            "WMS Viewer",
        ]:
            self.assertTrue(
                frappe.db.exists("Role", role),
                f"Missing WMS role: {role}",
            )
