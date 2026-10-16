import frappe
from frappe.model.document import Document
from frappe.utils import today

from synarete_wms.synarete_wms.utils.stock import create_stock_reconciliation


class StockTakingEntry(Document):
    def before_insert(self):
        if not self.counted_by:
            self.counted_by = frappe.session.user
        if not self.count_date:
            self.count_date = today()
        if not self.status:
            self.status = "Draft"

    def validate(self):
        if not self.items:
            frappe.throw("Add at least one item to count.")

        for item in self.items:
            item.variance = item.physical_qty - item.system_qty

    def on_submit(self):
        if self.stock_reconciliation:
            return

        settings = frappe.get_single("WMS Settings")
        reconciliation = create_stock_reconciliation(
            warehouse=self.warehouse,
            items=[
                {
                    "item_code": item.item_code,
                    "physical_qty": item.physical_qty,
                }
                for item in self.items
            ],
            company=settings.company,
            posting_date=self.count_date,
            reference_name=self.name,
        )

        self.db_set("stock_reconciliation", reconciliation.name, update_modified=False)
        self.db_set("status", "Reconciled")
