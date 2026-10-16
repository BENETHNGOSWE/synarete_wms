# Synarete WMS user flow

## One-time setup

1. Create the Main physical Warehouse.
2. Create the Field Issued virtual Warehouse.
3. Open `WMS Settings` and select the Company, Main Warehouse, and Field Issued Warehouse.
4. Import the 948 telecom Sites into `WMS Site` using the agreed site list.
5. Mark Items as MP, HTT, Consumable, Spare Part, or Tool.
6. Assign WMS roles to users.

## MP materials

```text
Purchase Order
-> Purchase Receipt
-> Main Warehouse
-> Employee creates Site Work Order
-> Stock Manager reviews/approves
-> WMS Material Issue
-> Stock Entry moves stock to Field Issued
-> Site/Engineer consumes or returns material
```

## HTT materials

```text
Customer material arrives
-> HTT Material Receipt
-> WMS HTT ledger records custody
-> WMS Material Issue dispatches to Site
-> WMS Material Return Record tracks return
```

HTT records do not automatically create Synarete-owned stock valuation.

## ServiceNow Site Work Orders

This is a separate process from HTT.

```text
Import ServiceNow Work Order
-> Material Required
-> Receive material against the original work order
-> Issue to the original work order, or interchange to another work order
-> Optionally issue MP warehouse stock (client payback)
-> Consume
-> Reconcile
-> Complete
```

The original material request is never deleted. Interchange reason, user, and both work orders are stored. Use **SNWO MP Material Report** for MP stock that the client must pay back.

## ServiceNow Dashboard

In Desk search, type **ServiceNow Dashboard**.

The page shows this month's work-order counts, received material, MP issues, interchange, and consumed vs remaining. Use **Export Report** for Excel.

## Engineer consignment

```text
Engineer Consignment
-> Stock transfer from Main Warehouse to Field Issued
-> Engineer records WMS Material Consumption
-> Remaining quantity is calculated
-> Stock Manager reconciles periodically
```

## Stock taking

```text
Stock Taking Entry
-> enter physical quantities
-> submit
-> standard Stock Reconciliation is created
```

## Delivery confirmation

```text
Delivery Note submitted
-> Delivery Note Signature record created
-> engineer confirms or signs receipt
-> Delivery Note signature status updated
```
