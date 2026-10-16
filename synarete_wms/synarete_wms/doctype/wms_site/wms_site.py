import frappe
from frappe.model.document import Document


class WMSSite(Document):
    def validate(self):
        self.site_code = (self.site_code or "").strip().upper()
        self.site_name = (self.site_name or "").strip()

        if not self.site_code:
            frappe.throw("Site Code is required")

        if not self.site_name:
            frappe.throw("Site Name is required")
