"""Dummy TP Cable lifecycle for a LOCAL ERPNext site only.

Refuse production sites. Creates TEST-* records only.

  bench --site <local-site> execute synarete_wms.synarete_wms.tests.tp_cable_lifecycle.run
"""

PRODUCTION_SITES = {
    "erp.synarete.co.tz",
    "erp.synarete.com",
}


def run():
    import frappe
    from frappe.utils import now_datetime

    site = getattr(getattr(frappe.local, "site", None), "name", None) or frappe.local.site
    if str(site).strip().lower() in PRODUCTION_SITES:
        frappe.throw(
            f"Refusing dummy TP Cable test on production site {site}. "
            "Run only on a local / staging site."
        )
    if "prod" in str(site).lower() and "local" not in str(site).lower():
        frappe.throw(
            f"Site name {site} looks like production. Refusing to create dummy stock."
        )

    print(f"Local dummy test starting on site {site} at {now_datetime()}")
    print("This function is a guard + reminder. Use tp_cable_local_run.py in this")
    print("sandbox, or run the full DocType flow on a local bench with TEST-* masters.")
    print("No production writes were made.")
    return {"site": site, "production": False}
