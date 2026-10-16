import frappe
from frappe.model.document import Document
from frappe.utils import getdate, today


class MonthlyServiceSchedule(Document):
    def validate(self):
        if not self.items:
            frappe.throw("Add at least one monthly service material.")

        if self.month_year:
            self.month_year = getdate(self.month_year).replace(day=1)

        for item in self.items:
            if item.qty <= 0:
                frappe.throw(
                    f"Quantity must be greater than zero for {item.item_code}."
                )
            item.balance_qty = max(
                0,
                item.qty - item.issued_qty,
            )

    def on_submit(self):
        if self.status == "Draft":
            self.db_set("status", "Suggested")
