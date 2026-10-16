from frappe.model.document import Document


class MonthlyServiceItem(Document):
    def validate(self):
        self.balance_qty = max(
            0,
            self.qty - self.issued_qty,
        )
