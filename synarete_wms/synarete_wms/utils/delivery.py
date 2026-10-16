import frappe
from frappe.utils import today


@frappe.whitelist()
def create_delivery_note_for_issue(material_issue):
    issue = frappe.get_doc("WMS Material Issue", material_issue)

    if issue.docstatus != 1 or issue.status != "Issued":
        frappe.throw("A Delivery Note can only be created after the Material Issue is Issued.")

    name = create_printable_delivery_note(issue)
    return {"name": name}


def create_printable_delivery_note(issue):
    """Create a draft standard Delivery Note for printing/signing only.

    The WMS Material Issue remains the actual stock transaction. This draft
    Delivery Note must never be submitted, because submitting it would deduct
    stock a second time.
    """
    if issue.delivery_note and frappe.db.exists("Delivery Note", issue.delivery_note):
        return issue.delivery_note

    settings = frappe.get_single("WMS Settings")
    customer = issue.customer or settings.internal_delivery_customer

    if not customer:
        frappe.msgprint(
            "Internal Delivery Customer is not set in WMS Settings. "
            "Stock was still issued. Set the customer later if you need a printable Delivery Note.",
            indicator="orange",
            alert=True,
        )
        return None

    delivery_note = frappe.new_doc("Delivery Note")
    delivery_note.company = settings.company
    delivery_note.customer = customer
    delivery_note.posting_date = issue.issue_date or today()
    delivery_note.set_posting_time = 1

    if delivery_note.meta.get_field("custom_wms_material_type"):
        delivery_note.custom_wms_material_type = issue.material_type
    if delivery_note.meta.get_field("custom_wms_material_issue"):
        delivery_note.custom_wms_material_issue = issue.name
    if delivery_note.meta.get_field("custom_wms_site"):
        delivery_note.custom_wms_site = issue.site
    if delivery_note.meta.get_field("custom_wms_engineer"):
        delivery_note.custom_wms_engineer = issue.engineer
    if delivery_note.meta.get_field("custom_wms_signature_status"):
        delivery_note.custom_wms_signature_status = "Pending"

    for item in issue.items:
        delivery_note.append(
            "items",
            {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty": item.fulfilled_qty or item.qty,
                "uom": item.uom,
                "warehouse": issue.source_warehouse or settings.main_warehouse,
                "description": item.remarks,
            },
        )

    delivery_note.insert(ignore_permissions=True)
    issue.db_set("delivery_note", delivery_note.name, update_modified=False)
    return delivery_note.name


def prevent_wms_delivery_note_submit(doc, method=None):
    if doc.get("custom_wms_material_issue"):
        frappe.throw(
            "This WMS Delivery Note is for printing and signature only. "
            "The WMS Material Issue already posted the stock transfer. "
            "Do not submit this Delivery Note."
        )
