import frappe
from frappe.model.document import Document

from synarete_wms.synarete_wms.utils.stock import (
    cancel_linked_stock_entry,
    create_material_transfer,
)


class EngineerConsignment(Document):
    def validate(self):
        if not self.items:
            frappe.throw("Add at least one consignment item.")

        for item in self.items:
            item.remaining_qty = max(
                0,
                item.allocated_qty - item.consumed_qty,
            )

    def on_submit(self):
        if self.stock_entry:
            return

        settings = frappe.get_single("WMS Settings")
        configured = {
            "main": settings.main_warehouse,
            "field_issued": settings.field_issued_warehouse,
        }

        items = []
        for item in self.items:
            items.append(
                {
                    "item_code": item.item_code,
                    "qty": item.allocated_qty,
                    "uom": item.uom,
                    "serial_no": item.serial_no,
                }
            )

        stock_entry = create_material_transfer(
            items=items,
            source_warehouse=configured["main"],
            target_warehouse=configured["field_issued"],
            company=settings.company,
            reference_doctype=self.doctype,
            reference_name=self.name,
            engineer=self.engineer,
        )

        self.db_set("stock_entry", stock_entry.name, update_modified=False)
        self.db_set("status", "Active")

    def on_cancel(self):
        cancel_linked_stock_entry(self.stock_entry)
        self.db_set("status", "Closed")
