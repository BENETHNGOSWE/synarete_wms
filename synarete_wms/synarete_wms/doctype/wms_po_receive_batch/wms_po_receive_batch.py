import frappe
from frappe.model.document import Document
from frappe.utils import flt, today


class WMSPOReceiveBatch(Document):
    def before_insert(self):
        if not self.received_by:
            self.received_by = frappe.session.user
        if not self.posting_date:
            self.posting_date = today()

    def validate(self):
        if not self.items:
            frappe.throw("Add at least one item in this batch.")
        if not any(flt(row.batch_qty) > 0 for row in self.items):
            frappe.throw("Enter a quantity greater than zero for at least one item.")
        if self.purchase_order:
            po = frappe.get_doc("Purchase Order", self.purchase_order)
            self.supplier = po.supplier
            if not self.company:
                self.company = po.company

    def on_submit(self):
        if self.purchase_receipt:
            return
        po = frappe.get_doc("Purchase Order", self.purchase_order)
        receipt = frappe.new_doc("Purchase Receipt")
        receipt.supplier = po.supplier
        receipt.company = self.company or po.company
        receipt.posting_date = self.posting_date or today()
        if receipt.meta.get_field("set_posting_time"):
            receipt.set_posting_time = 1
        receipt.set_warehouse = self.warehouse
        if receipt.meta.get_field("remarks"):
            receipt.remarks = f"WMS PO Receive Batch {self.name} for {po.name}"

        for row in self.items:
            if flt(row.batch_qty) <= 0:
                continue
            receipt.append(
                "items",
                {
                    "item_code": row.item_code,
                    "item_name": row.item_name,
                    "qty": row.batch_qty,
                    "uom": row.uom,
                    "warehouse": self.warehouse,
                    "purchase_order": po.name,
                    "purchase_order_item": row.po_detail,
                    "rate": flt(row.rate),
                },
            )

        if not receipt.items:
            frappe.throw("No batch quantities to receive.")

        receipt.insert(ignore_permissions=True)
        receipt.submit()
        self.db_set("purchase_receipt", receipt.name, update_modified=False)
        frappe.msgprint(
            f"Batch received on Purchase Receipt {receipt.name}. "
            "This PO stays open until every ordered quantity is received.",
            indicator="green",
            alert=True,
        )

    def on_cancel(self):
        if self.purchase_receipt and frappe.db.exists(
            "Purchase Receipt", self.purchase_receipt
        ):
            pr = frappe.get_doc("Purchase Receipt", self.purchase_receipt)
            if pr.docstatus == 1:
                pr.cancel()
