# Local implementation plan

## Phase 0 — app foundation

- Install and import the app locally.
- Confirm the app repository is persistent.
- Confirm `bench migrate` and `bench list-apps` work.
- Keep hooks minimal.
- Add a test command and basic documentation.

## Phase 1 — masters and roles

- Decide the Site master fields.
- Define Main Warehouse and Field Issued warehouse behavior.
- Define MP and HTT classification.
- Define WMS roles and DocPerm.
- Create safe import templates for the existing site list; do not commit the site data to Git.

## Phase 2 — MP material issue MVP

- Site Request / Site Work Order.
- Required item lines.
- Stock Manager review and approval.
- Standard Stock Entry or Delivery Note for the physical issue.
- WMS issue context: Site, Employee/Engineer, request, and quantities.
- Submit/cancel/retry tests.

## Phase 3 — HTT custody

- Customer material receipt.
- Temporary custody and dispatch.
- Serial/batch support where required.
- Return status and audit trail.

## Phase 4 — remaining operations

- Asset movement and returns.
- Engineer consignment.
- Monthly service materials.
- Stock taking and standard Stock Reconciliation.
- Supplier delivery phases.
- Delivery confirmation/signature.
- Reports and dashboards.

## Rule for each phase

Every phase must pass local tests before the next phase is implemented. No production code or production data is used during local development.
