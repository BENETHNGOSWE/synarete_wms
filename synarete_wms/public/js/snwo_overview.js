frappe.pages["snwo-overview"] = frappe.pages["snwo-overview"] || {};

frappe.pages["snwo-overview"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("ServiceNow Dashboard"),
		single_column: true,
	});

	$(wrapper).addClass("snwo-dashboard-shell");
	if (page.wrapper) {
		$(page.wrapper).addClass("snwo-dashboard-shell");
	}
	page.main.addClass("snwo-dashboard-page");
	$(dashboard_html()).appendTo(page.main);
	inject_styles();

	const state = {
		from_date: frappe.datetime.month_start(),
		to_date: month_end(),
		group_by: "week",
		charts: {},
	};

	page.add_field({
		fieldname: "from_date",
		label: __("From"),
		fieldtype: "Date",
		default: state.from_date,
		change() {
			state.from_date = this.get_value();
			load_dashboard(page, state);
		},
	});
	page.add_field({
		fieldname: "to_date",
		label: __("To"),
		fieldtype: "Date",
		default: state.to_date,
		change() {
			state.to_date = this.get_value();
			load_dashboard(page, state);
		},
	});
	page.add_inner_button(__("This Month"), () => {
		state.from_date = frappe.datetime.month_start();
		state.to_date = month_end();
		page.fields_dict.from_date.set_value(state.from_date);
		page.fields_dict.to_date.set_value(state.to_date);
		load_dashboard(page, state);
	});
	page.set_primary_action(__("Export Report"), () => export_report(state), "octicon octicon-desktop-download");

	bind_nav(page, state);
	load_dashboard(page, state);
};

frappe.pages["snwo-overview"].on_page_show = function () {
	$(".snwo-dashboard-page").closest(".page-body").addClass("snwo-dashboard-body");
	$(".snwo-dashboard-shell").closest(".page-container").addClass("snwo-dashboard-shell");
};

function bind_nav(page, state) {
	page.main.on("click", "[data-snwo-nav]", function () {
		const target = $(this).data("snwo-nav");
		if (target === "overview") {
			return;
		}
		if (target === "work-orders") {
			frappe.set_route("List", "ServiceNow Site Work Order");
		} else if (target === "materials") {
			frappe.set_route("query-report", "SNWO Material Traceability");
		} else if (target === "reports") {
			frappe.set_route("query-report", "SNWO Material Traceability");
		} else if (target === "interchange") {
			frappe.set_route("query-report", "SNWO Interchange Report");
		} else if (target === "mp") {
			frappe.set_route("query-report", "SNWO MP Material Report");
		}
	});
	page.main.on("change", "[data-chart-group]", function () {
		state.group_by = this.value || "week";
		page.main.find("[data-chart-group]").val(state.group_by);
		load_dashboard(page, state);
	});
}

function load_dashboard(page, state) {
	frappe.call({
		method: "synarete_wms.synarete_wms.utils.servicenow_dashboard.get_overview",
		args: {
			from_date: state.from_date,
			to_date: state.to_date,
			group_by: state.group_by || "week",
		},
		freeze: true,
		freeze_message: __("Loading ServiceNow dashboard..."),
		callback(r) {
			const data = r.message || {};
			render_kpis(page, data);
			try {
				render_charts(page, state, data);
			} catch (e) {
				console.error(e);
			}
		},
		error() {
			frappe.msgprint(__("Could not load ServiceNow dashboard data."));
		},
	});
}

function month_end() {
	if (frappe.datetime.month_end) {
		return frappe.datetime.month_end();
	}
	return frappe.datetime.add_days(
		frappe.datetime.add_months(frappe.datetime.month_start(), 1),
		-1
	);
}

function fmt(n) {
	const value = Math.round(flt(n));
	if (typeof frappe.format_number === "function") {
		return frappe.format_number(value, null, 0);
	}
	return String(value);
}

function render_kpis(page, data) {
	page.main.find("[data-kpi='total_work_orders']").text(fmt(data.total_work_orders));
	page.main.find("[data-kpi='material_received']").text(fmt(data.material_received));
	page.main.find("[data-kpi='completed_work_orders']").text(fmt(data.completed_work_orders));
	page.main.find("[data-kpi='completion_pct']").text((data.completion_pct || 0) + "% of total");
	page.main.find("[data-kpi='in_progress_work_orders']").text(fmt(data.in_progress_work_orders));
	page.main.find("[data-kpi='in_progress_pct']").text((data.in_progress_pct || 0) + "% of total");
	page.main.find("[data-kpi='mp_site_count']").text(fmt(data.mp_site_count));
	page.main.find("[data-kpi='material_not_issued']").text(fmt(data.material_not_issued));
	page.main.find("[data-kpi='material_returned']").text(fmt(data.material_returned));
	page.main.find("[data-range]").text(
		frappe.datetime.str_to_user(data.from_date) + " – " + frappe.datetime.str_to_user(data.to_date)
	);

	page.main.find("[data-sum='completion']").text((data.completion_pct || 0) + "%");
	page.main.find("[data-sum='received']").text(fmt(data.material_received));
	page.main.find("[data-sum='not_issued']").text(fmt(data.material_not_issued) + " pcs");
	page.main.find("[data-sum='mp']").text(fmt(data.mp_site_count));
	const mp_count = data.mp_site_count || 0;
	page.main.find("[data-kpi='mp_site_hint']").text(
		mp_count === 1
			? __("1 site used MP material")
			: __("{0} sites used MP material", [mp_count])
	);
	page.main.find("[data-sum='returned']").text(fmt(data.material_returned) + " pcs");
	page.main.find("[data-sum='progress']").text(
		fmt(data.in_progress_work_orders) + " (" + (data.in_progress_pct || 0) + "%)"
	);
}

function render_charts(page, state, data) {
	const charts = data.charts || {};
	const labels = charts.labels && charts.labels.length ? charts.labels : ["-"];
	const zeros = labels.map(() => 0);
	const interchange = (charts.interchange || []).length ? charts.interchange : zeros;
	const consumed = (charts.consumed || []).length ? charts.consumed : zeros;
	const remaining = (charts.remaining || []).length ? charts.remaining : zeros;

	["snwo-interchange-chart", "snwo-consumed-chart"].forEach((id) => {
		page.main.find("#" + id).empty();
	});

	const axis_mode = labels.length > 10 ? 1 : 0;

	state.charts.interchange = new frappe.Chart(
		page.main.find("#snwo-interchange-chart")[0],
		{
			title: "",
			data: {
				labels: labels,
				datasets: [
					{
						name: __("Site Interchange Activity"),
						values: interchange,
					},
				],
			},
			type: "line",
			height: 250,
			colors: ["#2563eb"],
			lineOptions: { hideDots: 0, regionFill: 1, dotSize: 4 },
			axisOptions: { xIsSeries: axis_mode, shortenYAxisNumbers: 1 },
			tooltipOptions: { formatTooltipY: (d) => fmt(d) },
		}
	);

	state.charts.consumed = new frappe.Chart(
		page.main.find("#snwo-consumed-chart")[0],
		{
			title: "",
			data: {
				labels: labels,
				datasets: [
					{
						name: __("Consumed Stock"),
						values: consumed,
					},
					{
						name: __("Remaining Stock"),
						values: remaining,
					},
				],
			},
			type: "bar",
			height: 250,
			colors: ["#16a34a", "#3b82f6"],
			barOptions: { stacked: 0, spaceRatio: 0.45 },
			axisOptions: { xIsSeries: axis_mode, shortenYAxisNumbers: 1 },
			tooltipOptions: { formatTooltipY: (d) => fmt(d) },
		}
	);
}

function export_report(state) {
	const url = frappe.urllib.get_full_url(
		"/api/method/synarete_wms.synarete_wms.utils.servicenow_dashboard.export_overview?"
		+ "from_date=" + encodeURIComponent(state.from_date)
		+ "&to_date=" + encodeURIComponent(state.to_date)
		+ "&group_by=" + encodeURIComponent(state.group_by || "week")
	);
	window.open(url);
}

function icon_svg(paths) {
	return (
		'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" '
		+ 'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
		+ paths
		+ "</svg>"
	);
}

function inject_styles() {
	let css = document.getElementById("snwo-dashboard-css");
	if (!css) {
		css = document.createElement("style");
		css.id = "snwo-dashboard-css";
		document.head.appendChild(css);
	}
	css.innerHTML = `
	.snwo-dashboard-shell .page-head {
		background: #ffffff !important;
		border-bottom: 1px solid #e8edf4 !important;
		box-shadow: none !important;
	}
	.snwo-dashboard-shell .page-head h3,
	.snwo-dashboard-shell .page-title h3,
	.snwo-dashboard-shell .page-title .title-text {
		font-weight: 700 !important;
		color: #0f172a !important;
		letter-spacing: -0.02em;
	}
	.snwo-dashboard-shell .btn-primary {
		background: #1d4ed8 !important;
		border: 1px solid #1d4ed8 !important;
		border-radius: 10px !important;
		font-weight: 600 !important;
		padding: 7px 14px !important;
		box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08) !important;
	}
	.snwo-dashboard-shell .btn-primary:hover {
		background: #1e40af !important;
		border-color: #1e40af !important;
	}
	.snwo-dashboard-shell .page-actions .btn-default,
	.snwo-dashboard-shell .inner-group-button .btn {
		background: #ffffff !important;
		border: 1px solid #dbe2ea !important;
		border-radius: 10px !important;
		color: #334155 !important;
		font-weight: 600 !important;
		box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04) !important;
	}
	.snwo-dashboard-shell .frappe-control[data-fieldtype="Date"] .control-input,
	.snwo-dashboard-shell .frappe-control[data-fieldtype="Date"] input {
		background: #ffffff !important;
		border: 1px solid #dbe2ea !important;
		border-radius: 10px !important;
		font-weight: 500 !important;
		color: #0f172a !important;
	}
	.snwo-dashboard-body {
		background: #f4f7fb !important;
	}
	.snwo-dashboard-page {
		padding-bottom: 28px;
	}
	.snwo-wrap {
		font-family: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
		color: #0f172a;
		padding: 4px 4px 8px;
		max-width: 1280px;
	}
	.snwo-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 16px;
		margin: 8px 0 20px;
	}
	.snwo-header h1 {
		margin: 0;
		font-size: 30px;
		line-height: 1.15;
		font-weight: 750;
		letter-spacing: -0.03em;
		color: #0b1220;
	}
	.snwo-header p {
		margin: 8px 0 0;
		color: #64748b;
		font-size: 14px;
	}
	.snwo-range {
		background: #ffffff;
		border: 1px solid #e6edf5;
		border-radius: 999px;
		padding: 8px 14px;
		color: #475569;
		font-size: 13px;
		font-weight: 600;
		box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
		white-space: nowrap;
	}
	.snwo-nav {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		margin-bottom: 20px;
	}
	.snwo-nav button {
		border: 1px solid transparent;
		background: #ffffff;
		border-radius: 999px;
		padding: 8px 16px;
		color: #475569;
		font-size: 13px;
		font-weight: 600;
		box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
	}
	.snwo-nav button:hover {
		color: #1e3a8a;
		border-color: #dbeafe;
	}
	.snwo-nav button.active {
		background: #e8f0ff;
		color: #1d4ed8;
		border-color: #d6e4ff;
		box-shadow: none;
	}
	.snwo-kpis {
		display: grid;
		grid-template-columns: repeat(4, minmax(190px, 1fr));
		gap: 16px;
		margin-bottom: 16px;
	}
	.snwo-kpis.row2 {
		grid-template-columns: repeat(3, minmax(190px, 1fr));
	}
	.snwo-card {
		position: relative;
		background: #ffffff;
		border: 1px solid #eef2f7;
		border-radius: 16px;
		padding: 18px 18px 20px;
		min-height: 148px;
		box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 10px 24px rgba(15, 23, 42, 0.04);
		overflow: hidden;
	}
	.snwo-card::after {
		content: "";
		position: absolute;
		left: 0;
		right: 0;
		bottom: 0;
		height: 3px;
		background: var(--snwo-accent, #3b82f6);
	}
	.snwo-card.accent-blue { --snwo-accent: #3b82f6; }
	.snwo-card.accent-green { --snwo-accent: #16a34a; }
	.snwo-card.accent-purple { --snwo-accent: #7c3aed; }
	.snwo-card.accent-orange { --snwo-accent: #ea580c; }
	.snwo-card.accent-amber { --snwo-accent: #d97706; }
	.snwo-card.accent-teal { --snwo-accent: #0d9488; }
	.snwo-card.accent-rose { --snwo-accent: #e11d48; }
	.snwo-card .label {
		font-size: 11px;
		letter-spacing: 0.06em;
		font-weight: 700;
		color: #64748b;
		text-transform: uppercase;
		line-height: 1.35;
	}
	.snwo-card .value {
		font-size: 36px;
		line-height: 1.1;
		font-weight: 750;
		margin-top: 10px;
		color: #0b1220;
		letter-spacing: -0.03em;
	}
	.snwo-card .hint {
		color: #94a3b8;
		font-size: 12.5px;
		margin-top: 8px;
		font-weight: 500;
	}
	.snwo-icon {
		width: 36px;
		height: 36px;
		border-radius: 10px;
		display: flex;
		align-items: center;
		justify-content: center;
		margin-bottom: 14px;
	}
	.snwo-icon svg {
		width: 18px;
		height: 18px;
	}
	.snwo-icon.blue { background: #eff6ff; color: #2563eb; }
	.snwo-icon.green { background: #f0fdf4; color: #16a34a; }
	.snwo-icon.purple { background: #f5f3ff; color: #7c3aed; }
	.snwo-icon.orange { background: #fff7ed; color: #ea580c; }
	.snwo-icon.amber { background: #fffbeb; color: #d97706; }
	.snwo-icon.teal { background: #f0fdfa; color: #0d9488; }
	.snwo-icon.rose { background: #fff1f2; color: #e11d48; }
	.snwo-charts {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 16px;
		margin: 4px 0 16px;
	}
	.snwo-chart {
		background: #ffffff;
		border: 1px solid #eef2f7;
		border-radius: 16px;
		padding: 18px 18px 10px;
		box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 10px 24px rgba(15, 23, 42, 0.04);
	}
	.snwo-chart-head {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 12px;
		margin-bottom: 6px;
	}
	.snwo-chart h3 {
		margin: 0;
		font-size: 15px;
		font-weight: 700;
		color: #0f172a;
		letter-spacing: -0.01em;
		text-transform: none;
	}
	.snwo-chart .snwo-chart-desc {
		margin: 4px 0 0;
		color: #64748b;
		font-size: 12.5px;
	}
	.snwo-chart-select {
		border: 1px solid #e2e8f0;
		background: #ffffff;
		border-radius: 8px;
		padding: 5px 10px;
		font-size: 12px;
		font-weight: 600;
		color: #334155;
	}
	.snwo-chart .frappe-chart,
	.snwo-chart .chart-container {
		font-family: inherit;
	}
	.snwo-summary {
		background: #ffffff;
		border: 1px solid #eef2f7;
		border-radius: 16px;
		padding: 16px 18px;
		box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 10px 24px rgba(15, 23, 42, 0.04);
		display: grid;
		grid-template-columns: repeat(6, minmax(120px, 1fr));
		gap: 12px 18px;
	}
	.snwo-summary .item .k {
		color: #64748b;
		font-size: 12px;
		font-weight: 600;
	}
	.snwo-summary .item .v {
		font-weight: 750;
		margin-top: 4px;
		font-size: 15px;
		color: #0f172a;
	}
	@media (max-width: 1100px) {
		.snwo-kpis, .snwo-kpis.row2, .snwo-charts, .snwo-summary {
			grid-template-columns: 1fr 1fr;
		}
	}
	@media (max-width: 700px) {
		.snwo-kpis, .snwo-kpis.row2, .snwo-charts, .snwo-summary {
			grid-template-columns: 1fr;
		}
		.snwo-header { flex-direction: column; }
		.snwo-card .value { font-size: 30px; }
	}
	`;
}

function dashboard_html() {
	const clipboard = icon_svg(
		'<path d="M8 7V6a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v1"/>'
		+ '<rect x="6" y="7" width="12" height="13" rx="2"/>'
		+ '<path d="M9 12h6M9 16h4"/>'
	);
	const package_icon = icon_svg(
		'<path d="M21 8 12 3 3 8l9 5 9-5Z"/>'
		+ '<path d="M3 8v8l9 5 9-5V8"/>'
		+ '<path d="M12 13v8"/>'
	);
	const check = icon_svg(
		'<circle cx="12" cy="12" r="9"/>'
		+ '<path d="m8.5 12.5 2.2 2.2 4.8-5.2"/>'
	);
	const progress = icon_svg(
		'<circle cx="12" cy="12" r="9"/>'
		+ '<path d="M12 7v5l3 2"/>'
	);
	const amount = icon_svg(
		'<path d="M4 21V9l8-5 8 5v12"/>'
		+ '<path d="M9 21v-7h6v7"/>'
		+ '<path d="M4 21h16"/>'
	);
	const warehouse = icon_svg(
		'<path d="M4 21V9l8-5 8 5v12"/>'
		+ '<path d="M9 21v-7h6v7"/>'
		+ '<path d="M4 21h16"/>'
	);
	const returned = icon_svg(
		'<path d="M4 10h11a5 5 0 0 1 5 5v2"/>'
		+ '<path d="m4 10 5 5M4 10l5-5"/>'
		+ '<rect x="13" y="15" width="7" height="6" rx="1"/>'
	);

	return `
<div class="snwo-wrap">
  <div class="snwo-header">
    <div>
      <h1>Dashboard Overview</h1>
      <p>Track key metrics and site progress at a glance.</p>
    </div>
    <div class="snwo-range" data-range></div>
  </div>
  <div class="snwo-nav">
    <button type="button" class="active" data-snwo-nav="overview">Overview</button>
    <button type="button" data-snwo-nav="work-orders">Work Orders</button>
    <button type="button" data-snwo-nav="materials">Materials</button>
    <button type="button" data-snwo-nav="interchange">Interchange</button>
    <button type="button" data-snwo-nav="mp">MP Material</button>
    <button type="button" data-snwo-nav="reports">Reports</button>
  </div>
  <div class="snwo-kpis">
    <div class="snwo-card accent-blue">
      <div class="snwo-icon blue">${clipboard}</div>
      <div class="label">Total Work Orders</div>
      <div class="value" data-kpi="total_work_orders">0</div>
      <div class="hint">All work orders created</div>
    </div>
    <div class="snwo-card accent-green">
      <div class="snwo-icon green">${package_icon}</div>
      <div class="label">Total Work Orders Receive Material</div>
      <div class="value" data-kpi="material_received">0</div>
      <div class="hint">Sites with work orders that received material</div>
    </div>
    <div class="snwo-card accent-purple">
      <div class="snwo-icon purple">${check}</div>
      <div class="label">Completed Work Orders</div>
      <div class="value" data-kpi="completed_work_orders">0</div>
      <div class="hint" data-kpi="completion_pct">0% of total</div>
    </div>
    <div class="snwo-card accent-orange">
      <div class="snwo-icon orange">${progress}</div>
      <div class="label">On Progress Work Orders</div>
      <div class="value" data-kpi="in_progress_work_orders">0</div>
      <div class="hint" data-kpi="in_progress_pct">0% of total</div>
    </div>
  </div>
  <div class="snwo-kpis row2">
    <div class="snwo-card accent-amber" data-snwo-nav="mp">
      <div class="snwo-icon amber">${amount}</div>
      <div class="label">Total Site Use MP Material</div>
      <div class="value" data-kpi="mp_site_count">0</div>
      <div class="hint" data-kpi="mp_site_hint">Sites that used MP material</div>
    </div>
    <div class="snwo-card accent-teal">
      <div class="snwo-icon teal">${warehouse}</div>
      <div class="label">Total Site Material Not Issued</div>
      <div class="value" data-kpi="material_not_issued">0</div>
      <div class="hint">Units (pcs)</div>
    </div>
    <div class="snwo-card accent-rose">
      <div class="snwo-icon rose">${returned}</div>
      <div class="label">Total Site Material Returned</div>
      <div class="value" data-kpi="material_returned">0</div>
      <div class="hint">Units (pcs)</div>
    </div>
  </div>
  <div class="snwo-charts">
    <div class="snwo-chart">
      <div class="snwo-chart-head">
        <div>
          <h3>Site Interchange</h3>
          <p class="snwo-chart-desc">Total site interchange activity over time.</p>
        </div>
        <select class="snwo-chart-select" data-chart-group aria-label="Interchange grouping">
          <option value="day">Daily</option>
          <option value="week" selected>Weekly</option>
        </select>
      </div>
      <div id="snwo-interchange-chart"></div>
    </div>
    <div class="snwo-chart">
      <div class="snwo-chart-head">
        <div>
          <h3>Consumed Stock vs Remain</h3>
          <p class="snwo-chart-desc">Comparison of consumed stock and remaining stock over time.</p>
        </div>
        <select class="snwo-chart-select" data-chart-group aria-label="Stock grouping">
          <option value="day">Daily</option>
          <option value="week" selected>Weekly</option>
        </select>
      </div>
      <div id="snwo-consumed-chart"></div>
    </div>
  </div>
  <div class="snwo-summary">
    <div class="item"><div class="k">Work Order Completion</div><div class="v" data-sum="completion">0%</div></div>
    <div class="item"><div class="k">Sites with material received</div><div class="v" data-sum="received">0</div></div>
    <div class="item"><div class="k">Material Not Issued</div><div class="v" data-sum="not_issued">0 pcs</div></div>
    <div class="item"><div class="k">Sites using MP material</div><div class="v" data-sum="mp">0</div></div>
    <div class="item"><div class="k">Material Returned</div><div class="v" data-sum="returned">0 pcs</div></div>
    <div class="item"><div class="k">On Progress Work Orders</div><div class="v" data-sum="progress">0</div></div>
  </div>
</div>
`;
}
