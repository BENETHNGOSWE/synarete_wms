import unittest
from datetime import date

from synarete_wms.synarete_wms.utils.htt_return_rules import (
    cycle_dates_for_completion,
    days_remaining,
    pending_return_qty,
    previous_month_range,
    return_status,
)


class TestHTTReturnRules(unittest.TestCase):
    def test_completion_month_deadlines_are_next_month(self):
        self.assertEqual(
            cycle_dates_for_completion(date(2026, 8, 31)),
            (date(2026, 9, 15), date(2026, 9, 25)),
        )

    def test_year_boundary(self):
        self.assertEqual(
            cycle_dates_for_completion(date(2026, 12, 30)),
            (date(2027, 1, 15), date(2027, 1, 25)),
        )

    def test_deadline_month_selects_prior_completion_month(self):
        self.assertEqual(
            previous_month_range(date(2026, 9, 1)),
            (date(2026, 8, 1), date(2026, 8, 31)),
        )
        self.assertEqual(
            previous_month_range(date(2027, 1, 20)),
            (date(2026, 12, 1), date(2026, 12, 31)),
        )

    def test_pending_and_no_grace_statuses(self):
        self.assertEqual(pending_return_qty(6, 2), 4)
        self.assertEqual(
            return_status(6, 2, date(2026, 9, 25), date(2026, 9, 25)),
            "Partially Returned",
        )
        self.assertEqual(
            return_status(6, 2, date(2026, 9, 25), date(2026, 9, 26)),
            "Overdue",
        )
        self.assertEqual(
            return_status(
                6,
                6,
                date(2026, 9, 25),
                date(2026, 9, 26),
                date(2026, 9, 25),
            ),
            "Returned",
        )
        self.assertEqual(
            return_status(
                6,
                6,
                date(2026, 9, 25),
                date(2026, 9, 26),
                date(2026, 9, 26),
            ),
            "Returned Late",
        )

    def test_days_remaining(self):
        self.assertEqual(
            days_remaining(date(2026, 9, 15), date(2026, 9, 1)),
            14,
        )
        self.assertEqual(
            days_remaining(date(2026, 9, 15), date(2026, 9, 16)),
            -1,
        )


if __name__ == "__main__":
    unittest.main()
