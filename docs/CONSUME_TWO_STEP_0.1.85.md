# Two-step Consume — v0.1.85 (local test)

Receive / Issue stay on **Inventory 1040010**. Expense posts **only** when warehouse **Approves** consume.

## Flow

1. Engineer (or warehouse) on **Site Work Order** → **Material → Consume Material**.
2. Enter **qty used** only → **Submit**.
   Status = **Pending Verification**. **No** Stock Ledger. **No** expense.
3. Warehouse / Stock Manager opens the consumption.
   **Expense Account** on each item (prefilled from Item default; they can change).
   **Actions → Approve**.
   Then: Credit **1040010**, Debit the chosen expense GL.

## Item setup

On each stock Item, set **Default Expense Account** (Consumables or another). Warehouse can still pick a different account on Approve.

## Do not

- Engineer picking GL (they do not see Expense Account).
- Expense on Issue to the engineer.
- Production until local test is OK.
