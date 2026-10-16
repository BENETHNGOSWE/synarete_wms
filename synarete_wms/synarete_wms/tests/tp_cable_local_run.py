"""Local dummy TP Cable lifecycle.

This file is safe to run without ERPNext. It uses the real
`compute_issue_split` helper and the same posting rules as the WMS
doctypes (transfer on issue/return, expense only on consume).

It never connects to a site. Do not point this at production.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path


def _load_compute_issue_split():
    """Import the real helper without installing Frappe."""
    source = Path(__file__).resolve().parents[1] / "utils" / "accountability.py"
    text = source.read_text()
    marker = "def get_open_balance"
    snippet = text.split(marker)[0]
    snippet = snippet.replace("import frappe\n", "")
    snippet = snippet.replace("from frappe.utils import flt, today\n", "")
    ns = {}
    exec(
        "def flt(v):\n    return float(v or 0)\n" + snippet,
        ns,
        ns,
    )
    return ns["compute_issue_split"]


compute_issue_split = _load_compute_issue_split()


ITEM = "TEST-TP-CABLE"
ITEM_NAME = "TP Cable (TEST)"
UOM = "Meter"
RATE = 2000.0
ENGINEER = "TEST-EMP-TPCABLE"
SITE = "TEST-TPCABLE-SITE"
MAIN = "TEST-Main Warehouse"
FIELD = "TEST-Field Issued Warehouse"
COMPANY = "TEST-Synarete"


class Ledger:
    """Minimal Bin + SLE + GL + accountability store for local dummy runs."""

    def __init__(self):
        self.bin_qty = defaultdict(float)
        self.bin_value = defaultdict(float)
        self.sle = []
        self.gl = []
        self.accountability = {}
        self.docs = []
        self.failed = None

    def _key(self, warehouse):
        return (ITEM, warehouse)

    def valuation_rate(self, warehouse):
        qty = self.bin_qty[self._key(warehouse)]
        if qty <= 0:
            return RATE
        return self.bin_value[self._key(warehouse)] / qty

    def post_sle(self, warehouse, qty, rate, voucher_type, voucher, purpose):
        value = qty * rate
        key = self._key(warehouse)
        self.bin_qty[key] += qty
        self.bin_value[key] += value
        self.sle.append(
            {
                "item_code": ITEM,
                "warehouse": warehouse,
                "qty": qty,
                "rate": rate,
                "value": value,
                "qty_after": self.bin_qty[key],
                "value_after": self.bin_value[key],
                "voucher_type": voucher_type,
                "voucher": voucher,
                "purpose": purpose,
            }
        )
        return value

    def post_gl(self, account, debit, credit, voucher, remarks):
        self.gl.append(
            {
                "account": account,
                "debit": debit,
                "credit": credit,
                "voucher": voucher,
                "remarks": remarks,
            }
        )

    def snapshot(self, stage):
        main_qty = self.bin_qty[self._key(MAIN)]
        field_qty = self.bin_qty[self._key(FIELD)]
        consumed = sum(-r["qty"] for r in self.sle if r["purpose"] == "Material Issue")
        expense = sum(g["debit"] for g in self.gl if g["account"] == "Consumption Expense")
        outstanding = {
            name: {
                "wo": row["site_work_order"],
                "issued": row["issued_qty"],
                "carried": row["carried_forward_qty"],
                "consumed": row["consumed_qty"],
                "returned": row["returned_qty"],
                "transferred_out": row["transferred_out_qty"],
                "outstanding": row["outstanding_qty"],
            }
            for name, row in self.accountability.items()
        }
        return {
            "stage": stage,
            "main_qty": main_qty,
            "main_value": self.bin_value[self._key(MAIN)],
            "field_qty": field_qty,
            "field_value": self.bin_value[self._key(FIELD)],
            "physical_total": main_qty + field_qty,
            "consumed_qty": consumed,
            "expense_tzs": expense,
            "inventory_asset": self.bin_value[self._key(MAIN)]
            + self.bin_value[self._key(FIELD)],
            "accountability": outstanding,
        }


def refresh_acc(row):
    total = row["issued_qty"] + row["carried_forward_qty"]
    accounted = (
        row["consumed_qty"] + row["returned_qty"] + row["transferred_out_qty"]
    )
    row["outstanding_qty"] = max(0.0, total - accounted)
    return row


def run():
    compute_issue_split  # real WMS helper
    led = Ledger()
    stages = []

    def record(stage):
        snap = led.snapshot(stage)
        stages.append(snap)
        return snap

    # 1. Receive 500 into Main — inventory asset, not expense.
    led.post_sle(MAIN, 500, RATE, "Stock Entry", "TEST-SE-RECEIPT", "Material Receipt")
    led.post_gl("Inventory Asset", 1_000_000, 0, "TEST-SE-RECEIPT", "Dummy receive TP Cable")
    led.post_gl("Stock Adjustment", 0, 1_000_000, "TEST-SE-RECEIPT", "Dummy receive TP Cable")
    led.docs.append("TEST-SE-RECEIPT Material Receipt 500 @ 2000")
    s1 = record("1. Receive 500m into Main Warehouse")

    # 2–3. Work order 100, approve, issue 100 Main → Field (transfer, no expense).
    wo1 = "TEST-SWO-001"
    applied, additional = compute_issue_split(100, 0, True)
    assert additional == 100 and applied == 0
    led.post_sle(MAIN, -100, RATE, "Stock Entry", "TEST-SE-ISSUE-1", "Material Transfer")
    led.post_sle(FIELD, 100, RATE, "Stock Entry", "TEST-SE-ISSUE-1", "Material Transfer")
    # Same inventory account: no P&L. Optional warehouse-account reclass omitted
    # because WMS does not set expense_account on transfers.
    acc1 = refresh_acc(
        {
            "site_work_order": wo1,
            "issued_qty": 100.0,
            "carried_forward_qty": 0.0,
            "consumed_qty": 0.0,
            "returned_qty": 0.0,
            "transferred_out_qty": 0.0,
            "outstanding_qty": 0.0,
        }
    )
    led.accountability["ACC-WO1"] = acc1
    s3 = record("3. Issue 100m Main → Field Issued")

    # 4. Consume 70 — only this posts expense.
    led.post_sle(FIELD, -70, RATE, "Stock Entry", "TEST-SE-CONS-1", "Material Issue")
    led.post_gl("Consumption Expense", 140_000, 0, "TEST-SE-CONS-1", "Consume 70m")
    led.post_gl("Inventory Asset", 0, 140_000, "TEST-SE-CONS-1", "Consume 70m")
    acc1["consumed_qty"] += 70
    refresh_acc(acc1)
    s4 = record("4. Consume 70m (expense)")

    # 5. Return 10 Field → Main — transfer, not expense.
    led.post_sle(FIELD, -10, RATE, "Stock Entry", "TEST-SE-RET-1", "Material Transfer")
    led.post_sle(MAIN, 10, RATE, "Stock Entry", "TEST-SE-RET-1", "Material Transfer")
    acc1["returned_qty"] += 10
    refresh_acc(acc1)
    s5 = record("5. Return 10m to Main Warehouse")

    # 6. Close WO1. Leftover 20 stays inventory + engineer outstanding.
    s6 = record("6. Close WO1 — leftover 20m still with engineer")

    # 7. WO2 reuses 15 from leftover 20. No second physical transfer.
    wo2 = "TEST-SWO-002"
    applied, additional = compute_issue_split(15, acc1["outstanding_qty"], True)
    if additional != 0 or applied != 15:
        led.failed = (
            f"Reuse split wrong: applied={applied} additional={additional} "
            f"(expected applied=15 additional=0)"
        )
        return led, stages
    acc1["transferred_out_qty"] += applied
    refresh_acc(acc1)
    acc2 = refresh_acc(
        {
            "site_work_order": wo2,
            "issued_qty": additional,
            "carried_forward_qty": applied,
            "consumed_qty": 0.0,
            "returned_qty": 0.0,
            "transferred_out_qty": 0.0,
            "outstanding_qty": 0.0,
        }
    )
    led.accountability["ACC-WO2"] = acc2
    s7 = record("7. WO2 reuse 15m (no Stock Entry)")

    # 8. Consume the reused 15.
    led.post_sle(FIELD, -15, RATE, "Stock Entry", "TEST-SE-CONS-2", "Material Issue")
    led.post_gl("Consumption Expense", 30_000, 0, "TEST-SE-CONS-2", "Consume 15m reused")
    led.post_gl("Inventory Asset", 0, 30_000, "TEST-SE-CONS-2", "Consume 15m reused")
    acc2["consumed_qty"] += 15
    refresh_acc(acc2)
    s8 = record("8. Consume 15m on WO2")

    expected = {
        "main_qty": 410,
        "field_qty": 5,
        "consumed_qty": 85,
        "physical_total": 415,
        "expense_tzs": 170_000,
        "inventory_asset": 415 * RATE,
        "wo1_outstanding": 5,
        "wo2_outstanding": 0,
    }
    final = stages[-1]
    mismatches = []
    if abs(final["main_qty"] - expected["main_qty"]) > 0.001:
        mismatches.append(f"Main {final['main_qty']} != {expected['main_qty']}")
    if abs(final["field_qty"] - expected["field_qty"]) > 0.001:
        mismatches.append(f"Field {final['field_qty']} != {expected['field_qty']}")
    if abs(final["consumed_qty"] - expected["consumed_qty"]) > 0.001:
        mismatches.append(f"Consumed {final['consumed_qty']} != {expected['consumed_qty']}")
    if abs(final["physical_total"] - expected["physical_total"]) > 0.001:
        mismatches.append(
            f"Physical {final['physical_total']} != {expected['physical_total']}"
        )
    if abs(final["expense_tzs"] - expected["expense_tzs"]) > 0.001:
        mismatches.append(f"Expense {final['expense_tzs']} != {expected['expense_tzs']}")
    if abs(acc1["outstanding_qty"] - 5) > 0.001:
        mismatches.append(f"WO1 outstanding {acc1['outstanding_qty']} != 5")
    if abs(acc2["outstanding_qty"] - 0) > 0.001:
        mismatches.append(f"WO2 outstanding {acc2['outstanding_qty']} != 0")

    led.failed = "; ".join(mismatches) if mismatches else None
    led.expected = expected
    # silence unused
    _ = (s1, s3, s4, s5, s6, s7, s8)
    return led, stages


def main():
    led, stages = run()
    payload = {
        "environment": "local-dummy-only",
        "production": False,
        "item": ITEM,
        "item_name": ITEM_NAME,
        "passed": led.failed is None,
        "failure": led.failed,
        "stages": stages,
        "sle": led.sle,
        "gl": led.gl,
        "expected": getattr(led, "expected", None),
    }
    out = Path("/home/user/TP_CABLE_LOCAL_TEST.json")
    out.write_text(json.dumps(payload, indent=2))
    print("PASSED" if payload["passed"] else "FAILED")
    if led.failed:
        print(led.failed)
    for snap in stages:
        print(
            f"{snap['stage']}: Main={snap['main_qty']:.0f} "
            f"Field={snap['field_qty']:.0f} consumed={snap['consumed_qty']:.0f} "
            f"physical={snap['physical_total']:.0f} "
            f"expense={snap['expense_tzs']:.0f} "
            f"inventory={snap['inventory_asset']:.0f}"
        )
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
