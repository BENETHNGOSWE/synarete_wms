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
        if (!listview.filter_area) return;
        const roles = frappe.user_roles || [];
        const is_wm = roles.includes("Warehouse Manager") || roles.includes("Stock Manager");
        if (is_wm || roles.includes("System Manager")) {
            listview.page.add_inner_button(__("Awaiting Material"), () => {
                listview.filter_area.add([
                    [listview.doctype, "awaiting_warehouse_issue", "=", 1],
                ]);
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
