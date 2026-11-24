"""Pure date and quantity rules for monthly HTT return reporting."""

from calendar import monthrange
from datetime import date, datetime, timedelta


def as_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def next_month(value):
    value = as_date(value)
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def cycle_dates_for_completion(completion_date):
    """Return the next-month report (15th) and return (25th) deadlines."""
    completed = as_date(completion_date)
    if not completed:
        return None, None
    deadline_month = next_month(completed)
    return (
        date(deadline_month.year, deadline_month.month, 15),
        date(deadline_month.year, deadline_month.month, 25),
    )


def previous_month_range(deadline_month):
    """The cycle month contains work orders completed in the prior month."""
    selected = as_date(deadline_month)
    month_start = date(selected.year, selected.month, 1)
    previous_month_last = month_start - timedelta(days=1)
    previous_month_first = date(
        previous_month_last.year,
        previous_month_last.month,
        1,
    )
    return previous_month_first, previous_month_last


def pending_return_qty(required_qty, returned_qty):
    return max(0.0, float(required_qty or 0) - float(returned_qty or 0))


def days_remaining(due_date, today_date):
    due = as_date(due_date)
    current = as_date(today_date)
    if not due or not current:
        return None
    return (due - current).days


def return_status(required_qty, returned_qty, due_date, today_date, last_return_date=None):
    required = float(required_qty or 0)
    returned = float(returned_qty or 0)
    pending = pending_return_qty(required, returned)
    due = as_date(due_date)
    current = as_date(today_date)
    last_return = as_date(last_return_date)

    if required <= 0:
        return "No HTT Quantity"
    if pending <= 0:
        if due and last_return and last_return > due:
            return "Returned Late"
        return "Returned"
    if due and current and current > due:
        return "Overdue"
    if returned > 0:
        return "Partially Returned"
    return "Pending"
