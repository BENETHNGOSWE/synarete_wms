import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, today


class DeliveryNoteSignature(Document):
    def before_insert(self):
        if not self.issue_date:
            self.issue_date = today()
        if not self.warehouse_officer:
            self.warehouse_officer = frappe.session.user
        if not self.status:
            self.status = "Pending"

    def validate(self):
        if not self.delivery_note and not self.material_issue:
            frappe.throw("Link the signature to a Delivery Note or WMS Material Issue.")

        if self.status == "Signed" and not self.signature:
            frappe.throw("A signature is required before marking Signed.")

    def mark_signed(self):
        self.status = "Signed"
        self.signed_at = now_datetime()
        self.receiving_date = today()
        self.save(ignore_permissions=True)

        if self.delivery_note:
            frappe.db.set_value(
                "Delivery Note",
                self.delivery_note,
                "custom_wms_signature_status",
                "Signed",
                update_modified=True,
            )
