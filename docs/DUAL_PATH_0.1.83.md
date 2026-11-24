# Dual path work orders — v0.1.83 (local test)

Test this **locally** before production.

## Once

1. Search **WMS Settings**. Leave **Allow Self-Approve** unticked (default).
2. Engineer user must have **Employee** with **User ID** linked.

## Site Work Order (warehouse raises)

1. Log in as Warehouse Manager.
2. **Site Work Order** → New. Fill site, **Engineer** (required), items. Save → Submit.
3. Same user: **Approve** should be hidden / blocked.
4. Log in as a **second** warehouse/stock user → **Approve**.
5. First warehouse user: Issue → Consume → Complete.
6. Log in as the **assigned engineer**. Open **Site Work Order**. They must see this job (**My Work Orders**).

## Allow one person to do all

Tick **WMS Settings → Allow Self-Approve**. Same warehouse user can Approve their own WO. Untick again for four-eyes.

## Engineer raises (still works)

Log in as WMS Engineer only. New Site Work Order. Engineer field fills themselves. Submit. Warehouse Approves and Issues. Engineer Consume.

## ServiceNow

Warehouse: **ServiceNow Site Work Order** → New. Assign engineer. Material → Receive → Issue → Consume → Complete.

Engineer login: list shows that WO.

Import from ServiceNow is unchanged.

## Do not

- Create a WO without an engineer.
- Use ServiceNow Receive on warehouse **Site Work Order**.
- Push to production until this local test passes.
