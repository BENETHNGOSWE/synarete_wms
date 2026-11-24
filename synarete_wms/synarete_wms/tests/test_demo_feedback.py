import unittest

from synarete_wms.synarete_wms.utils.qty_rules import (
    expected_delivery,
    receive_status,
    remaining_qty,
    validate_batch_qty,
    validate_closeout_quantities,
    validate_closeout_shortfall_reason,
)


class TestDemoFeedbackRules(unittest.TestCase):
    def test_partial_then_complete_receive(self):
        self.assertEqual(remaining_qty(10, 5), 5)
        self.assertEqual(receive_status(10, 5), "Partially Received")
        self.assertEqual(remaining_qty(10, 10), 0)
        self.assertEqual(receive_status(10, 10), "Completed")

    def test_over_receive_blocked(self):
        self.assertIsNotNone(validate_batch_qty(6, 5, allow_over=False))
        self.assertIsNone(validate_batch_qty(5, 5, allow_over=False))
        self.assertIsNone(validate_batch_qty(6, 5, allow_over=True))

    def test_previous_outstanding_not_merged_into_new_po(self):
        summary = expected_delivery(10, 3)
        self.assertEqual(summary["new_order_qty"], 10)
        self.assertEqual(summary["previous_outstanding_qty"], 3)
        self.assertEqual(summary["total_expected_delivery"], 13)

    def test_closeout_must_balance(self):
        self.assertIsNone(validate_closeout_quantities(3, 2, 1))
        self.assertIsNone(validate_closeout_quantities(3, 3, 0))
        self.assertIsNone(validate_closeout_quantities(3, 0, 3))
        self.assertIsNone(validate_closeout_quantities(10, 6, 0))
        self.assertIsNotNone(validate_closeout_quantities(3, 4, 0))
        self.assertIsNotNone(
            validate_closeout_quantities(10, 5, 4, previously_used=6)
        )
        self.assertIsNotNone(validate_closeout_shortfall_reason(10, 6, 0, ""))
        self.assertIsNone(
            validate_closeout_shortfall_reason(10, 6, 0, "Damaged units still on site")
        )


if __name__ == "__main__":
    unittest.main()
