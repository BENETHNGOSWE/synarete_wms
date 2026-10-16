import frappe
from frappe.model.document import Document
from frappe.utils import today


class HTTMaterialReceipt(Document):
    def before_insert(self):
        if not self.received_by:
            self.received_by = frappe.session.user
        if not self.receipt_date:
            self.receipt_date = today()
        if not self.dispatch_status:
            self.dispatch_status = "Pending"

    def validate(self):
        if not self.items:
            frappe.throw("Add at least one HTT material item.")

        for item in self.items:
            if item.qty <= 0:
                frappe.throw(
                    f"Quantity must be greater than zero for {item.item_code}."
                )

    def on_submit(self):
        existing = frappe.get_all(
            "WMS HTT Transaction",
            filters={
                "htt_receipt": self.name,
                "transaction_type": "Receipt",
                "is_cancelled": 0,
            },
            pluck="name",
        )

        if existing:
            return

        for item in self.items:
            frappe.get_doc(
                {
                    "doctype": "WMS HTT Transaction",
                    "transaction_type": "Receipt",
                    "posting_date": self.receipt_date,
                    "customer": self.customer,
                    "site": self.target_site,
                    "engineer": self.related_engineer,
                    "item_code": item.item_code,
                    "qty": item.qty,
                    "uom": item.uom,
                    "serial_no": item.serial_no,
                    "htt_receipt": self.name,
                    "is_cancelled": 0,
                }
            ).insert(ignore_permissions=True)

    def on_cancel(self):
        transactions = frappe.get_all(
            "WMS HTT Transaction",
            filters={"htt_receipt": self.name, "is_cancelled": 0},
            pluck="name",
        )

        for transaction_name in transactions:
            frappe.db.set_value(
                "WMS HTT Transaction",
                transaction_name,
                "is_cancelled",
                1,
                update_modified=True,
            )
