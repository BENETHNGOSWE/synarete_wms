from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


class TestSiteWorkOrder(FrappeTestCase):
    def test_outstanding_material_is_a_warning_not_a_blocker(self):
        work_order = frappe.get_doc(
            {
                "doctype": "Site Work Order",
                "title": "Outstanding material regression test",
                "site": "TEST-SITE",
                "work_type": "Corrective Maintenance",
                "engineer": "TEST-EMPLOYEE",
                "planned_date": "2026-08-24",
                "material_type": "MP",
                "status": "Pending Stock Review",
                "materials": [
                    {
                        "doctype": "Site Work Order Item",
                        "item_code": "TEST-ITEM",
                        "qty": 20,
                        "uom": "Nos",
                        "source_warehouse": "TEST-WAREHOUSE",
                        "material_type": "MP",
                    }
                ],
            }
        )

        with patch(
            "synarete_wms.synarete_wms.doctype.site_work_order.site_work_order.get_open_balance",
            return_value=30,
        ), patch("frappe.msgprint"):
            # This must not raise.  The Stock Manager handles the decision
            # to reuse outstanding stock when creating the Material Issue.
            work_order.validate()

        self.assertIn("request may still be submitted", work_order.outstanding_material_notice)
        self.assertIn("TEST-ITEM: 30.0 unit(s) outstanding", work_order.outstanding_material_notice)

    def test_approval_persists_default_and_reduced_approved_quantities(self):
        from synarete_wms.synarete_wms.utils.workflow_api import (
            _prepare_site_work_order_approval,
        )

        document = SimpleNamespace(
            materials=[
                SimpleNamespace(item_code="TEST-WMS-17", qty=10, approved_qty=0),
                SimpleNamespace(item_code="TEST-WMS-18", qty=8, approved_qty=5),
            ]
        )
        with patch("frappe.session") as session, patch(
            "synarete_wms.synarete_wms.utils.workflow_api.today",
            return_value="2026-09-01",
        ):
            session.user = "reviewer@example.test"
            _prepare_site_work_order_approval(document)

        self.assertEqual(document.materials[0].approved_qty, 10)
        self.assertEqual(document.materials[1].approved_qty, 5)
        self.assertEqual(document.reviewed_by, "reviewer@example.test")
        self.assertEqual(document.review_date, "2026-09-01")

    def test_approval_rejects_quantity_above_request(self):
        from synarete_wms.synarete_wms.utils.workflow_api import (
            _prepare_site_work_order_approval,
        )

        document = SimpleNamespace(
            materials=[
                SimpleNamespace(item_code="TEST-WMS-17", qty=5, approved_qty=6)
            ]
        )
        with patch("frappe.session") as session:
            session.user = "reviewer@example.test"
            with self.assertRaises(frappe.ValidationError):
                _prepare_site_work_order_approval(document)
