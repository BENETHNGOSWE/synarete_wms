frappe.ui.form.on("Delivery Note", {
    refresh(frm) {
        if (frm.doc.docstatus !== 1) return;

        if (frm.doc.custom_wms_site_work_order) {
            frm.add_custom_button(
                __("Open WMS Site Work Order"),
                () => frappe.set_route(
                    "Form",
                    "Site Work Order",
                    frm.doc.custom_wms_site_work_order
                ),
                __("WMS")
            );
        }

        if (frm.doc.custom_wms_signature_status) {
            frm.dashboard.set_headline_alert(
                __("Signature Status: {0}", [frm.doc.custom_wms_signature_status]),
                frm.doc.custom_wms_signature_status === "Signed" ? "green" : "orange"
            );
        }

        frappe.db.get_list("Delivery Note Signature", {
            filters: { delivery_note: frm.doc.name },
            fields: ["name", "status"],
            limit: 1,
        }).then((records) => {
            if (!records.length) return;

            frm.add_custom_button(
                __("Manage Signature"),
                () => frappe.set_route(
                    "Form",
                    "Delivery Note Signature",
                    records[0].name
                ),
                __("WMS")
            );
        });
    },
});
