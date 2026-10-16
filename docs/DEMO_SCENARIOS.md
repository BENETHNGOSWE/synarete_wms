# Local WMS demo data and test scenarios

## Seed the demo setup

Run only on the local site:

```bash
cd /mnt/d/2026/BENETH/CLIENTS/SYNARATE/synarate-local/frappe-setup

docker compose exec backend bash -lc '
cd /home/frappe/frappe-bench
bench --site erp.synarete.co.tz execute \
  synarete_wms.synarete_wms.utils.demo_data.seed_local_demo
'
```

The seed creates or reuses:

```text
WMS Site: DEMO-SITE-001
Customer: DEMO CUSTOMER
Item: DEMO-MP-CABLE (100 units opening stock)
Item: DEMO-MP-DEVICE (10 units opening stock)
Item: DEMO-HTT-DEVICE (customer-owned demo item)
```

It does not create Users, passwords, employees, production records, or production transactions.

## MP happy path

Expected opening stock:

```text
Main Warehouse:
DEMO-MP-CABLE = 100
DEMO-MP-DEVICE = 10

Field Issued Warehouse:
No demo issue yet
```

1. Employee/Stock User creates a Site Work Order:
   - Site: `DEMO-SITE-001`
   - Engineer: an existing local Employee
   - Material Type: MP
   - Item: `DEMO-MP-CABLE`
   - Quantity: 10
   - Source Warehouse: Main Warehouse
2. Employee submits the Work Order.
3. Stock Manager approves it.
4. Stock Manager/Warehouse Manager creates WMS Material Issue from the approved Work Order.
5. Submit WMS Material Issue through the standard Actions menu.
6. Confirm automatic Stock Entry:
   - Material Transfer
   - Main Warehouse → Field Issued Warehouse
   - Quantity: 10
7. Create WMS Material Consumption for quantity 4.
8. Confirm automatic Material Issue from Field Issued Warehouse.

Expected final values:

```text
Main Warehouse DEMO-MP-CABLE: 90
Field Issued DEMO-MP-CABLE: 6
Consumed: 4
```

## MP partial return

Create Material Return Record:

```text
Material Type: MP
Installation Type: New Installation
Site: DEMO-SITE-001
Engineer: same demo Employee
Quantity to Return/Replace: 3
New Item: DEMO-MP-CABLE
Serial fields: blank for non-serialized demo item
```

Submit and confirm:

```text
Field Issued Warehouse → Main Warehouse
Quantity: 3
```

Expected values:

```text
Main Warehouse: 93
Field Issued Warehouse: 3
```

## MP replacement

Use a separate replacement item if the replacement must be distinguishable. The replacement record requires:

```text
Installation Type: Replacement
Quantity to Return/Replace: 3
Old Item: existing issued item
New Item: replacement item
```

The system creates two transfers:

```text
Old item: Field Issued → Main Warehouse
New item: Main Warehouse → Field Issued
```

## HTT custody flow

1. Create/confirm `DEMO CUSTOMER`.
2. Create HTT Material Receipt:
   - Customer: `DEMO CUSTOMER`
   - Site: `DEMO-SITE-001`
   - Item: `DEMO-HTT-DEVICE`
   - Quantity: 5
3. Submit the receipt.
4. Create WMS Material Issue with Material Type HTT.
5. Link the HTT Material Receipt.
6. Dispatch quantity 2.
7. Confirm the HTT ledger balance is 3.
8. Create a Material Return Record for quantity 1.
9. Confirm the custody balance becomes 4.

HTT transactions must not be treated as Synarete-owned valued stock.

## Delivery Note test

After a WMS Material Issue is submitted:

```text
WMS → Print Delivery Note
WMS → Open Delivery Signature
```

The print should show site, engineer, items, quantities, delivered-by, received-by, and signature areas. The signature record can be confirmed or marked Signed.
