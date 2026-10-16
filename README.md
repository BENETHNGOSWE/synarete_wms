# Synarete WMS

Custom Warehouse Management System for Synarete Engineering Limited, Tanzania.

This is a separate Frappe/ERPNext v15 application. It does not modify the existing `synarete_hr` app.

## Current scope

The application will cover:

- MP company-owned materials;
- HTT customer-owned materials;
- site work orders and material requests;
- ServiceNow Site Work Order material lifecycle, interchange, and MP payback;
- main warehouse receiving and issuing;
- engineer/site issue tracking;
- asset movement and returns;
- engineer consignment stock;
- monthly service materials;
- supplier delivery phases;
- stock taking and reconciliation;
- delivery confirmation and signature;
- WMS reports and dashboards.

## Stock model

Synarete operates one physical Main Warehouse. The application uses one additional virtual ERPNext warehouse, `Field Issued`, to preserve stock-ledger accuracy without creating approximately 948 ERPNext Warehouses.

Every issue records the actual telecom Site, Employee/Engineer, request, items, quantities, and destination context. Site is a separate business master and is not automatically an ERPNext Warehouse.

## Development rule

Build and test locally first. Do not put production data, employee data, passwords, API keys, site configuration, or backups in this repository.

## Requirements

- Frappe v15
- ERPNext v15
- HRMS v15
- Python version supplied by the local Frappe bench

## Local installation

Use the local Docker bench and the local site configured for this project. Do not run production container commands from this repository.

The implementation is intentionally staged. Standard ERPNext stock transactions are used wherever possible; custom DocTypes are added only where the business process is not covered by ERPNext.

## Install this zip (do not skip the outer folder)

Unzip `synarete_wms-v0.1.76.zip`. You should see **nine** items:

`docs`, `scripts`, `synarete_wms`, `.gitignore`, `license.txt`, `MANIFEST.in`, `README.md`, `requirements.txt`, `setup.py`

Copy **that whole folder** to `apps/synarete_wms/` so this path exists:

`apps/synarete_wms/synarete_wms/hooks.py`

Do **not** copy only the inner `synarete_wms` package (the one that contains `hooks.py` and `config`). That layout causes:

`ModuleNotFoundError: No module named 'synarete_wms.synarete_wms'`

Then: `bench --site <local-site> migrate` and restart backend. Do not install this on production until local testing passes.
