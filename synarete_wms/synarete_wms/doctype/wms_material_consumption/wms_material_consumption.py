import frappe
from frappe.model.document import Document
from frappe.utils import flt, today

from synarete_wms.synarete_wms.utils.accountability import (
    add_consumption,
    get_accountability,
    reverse_consumption,
)
from synarete_wms.synarete_wms.utils.stock import (
    cancel_linked_stock_entry,
    create_material_issue,
)


class WMSMaterialConsumption(Document):
    def before_insert(self):
        if not self.consumption_date:
            self.consumption_date = today()
        if not self.status:
            self.status = "Draft"

    def validate(self):
        if not self.material_issue:
            frappe.throw("Material Issue is required for consumption.")

        if not self.items:
            frappe.throw("Add at least one consumed material.")

        issue = frappe.get_doc(
            "WMS Material Issue",
            self.material_issue,
        )

        if issue.docstatus != 1 or issue.status != "Issued":
            frappe.throw("The linked Material Issue must be Issued first.")

        if self.engineer != issue.engineer:
            frappe.throw("Engineer must match the linked Material Issue.")

        if self.site != issue.site:
            frappe.throw("Site must match the linked Material Issue.")

        self._issue_doc = issue

        for item in self.items:
            if flt(item.qty) <= 0:
                frappe.throw(
                    f"Consumed quantity must be greater than zero for {item.item_code}."
                )

            accountability = get_accountability(
                self.material_issue,
                item.material_issue_item,
                item.item_code,
            )

            if not accountability:
                frappe.throw(
                    f"No accountability record was found for {item.item_code}."
                )

            item.accountability = accountability.name
            item.material_issue_item = accountability.material_issue_item
            item.issued_qty = accountability.issued_qty
            item.carried_forward_qty = accountability.carried_forward_qty
            item.transferred_out_qty = accountability.transferred_out_qty
            item.previous_consumed_qty = accountability.consumed_qty
            item.previous_returned_qty = accountability.returned_qty
            item.available_outstanding_qty = accountability.outstanding_qty
            item.consumed_qty = accountability.consumed_qty + flt(item.qty)
            item.returned_qty = accountability.returned_qty
            item.outstanding_qty = max(
                0,
                flt(accountability.outstanding_qty) - flt(item.qty),
            )

            if flt(item.qty) > flt(accountability.outstanding_qty):
                frappe.throw(
                    f"Consumed quantity exceeds outstanding quantity for {item.item_code}. "
                    f"Outstanding: {accountability.outstanding_qty}."
                )

        self._validate_field_issued_stock()

        if self.engineer_consignment:
            consignment = frappe.get_doc(
                "Engineer Consignment",
                self.engineer_consignment,
            )
            if consignment.engineer != self.engineer:
                frappe.throw(
                    "Engineer Consignment does not belong to the selected Engineer."
                )

            for item in self.items:
                matched = False
                for consignment_item in consignment.items:
                    if consignment_item.item_code == item.item_code:
                        matched = True
                        if (
                            flt(consignment_item.consumed_qty)
                            + flt(item.qty)
                            > flt(consignment_item.allocated_qty)
                        ):
                            frappe.throw(
                                f"Consumption exceeds consignment balance for {item.item_code}."
                            )
                        break
                if not matched:
                    frappe.throw(
                        f"{item.item_code} is not allocated in the selected consignment."
                    )

    def _validate_field_issued_stock(self):
        settings = frappe.get_single("WMS Settings")
        warehouse = settings.field_issued_warehouse
        if not warehouse:
            frappe.throw("Configure the Field Issued Warehouse first.")

        needed = {}
        for item in self.items:
            needed[item.item_code] = needed.get(item.item_code, 0) + flt(item.qty)

        for item_code, qty in needed.items():
            stock_bin = frappe.db.get_value(
                "Bin",
                {"item_code": item_code, "warehouse": warehouse},
                ["actual_qty", "reserved_qty"],
                as_dict=True,
            )
            available = 0
            if stock_bin:
                available = max(
                    0,
                    flt(stock_bin.actual_qty) - flt(stock_bin.reserved_qty),
                )
            if qty > available:
                frappe.throw(
                    f"Field Issued Warehouse has only {available} of {item_code}; "
                    f"cannot consume {qty}. Reconcile physical stock before expensing."
                )

    def on_submit(self):
        if self.stock_entry:
            return

        settings = frappe.get_single("WMS Settings")
        if not settings.field_issued_warehouse:
            frappe.throw("Configure the Field Issued Warehouse first.")

        issue = getattr(self, "_issue_doc", None) or frappe.get_doc(
            "WMS Material Issue",
            self.material_issue,
        )
        remarks = (
            f"WMS Material Consumption {self.name}"
            f" / Issue {self.material_issue}"
            f" / Work Order {issue.site_work_order or ''}"
        )

        stock_entry = create_material_issue(
            items=[
                {
                    "item_code": item.item_code,
                    "qty": item.qty,
                    "uom": item.uom,
                    "serial_no": item.serial_no,
                }
                for item in self.items
            ],
            source_warehouse=settings.field_issued_warehouse,
            company=settings.company,
            reference_doctype=self.doctype,
            reference_name=self.name,
            site=self.site,
            engineer=self.engineer,
            remarks=remarks,
        )

        self.db_set("stock_entry", stock_entry.name, update_modified=False)

        for item in self.items:
            accountability = get_accountability(
                self.material_issue,
                item.material_issue_item,
                item.item_code,
            )
            add_consumption(
                accountability,
                item.qty,
                self.name,
            )

        if self.engineer_consignment:
            consignment = frappe.get_doc(
                "Engineer Consignment",
                self.engineer_consignment,
            )
            for consumed in self.items:
                for allocated in consignment.items:
                    if allocated.item_code == consumed.item_code:
                        new_consumed = flt(allocated.consumed_qty) + flt(consumed.qty)
                        allocated.db_set("consumed_qty", new_consumed)
                        allocated.db_set(
                            "remaining_qty",
                            max(0, allocated.allocated_qty - new_consumed),
                        )
                        break

        self.db_set("status", "Consumed")

    def on_cancel(self):
        cancel_linked_stock_entry(self.stock_entry)

        for item in self.items:
            accountability = get_accountability(
                self.material_issue,
                item.material_issue_item,
                item.item_code,
            )
            if accountability:
                reverse_consumption(accountability, item.qty)

        if self.engineer_consignment:
            consignment = frappe.get_doc(
                "Engineer Consignment",
                self.engineer_consignment,
            )
            for consumed in self.items:
                for allocated in consignment.items:
                    if allocated.item_code == consumed.item_code:
                        new_consumed = max(
                            0,
                            flt(allocated.consumed_qty) - flt(consumed.qty),
                        )
                        allocated.db_set("consumed_qty", new_consumed)
                        allocated.db_set(
                            "remaining_qty",
                            max(0, allocated.allocated_qty - new_consumed),
                        )
                        break

        self.db_set("status", "Cancelled")
