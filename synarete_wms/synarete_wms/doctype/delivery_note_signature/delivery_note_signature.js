frappe.ui.form.on("Delivery Note Signature", {
    refresh(frm) {
        if (frm.is_new()) return;

        if (frm.doc.status === "Pending") {
            frm.add_custom_button(
                __("Confirm Receipt"),
                () => frappe.xcall(
                    "synarete_wms.synarete_wms.utils.signature.confirm_receipt",
                    { signature_name: frm.doc.name }
                ).then(() => frm.reload_doc()),
                __("WMS")
            );

            frm.add_custom_button(
                __("Mark Signed"),
                () => {
                    if (!frm.doc.signature) {
                        frappe.msgprint(__("Capture the engineer signature first."));
                        return;
                    }

                    frappe.xcall(
                        "synarete_wms.synarete_wms.utils.signature.mark_signed",
                        { signature_name: frm.doc.name }
                    ).then(() => frm.reload_doc());
                },
                __("WMS")
            );
        }
    },
});
