# -*- coding: utf-8 -*-
{
    "name": "Network",
    "summary": "Module for managing network configurations and devices",
    "description": """
        This module provides comprehensive tools for managing network devices, 
        types, and configurations directly within Odoo. Ideal for IT administrators 
        and network managers to organize and monitor network-related assets.
    """,
    "author": "Softbox",
    "website": "https://www.softbox.pk",
    # Categories can be used to filter modules in the module listing
    "category": "Network/Management",
    "version": "18.0",
    # Any module necessary for this one to work correctly
    "depends": ["base", "mail", "odoo_radius", "base_security_groups"],
    # Always loaded data files
    "data": [
        "security/ir.model.access.csv",
        "views/network_vlan_views.xml",
        "views/network_nas_view.xml",
        "views/network_type_view.xml",
        "views/res_config_settings_views.xml",
    ],
    # Only loaded in demonstration mode
    "demo": [
        "demo/demo.xml",
    ],
    # Additional technical details
    "license": "AGPL-3",
    "application": True,
    "installable": True,
}
