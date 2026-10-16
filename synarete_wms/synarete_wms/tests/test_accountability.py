import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt


class TestWMSAccountability(FrappeTestCase):
    def test_outstanding_calculation(self):
        doc = frappe.get_doc(
            {
                "doctype": "WMS Material Accountability",
                "material_issue": "TEST-ISSUE",
                "site": "TEST-SITE",
                "engineer": "TEST-EMPLOYEE",
                "item_code": "TEST-ITEM",
                "issued_qty": 30,
                "consumed_qty": 20,
                "returned_qty": 5,
            }
        )
        doc.validate()
        self.assertEqual(flt(doc.outstanding_qty), 5)
        self.assertEqual(doc.accountability_status, "Partially Accounted")

    def test_fully_accounted_calculation(self):
        doc = frappe.get_doc(
            {
                "doctype": "WMS Material Accountability",
                "material_issue": "TEST-ISSUE",
                "site": "TEST-SITE",
                "engineer": "TEST-EMPLOYEE",
                "item_code": "TEST-ITEM",
                "issued_qty": 30,
                "consumed_qty": 20,
                "returned_qty": 10,
            }
        )
        doc.validate()
        self.assertEqual(flt(doc.outstanding_qty), 0)
        self.assertEqual(doc.accountability_status, "Fully Accounted")

    def test_carried_forward_quantity_is_accounted(self):
        doc = frappe.get_doc(
            {
                "doctype": "WMS Material Accountability",
                "material_issue": "TEST-ISSUE",
                "site": "TEST-SITE",
                "engineer": "TEST-EMPLOYEE",
                "item_code": "TEST-ITEM",
                "issued_qty": 0,
                "carried_forward_qty": 30,
                "consumed_qty": 20,
                "returned_qty": 0,
            }
        )
        doc.validate()
        self.assertEqual(flt(doc.outstanding_qty), 10)
        self.assertEqual(doc.accountability_status, "Partially Accounted")

    def test_reallocated_quantity_closes_source_balance(self):
        doc = frappe.get_doc(
            {
                "doctype": "WMS Material Accountability",
                "material_issue": "TEST-ISSUE",
                "site": "TEST-SITE",
                "engineer": "TEST-EMPLOYEE",
                "item_code": "TEST-ITEM",
                "issued_qty": 30,
                "transferred_out_qty": 30,
            }
        )
        doc.validate()
        self.assertEqual(flt(doc.outstanding_qty), 0)
        self.assertEqual(doc.accountability_status, "Fully Accounted")
