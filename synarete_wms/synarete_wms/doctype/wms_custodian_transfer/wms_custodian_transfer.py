import frappe
from frappe.model.document import Document
from frappe.utils import flt, today

from synarete_wms.synarete_wms.utils.accountability import transfer_custodian


class WMSCustodianTransfer(Document):
    def before_insert(self):
        if not self.transfer_date:
            self.transfer_date = today()
        if not self.status:
            self.status = "Draft"

    def validate(self):
        if flt(self.qty) <= 0:
            frappe.throw("Transfer quantity must be greater than zero.")
        if self.source_engineer == self.target_engineer and not self.site:
            frappe.throw("Choose a different engineer or a different target site.")

        source = frappe.get_doc(
            "WMS Material Accountability",
            self.source_accountability,
        )
        if source.engineer != self.source_engineer:
            frappe.throw("Source Accountability does not belong to the From Engineer.")
        if source.item_code != self.item_code:
            frappe.throw("Item must match the Source Accountability.")
        if flt(self.qty) > flt(source.outstanding_qty):
            frappe.throw(
                f"Transfer quantity exceeds outstanding {source.outstanding_qty} "
                f"for {source.item_code}."
            )
        if not self.site:
            self.site = source.site

    def on_submit(self):
        transfer_custodian(
            self.source_accountability,
            self.target_engineer,
            self.site,
            self.qty,
            transfer_name=self.name,
        )
        self.db_set("status", "Transferred")

    def on_cancel(self):
        frappe.throw(
            "Cancel is not supported for custodian transfers. "
            "Create a reverse transfer from the receiving engineer."
        )
