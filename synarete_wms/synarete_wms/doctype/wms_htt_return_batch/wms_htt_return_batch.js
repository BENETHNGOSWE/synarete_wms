frappe.ui.form.on("WMS HTT Return Batch", {
    refresh(frm) {
        frm.set_intro(
            __(
                "Record the warehouse's bulk return to HTT. Use Used or Faulty items only. "
                + "This record does not change Work Orders or post stock / GL entries."
            ),
            "blue"
        );
    },
});

frappe.ui.form.on("WMS HTT Return Batch Item", {
    material_issue(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.material_issue) return;

        frappe.db.get_doc("WMS Material Issue", row.material_issue).then((issue) => {
            frappe.model.set_value(
                cdt,
                cdn,
                "work_order",
                issue.site_work_order || ""
            );
            frappe.model.set_value(
                cdt,
                cdn,
                "servicenow_work_order",
                issue.servicenow_work_order || ""
            );
            if (!frm.doc.customer && issue.customer) {
                frm.set_value("customer", issue.customer);
            }

            const htt_items = (issue.items || []).filter(
                (item) => (item.material_type || issue.material_type) === "HTT"
            );
            if (htt_items.length === 1 && !row.item_code) {
                frappe.model.set_value(cdt, cdn, "item_code", htt_items[0].item_code);
                frappe.model.set_value(cdt, cdn, "uom", htt_items[0].uom);
            }
        });
    },

    item_code(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.item_code) return;
        frappe.db.get_value("Item", row.item_code, ["item_name", "stock_uom"]).then((r) => {
            if (r && r.message) {
                frappe.model.set_value(
                    cdt,
                    cdn,
                    "item_name",
                    r.message.item_name || row.item_code
                );
                if (!row.uom && r.message.stock_uom) {
                    frappe.model.set_value(cdt, cdn, "uom", r.message.stock_uom);
                }
            }
        });
    },
});
