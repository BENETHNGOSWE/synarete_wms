import frappe


WMS_STANDARD_DELIVERY_NOTE_HTML = r"""
<style>
    .page {
        width: 210mm;
        min-height: 285mm;
        margin: 0 auto;
        background: #fff;
        padding: 14mm 12mm;
        box-sizing: border-box;
    }
    .dn-wrapper {
        font-family: Arial, Helvetica, sans-serif;
        color: #000;
        font-size: 12px;
    }
    .dn-header {
        width: 100%;
        border-collapse: collapse;
    }
    .dn-header td {
        vertical-align: top;
        border: none;
    }
    .dn-company {
        text-align: right;
        font-size: 12px;
        line-height: 1.35;
    }
    .dn-company .name {
        font-size: 15px;
        font-weight: bold;
    }
    .dn-title {
        text-align: center;
        font-size: 18px;
        font-weight: bold;
        letter-spacing: 1px;
        margin: 6px 0 10px 0;
    }
    .dn-meta {
        width: 100%;
        margin-bottom: 8px;
        border-collapse: collapse;
    }
    .dn-meta td {
        border: none;
        padding: 2px 0;
    }
    .dn-label {
        font-weight: bold;
    }
    .dn-dotted {
        border-bottom: 1px dotted #000;
        display: inline-block;
        min-width: 240px;
    }
    table.dn-items {
        width: 100%;
        border-collapse: collapse;
        margin-top: 6px;
    }
    table.dn-items th,
    table.dn-items td {
        border: 1px solid #000;
        padding: 4px 6px;
        font-size: 12px;
    }
    table.dn-items th {
        text-align: left;
        font-weight: bold;
        background: #f2f2f2;
    }
    table.dn-items td.qty,
    table.dn-items td.type {
        text-align: center;
        width: 85px;
    }
    table.dn-items td.no {
        text-align: center;
        width: 40px;
    }
    table.dn-items td.remarks {
        width: 120px;
    }
    table.dn-items tr.blank td {
        height: 22px;
    }
    table.dn-sign {
        width: 100%;
        border-collapse: collapse;
        margin-top: 14px;
    }
    table.dn-sign td {
        border: 1px solid #000;
        padding: 6px 8px;
        font-size: 12px;
        width: 50%;
    }
    .dn-sign .line {
        display: inline-block;
        border-bottom: 1px dotted #000;
        min-width: 180px;
    }
    .dn-footbar {
        height: 8px;
        background: #1a1a1a;
        margin-top: 10px;
    }
    .logo-box svg {
        display: block;
    }
</style>

{% set settings = frappe.get_single("WMS Settings") %}
{% set wmi = frappe.get_doc("WMS Material Issue", doc.custom_wms_material_issue) if doc.custom_wms_material_issue else None %}
{% set site = frappe.db.get_value("WMS Site", doc.custom_wms_site, ["site_code", "site_name"], as_dict=True) %}
{% set engineer = frappe.db.get_value("Employee", doc.custom_wms_engineer, ["employee_name", "user_id"], as_dict=True) %}
{% set issue_rows = wmi.items if wmi else doc.items %}
{% set client_name = wmi.customer if wmi and wmi.customer else doc.customer %}
{% set reference_number = wmi.name if wmi else doc.custom_wms_material_issue or doc.name %}
{% set work_order = wmi.site_work_order if wmi else "" %}
{% set issue_date = wmi.issue_date if wmi else doc.posting_date %}
{% set delivered_by = wmi.issued_by if wmi else doc.owner %}

<div class="page">
<div class="dn-wrapper">

    <table class="dn-header">
        <tr>
            <td style="width: 35%;">
                <div class="logo-box">
                    <svg width="120" height="70" viewBox="0 0 120 70" xmlns="http://www.w3.org/2000/svg">
                        <g fill="#1a1a1a">
                            <circle cx="30" cy="14" r="7"/>
                            <circle cx="46" cy="10" r="5"/>
                            <circle cx="42" cy="22" r="4"/>
                            <circle cx="30" cy="14" r="3" fill="#fff"/>
                            <circle cx="46" cy="10" r="2" fill="#fff"/>
                            <circle cx="42" cy="22" r="1.6" fill="#fff"/>
                            <text x="2" y="45" font-family="Arial Black, Arial" font-size="17" font-weight="900">SYNARETE</text>
                            <text x="4" y="56" font-family="Arial" font-size="7" letter-spacing="1">ENGINEERING LIMITED</text>
                        </g>
                    </svg>
                </div>
            </td>
            <td class="dn-company">
                <div class="name">SYNARETE ENGINEERING LIMITED</div>
                5th Floor Morocco Square<br>
                Morocco,<br>
                Dar es Salaam, Tanzania<br>
                <b>+255 766 222 272</b>
            </td>
        </tr>
    </table>

    <div class="dn-title">DELIVERY NOTE</div>

    <table class="dn-meta">
        <tr>
            <td style="width:55%;"></td>
            <td style="text-align:right;"><span class="dn-label">TIN:</span> 183-988-506</td>
        </tr>
        <tr>
            <td></td>
            <td style="text-align:right;"><span class="dn-label">VRN:</span> 40-323767-Q</td>
        </tr>
        <tr>
            <td><span class="dn-label">Client:</span> <span class="dn-dotted">{{ client_name or "" }}</span></td>
            <td style="text-align:right;"><span class="dn-label">Ref. no.</span> {{ reference_number }}</td>
        </tr>
        <tr>
            <td><span class="dn-label">Site:</span> <span class="dn-dotted">{{ (site.site_code ~ " - " ~ site.site_name) if site else (doc.custom_wms_site or "") }}</span></td>
            <td style="text-align:right;"><span class="dn-label">Date:</span> {{ frappe.utils.formatdate(issue_date, "dd-MM-yyyy") if issue_date else "" }}</td>
        </tr>
        <tr>
            <td><span class="dn-label">Engineer:</span> <span class="dn-dotted">{{ (engineer.employee_name ~ " (" ~ doc.custom_wms_engineer ~ ")") if engineer else (doc.custom_wms_engineer or "") }}</span></td>
            <td style="text-align:right;"><span class="dn-label">Work Order:</span> {{ work_order }}</td>
        </tr>
    </table>

    <table class="dn-items">
        <thead>
            <tr>
                <th class="no">No.</th>
                <th>Description / Items</th>
                <th class="type">Material Type</th>
                <th class="qty">Quantity</th>
                <th class="remarks">Remarks</th>
            </tr>
        </thead>
        <tbody>
            {% for item in issue_rows %}
            <tr>
                <td class="no">{{ loop.index }}</td>
                <td>
                    {{ item.item_code }} - {{ item.item_name or item.item_code }}
                    {% if item.serial_no %}<br><small>S/N: {{ item.serial_no }}</small>{% endif %}
                </td>
                <td class="type">{{ item.material_type or (wmi.material_type if wmi else doc.custom_wms_material_type) or "" }}</td>
                <td class="qty">{{ item.qty }}</td>
                <td class="remarks">{{ item.remarks or item.description or "" }}</td>
            </tr>
            {% endfor %}
            {% if issue_rows|length < 12 %}
                {% for blank in range(12 - (issue_rows|length)) %}
                <tr class="blank"><td class="no"></td><td></td><td class="type"></td><td class="qty"></td><td class="remarks"></td></tr>
                {% endfor %}
            {% endif %}
        </tbody>
    </table>

    <table class="dn-sign">
        <tr>
            <td><b>Delivered By:</b> <span class="line">{{ delivered_by or "" }}</span></td>
            <td><b>Received By:</b> <span class="line">{{ engineer.employee_name if engineer else (doc.custom_wms_engineer or "") }}</span></td>
        </tr>
        <tr>
            <td><b>Signature:</b> <span class="line"></span></td>
            <td><b>Signature:</b> <span class="line"></span></td>
        </tr>
    </table>

    <div class="dn-footbar"></div>
</div>
</div>
"""

# Keep the WMS Material Issue fallback print format available.
WMS_DELIVERY_NOTE_HTML = WMS_STANDARD_DELIVERY_NOTE_HTML


def _ensure_print_format(name, doc_type, html):
    if frappe.db.exists("Print Format", name):
        doc = frappe.get_doc("Print Format", name)
        doc.html = html
        doc.doc_type = doc_type
        doc.print_format_type = "Jinja"
        doc.disabled = 0
        if doc.meta.get_field("standard"):
            doc.standard = "No"
        doc.save(ignore_permissions=True)
        return

    frappe.get_doc(
        {
            "doctype": "Print Format",
            "name": name,
            "doc_type": doc_type,
            "print_format_type": "Jinja",
            "html": html,
            "standard": "No",
            "disabled": 0,
            "module": "Synarete WMS",
        }
    ).insert(ignore_permissions=True)


def ensure_print_formats():
    _ensure_print_format(
        "WMS Delivery Note",
        "WMS Material Issue",
        WMS_DELIVERY_NOTE_HTML,
    )
    _ensure_print_format(
        "WMS Standard Delivery Note",
        "Delivery Note",
        WMS_STANDARD_DELIVERY_NOTE_HTML,
    )
