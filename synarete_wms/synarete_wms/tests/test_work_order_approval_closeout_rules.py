import unittest

from synarete_wms.synarete_wms.utils.qty_rules import (
    normalize_approved_quantity,
    site_work_order_issue_status_error,
    validate_closeout_quantities,
    validate_reconcile_quantity,
)


class TestWorkOrderApprovalAndCloseoutRules(unittest.TestCase):
    def test_blank_approval_defaults_to_requested_and_reduction_is_preserved(self):
        self.assertEqual(normalize_approved_quantity(10, 0), 10)
        self.assertEqual(normalize_approved_quantity(10, 7), 7)

    def test_approval_cannot_exceed_request_or_be_negative(self):
        with self.assertRaises(ValueError):
            normalize_approved_quantity(10, 11)
        with self.assertRaises(ValueError):
            normalize_approved_quantity(10, -1)

    def test_mp_issue_requires_approval_before_issue(self):
        self.assertIsNone(site_work_order_issue_status_error("Approved"))
        self.assertIsNone(site_work_order_issue_status_error("Issued"))
        self.assertIsNone(site_work_order_issue_status_error("In Progress"))
        self.assertIn(
            "must be approved",
            site_work_order_issue_status_error("Pending Stock Review"),
        )

    def test_reconcile_cannot_record_material_already_consumed(self):
        message = validate_reconcile_quantity(5, 0)
        self.assertIn("Use Consume", message)
        self.assertIsNone(validate_reconcile_quantity(3, 3))
        self.assertIn("only 2", validate_reconcile_quantity(3, 2))

    def test_fully_consumed_material_has_zero_unused_return(self):
        self.assertIsNone(
            validate_closeout_quantities(
                issued=5,
                used=5,
                returned_unused=0,
                previously_used=5,
                previously_returned=0,
            )
        )

    def test_closeout_cannot_reduce_a_real_prior_return(self):
        message = validate_closeout_quantities(
            issued=5,
            used=0,
            returned_unused=0,
            previously_returned=5,
        )
        self.assertIn("cumulative total", message)
        self.assertIn("correct the earlier return/reconciliation", message)


if __name__ == "__main__":
    unittest.main()
