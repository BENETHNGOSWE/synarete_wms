frappe.ui.form.on("WMS Material Issue", {
    onload(frm) {
        if (!frm.is_new()) return;

        if (frm.doc.material_type === "HTT") {
            clear_stock_warehouses(frm);
        } else {
            set_default_stock_warehouses(frm);
        }

        if (frm.doc.site_work_order) {
            load_site_work_order(frm);
        }
    },

    refresh(frm) {
        toggle_stock_warehouses(frm);
        show_reuse_intro(frm);

        if (frm.is_new() && frm.doc.site_work_order) {
            load_site_work_order(frm);
        }

        if (!frm.is_new() && frm.doc.docstatus === 0) {
            // Do not replace Save. A previous handler called save() first,
            // which shows "No changes in document" and never submits.
            frm.add_custom_button(
                __("Submit"),
                () => {
                    frappe.confirm(
                        __("Submit this Material Issue and transfer stock to Field Issued?"),
                        () => frm.save("Submit")
                    );
                },
                __("WMS")
            );
        }

        if (frm.doc.delivery_note) {
            frm.add_custom_button(
                __("Print Delivery Note"),
                () => frappe.set_route(
                    "print",
                    "Delivery Note",
                    frm.doc.delivery_note,
                    { format: "WMS Standard Delivery Note" }
                ),
                __("WMS")
            );
        }

        if (frm.doc.delivery_signature) {
            frm.add_custom_button(
                __("Open Delivery Signature"),
                () => frappe.set_route(
                    "Form",
                    "Delivery Note Signature",
                    frm.doc.delivery_signature
                ),
                __("WMS")
            );
        }

        if (frm.doc.stock_entry) {
            frm.add_custom_button(
                __("Open Stock Entry"),
                () => frappe.set_route(
                    "Form",
                    "Stock Entry",
                    frm.doc.stock_entry
                ),
                __("WMS")
            );
        }
    },

    material_type(frm) {
        toggle_stock_warehouses(frm);

        if (frm.doc.material_type === "HTT") {
            clear_stock_warehouses(frm);
            set_existing_item_material_type(frm, "HTT");
        } else if (frm.doc.material_type === "MP") {
            set_default_stock_warehouses(frm);
            set_existing_item_material_type(frm, "MP");
            refresh_all_mp_outstanding(frm);
        }
    },

    engineer(frm) {
        refresh_all_mp_outstanding(frm);
    },

    htt_receipt(frm) {
        if (!frm.doc.htt_receipt) return;

        frappe.db.get_doc(
            "HTT Material Receipt",
            frm.doc.htt_receipt
        ).then((receipt) => {
            if (receipt.docstatus !== 1) {
                frappe.msgprint({
                    message: __("Submit the HTT Material Receipt before creating a dispatch."),
                    indicator: "orange",
                });
                return;
            }

            if (frm.doc.material_type !== "HTT") {
                frm.set_value("material_type", "HTT");
            }

            frm.set_value("customer", receipt.customer);
            frm.set_value("site", receipt.target_site);
            if (receipt.related_engineer) {
                frm.set_value("engineer", receipt.related_engineer);
            }
            clear_stock_warehouses(frm);
            frm.clear_table("items");

            (receipt.items || []).forEach((source_row) => {
                const row = frm.add_child("items");
                const available = Math.max(
                    0,
                    flt(source_row.qty || 0) - flt(source_row.dispatched_qty || 0)
                );

                row.item_code = source_row.item_code;
                row.item_name = source_row.item_name;
                row.material_type = "HTT";
                row.requested_qty = source_row.qty;
                row.approved_qty = available;
                row.qty = available;
                row.fulfilled_qty = available;
                row.uom = source_row.uom;
            });

            frm.refresh_field("items");
        });
    },

    site_work_order(frm) {
        load_site_work_order(frm);
    },
});

frappe.ui.form.on("WMS Material Issue Item", {
    item_code(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row || row.material_type) return;

        frappe.model.set_value(
            cdt,
            cdn,
            "material_type",
            frm.doc.material_type === "HTT" ? "HTT" : "MP"
        );
    },

    use_outstanding(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row || material_type_for_row(frm, row) === "HTT") return;

        const approved = flt(row.approved_qty || row.requested_qty || 0);
        const previous = flt(row.previous_outstanding_qty || 0);
        row.__reuse_initialized = 1;

        const applied = row.use_outstanding
            ? Math.min(previous, approved)
            : 0;

        row.outstanding_applied_qty = applied;
        row.qty = row.use_outstanding
            ? Math.max(0, approved - applied)
            : approved;
        row.fulfilled_qty = applied + flt(row.qty);
        frm.refresh_field("items");
        refresh_mp_outstanding(frm, row);
    },

    qty(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row) return;

        if (material_type_for_row(frm, row) === "HTT") {
            row.fulfilled_qty = flt(row.qty);
            frm.refresh_field("items");
            return;
        }

        recalculate_mp_row(frm, row);
    },
});

function load_site_work_order(frm) {
    const work_order_name = frm.doc.site_work_order;
    if (!work_order_name) return;

    if (frm.__wms_loading_site_work_order === work_order_name) {
        return;
    }

    frm.__wms_loading_site_work_order = work_order_name;

    frappe.db.get_doc(
        "Site Work Order",
        work_order_name
    ).then((work_order) => {
        // Do not apply a response for an older work order after the user
        // has selected a different one.
        if (frm.doc.site_work_order !== work_order_name) return;

        frm.set_value("site", work_order.site);
        frm.set_value("engineer", work_order.engineer);
        frm.set_value("material_type", work_order.material_type);
        frm.clear_table("items");

        (work_order.materials || []).forEach((source_row) => {
            const row = frm.add_child("items");
            row.item_code = source_row.item_code;
            row.requested_qty = source_row.qty;
            row.approved_qty = source_row.approved_qty || source_row.qty;
            row.qty = source_row.approved_qty || source_row.qty;
            row.uom = source_row.uom;
            row.material_type = source_row.material_type || work_order.material_type;
            row.use_outstanding = 0;
            row.outstanding_applied_qty = 0;
            row.__reuse_initialized = 0;
            row.fulfilled_qty = row.qty;
        });

        frm.refresh_field("items");
        refresh_all_mp_outstanding(frm);
    }).finally(() => {
        if (frm.__wms_loading_site_work_order === work_order_name) {
            frm.__wms_loading_site_work_order = null;
        }
    });
}

function refresh_all_mp_outstanding(frm) {
    (frm.doc.items || []).forEach((row) => {
        if (material_type_for_row(frm, row) === "MP") {
            refresh_mp_outstanding(frm, row);
        }
    });
}

function refresh_mp_outstanding(frm, row) {
    const engineer = frm.doc.engineer;
    const row_name = row && row.name;

    if (
        !row ||
        !row_name ||
        !engineer ||
        !row.item_code ||
        material_type_for_row(frm, row) !== "MP"
    ) {
        return;
    }

    frappe.xcall(
        "synarete_wms.synarete_wms.utils.accountability.get_engineer_item_outstanding",
        {
            engineer: engineer,
            item_code: row.item_code,
        }
    ).then((value) => {
        const current = locals[row.doctype] && locals[row.doctype][row_name];
        if (!current || frm.doc.engineer !== engineer) return;

        current.previous_outstanding_qty = flt(value || 0);
        if (flt(current.previous_outstanding_qty) > 0 && !current.__reuse_initialized) {
            current.use_outstanding = 1;
            current.__reuse_initialized = 1;
        }
        recalculate_mp_row(frm, current);
        frm.refresh_field("items");
        show_reuse_intro(frm);
    }).catch(() => {
        show_reuse_intro(frm);
    });
}

function recalculate_mp_row(frm, row) {
    if (material_type_for_row(frm, row) === "HTT") return;

    const approved = flt(row.approved_qty || row.requested_qty || 0);
    const previous = flt(row.previous_outstanding_qty || 0);
    const applied = row.use_outstanding
        ? Math.min(previous, approved)
        : 0;
    const maximum_new_issue = Math.max(0, approved - applied);

    row.outstanding_applied_qty = applied;

    if (row.use_outstanding && flt(row.qty) > maximum_new_issue) {
        row.qty = maximum_new_issue;
    }

    row.fulfilled_qty = applied + flt(row.qty);
    frm.refresh_field("items");
}

function show_reuse_intro(frm) {
    if (frm.doc.material_type === "HTT") {
        frm.set_intro();
        return;
    }

    const lines = [];
    (frm.doc.items || []).forEach((row) => {
        if (material_type_for_row(frm, row) !== "MP") return;
        const available = flt(row.previous_outstanding_qty || 0);
        if (!row.item_code || available <= 0) return;
        const requested = flt(row.approved_qty || row.requested_qty || 0);
        const reused = flt(row.outstanding_applied_qty || 0);
        const additional = flt(row.qty || 0);
        lines.push(
            `${row.item_code}: this engineer already holds ${available} of the same item. Reuse ${reused}, take ${additional} from Main Warehouse.`
        );
    });

    if (!lines.length) {
        // Different items cannot be reused. Do not show the leftover message.
        frm.set_intro();
        return;
    }

    frm.set_intro(
        __(
            "This engineer already holds leftover stock of the same item. Reused quantity is not transferred again and is not an expense."
        ) + "<br>" + lines.join(" | "),
        "blue"
    );
}

function material_type_for_row(frm, row) {
    return row.material_type || frm.doc.material_type;
}

function set_existing_item_material_type(frm, material_type) {
    (frm.doc.items || []).forEach((row) => {
        if (row.material_type !== material_type) {
            frappe.model.set_value(
                row.doctype,
                row.name,
                "material_type",
                material_type
            );
        }
    });
}

function set_default_stock_warehouses(frm) {
    const apply = (field, value) => {
        if (
            (frm.doc.material_type === "MP" || frm.doc.material_type === "Both") &&
            value &&
            !frm.doc[field]
        ) {
            frm.set_value(field, value);
        }
    };

    frappe.db.get_single_value("WMS Settings", "main_warehouse")
        .then((value) => apply("source_warehouse", value))
        .catch(() => {
            // Missing WMS Settings read permission must not freeze Save.
        });

    frappe.db.get_single_value("WMS Settings", "field_issued_warehouse")
        .then((value) => apply("target_warehouse", value))
        .catch(() => {});
}

function clear_stock_warehouses(frm) {
    if (frm.doc.source_warehouse) {
        frm.set_value("source_warehouse", null);
    }
    if (frm.doc.target_warehouse) {
        frm.set_value("target_warehouse", null);
    }
}

function toggle_stock_warehouses(frm) {
    const show = frm.doc.material_type === "MP" || frm.doc.material_type === "Both";
    frm.toggle_display("source_warehouse", show);
    frm.toggle_display("target_warehouse", show);
}
