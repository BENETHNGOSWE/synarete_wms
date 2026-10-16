import frappe
from frappe.model.document import Document
from frappe.utils import cint

from synarete_wms.synarete_wms.utils.servicenow import (
    apply_awaiting_material,
    apply_derived_fields,
    derive_process_status,
    ensure_material_row_from_header,
)


class ServiceNowSiteWorkOrder(Document):
    @frappe.whitelist()
    def recalculate_quantities(self):
        from synarete_wms.synarete_wms.utils.servicenow import refresh_work_order_balances

        refresh_work_order_balances(self.name)
        return self.name

    def before_insert(self):
        apply_derived_fields(self)
        ensure_material_row_from_header(self)
        if not self.process_status:
            self.process_status = "Created"
        apply_awaiting_material(self)

    def after_insert(self):
        apply_awaiting_material(self)
        if self.meta.has_field("awaiting_warehouse_issue"):
            self.db_set(
                "awaiting_warehouse_issue",
                1 if cint(self.awaiting_warehouse_issue) else 0,
                update_modified=False,
            )

    def validate(self):
        apply_derived_fields(self)
        ensure_material_row_from_header(self)
        if not self.swo_number:
            frappe.throw("SWO Number is required.")
        if not self.site:
            frappe.throw("Site is required.")
        if self.process_status != "Completed" and not frappe.flags.in_migrate:
            self.process_status = derive_process_status(self)
        apply_awaiting_material(self)

    def on_update(self):
        # Original material request quantities are never deleted here.
        return
