"""Safe, idempotent local-only WMS demo setup.

This creates master data and valued MP opening stock. It does not create Users,
passwords, production data, workflows, or transactional WMS documents.
"""

import frappe
from frappe.utils import flt, today


COMPANY = "SYNARETE ENGINEERING LIMITED"
MAIN_WAREHOUSE = "SYNARETE MAIN WAREHOUSE - SEL"
FIELD_ISSUED_WAREHOUSE = "Field Issued Warehouse - SEL"
SITE_CODE = "DEMO-SITE-001"
CUSTOMER_NAME = "DEMO CUSTOMER"

DEMO_ITEMS = [
    {
        "item_code": "DEMO-MP-CABLE",
        "item_name": "Demo MP Cable",
        "category": "MP",
        "opening_qty": 100,
        "rate": 1000,
    },
    {
        "item_code": "DEMO-MP-DEVICE",
        "item_name": "Demo MP Device",
        "category": "MP",
        "opening_qty": 10,
        "rate": 50000,
    },
    {
        "item_code": "DEMO-HTT-DEVICE",
        "item_name": "Demo HTT Customer Device",
        "category": "HTT",
        "opening_qty": 0,
        "rate": 0,
    },
]


def _first_existing(doctype, fieldname, filters=None):
    rows = frappe.get_all(
        doctype,
        filters=filters or {},
        pluck=fieldname,
        limit_page_length=1,
    )
    return rows[0] if rows else None


def _ensure_uom():
    if frappe.db.exists("UOM", "Nos"):
        return "Nos"

    uom = frappe.new_doc("UOM")
    uom.uom_name = "Nos"
    uom.insert(ignore_permissions=True)
    return uom.name


def _ensure_item(item_data, item_group, uom):
    item_code = item_data["item_code"]

    if frappe.db.exists("Item", item_code):
        item = frappe.get_doc("Item", item_code)
    else:
        item = frappe.new_doc("Item")
        item.item_code = item_code
        item.item_name = item_data["item_name"]
        item.item_group = item_group
        item.stock_uom = uom
        item.is_stock_item = 1
        item.disabled = 0
        item.insert(ignore_permissions=True)

    item_meta = frappe.get_meta("Item")

    if item_meta.get_field("custom_wms_material_category"):
        item.db_set(
            "custom_wms_material_category",
            item_data["category"],
            update_modified=False,
        )

    if item_meta.get_field("custom_wms_is_monthly_service"):
        item.db_set(
            "custom_wms_is_monthly_service",
            0,
            update_modified=False,
        )

    if item_meta.get_field("custom_wms_min_stock_level"):
        item.db_set(
            "custom_wms_min_stock_level",
            0,
            update_modified=False,
        )

    return item.name


def _ensure_site():
    if frappe.db.exists("WMS Site", SITE_CODE):
        return SITE_CODE

    site = frappe.new_doc("WMS Site")
    site.site_code = SITE_CODE
    site.site_name = "Demo Telecom Site"
    site.status = "Active"
    site.region = "Dar es Salaam"
    site.district = "Demo District"
    site.insert(ignore_permissions=True)
    return site.name


def _ensure_customer():
    if frappe.db.exists("Customer", CUSTOMER_NAME):
        return CUSTOMER_NAME

    customer_group = _first_existing("Customer Group", "name")
    territory = _first_existing("Territory", "name")

    if not customer_group or not territory:
        print("Customer Group or Territory is missing; customer was not created.")
        return None

    customer = frappe.new_doc("Customer")
    customer.customer_name = CUSTOMER_NAME
    customer.customer_type = "Company"
    customer.customer_group = customer_group
    customer.territory = territory
    customer.insert(ignore_permissions=True)
    return customer.name


def _ensure_opening_stock(item_code, target_qty, rate, warehouse):
    if not warehouse or not target_qty:
        return None

    current = frappe.db.get_value(
        "Bin",
        {"item_code": item_code, "warehouse": warehouse},
        "actual_qty",
    )
    current = flt(current)
    difference = flt(target_qty) - current

    if difference <= 0:
        return None

    settings = frappe.get_single("WMS Settings")
    if not settings.company:
        frappe.throw("Set Company in WMS Settings before seeding demo stock.")

    stock_entry = frappe.new_doc("Stock Entry")
    stock_entry.stock_entry_type = "Material Receipt"
    stock_entry.company = settings.company
    stock_entry.posting_date = today()
    stock_entry.append(
        "items",
        {
            "item_code": item_code,
            "qty": difference,
            "t_warehouse": warehouse,
            "basic_rate": rate,
        },
    )
    stock_entry.insert(ignore_permissions=True)
    stock_entry.submit()
    return stock_entry.name


def seed_local_demo():
    """Create repeatable local WMS demo setup; never run this in production."""
    if frappe.local.site != "erp.synarete.co.tz":
        frappe.throw(
            "This demo seed is restricted to the local site name erp.synarete.co.tz."
        )

    item_group = _first_existing(
        "Item Group",
        "name",
        {"is_group": 0},
    )
    if not item_group:
        frappe.throw("Create a leaf Item Group before seeding demo data.")

    uom = _ensure_uom()
    site = _ensure_site()
    customer = _ensure_customer()

    settings = frappe.get_single("WMS Settings")
    print("Company:", settings.company or COMPANY)
    print("Main Warehouse:", settings.main_warehouse)
    print("Field Issued Warehouse:", settings.field_issued_warehouse)
    print("Site:", site)
    print("Customer:", customer)

    for item_data in DEMO_ITEMS:
        item_code = _ensure_item(item_data, item_group, uom)
        opening_entry = _ensure_opening_stock(
            item_code,
            item_data["opening_qty"],
            item_data["rate"],
            settings.main_warehouse,
        )
        print(
            "Item:",
            item_code,
            "| category:",
            item_data["category"],
            "| opening Stock Entry:",
            opening_entry or "already sufficient",
        )

    frappe.db.commit()
    frappe.clear_cache()
    print("Local WMS demo setup completed.")
