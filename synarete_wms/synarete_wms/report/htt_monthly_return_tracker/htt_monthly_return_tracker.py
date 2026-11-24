import frappe
from frappe import _
from frappe.utils import flt, getdate, today

from synarete_wms.synarete_wms.utils.htt_return_rules import (
    cycle_dates_for_completion,
    days_remaining,
    pending_return_qty,
    previous_month_range,
    return_status,
)


ISSUE_ITEM_JOIN = """
    INNER JOIN (
        SELECT
            parent,
            item_code,
            MAX(NULLIF(item_name, '')) AS item_name,
            MAX(uom) AS uom,
            MAX(CASE WHEN material_type = 'HTT' THEN 1 ELSE 0 END) AS has_htt
        FROM `tabWMS Material Issue Item`
        GROUP BY parent, item_code
    ) issue_item
        ON issue_item.parent = issue.name
    INNER JOIN `tabItem` item
        ON item.name = issue_item.item_code
    INNER JOIN (
        SELECT material_issue, item_code, SUM(qty) AS qty
        FROM `tabWMS HTT Transaction`
        WHERE transaction_type = 'Dispatch'
          AND is_cancelled = 0
        GROUP BY material_issue, item_code
    ) dispatch
        ON dispatch.material_issue = issue.name
       AND dispatch.item_code = issue_item.item_code
"""


def execute(filters=None):
    filters = filters or {}
    deadline_month = getdate(filters.get("deadline_month") or today())
    report_due = deadline_month.replace(day=15)
    return_deadline = deadline_month.replace(day=25)
    completion_from, completion_to = previous_month_range(deadline_month)
    current_date = getdate(today())

    columns = [
        {"fieldname": "work_order_type", "label": _("WO Type"), "fieldtype": "Data", "width": 125},
        {"fieldname": "site_work_order", "label": _("Site Work Order"), "fieldtype": "Link", "options": "Site Work Order", "width": 150},
        {"fieldname": "servicenow_work_order", "label": _("ServiceNow Work Order"), "fieldtype": "Link", "options": "ServiceNow Site Work Order", "width": 175},
        {"fieldname": "site", "label": _("Site"), "fieldtype": "Link", "options": "WMS Site", "width": 130},
        {"fieldname": "work_order_status", "label": _("WO Status"), "fieldtype": "Data", "width": 125},
        {"fieldname": "requested_on", "label": _("Requested On"), "fieldtype": "Date", "width": 110},
        {"fieldname": "completion_date", "label": _("Completed On"), "fieldtype": "Date", "width": 110},
        {"fieldname": "material_issue", "label": _("HTT Issue"), "fieldtype": "Link", "options": "WMS Material Issue", "width": 150},
        {"fieldname": "issue_date", "label": _("HTT Issued On"), "fieldtype": "Date", "width": 110},
        {"fieldname": "item_code", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 130},
        {"fieldname": "item_name", "label": _("Item Name"), "fieldtype": "Data", "width": 160},
        {"fieldname": "htt_supplied_qty", "label": _("HTT Supplied / Return Due"), "fieldtype": "Float", "width": 150},
        {"fieldname": "returned_used_qty", "label": _("Returned Used"), "fieldtype": "Float", "width": 110},
        {"fieldname": "returned_faulty_qty", "label": _("Returned Faulty"), "fieldtype": "Float", "width": 115},
        {"fieldname": "returned_total_qty", "label": _("Returned Total"), "fieldtype": "Float", "width": 115},
        {"fieldname": "pending_return_qty", "label": _("Still Pending"), "fieldtype": "Float", "width": 105},
        {"fieldname": "last_return_date", "label": _("Last Client Return"), "fieldtype": "Date", "width": 125},
        {"fieldname": "report_due_date", "label": _("Client Report Due"), "fieldtype": "Date", "width": 115},
        {"fieldname": "days_to_report_due", "label": _("Days to Report"), "fieldtype": "Int", "width": 100},
        {"fieldname": "return_deadline", "label": _("HTT Return Deadline"), "fieldtype": "Date", "width": 125},
        {"fieldname": "days_to_return_deadline", "label": _("Days to Return"), "fieldtype": "Int", "width": 100},
        {"fieldname": "return_status", "label": _("Return Status"), "fieldtype": "Data", "width": 145},
    ]

    site_rows = []
    if not filters.get("servicenow_work_order"):
        site_rows = _get_site_work_order_rows(
            filters, completion_from, completion_to
        )
    servicenow_rows = []
    if not filters.get("site_work_order"):
        servicenow_rows = _get_servicenow_work_order_rows(
            filters, completion_from, completion_to
        )
    rows = site_rows + servicenow_rows

    site_completion_by_version = _version_completion_dates(
        "Site Work Order",
        {
            row.work_order_name
            for row in site_rows
            if not row.completion_date
        },
        {"status": {"Completed", "Closed"}},
    )
    snwo_completion_by_version = _version_completion_dates(
        "ServiceNow Site Work Order",
        {
            row.work_order_name
            for row in servicenow_rows
            if not row.completion_date
        },
        {
            "process_status": {"Completed"},
            "status": {"Closed Complete"},
        },
    )
    returned = _get_return_totals()
    data = []
    missing_completion_dates = 0
    total_pending = 0
    included_rows = 0

    for source in rows:
        key = (source.material_issue, source.item_code)
        totals = returned.get(key, {})
        used_qty = flt(totals.get("used_qty"))
        faulty_qty = flt(totals.get("faulty_qty"))
        returned_qty = used_qty + faulty_qty
        supplied_qty = flt(source.htt_supplied_qty)
        pending_qty = pending_return_qty(supplied_qty, returned_qty)
        last_return = totals.get("last_return_date")

        version_dates = (
            site_completion_by_version
            if source.work_order_type == "Site Work Order"
            else snwo_completion_by_version
        )
        completion_date = (
            source.completion_date
            or version_dates.get(source.work_order_name)
        )
        if completion_date:
            report_due_date, material_due_date = cycle_dates_for_completion(
                completion_date
            )
            if (
                report_due_date.month != deadline_month.month
                or report_due_date.year != deadline_month.year
            ):
                continue
            status = return_status(
                supplied_qty,
                returned_qty,
                material_due_date,
                current_date,
                last_return,
            )
            report_days = days_remaining(report_due_date, current_date)
            material_days = days_remaining(material_due_date, current_date)
        else:
            # Leave the job visible but do not guess its completion month or deadlines.
            report_due_date = None
            material_due_date = None
            report_days = None
            material_days = None
            status = "Completion Date Missing"

        if filters.get("return_status") and status != filters.get("return_status"):
            continue

        if not completion_date:
            missing_completion_dates += 1
        else:
            total_pending += pending_qty
        included_rows += 1
        data.append(
            {
                "work_order_type": source.work_order_type,
                "site_work_order": source.site_work_order,
                "servicenow_work_order": source.servicenow_work_order,
                "site": source.site,
                "work_order_status": source.work_order_status,
                "requested_on": source.requested_on,
                "completion_date": completion_date,
                "material_issue": source.material_issue,
                "issue_date": source.issue_date,
                "item_code": source.item_code,
                "item_name": source.item_name,
                "htt_supplied_qty": supplied_qty,
                "returned_used_qty": used_qty,
                "returned_faulty_qty": faulty_qty,
                "returned_total_qty": returned_qty,
                "pending_return_qty": pending_qty,
                "last_return_date": last_return,
                "report_due_date": report_due_date,
                "days_to_report_due": report_days,
                "return_deadline": material_due_date,
                "days_to_return_deadline": material_days,
                "return_status": status,
            }
        )

    summary = [
        {
            "label": _("Client Report Due"),
            "value": str(report_due),
            "datatype": "Date",
            "indicator": "blue",
        },
        {
            "label": _("Days to Report Deadline"),
            "value": days_remaining(report_due, current_date),
            "datatype": "Int",
            "indicator": _deadline_indicator(report_due, current_date),
        },
        {
            "label": _("HTT Return Deadline"),
            "value": str(return_deadline),
            "datatype": "Date",
            "indicator": "orange",
        },
        {
            "label": _("Days to HTT Return Deadline"),
            "value": days_remaining(return_deadline, current_date),
            "datatype": "Int",
            "indicator": _deadline_indicator(return_deadline, current_date),
        },
        {
            "label": _("Pending HTT Units"),
            "value": total_pending,
            "datatype": "Float",
            "indicator": "orange" if total_pending else "green",
        },
    ]

    messages = [
        _(
            "This monthly cycle covers Work Orders completed in the previous calendar month. "
            "The client report is due on the 15th. The used/faulty HTT return window is the 20th–25th, "
            "with final delivery due by the 25th. From the 26th, any pending quantity is overdue; "
            "there is no grace period."
        ),
        _(
            "Returns are counted only from submitted WMS HTT Return Batches. These warehouse records "
            "do not change Work Orders or post stock / GL entries."
        ),
    ]
    if missing_completion_dates:
        messages.append(
            _(
                f"{missing_completion_dates} completed HTT Work Order item row(s) have no usable completion date. "
                "They remain visible without deadlines rather than being assigned to an assumed month."
            )
        )
    if not included_rows:
        messages.append(
            _(
                "No HTT material issues were found for this selected cycle/filter. Records require a submitted "
                "HTT dispatch linked explicitly to a completed Work Order. For imported ServiceNow jobs, link "
                "the HTT-only WMS Material Issue to the ServiceNow Work Order; ordinary MP or SNWO material "
                "transactions are not assumed to be HTT."
            )
        )

    return columns, data, "<br>".join(messages), None, summary


def _get_site_work_order_rows(filters, completion_from, completion_to):
    conditions = [
        "issue.docstatus = 1",
        "issue.site_work_order = wo.name",
        "wo.status IN ('Completed', 'Closed')",
        "(issue.material_type = 'HTT' OR issue_item.has_htt = 1)",
        "COALESCE(dispatch.qty, 0) > 0",
        "(wo.completion_date BETWEEN %(completion_from)s AND %(completion_to)s "
        "OR wo.completion_date IS NULL)",
    ]
    values = {
        "completion_from": completion_from,
        "completion_to": completion_to,
    }
    _append_work_order_permission_scope(conditions, "Site Work Order")
    _append_material_issue_permission_scope(conditions)
    if filters.get("site"):
        conditions.append("wo.site = %(site)s")
        values["site"] = filters["site"]
    if filters.get("site_work_order"):
        conditions.append("wo.name = %(site_work_order)s")
        values["site_work_order"] = filters["site_work_order"]

    return frappe.db.sql(
        f"""
        SELECT
            'Site Work Order' AS work_order_type,
            wo.name AS work_order_name,
            wo.name AS site_work_order,
            NULL AS servicenow_work_order,
            wo.site,
            wo.status AS work_order_status,
            wo.requested_on,
            wo.completion_date,
            issue.name AS material_issue,
            issue.issue_date,
            issue_item.item_code,
            COALESCE(NULLIF(issue_item.item_name, ''), item.item_name) AS item_name,
            dispatch.qty AS htt_supplied_qty
        FROM `tabSite Work Order` wo
        INNER JOIN `tabWMS Material Issue` issue
            ON issue.site_work_order = wo.name
        {ISSUE_ITEM_JOIN}
        WHERE {' AND '.join(conditions)}
        ORDER BY wo.completion_date, wo.name, issue.issue_date, issue.name, issue_item.item_code
        """,
        values,
        as_dict=True,
    )


def _get_servicenow_work_order_rows(filters, completion_from, completion_to):
    conditions = [
        "issue.docstatus = 1",
        "issue.servicenow_work_order = wo.name",
        "(wo.process_status = 'Completed' OR wo.status = 'Closed Complete')",
        "(issue.material_type = 'HTT' OR issue_item.has_htt = 1)",
        "COALESCE(dispatch.qty, 0) > 0",
        "(COALESCE(wo.actual_wo_date, DATE(wo.closed_at)) "
        "BETWEEN %(completion_from)s AND %(completion_to)s "
        "OR COALESCE(wo.actual_wo_date, DATE(wo.closed_at)) IS NULL)",
    ]
    values = {
        "completion_from": completion_from,
        "completion_to": completion_to,
    }
    _append_work_order_permission_scope(conditions, "ServiceNow Site Work Order")
    _append_material_issue_permission_scope(conditions)
    if filters.get("site"):
        conditions.append("wo.site = %(site)s")
        values["site"] = filters["site"]
    if filters.get("servicenow_work_order"):
        conditions.append("wo.name = %(servicenow_work_order)s")
        values["servicenow_work_order"] = filters["servicenow_work_order"]

    return frappe.db.sql(
        f"""
        SELECT
            'ServiceNow Work Order' AS work_order_type,
            wo.name AS work_order_name,
            NULL AS site_work_order,
            wo.name AS servicenow_work_order,
            wo.site,
            wo.status AS work_order_status,
            DATE(COALESCE(wo.opened_at, wo.created_on)) AS requested_on,
            COALESCE(wo.actual_wo_date, DATE(wo.closed_at)) AS completion_date,
            issue.name AS material_issue,
            issue.issue_date,
            issue_item.item_code,
            COALESCE(NULLIF(issue_item.item_name, ''), item.item_name) AS item_name,
            dispatch.qty AS htt_supplied_qty
        FROM `tabServiceNow Site Work Order` wo
        INNER JOIN `tabWMS Material Issue` issue
            ON issue.servicenow_work_order = wo.name
        {ISSUE_ITEM_JOIN}
        WHERE {' AND '.join(conditions)}
        ORDER BY COALESCE(wo.actual_wo_date, DATE(wo.closed_at)), wo.name,
                 issue.issue_date, issue.name, issue_item.item_code
        """,
        values,
        as_dict=True,
    )


def _append_material_issue_permission_scope(conditions):
    """Honor row-level Material Issue permission rules in the tracker SQL."""
    from synarete_wms.synarete_wms.utils.permissions import (
        material_issue_permission_query,
    )

    permission_sql = material_issue_permission_query()
    if permission_sql:
        conditions.append(
            f"({permission_sql.replace('`tabWMS Material Issue`', 'issue')})"
        )


def _append_work_order_permission_scope(conditions, ref_doctype):
    """Honor the app's Work Order row-level permission rules in raw SQL."""
    from synarete_wms.synarete_wms.utils.permissions import (
        servicenow_work_order_permission_query,
        site_work_order_permission_query,
    )

    if ref_doctype == "Site Work Order":
        permission_sql = site_work_order_permission_query()
        table_name = "`tabSite Work Order`"
    else:
        permission_sql = servicenow_work_order_permission_query()
        table_name = "`tabServiceNow Site Work Order`"

    if permission_sql:
        conditions.append(
            f"({permission_sql.replace(table_name, 'wo')})"
        )


def _version_completion_dates(ref_doctype, work_order_names, completed_fields):
    """Use the existing audit trail for local completion events when no date exists."""
    names = sorted(name for name in work_order_names if name)
    if not names or not frappe.db.exists("DocType", "Version"):
        return {}

    versions = frappe.get_all(
        "Version",
        filters={
            "ref_doctype": ref_doctype,
            "docname": ["in", names],
        },
        fields=["docname", "creation", "data"],
        order_by="creation asc",
        limit_page_length=10000,
    )
    completed = {}
    for version in versions:
        try:
            payload = (
                frappe.parse_json(version.data)
                if isinstance(version.data, str)
                else version.data
            ) or {}
        except Exception:
            continue

        changes = payload.get("changed", []) if isinstance(payload, dict) else []
        for change in changes:
            if isinstance(change, dict):
                fieldname = change.get("fieldname") or change.get("field")
                old_value = change.get("old_value", change.get("old", ""))
                new_value = change.get("new_value", change.get("new"))
            elif isinstance(change, (list, tuple)) and len(change) >= 3:
                fieldname, old_value, new_value = change[0], change[1], change[2]
            else:
                continue

            accepted_values = completed_fields.get(fieldname, set())
            if (
                str(new_value) in accepted_values
                and str(old_value) not in accepted_values
            ):
                completed[version.docname] = getdate(version.creation)
                break

    return completed


def _get_return_totals():
    rows = frappe.db.sql(
        """
        SELECT
            item.material_issue,
            item.item_code,
            SUM(CASE WHEN item.condition = 'Used' THEN item.returned_qty ELSE 0 END) AS used_qty,
            SUM(CASE WHEN item.condition = 'Faulty' THEN item.returned_qty ELSE 0 END) AS faulty_qty,
            MAX(batch.return_date) AS last_return_date
        FROM `tabWMS HTT Return Batch Item` item
        INNER JOIN `tabWMS HTT Return Batch` batch
            ON batch.name = item.parent
        WHERE batch.docstatus = 1
        GROUP BY item.material_issue, item.item_code
        """,
        as_dict=True,
    )
    return {
        (row.material_issue, row.item_code): {
            "used_qty": flt(row.used_qty),
            "faulty_qty": flt(row.faulty_qty),
            "last_return_date": row.last_return_date,
        }
        for row in rows
    }


def _deadline_indicator(due_date, current_date):
    remaining = days_remaining(due_date, current_date)
    if remaining is None:
        return "gray"
    if remaining < 0:
        return "red"
    if remaining <= 5:
        return "orange"
    return "blue"
