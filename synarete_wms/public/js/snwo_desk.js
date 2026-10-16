(function () {
	function current_route() {
		if (frappe.get_route) {
			return frappe.get_route() || [];
		}
		return [];
	}

	function is_colliding_workspace(route) {
		const r = (route || []).map(function (part) {
			return (part || "").toString();
		});
		if (!r.length) {
			return false;
		}
		if (r[0] === "snwo-overview") {
			return false;
		}
		if (r[0] === "servicenow-dashboard") {
			return true;
		}
		if (
			(r[0] === "Workspaces" || r[0] === "workspace")
			&& (
				r[1] === "ServiceNow Dashboard"
				|| r[1] === "servicenow-dashboard"
			)
		) {
			return true;
		}
		return false;
	}

	function maybe_open_dashboard() {
		if (is_colliding_workspace(current_route())) {
			frappe.set_route("snwo-overview");
		}
	}

	if (frappe.router && frappe.router.on) {
		frappe.router.on("change", maybe_open_dashboard);
	}
	$(document).on("app_ready", maybe_open_dashboard);
	$(document).on("page-change", maybe_open_dashboard);
})();
