# MULTIFOAM full-flow demo test (v0.1.88)

Use **only local**. Do not run this on production. Do not create dummy TEST items — use the real item **MULTIFOAM**.

Goal: prove Purchase Order batch receiving, leftover qty across POs, then Site Work Order issue → closeout → complete. Write **Pass / Fail** on every step. If it fails, stop, screenshot, write the exact error.

## 0. Before you start

1. About should show **Synarete WMS 0.1.88**. If not, copy the 0.1.88 app folder, migrate, restart backend, Ctrl+Shift+R.
2. WMS Settings: Company, **Main Warehouse**, **Field Issued Warehouse**. **Allow PO Over-Receive** = No. **Allow Complete Without Closeout** = No. **Allow Self-Approve** = No unless you are one warehouse user doing every step.
3. Pick and write down:

| Field | Value you will use |
|---|---|
| Item | MULTIFOAM |
| Supplier | ________________ |
| Main Warehouse | ________________ |
| Field Issued Warehouse | ________________ |
| Site | ________________ |
| Engineer | ________________ |
| Expense account (warehouse picks on consume if you also test two-step) | ________________ |

4. Stock → Stock Balance (or Bin) for **MULTIFOAM**:

| Warehouse | Qty now (before demo) |
|---|---|
| Main | |
| Field Issued | |

All later counts are **this starting qty + demo movement**.

---

## Part A — Purchase Order, first batch of 5 (of 10)

**A1.** Buying → Purchase Order → New.

- Supplier = the supplier you chose.
- WMS Material Type = **MP** (not HTT).
- Item **MULTIFOAM**, qty **10**, rate = the real rate (or last purchase rate).
- Save. If a banner shows previous outstanding from this supplier, write it here: ________
- Submit the PO.
- Write PO name: **________________**

**Expected:** WMS Total Ordered = 10, Received = 0, Remaining = 10, WMS Receive Status = Open.

**A2.** On that PO: **WMS → Receive Batch**.

- Receive Into = Main Warehouse.
- This Batch for MULTIFOAM = **5**.
- Receive Batch.

**Expected:**

- Purchase Receipt created (open it, confirm qty 5, warehouse Main).
- PO Remaining = **5**, Received = **5**, WMS Receive Status = **Partially Received**.
- PO is **not** Completed.
- WMS Delivery Phases: one row, qty 5, date today, Received By = you.
- Stock: Main MULTIFOAM = start + 5.
- GL of the Purchase Receipt: **Debit inventory** (1040010 or warehouse account), **Credit SRBNB** (not Creditors, not 5010010).

**A3. Negative — over-receive.** Receive Batch again, This Batch = **6**.

**Expected:** Error. Outstanding is 5. No extra stock.

**Pass / Fail A:** ______   Notes: ________________

---

## Part B — Second batch completes the first PO

**B1.** Same PO → Receive Batch → This Batch = **5**.

**Expected:**

- Remaining = **0**.
- WMS Receive Status = **Completed**.
- Two phase rows (5 + 5).
- Main MULTIFOAM = start + 10.
- Receive Batch button gone (nothing left).

**Pass / Fail B:** ______

---

## Part C — Leftover on an old PO + a new PO (13 to deliver)

This is the “supplier still owes 3, then we order 10 more” test.

**C1.** New Purchase Order, same supplier, MULTIFOAM qty **10**. Submit.  
Write PO-2: **________________**

**C2.** Receive Batch **7** only. Leave **3** outstanding.

**Expected:** PO-2 Partially Received, Remaining 3. Main = start + 10 + 7.

**C3.** New Purchase Order, **same supplier**, MULTIFOAM qty **10**. **Do not change qty to 13.** Save.  
Write PO-3: **________________**

**Expected on PO-3 (must be visible, orange/notice):**

- New order quantity: **10**
- Previous outstanding: **3**
- Total expected delivery: **13**
- Ordered qty on PO-3 stays **10**

**C4.** Receive the leftover **3** on **PO-2** (original), not on PO-3.

**Expected:** PO-2 Remaining 0, Completed. PO-3 still Remaining 10. Report **Supplier Outstanding Items** shows PO-3 = 10, PO-2 gone.

**C5.** You can leave PO-3 open (do not have to receive it for the SWO demo). Stock needed for Part D is already in Main from A+B+C2+C4 = start + 20.

**Pass / Fail C:** ______

---

## Part D — Site Work Order: issue 3, use 2, return 1

Stock in Main must be enough for 3. If MULTIFOAM is not a stock item, maintain stock / valuation will fail here — that is a real bug/config to record.

**D1.** Synarete WMS → Site Work Order → New.

- Title: `MULTIFOAM closeout demo`
- Site, Engineer, Work Type = Corrective Maintenance.
- Materials: MULTIFOAM, qty **3**, source warehouse = **Main**.
- **Submit** (or Submit for Review).

Write SWO: **________________**

**D2.** Another warehouse user **Approve** (unless Allow Self-Approve is on).

**D3.** **Material → Issue Material**.

- Confirm item MULTIFOAM, qty 3, from Main.
- Save, then warehouse **Submit / Issue** (do not replace Issue Save with Submit if your role uses Save then Issue).
- Follow the usual Issue Material path until status **Issued**.

**Expected:**

- Main −3, Field Issued +3 (still inventory, **not** expense).
- GL: transfer between inventory accounts. **No** 5010010 on issue.

**D4. Negative — complete too early.** **Complete Work Order** now.

**Expected:** Blocked. Message that **WMS Material Closeout** is required. Status stays In Progress / Issued.

**D5.** **Material → Material Closeout**.

- Work Order Type = Site Work Order, Work Order = this SWO (should fill lines).
- MULTIFOAM: Issued **3**, Used **2**, Returned unused **1**.
- Submit.

**Expected:**

- Used 2 posted as consume from Field Issued (expense = item default; engineer did not pick GL).
- Unused 1 transferred Field Issued → Main.
- Field Issued MULTIFOAM for this job = 0 extra (demo +3 −2 −1).
- Main +1 vs after issue.
- Consume Stock Entry + Return Stock Entry on the closeout.

**D6.** **Complete Work Order**. Confirm.

**Expected:** Status **Completed**. No leftover Field Issued from this 3.

**D7. Negative — bad closeout numbers** (do on a **new** SWO later, or cancel if you still have a draft): Issued 3, Used 2, Returned 0 → must error.

**Pass / Fail D:** ______

---

## Part E — Optional: two-step consume then closeout

Only if you want to prove consume + leftover still need closeout.

1. New SWO, issue **3** MULTIFOAM.
2. Engineer **Consume Material** qty **2** → Submit (Pending Verification). Warehouse Approve + expense account.
3. Try Complete → must still fail (1 unused).
4. Closeout: Used 2, Returned unused 1. Submit. Complete.

**Pass / Fail E:** ______

---

## Stock and GL scorecard (fill at the end)

Starting Main: ______   Starting Field: ______

| Step | Main change | Field change | Expense? |
|---|---|---|---|
| PO receive 5 | +5 | 0 | No (SRBNB) |
| PO receive 5 | +5 | 0 | No |
| PO-2 receive 7 | +7 | 0 | No |
| PO-2 receive 3 | +3 | 0 | No |
| SWO Issue 3 | −3 | +3 | No |
| Closeout used 2 | 0 | −2 | **Yes**, 2 only |
| Closeout unused 1 | +1 | −1 | No |

Net from this demo: Main **+18**, Field **0**, expense **2 × rate**.

---

## Bug log

| Step | What you clicked | What you saw | Pass/Fail |
|---|---|---|---|
| A1 | | | |
| A2 | | | |
| A3 | | | |
| B1 | | | |
| C3 | | | |
| C4 | | | |
| D3 | | | |
| D4 | | | |
| D5 | | | |
| D6 | | | |
