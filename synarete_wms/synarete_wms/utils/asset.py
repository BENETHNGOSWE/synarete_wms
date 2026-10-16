import frappe
from frappe.utils import today


def on_asset_movement_submit(doc, method=None):
    """Update WMS asset location/condition after Asset Movement submit."""
    movement_type = doc.get("custom_wms_movement_type")
    destination_site = doc.get("custom_wms_destination_site")
    origin_site = doc.get("custom_wms_origin_site")
    engineer = doc.get("custom_wms_engineer")
    reason = doc.get("custom_wms_reason")

    for asset_row in doc.get("assets") or []:
        if not asset_row.asset:
            continue

        asset = frappe.get_doc("Asset", asset_row.asset)

        if destination_site:
            asset.db_set(
                "custom_wms_current_site",
                destination_site,
                update_modified=True,
            )

        if movement_type == "Site to Warehouse":
            asset.db_set(
                "custom_wms_asset_condition",
                "In Warehouse",
                update_modified=True,
            )
        elif movement_type in ("Warehouse to Site", "Site to Site"):
            asset.db_set(
                "custom_wms_asset_condition",
                "Installed",
                update_modified=True,
            )

        if engineer:
            asset.db_set(
                "custom_wms_installed_by",
                engineer,
                update_modified=False,
            )

        asset.db_set(
            "custom_wms_installation_date",
            today(),
            update_modified=False,
        )

        if reason and asset.meta.get_field("custom_wms_movement_reason"):
            asset.db_set(
                "custom_wms_movement_reason",
                reason,
                update_modified=False,
            )
