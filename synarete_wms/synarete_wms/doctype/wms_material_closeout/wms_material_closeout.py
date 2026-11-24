import frappe
from frappe.model.document import Document
from frappe.utils import flt, today

from synarete_wms.synarete_wms.utils.closeout import post_closeout_stock
from synarete_wms.synarete_wms.utils.qty_rules import (
    closeout_shortfall,
    validate_closeout_quantities,
    validate_closeout_shortfall_reason,
)
from synarete_wms.synarete_wms.utils.stock import cancel_linked_stock_entry


class WMSMaterialCloseout(Document):
    def before_insert(self):
        if not self.returned_by:
            self.returned_by = frappe.session.user
        if not self.posting_date:
            self.posting_date = today()

    def validate(self):
        if not self.work_order:
            frappe.throw("Select the Work Order.")

        existing = frappe.db.exists(
            "WMS Material Closeout",
            {
                "work_order_type": self.work_order_type,
                "work_order": self.work_order,
                "docstatus": 1,
                "name": ["!=", self.name],
            },
        )
        if existing:
            frappe.throw(
                f"Closeout {existing} is already submitted for {self.work_order}."
            )

        self._fill_from_work_order()
        self._ensure_issued_items()
        if not self.items:
            frappe.throw("No issued material to return on this work order.")

        for row in self.items:
            error = validate_closeout_quantities(
                row.issued_qty,
                row.used_qty,
                row.returned_unused_qty,
                row.previously_used_qty,
                row.previously_returned_qty,
            )
            if error:
                frappe.throw(f"{row.item_code}: {error}")
            row.shortfall_qty = closeout_shortfall(
                row.issued_qty,
                row.used_qty,
                row.returned_unused_qty,
            )
            reason = getattr(row, "shortfall_reason", None) or self.notes
            short = validate_closeout_shortfall_reason(
                row.issued_qty,
                row.used_qty,
                row.returned_unused_qty,
                reason,
            )
            if short:
                frappe.throw(f"{row.item_code}: {short}")

    def _fill_from_work_order(self):
        if self.work_order_type == "Site Work Order":
            site, engineer = frappe.db.get_value(
                "Site Work Order",
                self.work_order,
                ["site", "engineer"],
            )
            self.site = self.site or site
            self.engineer = self.engineer or engineer
        elif self.work_order_type == "ServiceNow Site Work Order":
            site, engineer = frappe.db.get_value(
                "ServiceNow Site Work Order",
                self.work_order,
                ["site", "assigned_to"],
            )
            self.site = self.site or site
            self.engineer = self.engineer or engineer

    def _ensure_issued_items(self):
        from synarete_wms.synarete_wms.utils.closeout import work_order_issued_lines

        lines = work_order_issued_lines(self.work_order_type, self.work_order)
        if not lines:
            return

        entered_by_code = {}
        entered_by_index = []
        for row in self.items or []:
            payload = {
                "used_qty": row.used_qty,
                "returned_unused_qty": row.returned_unused_qty,
                "shortfall_reason": getattr(row, "shortfall_reason", None),
            }
            entered_by_index.append(payload)
            if row.item_code:
                entered_by_code[row.item_code] = payload

        self.set("items", [])
        for index, line in enumerate(lines):
            extra = entered_by_code.get(line["item_code"])
            if extra is None and index < len(entered_by_index):
                extra = entered_by_index[index]
            extra = extra or {}
            self.append(
                "items",
                {
                    "item_code": line["item_code"],
                    "item_name": line.get("item_name") or line["item_code"],
                    "issued_qty": line["issued_qty"],
                    "previously_used_qty": line["previously_used_qty"],
                    "previously_returned_qty": line["previously_returned_qty"],
                    "used_qty": extra.get("used_qty", line["used_qty"]),
                    "returned_unused_qty": extra.get(
                        "returned_unused_qty", line["returned_unused_qty"]
                    ),
                    "shortfall_reason": extra.get("shortfall_reason"),
                    "accountability": line.get("accountability"),
                    "material_issue": line.get("material_issue"),
                },
            )

    def on_submit(self):
        post_closeout_stock(self)
        if self.work_order_type == "Site Work Order":
            if frappe.get_meta("Site Work Order").has_field("material_closeout"):
                frappe.db.set_value(
                    "Site Work Order",
                    self.work_order,
                    "material_closeout",
                    self.name,
                    update_modified=False,
                )
        elif self.work_order_type == "ServiceNow Site Work Order":
            if frappe.get_meta("ServiceNow Site Work Order").has_field(
                "material_closeout"
            ):
                frappe.db.set_value(
                    "ServiceNow Site Work Order",
                    self.work_order,
                    "material_closeout",
                    self.name,
                    update_modified=False,
                )
            from synarete_wms.synarete_wms.utils.servicenow import (
                refresh_work_order_balances,
            )

            refresh_work_order_balances(self.work_order)

        frappe.msgprint(
            "Material return submitted. You can Close Work Order now.",
            indicator="green",
            alert=True,
        )

    def on_cancel(self):
        cancel_linked_stock_entry(self.consume_stock_entry)
        cancel_linked_stock_entry(self.return_stock_entry)
        if self.work_order_type == "ServiceNow Site Work Order":
            from synarete_wms.synarete_wms.utils.servicenow import (
                refresh_work_order_balances,
            )

            refresh_work_order_balances(self.work_order)
