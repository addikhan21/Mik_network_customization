{
    "name": "GenieACS Integrations",
    "summary": "Integrate GenieACS and managing OLT devices",
    "description": """
        This module provides the integration for GenieACS in the ISP module.
        It handles CPE device fetching, rebooting, and factory reset functionality via TR-069.
    """,
    "author": "Softbox",
    "category": "Network/Management",
    "version": "18.0",
    "depends": ["base", "network", "users"],
    "data": [
        "security/ir.model.access.csv",
        "views/network_olt_views.xml",
        "views/network_nas_view.xml",
        "views/res_config_settings_views.xml",
        "views/genieacs_pending_tasks_wizard_views.xml",
        "views/users_views.xml",
    ],
    "application": False,
    "installable": True,
}
