function snwo_can_issue() {
    const roles = frappe.user_roles || [];
    return roles.includes("System Manager")
        || roles.includes("Warehouse Manager")
        || roles.includes("Stock Manager");
}

frappe.ui.form.on("SNWO Material Transaction", {
    refresh(frm) {
        set_interchange_flags(frm);
        if (!snwo_can_issue() && frm.doc.docstatus === 0) {
            frm.set_df_property("transaction_type", "options", "Request\nConsume\nReconcile");
        }
        if (frm.is_new() && frm.doc.original_work_order && !(frm.doc.items || []).length) {
            load_work_order_items(frm);
        }
        if (
            frm.doc.docstatus === 1
            && (frm.doc.transaction_type === "MP Issue" || frm.doc.is_mp_stock)
            && !frm.doc.stock_entry
            && snwo_can_issue()
        ) {
            frm.add_custom_button(__("Deduct MP Stock"), () => {
                frappe.xcall(
                    "synarete_wms.synarete_wms.utils.servicenow.deduct_mp_stock",
                    { transaction: frm.doc.name }
                ).then(() => frm.reload_doc());
            });
        }
    },

    original_work_order(frm) {
        if (!frm.doc.original_work_order) return;
        if (!frm.doc.received_for_work_order) {
            frm.set_value("received_for_work_order", frm.doc.original_work_order);
        }
        if (!frm.doc.issued_to_work_order) {
            frm.set_value("issued_to_work_order", frm.doc.original_work_order);
        }
        frappe.db.get_value(
            "ServiceNow Site Work Order",
            frm.doc.original_work_order,
            "site"
        ).then((r) => {
            if (r && r.message) {
                frm.set_value("site", r.message.site);
            }
        });
        load_work_order_items(frm);
        set_interchange_flags(frm);
    },

    issued_to_work_order(frm) {
        set_interchange_flags(frm);
        fill_qty_from_issued_to(frm);
    },

    received_for_work_order(frm) {
        set_interchange_flags(frm);
    },

    transaction_type(frm) {
        if (frm.doc.transaction_type === "MP Issue") {
            frm.set_value("is_mp_stock", 1);
            if (!frm.doc.warehouse) {
                frappe.db.get_single_value("WMS Settings", "main_warehouse").then((warehouse) => {
                    if (warehouse) frm.set_value("warehouse", warehouse);
                });
            }
        }
        if (frm.doc.transaction_type === "Interchange") {
            frm.set_value("is_interchange", 1);
        }
        set_interchange_flags(frm);
    },

    is_mp_stock(frm) {
        if (frm.doc.is_mp_stock && frm.doc.transaction_type === "Issue") {
            frm.set_value("transaction_type", "MP Issue");
        }
    },
});

function set_interchange_flags(frm) {
    const original = frm.doc.original_work_order;
    const issued_to = frm.doc.issued_to_work_order || original;
    const is_issue = ["Issue", "Interchange", "MP Issue"].includes(frm.doc.transaction_type);
    if (is_issue && original && issued_to && original !== issued_to) {
        frm.set_value("is_interchange", 1);
        if (frm.doc.transaction_type === "Issue" && !frm.doc.is_mp_stock) {
            frm.set_value("transaction_type", "Interchange");
        }
    }
}

function fill_qty_from_issued_to(frm) {
    if (frm.doc.docstatus !== 0) return;
    const original = frm.doc.original_work_order;
    const issued_to = frm.doc.issued_to_work_order;
    if (!issued_to || issued_to === original) return;
    if (!["Issue", "Interchange", "MP Issue"].includes(frm.doc.transaction_type)) return;

    frappe.db.get_doc("ServiceNow Site Work Order", issued_to).then((wo) => {
        const materials = wo.materials || [];
        const need_qty = (source) => {
            const requested = Math.max(flt(source && source.qty_requested), flt(wo.quantity) || 0);
            return Math.max(0, requested - flt(source && source.qty_issued));
        };
        const items = frm.doc.items || [];
        if (!items.length) {
            if (materials.length) {
                materials.forEach((source) => {
                    const qty = need_qty(source);
                    if (flt(qty) <= 0) return;
                    const row = frm.add_child("items");
                    row.item_code = source.item_code;
                    row.item_name = source.part_name;
                    row.uom = source.uom;
                    row.qty = qty;
                    row.original_work_order = original;
                    row.received_for_work_order = frm.doc.received_for_work_order;
                    row.issued_to_work_order = issued_to;
                });
            } else if (flt(wo.quantity) > 0) {
                const row = frm.add_child("items");
                row.item_code = wo.part_code;
                row.item_name = wo.part_name;
                row.qty = flt(wo.quantity);
                row.original_work_order = original;
                row.issued_to_work_order = issued_to;
            }
        } else {
            items.forEach((row) => {
                const source = materials.find((m) => m.item_code === row.item_code)
                    || (materials.length === 1 ? materials[0] : null);
                if (source) {
                    row.qty = need_qty(source);
                } else if (flt(wo.quantity) > 0) {
                    row.qty = flt(wo.quantity);
                }
                row.issued_to_work_order = issued_to;
            });
        }
        frm.refresh_field("items");
    });
}

function load_work_order_items(frm) {
    if (!frm.doc.original_work_order) return;
    frappe.db.get_doc("ServiceNow Site Work Order", frm.doc.original_work_order).then((wo) => {
        if ((frm.doc.items || []).length) return;
        (wo.materials || []).forEach((source) => {
            let qty = 0;
            if (frm.doc.transaction_type === "Receive") {
                qty = Math.max(0, flt(source.qty_requested) - flt(source.qty_received));
            } else if (frm.doc.transaction_type === "Issue" || frm.doc.transaction_type === "Interchange") {
                qty = flt(source.qty_warehouse_remaining);
            } else if (frm.doc.transaction_type === "Consume") {
                qty = flt(source.qty_remaining);
            } else if (frm.doc.transaction_type === "MP Issue") {
                qty = Math.max(0, flt(source.qty_requested) - flt(source.qty_issued));
            } else {
                qty = flt(source.qty_requested);
            }
            if (flt(qty) <= 0) {
                return;
            }
            const row = frm.add_child("items");
            row.item_code = source.item_code;
            row.item_name = source.part_name;
            row.uom = source.uom;
            row.qty = qty;
            row.original_work_order = wo.name;
            row.received_for_work_order = frm.doc.received_for_work_order || wo.name;
            row.issued_to_work_order = frm.doc.issued_to_work_order || wo.name;
        });
        frm.refresh_field("items");
    });
}
