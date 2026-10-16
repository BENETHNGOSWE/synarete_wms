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
            "Monthly Service Schedule",
            "Stock Taking Entry",
            "Delivery Note Signature",
        ]

        for doctype in doctypes:
            self.assertTrue(
                frappe.db.exists("DocType", doctype),
                f"Missing DocType: {doctype}",
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
