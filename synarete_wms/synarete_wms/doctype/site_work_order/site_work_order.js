frappe.ui.form.on("Site Work Order", {
    refresh(frm) {
        if (frm.is_new()) {
            return;
        }

        const roles = warehouse_role_flags();
        const material = __("Material");

        if (frm.doc.docstatus === 0 && frm.doc.status === "Draft") {
            const submit_work_order = () => {
                frappe.confirm(
                    __("Submit this Site Work Order for Stock Manager review?"),
                    () => apply_swo_action(frm, "Submit")
                );
            };

            frm.page.set_primary_action(
                __("Submit"),
                submit_work_order,
                "octicon octicon-check"
            );
            frm.add_custom_button(__("Submit for Review"), submit_work_order, material);
        }

        if (frm.doc.status === "Pending Stock Review" && roles.can_warehouse) {
            frm.add_custom_button(__("Approve"), () => {
                frappe.confirm(
                    __("Approve this work order for warehouse issue?"),
                    () => apply_swo_action(frm, "Approve")
                );
            }, material);
            frm.add_custom_button(__("Reject"), () => {
                frappe.confirm(
                    __("Reject this work order?"),
                    () => apply_swo_action(frm, "Reject")
                );
            }, material);
        }

        if (roles.can_warehouse && ["Approved", "Issued", "In Progress"].includes(frm.doc.status)) {
            frm.add_custom_button(__("Issue Material"), () => {
                open_or_create_material_issue(frm);
            }, material);
        }

        if (frm.doc.material_issue) {
            frm.add_custom_button(__("Open Material Issue"), () => {
                frappe.set_route("Form", "WMS Material Issue", frm.doc.material_issue);
            }, material);

            if (roles.can_engineer || roles.can_warehouse) {
                frm.add_custom_button(__("Consume Material"), () => {
                    frappe.new_doc("WMS Material Consumption", {
                        site: frm.doc.site,
                        engineer: frm.doc.engineer,
                        material_issue: frm.doc.material_issue,
                    });
                }, material);

                frm.add_custom_button(__("Return Material"), () => {
                    frappe.new_doc("Material Return Record", {
                        material_type: "MP",
                        installation_type: "New Installation",
                        site: frm.doc.site,
                        engineer: frm.doc.engineer,
                        material_issue: frm.doc.material_issue,
                    });
                }, material);
            }
        } else if (frm.doc.status === "Approved" && roles.can_engineer && !roles.can_warehouse) {
            frm.dashboard.set_headline_alert(
                __("Work order approved. Waiting for warehouse to issue material."),
                "orange"
            );
        }

        if (frm.doc.status === "Approved" && roles.can_warehouse) {
            frm.add_custom_button(__("Mark Issued"), () => {
                apply_swo_action(frm, "Mark Issued");
            }, material);
        }

        if (frm.doc.status === "Issued" && (roles.can_engineer || roles.can_warehouse)) {
            frm.add_custom_button(__("Start Work"), () => {
                apply_swo_action(frm, "Start Work");
            }, material);
        }

        if (frm.doc.status === "In Progress" && (roles.can_engineer || roles.can_warehouse)) {
            frm.add_custom_button(__("Complete Work Order"), () => {
                frappe.confirm(
                    __("Mark this Site Work Order as completed? Unused stock stays with the engineer until it is consumed or returned."),
                    () => apply_swo_action(frm, "Complete")
                );
            }, material);
        }
    },

    planned_date(frm) {
        if (frm.doc.planned_date && frm.doc.planned_date < frappe.datetime.get_today()) {
            frappe.msgprint({
                message: __("Planned Date is in the past."),
                indicator: "orange",
            });
        }
    },
});

frappe.ui.form.on("Site Work Order Item", {
    item_code(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.item_code) return;
        frappe.model.set_value(cdt, cdn, "material_type", "MP");
    },
});

function warehouse_role_flags() {
    const roles = frappe.user_roles || [];
    const is_system = roles.includes("System Manager");
    const can_warehouse = is_system
        || roles.includes("Warehouse Manager")
        || roles.includes("Stock Manager");
    const can_engineer = is_system
        || roles.includes("Stock User")
        || roles.includes("Employee")
        || roles.includes("WMS Engineer");
    return { is_system, can_warehouse, can_engineer };
}

function apply_swo_action(frm, action) {
    return frappe.xcall(
        "synarete_wms.synarete_wms.utils.workflow_api.apply_wms_workflow",
        {
            doc: frm.doc,
            action: action,
        }
    ).then(() => frm.reload_doc());
}

function open_or_create_material_issue(frm) {
    if (frm.doc.material_issue) {
        frappe.set_route("Form", "WMS Material Issue", frm.doc.material_issue);
        return;
    }

    if (
        !frappe.model.can_create("WMS Material Issue")
        && !warehouse_role_flags().can_warehouse
    ) {
        frappe.msgprint({
            title: __("Cannot create Material Issue"),
            indicator: "red",
            message: __(
                "Ask a Stock Manager or Warehouse Manager to issue the stock."
            ),
        });
        return;
    }

    frappe.new_doc("WMS Material Issue", {
        site: frm.doc.site,
        engineer: frm.doc.engineer,
        site_work_order: frm.doc.name,
        material_type: frm.doc.material_type,
    });
}
