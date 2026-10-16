from frappe.model.document import Document
from frappe.utils import flt


class WMSMaterialAccountability(Document):
    def validate(self):
        # A target issue may be fulfilled partly or wholly with material
        # carried forward from an earlier issue.  Reallocated material is
        # deducted from the source accountability through transferred_out_qty.
        total_available = (
            flt(self.issued_qty)
            + flt(self.carried_forward_qty)
        )
        accounted = (
            flt(self.consumed_qty)
            + flt(self.returned_qty)
            + flt(self.transferred_out_qty)
        )
        self.outstanding_qty = max(0, total_available - accounted)

        if self.outstanding_qty <= 0:
            self.accountability_status = "Fully Accounted"
        elif accounted == 0:
            self.accountability_status = "Awaiting Consumption"
        else:
            self.accountability_status = "Partially Accounted"
