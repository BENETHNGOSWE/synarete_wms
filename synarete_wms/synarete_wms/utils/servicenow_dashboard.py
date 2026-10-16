"""ServiceNow Dashboard metrics. HTT is not included."""

from __future__ import annotations

from datetime import timedelta

import frappe
from frappe.utils import flt, formatdate, getdate, nowdate


def _period(from_date, to_date):
    start = getdate(from_date or nowdate())
    end = getdate(to_date or nowdate())
    if end < start:
        start, end = end, start
    return start, end


def _week_starts(start, end):
    cursor = start - timedelta(days=start.weekday())
    weeks = []
    while cursor <= end:
        weeks.append(cursor)
        cursor += timedelta(days=7)
    return weeks or [start]


def _mp_sites(start, end, start_dt, end_dt):
    from_tx = frappe.db.sql(
        """
        SELECT DISTINCT
            COALESCE(NULLIF(t.site, ''), wo.site) AS site
        FROM `tabSNWO Material Transaction` t
        LEFT JOIN `tabServiceNow Site Work Order` wo
            ON wo.name = COALESCE(NULLIF(t.issued_to_work_order, ''), t.original_work_order)
        WHERE t.docstatus = 1
          AND (t.is_mp_stock = 1 OR t.transaction_type = 'MP Issue')
          AND t.posting_date BETWEEN %(start)s AND %(end)s
        """,
        {"start": start, "end": end},
        as_dict=True,
    )
    from_wo = frappe.db.sql(
        """
        SELECT DISTINCT wo.site AS site
        FROM `tabServiceNow Site Work Order` wo
        LEFT JOIN `tabSNWO Material Item` item
            ON item.parent = wo.name
        WHERE wo.created_on BETWEEN %(start)s AND %(end)s
          AND (
            IFNULL(wo.mp_material_used, 0) = 1
            OR IFNULL(item.qty_mp_issued, 0) > 0
          )
        """,
        {"start": start_dt, "end": end_dt},
        as_dict=True,
    )
    codes = []
    seen = set()
    for row in list(from_tx) + list(from_wo):
        site = (row.get("site") or "").strip()
        if not site or site in seen:
            continue
        seen.add(site)
        codes.append(site)

    if not codes:
        return []

    names = {
        row.name: (row.site_name or row.name)
        for row in frappe.get_all(
            "WMS Site",
            filters={"name": ["in", codes]},
            fields=["name", "site_name"],
        )
    }
    sites = [
        {"site": code, "site_name": names.get(code) or code}
        for code in codes
    ]
    sites.sort(key=lambda row: (row["site_name"] or "").lower())
    return sites


def _received_sites(start_dt, end_dt):
    rows = frappe.db.sql(
        """
        SELECT DISTINCT wo.site AS site
        FROM `tabServiceNow Site Work Order` wo
        WHERE wo.created_on BETWEEN %(start)s AND %(end)s
          AND IFNULL(wo.site, '') != ''
          AND (
            wo.process_status IN (
                'Material Received',
                'Material Issued',
                'Material Consumed',
                'Reconciliation',
                'Completed'
            )
            OR EXISTS (
                SELECT 1
                FROM `tabSNWO Material Item` item
                WHERE item.parent = wo.name
                  AND IFNULL(item.qty_received, 0) > 0
            )
            OR EXISTS (
                SELECT 1
                FROM `tabSNWO Material Transaction` t
                WHERE t.docstatus = 1
                  AND t.transaction_type = 'Receive'
                  AND (
                    t.received_for_work_order = wo.name
                    OR t.original_work_order = wo.name
                  )
            )
          )
        """,
        {"start": start_dt, "end": end_dt},
        as_dict=True,
    )
    sites = []
    seen = set()
    for row in rows:
        site = (row.get("site") or "").strip()
        if not site or site in seen:
            continue
        seen.add(site)
        sites.append(site)
    return sites


def _chart_buckets(start, end, group_by=None):
    group_by = (group_by or "week").lower()
    buckets = []
    if group_by == "day":
        cursor = start
        while cursor <= end:
            buckets.append((cursor, cursor, formatdate(cursor, "dd MMM")))
            cursor += timedelta(days=1)
        return buckets or [(start, end, formatdate(start, "dd MMM"))]
    for week in _week_starts(start, end):
        week_end = min(week + timedelta(days=6), end)
        buckets.append((week, week_end, formatdate(week, "dd MMM")))
    return buckets


@frappe.whitelist()
def get_overview(from_date=None, to_date=None, group_by=None):
    start, end = _period(from_date, to_date)
    start_dt = f"{start} 00:00:00"
    end_dt = f"{end} 23:59:59"

    work_orders = frappe.db.sql(
        """
        SELECT
            name,
            process_status,
            status_group,
            created_on
        FROM `tabServiceNow Site Work Order`
        WHERE created_on BETWEEN %(start)s AND %(end)s
        """,
        {"start": start_dt, "end": end_dt},
        as_dict=True,
    )

    total_work_orders = len(work_orders)
    completed_work_orders = 0
    for order in work_orders:
        if order.process_status == "Completed" or order.status_group == "Closed":
            completed_work_orders += 1
    in_progress_work_orders = max(0, total_work_orders - completed_work_orders)
    completion_pct = (
        round((completed_work_orders / total_work_orders) * 100, 1)
        if total_work_orders
        else 0
    )
    in_progress_pct = (
        round((in_progress_work_orders / total_work_orders) * 100, 1)
        if total_work_orders
        else 0
    )

    qty_rows = frappe.db.sql(
        """
        SELECT
            SUM(item.qty_received) AS qty_received,
            SUM(item.qty_warehouse_remaining) AS qty_not_issued,
            SUM(item.qty_mp_issued) AS qty_mp,
            SUM(item.qty_consumed) AS qty_consumed,
            SUM(item.qty_remaining) AS qty_remaining
        FROM `tabServiceNow Site Work Order` wo
        INNER JOIN `tabSNWO Material Item` item
            ON item.parent = wo.name
        WHERE wo.created_on BETWEEN %(start)s AND %(end)s
        """,
        {"start": start_dt, "end": end_dt},
        as_dict=True,
    )
    qty = qty_rows[0] if qty_rows else {}

    received_in_period = frappe.db.sql(
        """
        SELECT SUM(item.qty) AS qty
        FROM `tabSNWO Material Transaction` t
        INNER JOIN `tabSNWO Material Transaction Item` item
            ON item.parent = t.name
        WHERE t.docstatus = 1
          AND t.transaction_type = 'Receive'
          AND t.posting_date BETWEEN %(start)s AND %(end)s
        """,
        {"start": start, "end": end},
        as_dict=True,
    )
    material_received_qty = flt((received_in_period[0] or {}).get("qty")) or flt(
        qty.get("qty_received")
    )
    material_received_sites = _received_sites(start_dt, end_dt)

    mp_in_period = frappe.db.sql(
        """
        SELECT SUM(item.qty) AS qty
        FROM `tabSNWO Material Transaction` t
        INNER JOIN `tabSNWO Material Transaction Item` item
            ON item.parent = t.name
        WHERE t.docstatus = 1
          AND (t.is_mp_stock = 1 OR t.transaction_type = 'MP Issue')
          AND t.posting_date BETWEEN %(start)s AND %(end)s
        """,
        {"start": start, "end": end},
        as_dict=True,
    )
    mp_qty = flt((mp_in_period[0] or {}).get("qty")) or flt(qty.get("qty_mp"))
    mp_sites = _mp_sites(start, end, start_dt, end_dt)

    not_issued = flt(qty.get("qty_not_issued"))
    consumed = flt(qty.get("qty_consumed"))
    remaining = flt(qty.get("qty_remaining"))

    returned = 0.0

    interchange_values = []
    consumed_values = []
    remaining_values = []
    labels = []

    for bucket_start, bucket_end, label in _chart_buckets(start, end, group_by):
        labels.append(label)
        interchange_values.append(
            flt(
                frappe.db.sql(
                    """
                    SELECT SUM(item.qty)
                    FROM `tabSNWO Material Transaction` t
                    INNER JOIN `tabSNWO Material Transaction Item` item
                        ON item.parent = t.name
                    WHERE t.docstatus = 1
                      AND t.is_interchange = 1
                      AND t.posting_date BETWEEN %(start)s AND %(end)s
                    """,
                    {"start": bucket_start, "end": bucket_end},
                )[0][0]
            )
        )
        consumed_values.append(
            flt(
                frappe.db.sql(
                    """
                    SELECT SUM(item.qty)
                    FROM `tabSNWO Material Transaction` t
                    INNER JOIN `tabSNWO Material Transaction Item` item
                        ON item.parent = t.name
                    WHERE t.docstatus = 1
                      AND t.transaction_type = 'Consume'
                      AND t.posting_date BETWEEN %(start)s AND %(end)s
                    """,
                    {"start": bucket_start, "end": bucket_end},
                )[0][0]
            )
        )
        remaining_values.append(
            flt(
                frappe.db.sql(
                    """
                    SELECT SUM(item.qty_remaining)
                    FROM `tabServiceNow Site Work Order` wo
                    INNER JOIN `tabSNWO Material Item` item
                        ON item.parent = wo.name
                    WHERE wo.created_on BETWEEN %(start)s AND %(end)s
                    """,
                    {
                        "start": f"{bucket_start} 00:00:00",
                        "end": f"{bucket_end} 23:59:59",
                    },
                )[0][0]
            )
        )

    return {
        "from_date": str(start),
        "to_date": str(end),
        "total_work_orders": total_work_orders,
        "material_received": len(material_received_sites),
        "material_received_qty": material_received_qty,
        "completed_work_orders": completed_work_orders,
        "completion_pct": completion_pct,
        "in_progress_work_orders": in_progress_work_orders,
        "in_progress_pct": in_progress_pct,
        "mp_qty": mp_qty,
        "mp_site_count": len(mp_sites),
        "mp_sites": mp_sites,
        "material_not_issued": not_issued,
        "material_returned": returned,
        "consumed": consumed,
        "remaining": remaining,
        "charts": {
            "labels": labels,
            "interchange": interchange_values,
            "consumed": consumed_values,
            "remaining": remaining_values,
        },
    }


@frappe.whitelist()
def export_overview(from_date=None, to_date=None, group_by=None):
    data = get_overview(from_date, to_date, group_by)
    rows = [
        ["ServiceNow Dashboard"],
        ["From", data["from_date"], "To", data["to_date"]],
        [],
        ["Metric", "Value"],
        ["Total Work Orders", data["total_work_orders"]],
        [
            "Sites with work order raised and material received",
            data["material_received"],
        ],
        ["Completed Work Orders", data["completed_work_orders"]],
        ["Completion %", data["completion_pct"]],
        ["On Progress Work Orders", data["in_progress_work_orders"]],
        ["On Progress %", data["in_progress_pct"]],
        ["Sites using MP material", data.get("mp_site_count") or 0],
        ["Site Material Not Issued (pcs)", data["material_not_issued"]],
        ["Site Material Returned (pcs)", data["material_returned"]],
        [],
        ["Period", "Interchange Qty", "Consumed", "Remaining"],
    ]
    charts = data.get("charts") or {}
    labels = charts.get("labels") or []
    for idx, label in enumerate(labels):
        rows.append(
            [
                label,
                (charts.get("interchange") or [0])[idx]
                if idx < len(charts.get("interchange") or [])
                else 0,
                (charts.get("consumed") or [0])[idx]
                if idx < len(charts.get("consumed") or [])
                else 0,
                (charts.get("remaining") or [0])[idx]
                if idx < len(charts.get("remaining") or [])
                else 0,
            ]
        )

    from frappe.utils.xlsxutils import make_xlsx

    xlsx = make_xlsx(rows, "ServiceNow Dashboard")
    frappe.response["filename"] = (
        f"ServiceNow-Dashboard-{data['from_date']}-to-{data['to_date']}.xlsx"
    )
    frappe.response["filecontent"] = xlsx.getvalue()
    frappe.response["type"] = "binary"
