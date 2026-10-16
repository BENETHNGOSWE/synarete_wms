from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


class TestHTTMaterialIssue(FrappeTestCase):
    def test_htt_dispatch_quantity_is_preserved(self):
        issue = frappe.get_doc(
            {
                "doctype": "WMS Material Issue",
                "site": "TEST-SITE",
                "customer": "TEST-CUSTOMER",
                "htt_receipt": "TEST-HTT-RECEIPT",
                "material_type": "HTT",
                "items": [
                    {
                        "doctype": "WMS Material Issue Item",
                        "item_code": "TEST-HTT-ITEM",
                        "material_type": "HTT",
                        "qty": 7,
                    }
                ],
            }
        )

        with patch(
            "synarete_wms.synarete_wms.doctype.wms_material_issue.wms_material_issue.frappe.db.get_value",
            return_value="Voice of Customer",
        ):
            issue.validate()

        self.assertEqual(issue.items[0].qty, 7)
        self.assertEqual(issue.items[0].requested_qty, 7)
        self.assertEqual(issue.items[0].approved_qty, 7)
        self.assertEqual(issue.items[0].fulfilled_qty, 7)
        self.assertEqual(issue.items[0].warehouse_stock_qty, 0)
