# Synarete WMS architecture decisions

## 1. One app

All warehouse modules live in the `synarete_wms` app. The existing `synarete_hr` app remains separate.

## 2. Site and warehouse

A telecom Site is a business location. It is not automatically an ERPNext Warehouse.

Synarete uses:

- one physical Main Warehouse for received stock;
- one virtual Field Issued warehouse for stock that has left the Main Warehouse but remains under WMS tracking;
- a separate Site master/list for approximately 948 telecom sites.

Each issue stores the Site, Engineer/Employee, request, item, quantity, and source/destination context. This avoids creating one ERPNext Warehouse per site while preserving a reliable stock ledger.

## 3. MP materials

MP materials are owned by Synarete and use normal ERPNext stock transactions:

```text
Purchase Order -> Purchase Receipt -> Main Warehouse
Site request -> approval -> Stock Entry / issue -> Field Issued
```

The Stock Ledger remains the source of truth for quantities. WMS records add operational context such as Site, Engineer, and request.

## 4. HTT materials

HTT materials are customer-owned. The design must prevent customer material from being treated as Synarete-owned valued inventory. Receipt, temporary custody, dispatch, and return are tracked with a dedicated WMS process and clear ownership fields.

## 5. ServiceNow Site Work Orders

ServiceNow work orders are a separate operational process from HTT. They do not create HTT custody records and HTT does not create ServiceNow work orders.

Material movements are posted as `SNWO Material Transaction` rows so the original request, the work order that received the material, and the work order that actually received the issue remain visible. Interchange and MP payback are flags on that ledger.

## 6. Standard ERPNext first

Use Item, Item Group, Warehouse, Purchase Order, Purchase Receipt, Material Request, Stock Entry, Delivery Note, Stock Ledger, Asset, Asset Movement, Serial Number, Batch, and Stock Reconciliation where they cover the requirement.

Custom DocTypes should represent the missing business process, not duplicate standard stock transactions.
