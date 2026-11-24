"""Pure quantity rules for PO receiving and work-order closeout (no Frappe)."""


def _num(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def remaining_qty(ordered, received):
    return max(0.0, _num(ordered) - _num(received))


def receive_status(ordered, received):
    ordered = _num(ordered)
    received = _num(received)
    if ordered <= 0:
        return "Open"
    if received <= 0:
        return "Open"
    if received + 1e-9 >= ordered:
        return "Completed"
    return "Partially Received"


def validate_batch_qty(batch_qty, outstanding, allow_over=False):
    batch_qty = _num(batch_qty)
    outstanding = _num(outstanding)
    if batch_qty <= 0:
        return "This batch quantity must be greater than zero."
    if not allow_over and batch_qty - outstanding > 1e-9:
        return (
            f"Cannot receive {batch_qty}: outstanding is {outstanding}. "
            "Over-receiving is not allowed."
        )
    return None


def expected_delivery(new_order_qty, previous_outstanding):
    new_order_qty = _num(new_order_qty)
    previous_outstanding = _num(previous_outstanding)
    return {
        "new_order_qty": new_order_qty,
        "previous_outstanding_qty": previous_outstanding,
        "total_expected_delivery": new_order_qty + previous_outstanding,
    }


def normalize_approved_quantity(requested, entered):
    """Use the requested qty when approval is left at zero; preserve reductions."""
    requested = _num(requested)
    entered = _num(entered)
    if requested <= 0:
        raise ValueError("Requested quantity must be greater than zero.")
    if entered < 0:
        raise ValueError("Approved quantity cannot be negative.")
    if entered <= 1e-9:
        return requested
    if entered - requested > 1e-9:
        raise ValueError(
            f"Approved quantity {entered} cannot exceed requested quantity {requested}."
        )
    return entered


def site_work_order_issue_status_error(status):
    """MP issue may proceed only after a Site Work Order is approved."""
    if (status or "") not in ("Approved", "Issued", "In Progress"):
        return (
            "The Site Work Order must be approved before MP material can be issued. "
            f"Current status: {status or 'not set'}."
        )
    return None


def validate_reconcile_quantity(quantity, remaining):
    """Reconcile only unused material that remains after consumption."""
    quantity = _num(quantity)
    remaining = _num(remaining)
    if quantity <= 0:
        return "Reconcile quantity must be greater than zero."
    if quantity - remaining > 1e-6:
        return (
            f"Cannot reconcile {quantity} as unused/returned: only {remaining} "
            "unconsumed issued quantity remains. Use Consume for material that was used."
        )
    return None


def validate_closeout_quantities(
    issued,
    used,
    returned_unused,
    previously_used=0,
    previously_returned=0,
):
    issued = _num(issued)
    used = _num(used)
    returned_unused = _num(returned_unused)
    previously_used = _num(previously_used)
    previously_returned = _num(previously_returned)

    if issued < 0 or used < 0 or returned_unused < 0:
        return "Used and returned quantities cannot be negative."
    if used + 1e-9 < previously_used:
        return (
            f"Used total {used} cannot be less than the previously consumed "
            f"total {previously_used}. Enter the cumulative used quantity."
        )
    if returned_unused + 1e-9 < previously_returned:
        return (
            f"Returned-unused total {returned_unused} cannot be less than the "
            f"previously recorded returned total {previously_returned}. Enter "
            "the cumulative total, or correct the earlier return/reconciliation "
            "record if it was entered in error."
        )
    accounted = used + returned_unused
    if accounted - issued > 1e-6:
        return (
            f"Used {used} + Returned unused {returned_unused} cannot exceed "
            f"Issued {issued}."
        )
    return None


def closeout_shortfall(issued, used, returned_unused):
    issued = _num(issued)
    accounted = _num(used) + _num(returned_unused)
    return max(0.0, issued - accounted)


def validate_closeout_shortfall_reason(issued, used, returned_unused, reason):
    shortfall = closeout_shortfall(issued, used, returned_unused)
    if shortfall > 1e-6 and not str(reason or "").strip():
        return (
            f"You accounted { _num(used) + _num(returned_unused) } of Issued "
            f"{_num(issued)}. Write a reason for the missing {shortfall}."
        )
    return None
