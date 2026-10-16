#!/usr/bin/env python3
"""Static repository checks that do not require a running Frappe site."""

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors = []

for path in ROOT.glob("synarete_wms/**/*.json"):
    try:
        data = json.loads(path.read_text())
    except Exception as exc:
        errors.append(f"{path}: invalid JSON: {exc}")
        continue

    if data.get("doctype") != "DocType":
        continue

    fields = data.get("fields", [])
    fieldnames = [field.get("fieldname") for field in fields]
    duplicates = sorted(
        {
            fieldname
            for fieldname in fieldnames
            if fieldname and fieldnames.count(fieldname) > 1
        }
    )
    for fieldname in duplicates:
        errors.append(f"{path}: duplicate fieldname {fieldname}")

    for fieldname in data.get("field_order", []):
        if fieldname not in fieldnames:
            errors.append(f"{path}: field_order references {fieldname}")

for path in ROOT.glob("synarete_wms/**/*.py"):
    try:
        ast.parse(path.read_text())
    except Exception as exc:
        errors.append(f"{path}: invalid Python: {exc}")

hooks_path = ROOT / "synarete_wms" / "hooks.py"
if not hooks_path.exists():
    errors.append("synarete_wms/hooks.py is missing")

if errors:
    print("FAILED")
    for error in errors:
        print("-", error)
    raise SystemExit(1)

print("PASS: WMS repository static validation")
