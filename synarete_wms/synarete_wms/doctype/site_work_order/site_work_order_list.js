frappe.listview_settings["Site Work Order"] = {
    add_fields: ["engineer", "engineer_name", "status"],
    onload(listview) {
        if (listview.view_user_settings) {
            listview.view_user_settings.sort_by = "creation";
            listview.view_user_settings.sort_order = "desc";
        }
        listview.sort_by = "creation";
        listview.sort_order = "desc";

        const roles = frappe.user_roles || [];
        const is_manager =
            roles.includes("Warehouse Manager")
            || roles.includes("Stock Manager")
            || roles.includes("System Manager");

        if (roles.includes("Stock Manager")) {
            listview.page.add_inner_button(__("Approve Selected"), () => {
                const checked = listview.get_checked_items() || [];
                const names = checked
                    .map((item) => typeof item === "string" ? item : item && item.name)
                    .filter(Boolean);

                if (!names.length) {
                    frappe.msgprint(__("Select one or more Site Work Orders first."));
                    return;
                }

                frappe.confirm(
                    __(
                        `Approve ${names.length} selected Site Work Order(s)? `
                        + "Only orders still awaiting Stock Manager review will be approved. "
                        + "The existing self-approval rule still applies."
                    ),
                    () => {
                        frappe.call({
                            method: "synarete_wms.synarete_wms.utils.workflow_api.bulk_approve_site_work_orders",
                            args: { work_orders: names },
                            freeze: true,
                            freeze_message: __("Approving selected work orders..."),
                        }).then((response) => {
                            const result = (response && response.message) || {};
                            const approved = result.approved || [];
                            const failed = result.failed || [];
                            const escape_html = (value) => String(value || "")
                                .replace(/&/g, "&amp;")
                                .replace(/</g, "&lt;")
                                .replace(/>/g, "&gt;")
                                .replace(/\"/g, "&quot;")
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

        if (!listview.filter_area) {
            return;
        }
        if (!is_manager) {
            listview.page.add_inner_button(__("My Work Orders"), () => {
                frappe.db.get_value("Employee", { user_id: frappe.session.user }, "name").then((r) => {
                    const employee = r && r.message && r.message.name;
                    if (!employee) {
                        frappe.msgprint(__("Link your User ID on the Employee record to see assigned jobs."));
                        return;
                    }
                    listview.filter_area.add([
                        [listview.doctype, "engineer", "=", employee],
                    ]);
                });
            });
        }
    },
};
