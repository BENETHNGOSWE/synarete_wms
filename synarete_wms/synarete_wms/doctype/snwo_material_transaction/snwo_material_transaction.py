import frappe
from frappe.model.document import Document
from frappe.utils import today

from synarete_wms.synarete_wms.utils.servicenow import (
    is_mp_transaction,
    post_mp_stock_issue,
    refresh_work_order_balances,
    related_work_orders,
    validate_transaction,
)
from synarete_wms.synarete_wms.utils.stock import cancel_linked_stock_entry


class SNWOMaterialTransaction(Document):
    def before_insert(self):
        if not self.performed_by:
            self.performed_by = frappe.session.user
        if not self.posting_date:
            self.posting_date = today()
        if not self.status:
            self.status = "Draft"

    def validate(self):
        if self.original_work_order and not self.site:
            self.site = frappe.db.get_value(
                "ServiceNow Site Work Order",
                self.original_work_order,
                "site",
            )
        if self.original_work_order and not self.received_for_work_order:
            self.received_for_work_order = self.original_work_order
        if self.original_work_order and not self.issued_to_work_order:
            self.issued_to_work_order = self.original_work_order
        if self.transaction_type == "MP Issue":
            self.is_mp_stock = 1
        validate_transaction(self)

    def on_submit(self):
        self.db_set("status", "Submitted")
        if is_mp_transaction(self):
            stock_entry = post_mp_stock_issue(self)
            if not (stock_entry or self.stock_entry):
                frappe.throw(
                    "MP Issue did not deduct warehouse stock (no Stock Entry). "
                    "Set Company and Main Warehouse in WMS Settings, confirm the "
                    "item exists, then submit again. For already-submitted issues "
                    "use Material → Deduct MP Stock."
                )
            frappe.msgprint(
                f"Warehouse stock deducted on Stock Entry {self.stock_entry or stock_entry}.",
                indicator="green",
                alert=True,
            )
        for work_order in related_work_orders(self):
            refresh_work_order_balances(work_order)
        if self.transaction_type == "Reconcile":
            frappe.db.set_value(
                "ServiceNow Site Work Order",
                self.original_work_order,
                "process_status",
                "Reconciliation",
            )

    def on_cancel(self):
        cancel_linked_stock_entry(self.stock_entry)
        self.db_set("status", "Cancelled")
        for work_order in related_work_orders(self):
            refresh_work_order_balances(work_order)
