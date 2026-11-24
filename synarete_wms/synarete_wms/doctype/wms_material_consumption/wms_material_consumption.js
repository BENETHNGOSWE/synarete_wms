frappe.ui.form.on("WMS Material Consumption", {
    material_issue(frm) {
        if (!frm.doc.material_issue) return;

        frappe.db.get_doc(
            "WMS Material Issue",
            frm.doc.material_issue
        ).then((issue) => {
            frm.set_value("site", issue.site);
            frm.set_value("engineer", issue.engineer);
            frm.clear_table("items");

            (issue.items || []).forEach((source_row) => {
                const row = frm.add_child("items");
                row.item_code = source_row.item_code;
                row.item_name = source_row.item_name;
                row.material_issue_item = source_row.name;
                row.requested_qty = source_row.requested_qty;
                row.issued_qty = source_row.qty;
                row.qty = 0;
                row.uom = source_row.uom;
                row.material_type = source_row.material_type;
            });

            frm.refresh_field("items");

            (frm.doc.items || []).forEach((row) => {
                frappe.xcall(
                    "synarete_wms.synarete_wms.utils.accountability.get_accountability_summary",
                    {
                        material_issue: frm.doc.material_issue,
                        material_issue_item: row.material_issue_item,
                        item_code: row.item_code,
                    }
                ).then((summary) => {
                    if (!summary) return;

                    frappe.model.set_value(cdt_for_row(row), row.name, "accountability", summary.name);
                    frappe.model.set_value(cdt_for_row(row), row.name, "requested_qty", summary.requested_qty);
                    frappe.model.set_value(cdt_for_row(row), row.name, "issued_qty", summary.issued_qty);
                    frappe.model.set_value(cdt_for_row(row), row.name, "carried_forward_qty", summary.carried_forward_qty || 0);
                    frappe.model.set_value(cdt_for_row(row), row.name, "transferred_out_qty", summary.transferred_out_qty || 0);
                    frappe.model.set_value(cdt_for_row(row), row.name, "previous_consumed_qty", summary.consumed_qty);
                    frappe.model.set_value(cdt_for_row(row), row.name, "previous_returned_qty", summary.returned_qty);
                    frappe.model.set_value(cdt_for_row(row), row.name, "consumed_qty", summary.consumed_qty);
                    frappe.model.set_value(cdt_for_row(row), row.name, "returned_qty", summary.returned_qty);
                    frappe.model.set_value(cdt_for_row(row), row.name, "available_outstanding_qty", summary.outstanding_qty);
                    frappe.model.set_value(cdt_for_row(row), row.name, "outstanding_qty", summary.outstanding_qty);
                    frm.refresh_field("items");
                });
            });
        });
    },

    refresh(frm) {
        const is_manager =
            frappe.user.has_role("Stock Manager") ||
            frappe.user.has_role("Warehouse Manager") ||
            frappe.user.has_role("System Manager");

        if (frm.doc.status === "Pending Verification" && is_manager) {
            frm.dashboard.set_headline_alert(
                __("Choose the Expense Account on each item, then Approve. Inventory is deducted only after Approve."),
                "orange"
            );
            (frm.doc.items || []).forEach((row) => {
                if (row.item_code && !row.expense_account) {
                    frappe.xcall(
                        "synarete_wms.synarete_wms.utils.stock.get_item_expense_account",
                        { item_code: row.item_code }
                    ).then((account) => {
                        if (account) {
                            frappe.model.set_value(row.doctype, row.name, "expense_account", account);
                        }
                    });
                }
            });
        }

        if (
            frm.is_new() ||
            frm.doc.docstatus !== 0
        ) {
            return;
        }

        const apply_action = (action, message) => {
            frappe.confirm(message, () => {
                const run = () => frappe.xcall(
                    "synarete_wms.synarete_wms.utils.workflow_api.apply_wms_workflow",
                    {
                        doc: frm.doc,
                        action: action,
                    }
                ).then(() => frm.reload_doc());
                if (frm.is_dirty()) {
                    frm.save().then(run);
                } else {
                    run();
                }
            });
        };

        const can_request =
            is_manager
            || frappe.user.has_role("Employee")
            || frappe.user.has_role("Stock User")
            || frappe.user.has_role("WMS Engineer");

        if (frm.doc.status === "Draft" && can_request) {
            const submit_consume = () => apply_action(
                "Submit",
                __("Submit consumption request? Warehouse will choose the expense GL and Approve. Stock is not deducted yet.")
            );
            frm.page.set_primary_action(__("Submit"), submit_consume, "octicon octicon-check");
            frm.add_custom_button(__("Submit"), submit_consume, __("Actions"));
        }

        if (frm.doc.status === "Pending Verification" && is_manager) {
            frm.add_custom_button(
                __("Approve"),
                () => {
                    const missing = (frm.doc.items || []).filter((row) => flt(row.qty) > 0 && !row.expense_account);
                    if (missing.length) {
                        frappe.msgprint({
                            title: __("Expense Account required"),
                            indicator: "red",
                            message: __("Choose an Expense Account on each consumed item before Approve."),
                        });
                        return;
                    }
                    apply_action(
                        "Approve",
                        __("Approve consumption, post expense GL, and deduct inventory?")
                    );
                },
                __("Actions")
            );

            frm.add_custom_button(
                __("Reject"),
                () => apply_action(
                    "Reject",
                    __("Reject this consumption record?")
                ),
                __("Actions")
            );
        }
    },
});

frappe.ui.form.on("WMS Material Consumption Item", {
    qty(frm, cdt, cdn) {
        refresh_consumption_row(frm, cdt, cdn);
    },
    item_code(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row || !row.item_code) return;
        const is_manager =
            frappe.user.has_role("Stock Manager") ||
            frappe.user.has_role("Warehouse Manager") ||
            frappe.user.has_role("System Manager");
        if (!is_manager) return;
        frappe.xcall(
            "synarete_wms.synarete_wms.utils.stock.get_item_expense_account",
            { item_code: row.item_code }
        ).then((account) => {
            if (account && !locals[cdt][cdn].expense_account) {
                frappe.model.set_value(cdt, cdn, "expense_account", account);
            }
        });
    },
});

function cdt_for_row(row) {
    return row.doctype || "WMS Material Consumption Item";
}

function refresh_consumption_row(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (!row) return;

    const issued = flt(row.issued_qty || 0);
    const carried_forward = flt(row.carried_forward_qty || 0);
    const transferred_out = flt(row.transferred_out_qty || 0);
    const previous_consumed = flt(row.previous_consumed_qty || 0);
    const previous_returned = flt(row.previous_returned_qty || 0);
    const current_consumed = flt(row.qty || 0);

    // Use the accountability balance as the source of truth.  This keeps
    // the form correct when the issue contains carried-forward material or
    // when part of the original accountability was already reallocated.
    const calculated_available = Math.max(
        0,
        issued
        + carried_forward
        - transferred_out
        - previous_consumed
        - previous_returned
    );
    const available = row.available_outstanding_qty !== undefined
        ? flt(row.available_outstanding_qty)
        : calculated_available;
    const total_consumed = previous_consumed + current_consumed;
    const outstanding = Math.max(0, available - current_consumed);

    frappe.model.set_value(cdt, cdn, "consumed_qty", total_consumed);
    frappe.model.set_value(cdt, cdn, "returned_qty", previous_returned);
    frappe.model.set_value(cdt, cdn, "available_outstanding_qty", available);
    frappe.model.set_value(cdt, cdn, "outstanding_qty", outstanding);
    frm.refresh_field("items");
}
