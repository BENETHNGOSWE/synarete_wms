frappe.ui.form.on("Asset", {
    refresh(frm) {
        if (frm.doc.docstatus !== 1) return;

        frm.add_custom_button(
            __("Move Asset"),
            () => {
                frappe.new_doc("Asset Movement", {
                    custom_wms_engineer: frm.doc.custom_wms_installed_by,
                    assets: [{ asset: frm.doc.name }],
                });
            },
            __("WMS")
        );
    },
});
