"""Warehouse-only log of bulk used/faulty HTT material returns to the client.

This document deliberately does not create stock/GL transactions, update a
Work Order, or change the existing engineer closeout workflow.
"""

import frappe
from frappe.model.document import Document
from frappe.utils import flt, today


class WMSHTTReturnBatch(Document):
    def before_insert(self):
        if not self.returned_by:
            self.returned_by = frappe.session.user
        if not self.return_date:
            self.return_date = today()

    def validate(self):
        if not self.customer:
            frappe.throw("Select the HTT client.")
        if not self.items:
            frappe.throw("Add at least one HTT return item to this batch.")

        # Validate the complete batch as a whole so duplicate lines cannot
        # cause the same issued quantity to be returned twice.
        entered_by_issue_item = {}
        issue_cache = {}
        for row in self.items:
            if not row.material_issue:
                frappe.throw("Select the HTT Material Issue for every row.")
            if not row.item_code:
                frappe.throw("Select the returned item for every row.")
            if row.condition not in ("Used", "Faulty"):
                frappe.throw(
                    f"{row.item_code}: only Used or Faulty HTT items can be returned."
                )
            if flt(row.returned_qty) <= 0:
                frappe.throw(
                    f"{row.item_code}: Quantity Returned to Client must be greater than zero."
                )

            issue_name = row.material_issue
            if issue_name not in issue_cache:
                issue_cache[issue_name] = frappe.get_doc(
                    "WMS Material Issue", issue_name
                )
            issue = issue_cache[issue_name]

            if issue.docstatus != 1:
                frappe.throw(
                    f"Material Issue {issue.name} must be submitted before its HTT return is logged."
                )
            if issue.material_type not in ("HTT", "Both"):
                frappe.throw(
                    f"Material Issue {issue.name} is not an HTT material issue."
                )
            site_work_order = issue.site_work_order
            servicenow_work_order = issue.get("servicenow_work_order")
            if bool(site_work_order) == bool(servicenow_work_order):
                frappe.throw(
                    f"Material Issue {issue.name} must be linked to exactly one Site or ServiceNow Work Order."
                )
            if servicenow_work_order and issue.material_type != "HTT":
                frappe.throw(
                    f"Material Issue {issue.name}: ServiceNow tracking is supported for HTT-only issues."
                )
            if servicenow_work_order:
                snwo = frappe.get_doc("ServiceNow Site Work Order", servicenow_work_order)
                if issue.site != snwo.site:
                    frappe.throw(
                        f"Material Issue {issue.name} site does not match ServiceNow Work Order {snwo.name}."
                    )
                if issue.engineer and snwo.assigned_to and issue.engineer != snwo.assigned_to:
                    frappe.throw(
                        f"Material Issue {issue.name} engineer does not match ServiceNow Work Order {snwo.name}."
                    )
            if issue.customer != self.customer:
                frappe.throw(
                    f"Material Issue {issue.name} belongs to client {issue.customer}, "
                    f"not {self.customer}."
                )

            matching_items = [
                item
                for item in issue.items or []
                if item.item_code == row.item_code
                and (item.material_type or issue.material_type) == "HTT"
            ]
            if not matching_items:
                frappe.throw(
                    f"{row.item_code} is not an HTT item on Material Issue {issue.name}."
                )

            row.work_order = issue.site_work_order
            row.servicenow_work_order = issue.get("servicenow_work_order")
            row.item_name = frappe.db.get_value(
                "Item", row.item_code, "item_name"
            ) or row.item_code
            if not row.uom:
                row.uom = matching_items[0].uom

            key = (issue.name, row.item_code)
            entered_by_issue_item[key] = (
                entered_by_issue_item.get(key, 0) + flt(row.returned_qty)
            )

        for (issue_name, item_code), entered_qty in entered_by_issue_item.items():
            issue = issue_cache[issue_name]
            issued_qty = _htt_dispatched_qty(issue_name, item_code)
            if issued_qty <= 0:
                frappe.throw(
                    f"No submitted HTT dispatch quantity was found for {item_code} "
                    f"on Material Issue {issue_name}."
                )

            previous_returned = _submitted_returned_qty(
                issue_name,
                item_code,
                exclude_batch=self.name,
            )
            if previous_returned + entered_qty > issued_qty + 0.0001:
                remaining = max(0, issued_qty - previous_returned)
                frappe.throw(
                    f"{item_code} on {issue_name}: this batch returns {entered_qty}, "
                    f"but only {remaining} remains available to return "
                    f"(HTT supplied {issued_qty})."
                )

    def on_submit(self):
        frappe.msgprint(
            "HTT client return recorded for monthly tracking. "
            "No Work Order, stock ledger, or GL transaction was changed.",
            indicator="green",
            alert=True,
        )


def _htt_dispatched_qty(material_issue, item_code):
    rows = frappe.db.sql(
        """
        SELECT COALESCE(SUM(qty), 0)
        FROM `tabWMS HTT Transaction`
        WHERE material_issue = %s
          AND item_code = %s
          AND transaction_type = 'Dispatch'
          AND is_cancelled = 0
        """,
        (material_issue, item_code),
    )
    return flt(rows[0][0] if rows else 0)


def _submitted_returned_qty(material_issue, item_code, exclude_batch=None):
    conditions = [
        "batch.docstatus = 1",
        "item.material_issue = %(material_issue)s",
        "item.item_code = %(item_code)s",
    ]
    values = {
        "material_issue": material_issue,
        "item_code": item_code,
    }
    if exclude_batch:
        conditions.append("batch.name != %(exclude_batch)s")
        values["exclude_batch"] = exclude_batch

    rows = frappe.db.sql(
        f"""
        SELECT COALESCE(SUM(item.returned_qty), 0)
        FROM `tabWMS HTT Return Batch Item` item
        INNER JOIN `tabWMS HTT Return Batch` batch
            ON batch.name = item.parent
        WHERE {' AND '.join(conditions)}
        """,
        values,
    )
    return flt(rows[0][0] if rows else 0)
