# Site Work Order Engineer Name — v0.1.96

The Site Work Order list now displays the linked Employee's `employee_name` in the **Engineer Name** column instead of the Employee ID. The editable **Engineer** link remains on the form; the read-only **Engineer Name** field is populated from that link. Existing Site Work Orders are backfilled by the app's after-migrate hook, and future saves refresh the display value.

This is a list/display improvement only. It does not change assignment rules, approval workflow, Work Order closeout, stock posting, or GL behavior.

## Apply

After installing the updated app source, run the site's usual `bench migrate` command to add the display field and backfill existing Work Orders. The app's list script only adds the display field to the list; no separate asset build is needed.
