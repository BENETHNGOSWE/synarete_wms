import frappe
from frappe.model.document import Document
from frappe.utils import flt, today

from synarete_wms.synarete_wms.utils.accountability import (
    compute_issue_split,
    get_open_balance,
    reverse_for_material_issue,
)
from synarete_wms.synarete_wms.utils.stock import (
    cancel_linked_stock_entry,
    create_material_transfer,
)
from synarete_wms.synarete_wms.utils.htt import (
    cancel_htt_dispatch_transactions,
    create_htt_dispatch_transactions,
)


class WMSMaterialIssue(Document):
    def before_insert(self):
        if not self.issued_by:
            self.issued_by = frappe.session.user
        if not self.issue_date:
            self.issue_date = today()
        if not self.status:
            self.status = "Draft"

    def validate(self):
        if not self.items:
            frappe.throw("Add at least one item to issue.")

        if self.material_type == "MP" and not self.site_work_order:
            frappe.throw("Site Work Order is required for MP material issues.")

        self._prevent_duplicate_mp_issue()

        if self.material_type == "HTT":
            if not self.customer:
                frappe.throw("Customer is required for HTT material issues.")
            if not self.htt_receipt:
                frappe.throw("HTT Material Receipt is required for HTT issues.")

            receipt_type = frappe.db.get_value(
                "HTT Material Receipt",
                self.htt_receipt,
                "receipt_type",
            )

            if receipt_type == "Engineer Request" and not self.site_work_order:
                frappe.throw(
                    "Site Work Order is required for HTT Engineer Request issues."
                )

        work_order_items = []

        if self.site_work_order:
            work_order = frappe.get_doc(
                "Site Work Order",
                self.site_work_order,
            )

            if work_order.site != self.site:
                frappe.throw("Site must match the selected Site Work Order.")

            if work_order.engineer != self.engineer:
                frappe.throw("Engineer must match the selected Site Work Order.")

            for work_order_item in work_order.materials:
                work_order_items.append(work_order_item)

        for item in self.items:
            matched_work_order_item = None

            for work_order_item in work_order_items:
                if work_order_item.item_code == item.item_code:
                    matched_work_order_item = work_order_item
                    break

            if matched_work_order_item:
                item.requested_qty = matched_work_order_item.qty
                item.approved_qty = (
                    matched_work_order_item.approved_qty
                    or matched_work_order_item.qty
                )
                if not item.uom:
                    item.uom = matched_work_order_item.uom

            item_type = item.material_type or self.material_type
            if item_type not in ("MP", "HTT"):
                frappe.throw(
                    f"Select MP or HTT for {item.item_code} on the issue item row."
                )
            item.material_type = item_type

            # HTT material is customer-owned and is tracked through the HTT
            # custody ledger, not through Main/Field Issued stock.  Its
            # quantity must remain editable even when there is no Site Work
            # Order (Voice of Customer) and it must not pass through the MP
            # outstanding-stock calculations.
            if item_type == "HTT":
                dispatch_qty = flt(item.qty)
                if dispatch_qty <= 0:
                    frappe.throw(
                        f"Enter the quantity to dispatch for HTT item {item.item_code}."
                    )

                item.requested_qty = (
                    flt(item.requested_qty) or dispatch_qty
                )
                item.approved_qty = (
                    flt(item.approved_qty) or item.requested_qty
                )
                item.previous_outstanding_qty = 0
                item.outstanding_applied_qty = 0
                item.warehouse_stock_qty = 0
                item.fulfilled_qty = dispatch_qty
                continue

            item.previous_outstanding_qty = get_open_balance(
                self.engineer,
                item.item_code,
                exclude_material_issue=self.name,
            )

            stock_bin = frappe.db.get_value(
                "Bin",
                {
                    "item_code": item.item_code,
                    "warehouse": self.source_warehouse,
                },
                ["actual_qty", "reserved_qty"],
                as_dict=True,
            )

            if stock_bin:
                item.warehouse_stock_qty = max(
                    0,
                    flt(stock_bin.actual_qty) - flt(stock_bin.reserved_qty),
                )
            else:
                item.warehouse_stock_qty = 0

            requested_qty = flt(item.requested_qty)
            approved_qty = flt(item.approved_qty) or requested_qty
            previous_outstanding = flt(item.previous_outstanding_qty)

            # Reuse leftover Field Issued stock when Use Outstanding Stock
            # is ticked (the form enables this automatically when the
            # engineer already holds the item). Untick to issue fully from Main.
            applied, maximum_new_issue = compute_issue_split(
                approved_qty,
                previous_outstanding,
                item.use_outstanding,
            )
            item.outstanding_applied_qty = applied

            new_issue_qty = flt(item.qty)
            if new_issue_qty < 0:
                frappe.throw(
                    f"New warehouse issue quantity cannot be negative for {item.item_code}."
                )

            # A newly created issue can arrive with the original requested
            # quantity before the browser has loaded the engineer balance.
            # When leftover stock is applied, normalize the physical warehouse
            # quantity to the shortage instead of rejecting the document.
            if item.use_outstanding and new_issue_qty > maximum_new_issue:
                item.qty = maximum_new_issue
            elif new_issue_qty > maximum_new_issue:
                frappe.throw(
                    f"New warehouse issue quantity for {item.item_code} cannot exceed "
                    f"{maximum_new_issue} after applying outstanding stock."
                )

            if flt(item.qty) == 0 and item.outstanding_applied_qty == 0:
                frappe.throw(
                    f"Enter a quantity to issue or select Use Outstanding Stock for {item.item_code}."
                )

            if flt(item.qty) > flt(item.warehouse_stock_qty):
                frappe.throw(
                    f"Additional quantity {flt(item.qty)} for {item.item_code} exceeds "
                    f"Main Warehouse available stock {flt(item.warehouse_stock_qty)}."
                )

            item.fulfilled_qty = item.outstanding_applied_qty + flt(item.qty)

            if requested_qty and approved_qty > requested_qty:
                frappe.throw(
                    f"Approved quantity cannot exceed requested quantity for {item.item_code}."
                )

        if self.material_type in ("MP", "Both"):
            if not self.source_warehouse or not self.target_warehouse:
                frappe.throw(
                    "Source and Target Warehouses are required for MP issues."
                )

            if self.source_warehouse == self.target_warehouse:
                frappe.throw("Source and target warehouses must be different.")

    def _prevent_duplicate_mp_issue(self):
        if not self.site_work_order:
            return
        if (self.material_type or "") not in ("MP", "Both"):
            return

        others = frappe.get_all(
            "WMS Material Issue",
            filters={
                "site_work_order": self.site_work_order,
                "docstatus": 1,
                "name": ["!=", self.name or ""],
            },
            pluck="name",
            limit_page_length=1,
        )
        if others:
            frappe.throw(
                f"Site Work Order {self.site_work_order} already has submitted "
                f"Material Issue {others[0]}. Cancel that issue first, or reuse "
                "the engineer's leftover Field Issued stock on a later work order."
            )

    def on_submit(self):
        already_posted = bool(self.stock_entry)

        settings = frappe.get_single("WMS Settings")
        stock_items = []
        mp_items = []
        htt_items = []

        for item in self.items:
            material_type = item.material_type or self.material_type
            if material_type == "MP":
                mp_items.append(item)
            if material_type == "MP" and flt(item.qty) > 0:
                stock_items.append(
                    {
                        "item_code": item.item_code,
                        "qty": item.qty,
                        "uom": item.uom,
                        "serial_no": item.serial_no,
                        "batch_no": item.batch_no,
                    }
                )
            elif material_type == "HTT":
                htt_items.append(item)
            elif material_type == "Both":
                frappe.throw(
                    "Select MP or HTT on each item when the issue contains Both types."
                )

        if htt_items and not self.customer:
            frappe.throw("Customer is required for HTT material issues.")

        if stock_items and not already_posted:
            stock_entry = create_material_transfer(
                items=stock_items,
                source_warehouse=self.source_warehouse,
                target_warehouse=self.target_warehouse,
                company=settings.company,
                reference_doctype=self.doctype,
                reference_name=self.name,
                site=self.site,
                engineer=self.engineer,
            )
            self.db_set("stock_entry", stock_entry.name, update_modified=False)

        if htt_items and not already_posted:
            create_htt_dispatch_transactions(self)

        from synarete_wms.synarete_wms.utils.accountability import (
            create_for_material_issue,
        )

        if mp_items:
            create_for_material_issue(self)

        if already_posted:
            if mp_items:
                self.db_set("status", "Issued")
            return

        from synarete_wms.synarete_wms.utils.delivery import (
            create_printable_delivery_note,
        )
        from synarete_wms.synarete_wms.utils.signature import (
            create_signature_for_material_issue,
        )

        delivery_note = create_printable_delivery_note(self)
        create_signature_for_material_issue(self, delivery_note)

        if self.site_work_order:
            frappe.db.set_value(
                "Site Work Order",
                self.site_work_order,
                "material_issue",
                self.name,
                update_modified=True,
            )

        self.db_set("status", "Issued")

    def on_cancel(self):
        reverse_for_material_issue(self)
        cancel_linked_stock_entry(self.stock_entry)
        cancel_htt_dispatch_transactions(self)
        self.db_set("status", "Cancelled")
