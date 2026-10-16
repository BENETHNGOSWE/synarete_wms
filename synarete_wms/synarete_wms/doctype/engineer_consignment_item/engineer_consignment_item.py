import frappe
from frappe.model.document import Document


class EngineerConsignmentItem(Document):
    def validate(self):
        if self.allocated_qty <= 0:
            frappe.throw("Allocated quantity must be greater than zero.")
        self.remaining_qty = max(
            0,
            self.allocated_qty - self.consumed_qty,
        )
