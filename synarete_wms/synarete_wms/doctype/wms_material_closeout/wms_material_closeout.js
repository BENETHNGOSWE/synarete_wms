frappe.ui.form.on("WMS Material Closeout", {
    onload(frm) {
        if (frm.doc.work_order && !(frm.doc.items || []).length) {
            fill_issued_items(frm);
        }
    },

    refresh(frm) {
        frm.set_df_property("items", "cannot_add_rows", 1);
        frm.set_df_property("items", "cannot_delete_rows", 1);
        frm.set_intro(
            __(
                "Enter cumulative totals to date, not only the new amount. Used material was consumed and is not returned to stock; Unused is material physically returned to Main Warehouse. Do not reduce quantities below Already Used or Already Returned."
            ),
            "blue"
        );
    },

    work_order(frm) {
        fill_issued_items(frm);
    },
});

frappe.ui.form.on("WMS Material Closeout Item", {
    used_qty(frm, cdt, cdn) {
        update_shortfall(cdt, cdn);
    },
    returned_unused_qty(frm, cdt, cdn) {
        update_shortfall(cdt, cdn);
    },
});

function update_shortfall(cdt, cdn) {
    const row = locals[cdt][cdn];
    const shortfall = Math.max(
        0,
        flt(row.issued_qty) - flt(row.used_qty) - flt(row.returned_unused_qty)
    );
    frappe.model.set_value(cdt, cdn, "shortfall_qty", shortfall);
}

function fill_issued_items(frm) {
    if (!frm.doc.work_order || !frm.doc.work_order_type) {
        return;
    }
    frappe
        .xcall("synarete_wms.synarete_wms.utils.closeout.get_closeout_lines", {
            work_order_type: frm.doc.work_order_type,
            work_order: frm.doc.work_order,
        })
        .then((lines) => {
            frm.clear_table("items");
            (lines || []).forEach((line) => {
                const row = frm.add_child("items");
                frappe.model.set_value(row.doctype, row.name, "item_code", line.item_code);
                frappe.model.set_value(row.doctype, row.name, "item_name", line.item_name);
                frappe.model.set_value(row.doctype, row.name, "issued_qty", line.issued_qty);
                frappe.model.set_value(
                    row.doctype,
                    row.name,
                    "previously_used_qty",
                    line.previously_used_qty
                );
                frappe.model.set_value(
                    row.doctype,
                    row.name,
                    "previously_returned_qty",
                    line.previously_returned_qty
                );
                frappe.model.set_value(row.doctype, row.name, "used_qty", line.used_qty);
                frappe.model.set_value(
                    row.doctype,
                    row.name,
                    "returned_unused_qty",
                    line.returned_unused_qty
                );
                frappe.model.set_value(
                    row.doctype,
                    row.name,
                    "shortfall_qty",
                    Math.max(
                        0,
                        flt(line.issued_qty)
                            - flt(line.used_qty)
                            - flt(line.returned_unused_qty)
                    )
                );
                frappe.model.set_value(
                    row.doctype,
                    row.name,
                    "accountability",
                    line.accountability
                );
                frappe.model.set_value(
                    row.doctype,
                    row.name,
                    "material_issue",
                    line.material_issue
                );
            });
            frm.refresh_field("items");
            if (!(lines || []).length) {
                frappe.msgprint(__("No issued material to return on this work order."));
            }
        });
}
