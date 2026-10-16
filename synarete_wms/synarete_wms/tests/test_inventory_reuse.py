from frappe.tests.utils import FrappeTestCase

from synarete_wms.synarete_wms.utils.accountability import compute_issue_split
from synarete_wms.synarete_wms.utils.inventory_reports import classify_movement


class TestInventoryReuse(FrappeTestCase):
    def test_reuse_covers_full_request(self):
        applied, additional = compute_issue_split(5, 6, True)
        self.assertEqual(applied, 5)
        self.assertEqual(additional, 0)

    def test_reuse_then_shortage_from_main(self):
        applied, additional = compute_issue_split(10, 6, True)
        self.assertEqual(applied, 6)
        self.assertEqual(additional, 4)

    def test_manager_can_skip_reuse(self):
        applied, additional = compute_issue_split(10, 6, False)
        self.assertEqual(applied, 0)
        self.assertEqual(additional, 10)

    def test_no_outstanding(self):
        applied, additional = compute_issue_split(10, 0, True)
        self.assertEqual(applied, 0)
        self.assertEqual(additional, 10)

    def test_transfer_is_not_consumption(self):
        warehouses = {"main": "Main", "field": "Field"}
        bucket, qty, _value = classify_movement(
            {
                "actual_qty": 10,
                "stock_value_difference": 100,
                "voucher_type": "Stock Entry",
                "stock_entry_purpose": "Material Transfer",
                "warehouse": "Field",
            },
            warehouses,
        )
        self.assertEqual(bucket, "to_field")
        self.assertEqual(qty, 10)

    def test_stock_entry_material_receipt_is_received(self):
        warehouses = {"main": "Main", "field": "Field"}
        bucket, qty, _value = classify_movement(
            {
                "actual_qty": 500,
                "stock_value_difference": 1000000,
                "voucher_type": "Stock Entry",
                "stock_entry_purpose": "Material Receipt",
                "warehouse": "Main",
            },
            warehouses,
        )
        self.assertEqual(bucket, "received")
        self.assertEqual(qty, 500)

    def test_material_issue_is_consumption(self):
        warehouses = {"main": "Main", "field": "Field"}
        bucket, qty, value = classify_movement(
            {
                "actual_qty": -4,
                "stock_value_difference": -40,
                "voucher_type": "Stock Entry",
                "stock_entry_purpose": "Material Issue",
                "warehouse": "Field",
            },
            warehouses,
        )
        self.assertEqual(bucket, "consumed")
        self.assertEqual(qty, -4)
        self.assertEqual(value, -40)
