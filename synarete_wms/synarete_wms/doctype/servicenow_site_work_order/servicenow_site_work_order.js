frappe.ui.form.on("ServiceNow Site Work Order", {
    onload(frm) {
        if (frm.is_new() && (!frm.doc.status || frm.doc.status === "New")) {
            frm.set_value("status", "Awaiting Material");
            frm.set_value("awaiting_warehouse_issue", 1);
        }
        if (frm.is_new() && !frm.doc.assigned_to) {
            frappe.db.get_value("Employee", { user_id: frappe.session.user }, "name").then((r) => {
                if (r && r.message && r.message.name) {
                    frm.set_value("assigned_to", r.message.name);
                }
            });
        }
    },

    refresh(frm) {
        frm.set_df_property("swo_number", "read_only", !frm.is_new());
        toggle_part_fields(frm);

        if (frm.is_new()) {
            return;
        }

        const roles = snwo_role_flags();
        const open_transaction = (transaction_type, extras) => {
            const values = Object.assign(
                {
                    transaction_type: transaction_type,
                    original_work_order: frm.doc.name,
                    received_for_work_order: frm.doc.name,
                    issued_to_work_order: frm.doc.name,
                    site: frm.doc.site,
                },
                extras || {}
            );
            frappe.new_doc("SNWO Material Transaction", values);
        };

        if (cint(frm.doc.awaiting_warehouse_issue) && roles.can_issue) {
            frm.dashboard.set_headline_alert(
                __("Awaiting warehouse issue. Issue or receive material for the assigned engineer."),
                "orange"
            );
        } else if (cint(frm.doc.awaiting_warehouse_issue) && !roles.can_issue) {
            frm.dashboard.set_headline_alert(
                __("Material requested. Waiting for the Warehouse Manager to issue."),
                "orange"
            );
        }

        frm.add_custom_button(__("Recalculate Quantities"), () => {
            frm.call({
                method: "recalculate_quantities",
                freeze: true,
                freeze_message: __("Updating quantities..."),
            }).then(() => {
                frappe.show_alert({
                    message: __("Material quantities updated."),
                    indicator: "green",
                });
                frm.reload_doc();
            });
        }, __("Material"));

        if (roles.can_issue) {
            frm.add_custom_button(__("Receive Material"), () => {
                open_transaction("Receive");
            }, __("Material"));

            frm.add_custom_button(__("Issue Material"), () => {
                open_transaction("Issue");
            }, __("Material"));

            frm.add_custom_button(__("Issue MP Stock"), () => {
                open_transaction("MP Issue", { is_mp_stock: 1 });
            }, __("Material"));

            frm.add_custom_button(__("Deduct MP Stock"), () => {
                frappe.xcall(
                    "synarete_wms.synarete_wms.utils.servicenow.deduct_mp_stock",
                    { work_order: frm.doc.name }
                ).then((r) => {
                    const posted = (r && r.stock_entries) || [];
                    frappe.show_alert({
                        message: posted.length
                            ? __("MP warehouse stock deducted.")
                            : __("No MP issues waiting for warehouse deduction on this work order."),
                        indicator: posted.length ? "green" : "orange",
                    });
                    frm.reload_doc();
                });
            }, __("Material"));
        }

        if (roles.can_engineer) {
            frm.add_custom_button(__("Consume Material"), () => {
                const warehouse_left = (frm.doc.materials || []).some(
                    (row) => flt(row.qty_warehouse_remaining) > 0
                );
                const issued_left = (frm.doc.materials || []).some(
                    (row) => flt(row.qty_remaining) > 0
                );
                if (warehouse_left && !issued_left) {
                    frappe.msgprint({
                        title: __("Waiting for warehouse issue"),
                        indicator: "orange",
                        message: roles.can_issue
                            ? __(
                                "Consume is only for quantity already issued to this work order. "
                                + "Use Material → Issue Material, keep Issued To as this work order, "
                                + "submit the leftover qty, then Consume."
                            )
                            : __(
                                "Material is still in warehouse remaining. "
                                + "Ask the Warehouse Manager to Issue it to this work order, then Consume."
                            ),
                    });
                    return;
                }
                open_transaction("Consume");
            }, __("Material"));

            frm.add_custom_button(__("Reconcile"), () => {
                open_transaction("Reconcile");
            }, __("Material"));

            frm.add_custom_button(__("Request Extra Material"), () => {
                open_transaction("Request");
            }, __("Material"));

            if (frm.doc.process_status !== "Completed") {
                frm.add_custom_button(__("Complete Work Order"), () => {
                    frappe.confirm(
                        __("Mark this ServiceNow Site Work Order as completed?"),
                        () => {
                            frappe.xcall(
                                "synarete_wms.synarete_wms.utils.servicenow.complete_work_order",
                                { name: frm.doc.name }
                            ).then(() => frm.reload_doc());
                        }
                    );
                }, __("Material"));
            }
        }
    },

    site(frm) {
        if (!frm.doc.site) return;
        frappe.db.get_doc("WMS Site", frm.doc.site).then((site) => {
            frm.set_value("maintenance_partner", site.maintenance_partner);
            frm.set_value("transition_partner", site.transition_partner);
        });
    },

    status(frm) {
        const closed = [
            "Closed Complete",
            "Closed Incomplete",
            "Closed Rejected",
        ];
        const is_closed = closed.includes(frm.doc.status);
        frm.set_value("status_group", is_closed ? "Closed" : "Open");
        frm.set_value("is_pending", is_closed ? 0 : 1);
    },

    order_type(frm) {
        toggle_part_fields(frm);
    },

    part_code(frm) {
        if (!frm.doc.part_code) return;
        frappe.db.get_value("Item", frm.doc.part_code, "item_name").then((r) => {
            if (r && r.message) {
                frm.set_value("part_name", r.message.item_name);
            }
        });
    },
});

function snwo_role_flags() {
    const roles = frappe.user_roles || [];
    const is_system = roles.includes("System Manager");
    const can_issue = is_system
        || roles.includes("Warehouse Manager")
        || roles.includes("Stock Manager");
    const can_engineer = is_system
        || roles.includes("Stock User")
        || roles.includes("Employee")
        || roles.includes("WMS Engineer");
    return { is_system, can_issue, can_engineer };
}

function toggle_part_fields(frm) {
    ["part_code", "part_name", "part_category", "part_group", "quantity"].forEach((field) => {
        frm.toggle_display(field, true);
    });
}
