frappe.ui.form.on("Purchase Order", {
    before_save(frm) {
        let ordered = 0;
        (frm.doc.items || []).forEach((row) => {
            ordered += flt(row.qty || 0);
        });

        frm.set_value("custom_wms_total_ordered_qty", ordered);

        const received = flt(frm.doc.custom_wms_total_received_qty || 0);
        frm.set_value(
            "custom_wms_remaining_qty",
            Math.max(0, ordered - received)
        );
    },

    refresh(frm) {
        const ordered = flt(frm.doc.custom_wms_total_ordered_qty || 0);
        const received = flt(frm.doc.custom_wms_total_received_qty || 0);

        if (ordered > 0) {
            const percentage = Math.min(100, Math.round((received / ordered) * 100));
            frm.dashboard.add_progress(
                __("WMS Delivery Progress"),
                percentage,
                percentage >= 100 ? "green" : percentage >= 50 ? "blue" : "orange"
            );
        }
    },
});
