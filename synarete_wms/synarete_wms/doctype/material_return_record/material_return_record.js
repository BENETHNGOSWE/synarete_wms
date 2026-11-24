frappe.ui.form.on("Material Return Record", {
    refresh(frm) {
        if (frm.doc.material_type === "MP") {
            frm.set_intro(
                __(
                    "For site work order returns use Material → Return Material "
                    + "(Used / Unused on the issued item). This old form is for HTT / replacement."
                )
            );
        }
    },

    material_issue(frm) {
        if (!frm.doc.material_issue) {
            return;
        }
        frappe.db.get_doc("WMS Material Issue", frm.doc.material_issue).then((issue) => {
            if (issue.site) {
                frm.set_value("site", issue.site);
            }
            if (issue.engineer) {
                frm.set_value("engineer", issue.engineer);
            }
            const first = (issue.items || [])[0];
            if (first && first.item_code && !frm.doc.new_item_code) {
                frm.set_value("new_item_code", first.item_code);
                frm.set_value("issued_qty", first.qty);
            }
        });
    },
});
