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

        if (frm.doc.custom_wms_supplier_outstanding) {
            frm.dashboard.set_headline_alert(
                frm.doc.custom_wms_supplier_outstanding.replace(/\n/g, "<br>"),
                "orange"
            );
        }

        const can_receive =
            frappe.user.has_role("Warehouse Manager")
            || frappe.user.has_role("Stock Manager")
            || frappe.user.has_role("System Manager");
        const remaining = flt(frm.doc.custom_wms_remaining_qty || 0);
        const htt = frm.doc.custom_wms_material_type === "HTT";

        if (frm.doc.docstatus === 1 && can_receive && remaining > 0 && !htt) {
            frm.add_custom_button(__("Receive Batch"), () => open_receive_batch(frm), __("WMS"));
        }

        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__("Receiving History"), () => {
                frm.scroll_to_field("custom_wms_delivery_phases");
            }, __("WMS"));
        }
    },

    supplier(frm) {
        if (!frm.doc.supplier) {
            return;
        }
        frappe
            .xcall("synarete_wms.synarete_wms.utils.po_receive.get_supplier_outstanding", {
                supplier: frm.doc.supplier,
                exclude_po: frm.doc.name,
            })
            .then((rows) => {
                if (!(rows || []).length) {
                    return;
                }
                const lines = (rows || []).map(
                    (row) =>
                        `${row.item_code} on ${row.purchase_order}: ${row.outstanding_qty} outstanding`
                );
                frappe.msgprint({
                    title: __("Previous outstanding from this supplier"),
                    indicator: "orange",
                    message:
                        __("Do not add these quantities onto this new PO. Receive leftover on the original PO.")
                        + "<br><br>"
                        + lines.join("<br>"),
                });
            });
    },
});

function open_receive_batch(frm) {
    frappe
        .xcall("synarete_wms.synarete_wms.utils.po_receive.get_po_receive_preview", {
            purchase_order: frm.doc.name,
        })
        .then((preview) => {
            const fields = [
                {
                    fieldname: "warehouse",
                    fieldtype: "Link",
                    options: "Warehouse",
                    label: __("Receive Into"),
                    default: preview.warehouse,
                    reqd: 1,
                },
                {
                    fieldname: "posting_date",
                    fieldtype: "Date",
                    label: __("Receiving Date"),
                    default: frappe.datetime.get_today(),
                    reqd: 1,
                },
                {
                    fieldname: "items",
                    fieldtype: "Table",
                    label: __("This Batch"),
                    cannot_add_rows: true,
                    in_place_edit: true,
                    data: (preview.items || []).map((row) => Object.assign({}, row)),
                    fields: [
                        {
                            fieldname: "po_detail",
                            fieldtype: "Data",
                            hidden: 1,
                        },
                        {
                            fieldname: "item_code",
                            fieldtype: "Data",
                            in_list_view: 1,
                            read_only: 1,
                            label: __("Item"),
                            columns: 2,
                        },
                        {
                            fieldname: "ordered_qty",
                            fieldtype: "Float",
                            in_list_view: 1,
                            read_only: 1,
                            label: __("Ordered"),
                            columns: 1,
                        },
                        {
                            fieldname: "previously_received_qty",
                            fieldtype: "Float",
                            in_list_view: 1,
                            read_only: 1,
                            label: __("Received"),
                            columns: 1,
                        },
                        {
                            fieldname: "outstanding_qty",
                            fieldtype: "Float",
                            in_list_view: 1,
                            read_only: 1,
                            label: __("Outstanding"),
                            columns: 1,
                        },
                        {
                            fieldname: "previous_po_outstanding_qty",
                            fieldtype: "Float",
                            in_list_view: 1,
                            read_only: 1,
                            label: __("Prev PO"),
                            columns: 1,
                        },
                        {
                            fieldname: "batch_qty",
                            fieldtype: "Float",
                            in_list_view: 1,
                            label: __("This Batch"),
                            columns: 2,
                        },
                    ],
                },
            ];

            const dialog = new frappe.ui.Dialog({
                title: __("Receive Batch for {0}", [frm.doc.name]),
                fields,
                primary_action_label: __("Receive Batch"),
                primary_action(values) {
                    const rows = (dialog.fields_dict.items.grid.get_data() || []).map((row) => ({
                        po_detail: row.po_detail,
                        item_code: row.item_code,
                        batch_qty: row.batch_qty,
                    }));
                    dialog.hide();
                    frappe
                        .xcall(
                            "synarete_wms.synarete_wms.utils.po_receive.submit_po_receive_batch",
                            {
                                purchase_order: frm.doc.name,
                                items: rows,
                                warehouse: values.warehouse,
                                posting_date: values.posting_date,
                            }
                        )
                        .then((result) => {
                            frappe.show_alert({
                                message: __("Received on {0}", [result.purchase_receipt]),
                                indicator: "green",
                            });
                            frm.reload_doc();
                        });
                },
            });
            dialog.show();
        });
}
