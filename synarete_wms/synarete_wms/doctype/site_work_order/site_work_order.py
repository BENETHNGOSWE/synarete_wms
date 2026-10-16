import frappe
from frappe.model.document import Document
from frappe.utils import flt, today

from synarete_wms.synarete_wms.utils.accountability import get_open_balance


class SiteWorkOrder(Document):
    def before_insert(self):
        if not self.requested_by:
            self.requested_by = frappe.session.user
        if not self.requested_on:
            self.requested_on = today()
        if not self.status:
            self.status = "Draft"

    def validate(self):
        if not self.materials:
            frappe.throw("Add at least one required material.")

        self._refresh_outstanding_material_notice()

        for row in self.materials:
            if row.qty <= 0:
                frappe.throw(
                    f"Required quantity must be greater than zero for {row.item_code}."
                )

            if not row.source_warehouse:
                frappe.throw(
                    f"Select a source warehouse for {row.item_code}."
                )

            if row.material_type and row.material_type not in ("MP", "HTT"):
                frappe.throw(
                    f"Invalid material type for {row.item_code}."
                )

    def _refresh_outstanding_material_notice(self):
        notices = []

        for row in self.materials:
            outstanding = flt(
                get_open_balance(
                    self.engineer,
                    row.item_code,
                )
            )
            if outstanding > 0:
                notices.append(
                    f"{row.item_code}: {outstanding} unit(s) outstanding"
                )

        if notices:
            # Outstanding material is a control warning, not a submission
            # blocker. Completing a work order also must not expense or
            # remove leftover Field Issued stock — it stays company inventory.
            prefix = (
                "Warning only — unused stock remains company inventory "
                "with this engineer after work-order completion. Return it "
                "to Main Warehouse or reuse it on a later work order. "
                if self.status == "Completed"
                else (
                    "Warning only — this request may still be submitted. "
                    "This engineer has previously issued material that is not "
                    "fully accounted for. The Stock Manager must review the "
                    "outstanding quantity before issuing new stock: "
                )
            )
            self.outstanding_material_notice = prefix + "; ".join(notices)
            frappe.msgprint(
                self.outstanding_material_notice,
                title="Outstanding Material Warning",
                indicator="orange",
                alert=True,
            )
        else:
            self.outstanding_material_notice = None

    def on_submit(self):
        if self.status == "Draft":
            self.db_set("status", "Pending Stock Review")
