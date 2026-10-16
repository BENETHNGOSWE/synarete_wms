frappe.ui.form.on("Asset Movement", {
    refresh(frm) {
        if (frm.doc.docstatus === 1 && frm.doc.custom_wms_destination_site) {
            frm.dashboard.set_headline_alert(
                __("Destination Site: {0}", [frm.doc.custom_wms_destination_site]),
                "blue"
            );
        }
    },
});
