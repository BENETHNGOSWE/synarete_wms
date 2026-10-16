frappe.pages["servicenow-dashboard"] = frappe.pages["servicenow-dashboard"] || {};

frappe.pages["servicenow-dashboard"].on_page_load = function () {
	frappe.set_route("snwo-overview");
};

frappe.pages["servicenow-dashboard"].on_page_show = function () {
	frappe.set_route("snwo-overview");
};
