import json
import os

import frappe
from frappe.utils import now_datetime, today, get_site_path


def create_signature_for_material_issue(issue, delivery_note=None):
    existing = frappe.db.exists(
        "Delivery Note Signature",
        {"material_issue": issue.name},
    )
    if existing:
        return existing

    signature = frappe.new_doc("Delivery Note Signature")
    signature.material_issue = issue.name
    signature.delivery_note = delivery_note
    signature.engineer = issue.engineer
    signature.customer = issue.customer
    signature.site = issue.site
    signature.status = "Pending"
    signature.issue_date = issue.issue_date or today()
    signature.warehouse_officer = issue.issued_by or frappe.session.user

    for item in issue.items:
        signature.append(
            "items",
            {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty": item.qty,
                "uom": item.uom,
            },
        )

    signature.insert(ignore_permissions=True)
    issue.db_set("delivery_signature", signature.name, update_modified=False)
    issue.db_set("signature_status", "Pending", update_modified=False)
    return signature.name


@frappe.whitelist()
def mark_signed(signature_name, signature_data=None):
    signature = frappe.get_doc("Delivery Note Signature", signature_name)

    if signature_data:
        signature.signature = signature_data

    if not signature.signature:
        frappe.throw("A signature is required.")

    signature.status = "Signed"
    signature.signed_at = now_datetime()
    signature.receiving_date = today()
    signature.save(ignore_permissions=True)

    if signature.delivery_note:
        frappe.db.set_value(
            "Delivery Note",
            signature.delivery_note,
            "custom_wms_signature_status",
            "Signed",
            update_modified=True,
        )

    if signature.material_issue:
        frappe.db.set_value(
            "WMS Material Issue",
            signature.material_issue,
            {"signature_status": "Signed"},
            update_modified=True,
        )

    return {"status": "success", "name": signature.name}


@frappe.whitelist()
def confirm_receipt(signature_name):
    signature = frappe.get_doc("Delivery Note Signature", signature_name)
    signature.status = "Received"
    signature.receiving_date = today()
    signature.save(ignore_permissions=True)

    if signature.delivery_note:
        frappe.db.set_value(
            "Delivery Note",
            signature.delivery_note,
            "custom_wms_signature_status",
            "Received",
            update_modified=True,
        )

    if signature.material_issue:
        frappe.db.set_value(
            "WMS Material Issue",
            signature.material_issue,
            {"signature_status": "Received"},
            update_modified=True,
        )

    return {"status": "success", "name": signature.name}


def build_qr_data(delivery_note):
    return json.dumps(
        {
            "delivery_note": delivery_note.name,
            "site": delivery_note.get("custom_wms_site"),
            "engineer": delivery_note.get("custom_wms_engineer"),
        },
        separators=(",", ":"),
    )


def generate_qr_file(delivery_note):
    """Generate an optional QR image when qrcode/Pillow are installed."""
    try:
        import qrcode
    except ImportError:
        frappe.log_error(
            "Install qrcode and Pillow to enable WMS QR images.",
            "Synarete WMS QR",
        )
        return None

    qr_data = build_qr_data(delivery_note)
    directory = get_site_path("public", "files")
    os.makedirs(directory, exist_ok=True)
    filename = f"wms_qr_{delivery_note.name.replace('/', '-')}.png"
    path = os.path.join(directory, filename)

    image = qrcode.make(qr_data)
    image.save(path)
    return f"/files/{filename}"
