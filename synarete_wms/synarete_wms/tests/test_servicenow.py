from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from synarete_wms.synarete_wms.utils.servicenow import (
    compute_days_open,
    is_mp_transaction,
    is_pending_for,
    normalize_order_type,
    normalize_status,
    parse_servicenow_datetime,
    status_group_for,
    transform_servicenow_row,
)


class TestServiceNowTransform(FrappeTestCase):
    def test_mandatory_fields_are_auto_filled(self):
        row = {
            "number": "WO001234",
            "u_site": "SITE-001",
            "state": "Work in Progress",
            "u_type": "Material",
            "sys_created_on": "25-08-2026 14:30",
            "u_part_code": "PART-X",
            "u_quantity": 10,
            "short_description": "Replace rectifier",
        }
        transformed = transform_servicenow_row(row)
        self.assertEqual(transformed["swo_number"], "WO001234")
        self.assertEqual(transformed["site"], "SITE-001")
        self.assertEqual(transformed["status"], "Work in Progress")
        self.assertEqual(transformed["status_group"], "Open")
        self.assertEqual(transformed["is_pending"], 1)
        self.assertEqual(transformed["order_type"], "Material")
        self.assertEqual(transformed["created_on"], "2026-08-25 14:30:00")
        self.assertEqual(transformed["source_system"], "ServiceNow")
        self.assertEqual(transformed["process_status"], "Material Required")
        self.assertEqual(transformed["quantity"], 10)

    def test_closed_status_group(self):
        self.assertEqual(status_group_for("Closed Complete"), "Closed")
        self.assertEqual(status_group_for("Closed Incomplete"), "Closed")
        self.assertEqual(status_group_for("Closed Rejected"), "Closed")
        self.assertEqual(is_pending_for("Closed Complete"), 0)
        self.assertEqual(is_pending_for("Open"), 1)

    def test_datetime_and_aliases(self):
        self.assertEqual(
            parse_servicenow_datetime("01-09-2026 09:15"),
            "2026-09-01 09:15:00",
        )
        self.assertEqual(normalize_status("in progress"), "Work in Progress")
        self.assertEqual(normalize_order_type("Material"), "Material")
        self.assertEqual(normalize_order_type("service"), "Service")
        self.assertEqual(compute_days_open("2026-08-01", 1, as_of="2026-09-01"), 31)
        self.assertEqual(compute_days_open("2026-08-01", 0, as_of="2026-09-01"), 0)


class TestServiceNowDoctypes(FrappeTestCase):
    def test_required_doctypes_exist(self):
        for doctype in [
            "Maintenance Partner",
            "ServiceNow Site Work Order",
            "SNWO Material Item",
            "SNWO Material Transaction",
            "SNWO Material Transaction Item",
        ]:
            self.assertTrue(
                frappe.db.exists("DocType", doctype),
                f"Missing DocType: {doctype}",
            )

    def test_htt_process_is_unchanged(self):
        self.assertTrue(frappe.db.exists("DocType", "HTT Material Receipt"))
        self.assertTrue(frappe.db.exists("DocType", "WMS HTT Transaction"))
        meta = frappe.get_meta("HTT Material Receipt")
        self.assertIsNotNone(meta.get_field("receipt_type"))
        self.assertIsNotNone(meta.get_field("customer"))

    def test_maintenance_partner_records(self):
        from synarete_wms.synarete_wms.utils.servicenow import (
            ensure_maintenance_partners,
        )

        ensure_maintenance_partners()
        self.assertTrue(
            frappe.db.exists("Maintenance Partner", "Synarete")
            or frappe.db.exists("Maintenance Partner", {"partner_name": "Synarete"})
        )
        self.assertTrue(
            frappe.db.exists("Maintenance Partner", "JD Electronics")
            or frappe.db.exists(
                "Maintenance Partner", {"partner_name": "JD Electronics"}
            )
        )

    def test_interchange_requires_reason(self):
        from synarete_wms.synarete_wms.utils.servicenow import validate_transaction

        txn = frappe.get_doc(
            {
                "doctype": "SNWO Material Transaction",
                "transaction_type": "Issue",
                "original_work_order": "WO-A",
                "received_for_work_order": "WO-A",
                "issued_to_work_order": "WO-B",
                "items": [
                    {
                        "doctype": "SNWO Material Transaction Item",
                        "item_code": "PART-X",
                        "qty": 10,
                    }
                ],
            }
        )
        with patch(
            "synarete_wms.synarete_wms.utils.servicenow.collect_material_totals",
            return_value={"PART-X": {"qty_warehouse_remaining": 10}},
        ), patch("frappe.session") as session:
            session.user = "Administrator"
            with self.assertRaises(frappe.ValidationError):
                validate_transaction(txn)
