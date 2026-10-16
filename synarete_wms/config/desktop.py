from frappe import _


def get_data():
    return [
        {
            "module_name": "Synarete WMS",
            "type": "module",
            "label": _("Synarete WMS"),
            "color": "blue",
            "icon": "octicon octicon-package",
            "link": "List/WMS Site/List",
            "link_type": "DocType",
        }
    ]
