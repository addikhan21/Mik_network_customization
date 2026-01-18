{
    "name": "Isp Stats",
    "version": "18.0.2.0.0",
    "description": "Users Status Dashboard",
    "summary": "Status Dashboard",
    "author": "Softbox Team",
    "website": "",
    "license": "LGPL-3",
    "category": "",
    "depends": ["base", "web", "odoo_radius", "users", "base_security_groups",
    "subscription_oca",
    "account",
    "calendar",
    "purchase",
    "stock",
    "crm",
    "helpdesk_mgmt",],
    "data": [
        "security/ir.model.access.csv",
        "views/users_stats.xml",
        # "views/isp_notification_views.xml",
    ],
    "demo": [],
    "auto_install": False,
    "installable": True,
    "application": True,
    "assets": {
        "web.assets_backend": [
            "stats/static/src/components/**/*.js",
            "stats/static/src/components/**/*.xml",
            "stats/static/src/components/**/*.scss",
        ]
    },
}
