# When inventory vs expense — v0.1.84

WMS does **not** pay suppliers and does **not** raise Purchase Orders. It only tracks stock you **have**, **remain**, **cost**, then Issue / Consume.

## The two accounts

| When | Account | Document |
|---|---|---|
| Stock **in the store** (including issued to engineer, not yet used) | **`1040010 - INVENTORY - SEL`** (warehouse Account) | Receive / Issue / Return |
| Spare **used** (Consume) | **`5010010 - CONSUMABLES - SEL`** (or the expense you set) | WMS Material Consumption |
| Loading **stock you already own** (was expensed before) | Debit `1040010`, Credit **`5010010`** | Stock Reconciliation / Material Receipt **Difference Account** |

Never put `1040010` on Difference Account. Never debit the supplier from WMS.

## WMS Settings (do this once)

1. Search **WMS Settings**.
2. Company, Main Warehouse, Field Issued Warehouse.
3. **Consume Expense Account** = `5010010 - CONSUMABLES - SEL`.
4. **Opening Stock Adjustment Account** = same `5010010` (for uploading remaining stock).
5. Save.

Warehouse form **SYNARETE MAIN WAREHOUSE – SEL** → Account = **`1040010`**. Same idea for Field Issued if it is still company stock.

## Item (each spare)

Maintain Stock = Yes. Valuation Rate = cost per unit. Do **not** use item `5010010-CONSUMABLES` (that is a service / expense item, not stock).

## A. New goods arriving (qty + value onto inventory)

Stock Entry → **Material Receipt** → Main Warehouse.  
**Difference Account** = finance clearing if they use one; WMS only needs inventory Debit on `1040010`.  
Do **not** Consume here.

## B. Upload stock you already have (opening / previously expensed)

After physical count, **only remaining qty**:

Stock Reconciliation (or Material Receipt)  
Example: 300 m still there @ 2,000 = 600,000.  
Difference Account = **Opening Stock Adjustment Account** (`5010010`).

Result: Dr Inventory 600,000, Cr Consumables 600,000.  
The 200 m already used stays expense. **No supplier.**

Accountant must approve the count. **Local first. Not production auto-post.**

## C. After stock is in

Site Work Order → Approve → **Issue** (still `1040010`) → **Consume** (then `5010010`).

70 m @ 2,000 → Dr Consumables 140,000, Cr Inventory 140,000.

## Reports

- On hand / value: **WMS Inventory Valuation**, **WMS Inventory Movement**, Stock Ledger  
- Used cost: **WMS Work Order Material Cost**, GL on `5010010` for consume vouchers only  
