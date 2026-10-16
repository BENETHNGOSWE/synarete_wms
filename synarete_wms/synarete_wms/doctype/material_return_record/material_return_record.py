import frappe
from frappe.model.document import Document

from synarete_wms.synarete_wms.utils.accountability import (
    add_return,
    get_accountability,
    reverse_return,
)
from synarete_wms.synarete_wms.utils.stock import create_material_transfer


class MaterialReturnRecord(Document):
    def validate(self):
        if not self.return_qty or self.return_qty <= 0:
            frappe.throw("Quantity to Return/Replace must be greater than zero.")

        if self.material_issue:
            issue = frappe.get_doc(
                "WMS Material Issue",
                self.material_issue,
            )
            if self.site != issue.site:
                frappe.throw("Site must match the selected Material Issue.")
            if self.engineer and self.engineer != issue.engineer:
                frappe.throw("Engineer must match the selected Material Issue.")

            return_item_code = (
                self.old_item_code
                if self.installation_type == "Replacement"
                else self.new_item_code
            )
            if return_item_code:
                accountability = get_accountability(
                    self.material_issue,
                    item_code=return_item_code,
                )
                if not accountability:
                    frappe.throw(
                        f"No accountability record was found for {return_item_code}."
                    )
                self.accountability = accountability.name
                self.issued_qty = accountability.issued_qty
                self.consumed_qty = accountability.consumed_qty
                self.previous_returned_qty = accountability.returned_qty
                self.outstanding_qty = accountability.outstanding_qty

                if self.return_qty > accountability.outstanding_qty:
                    frappe.throw(
                        f"Returned quantity exceeds outstanding quantity for {return_item_code}. "
                        f"Outstanding: {accountability.outstanding_qty}."
                    )

        if self.material_type == "MP" and not self.material_issue:
            frappe.throw("Material Issue is required for MP returns.")

        if self.material_type == "HTT" and not self.customer:
            frappe.throw("Customer is required for HTT returns.")

        if self.installation_type == "Replacement":
            if not self.old_item_code:
                frappe.throw("Old Item is required for a replacement.")
            if not self.new_item_code:
                frappe.throw("New Item is required for a replacement.")

    def on_submit(self):
        if self.material_type == "HTT":
            self._submit_htt_return()
            return

        settings = frappe.get_single("WMS Settings")
        if not settings.field_issued_warehouse or not settings.main_warehouse:
            frappe.throw("Configure WMS Settings warehouses first.")

        returned_item_code = (
            self.old_item_code
            if self.installation_type == "Replacement"
            else self.new_item_code
        )

        if self.installation_type == "Replacement":
            # Return the old equipment from Field Issued to Main Warehouse.
            return_entry = create_material_transfer(
                items=[
                    {
                        "item_code": self.old_item_code,
                        "qty": self.return_qty,
                        "serial_no": self.old_serial_no,
                    }
                ],
                source_warehouse=settings.field_issued_warehouse,
                target_warehouse=settings.main_warehouse,
                company=settings.company,
                site=self.site,
                engineer=self.engineer,
            )

            # Issue the replacement from Main Warehouse to Field Issued.
            issue_entry = create_material_transfer(
                items=[
                    {
                        "item_code": self.new_item_code,
                        "qty": self.return_qty,
                        "serial_no": self.new_serial_no,
                    }
                ],
                source_warehouse=settings.main_warehouse,
                target_warehouse=settings.field_issued_warehouse,
                company=settings.company,
                site=self.site,
                engineer=self.engineer,
            )

            self.db_set(
                "stock_entry",
                return_entry.name,
                update_modified=False,
            )
            self.db_set(
                "issue_stock_entry",
                issue_entry.name,
                update_modified=False,
            )
        else:
            # For a normal return, New Item represents the returned item
            # in the current form design.
            if not self.new_item_code:
                frappe.throw("New Item is required for a return.")

            return_entry = create_material_transfer(
                items=[
                    {
                        "item_code": self.new_item_code,
                        "qty": self.return_qty,
                        "serial_no": self.new_serial_no,
                    }
                ],
                source_warehouse=settings.field_issued_warehouse,
                target_warehouse=settings.main_warehouse,
                company=settings.company,
                site=self.site,
                engineer=self.engineer,
            )

            self.db_set(
                "stock_entry",
                return_entry.name,
                update_modified=False,
            )

        if self.material_issue and returned_item_code:
            accountability = get_accountability(
                self.material_issue,
                item_code=returned_item_code,
            )
            if not accountability:
                frappe.throw(
                    f"No accountability record was found for {returned_item_code}."
                )
            add_return(
                accountability,
                self.return_qty,
                self.name,
            )

        self.db_set("actual_return_date", frappe.utils.today())
        self.db_set("return_status", "Returned")

    def _submit_htt_return(self):
        if not self.htt_receipt:
            frappe.throw("HTT Material Receipt is required for an HTT return.")
        if not self.old_item_code:
            frappe.throw("Old Item is required for an HTT return.")

        frappe.get_doc(
            {
                "doctype": "WMS HTT Transaction",
                "transaction_type": "Return",
                "posting_date": frappe.utils.today(),
                "customer": self.customer,
                "site": self.site,
                "engineer": self.engineer,
                "item_code": self.old_item_code,
                "qty": self.return_qty,
                "serial_no": self.old_serial_no,
                "htt_receipt": self.htt_receipt,
                "material_return": self.name,
                "is_cancelled": 0,
            }
        ).insert(ignore_permissions=True)

        self.db_set("actual_return_date", frappe.utils.today())
        self.db_set("return_status", "Returned")

    def on_cancel(self):
        from synarete_wms.synarete_wms.utils.stock import cancel_linked_stock_entry

        if self.accountability:
            accountability = frappe.get_doc(
                "WMS Material Accountability",
                self.accountability,
            )
            reverse_return(accountability, self.return_qty)

        cancel_linked_stock_entry(self.stock_entry)
        cancel_linked_stock_entry(self.issue_stock_entry)

        transactions = frappe.get_all(
            "WMS HTT Transaction",
            filters={
                "material_return": self.name,
                "is_cancelled": 0,
            },
            pluck="name",
        )

        for transaction_name in transactions:
            frappe.db.set_value(
                "WMS HTT Transaction",
                transaction_name,
                "is_cancelled",
                1,
                update_modified=True,
            )
