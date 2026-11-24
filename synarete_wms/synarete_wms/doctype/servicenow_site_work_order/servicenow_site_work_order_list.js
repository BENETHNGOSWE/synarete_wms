frappe.listview_settings["ServiceNow Site Work Order"] = {
    add_fields: ["assigned_to", "awaiting_warehouse_issue", "process_status", "status"],
    onload(listview) {
        if (listview.view_user_settings) {
            listview.view_user_settings.sort_by = "creation";
            listview.view_user_settings.sort_order = "desc";
        }
        listview.sort_by = "creation";
        listview.sort_order = "desc";
        const orig = listview.get_args.bind(listview);
        listview.get_args = function () {
            const args = orig();
            args.order_by =
                "`tabServiceNow Site Work Order`.`awaiting_warehouse_issue` desc, "
                + "`tabServiceNow Site Work Order`.`creation` desc";
            return args;
        };
        const bulk_approval_roles = [
            "Stock Manager",
            "Warehouse Manager",
            "System Manager",
        ];
        if ((frappe.user_roles || []).some((role) => bulk_approval_roles.includes(role))) {
            listview.page.add_inner_button(__("Approve Selected"), () => {
                const checked = listview.get_checked_items() || [];
                const names = checked
                    .map((item) => typeof item === "string" ? item : item && item.name)
                    .filter(Boolean);
                if (!names.length) {
                    frappe.msgprint(__("Select one or more ServiceNow Work Orders first."));
                    return;
                }

                frappe.confirm(
                    __(
                        `Approve ${names.length} selected ServiceNow Work Order(s)? `
                        + "Each order will use its existing WMS Approve action. "
                        + "Imported work orders are never approved automatically."
                    ),
                    () => {
                        frappe.call({
                            method: "synarete_wms.synarete_wms.utils.workflow_api.bulk_approve_servicenow_work_orders",
                            args: { work_orders: names },
                            freeze: true,
                            freeze_message: __("Approving selected ServiceNow work orders..."),
                        }).then((response) => {
                            const result = (response && response.message) || {};
                            const approved = result.approved || [];
                            const failed = result.failed || [];
                            const escape_html = (value) => String(value || "")
                                .replace(/&/g, "&amp;")
                                .replace(/</g, "&lt;")
                                .replace(/>/g, "&gt;")
                                .replace(/"/g, "&quot;")
                                .replace(/'/g, "&#39;");
                            const details = failed.map((row) =>
                                `${escape_html(row.name)}: ${escape_html(row.reason)}`
                            ).join("<br>");
                            const message = failed.length
                                ? `${__("Approved")}: ${approved.length}<br>`
                                    + `${__("Not approved")}: ${failed.length}<br><br>${details}`
                                : `${__("Approved")}: ${approved.length}`;

                            frappe.msgprint({
                                title: __("Bulk Approval Result"),
                                indicator: failed.length ? "orange" : "green",
                                message: message,
                            });
                            listview.refresh();
                        });
                    }
                );
            });
        }

        if (!listview.filter_area) return;
        const roles = frappe.user_roles || [];
        const is_wm = roles.includes("Warehouse Manager") || roles.includes("Stock Manager");
        if (is_wm || roles.includes("System Manager")) {
            listview.page.add_inner_button(__("Awaiting Material"), () => {
                listview.filter_area.add([
                    [listview.doctype, "awaiting_warehouse_issue", "=", 1],
                ]);
            });
        } else {
            listview.page.add_inner_button(__("My Work Orders"), () => {
                frappe.db.get_value("Employee", { user_id: frappe.session.user }, "name").then((r) => {
                    const employee = r && r.message && r.message.name;
                    if (!employee) {
                        frappe.msgprint(__("Link your User ID on the Employee record to see assigned jobs."));
                        return;
                    }
                    listview.filter_area.add([
                        [listview.doctype, "assigned_to", "=", employee],
                    ]);
                });
            });
        }
    },
    get_indicator(doc) {
        if (
            cint(doc.awaiting_warehouse_issue)
            || doc.status === "Awaiting Material"
            || doc.process_status === "Material Required"
        ) {
            return [__("Awaiting Material"), "orange", "awaiting_warehouse_issue,=,1"];
        }
        if (doc.process_status === "Completed") {
            return [__("Completed"), "green", "process_status,=,Completed"];
        }
        if (doc.process_status === "Material Consumed") {
            return [__("Consumed"), "blue", "process_status,=,Material Consumed"];
        }
        if (doc.process_status === "Material Issued") {
            return [__("Issued"), "blue", "process_status,=,Material Issued"];
        }
        return [__(doc.status || "Open"), "gray", "status,=," + (doc.status || "Open")];
    },
};
