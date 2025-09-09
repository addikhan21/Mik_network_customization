# -*- coding: utf-8 -*-
{
    'name': "Radius Manager",

    'summary': "Module for RADIUS server management and authentication",

    'description': """
    This module provides functionality for managing RADIUS server configurations,
    user groups, and authentication mechanisms directly within Odoo. It allows 
    administrators to manage RADIUS-related settings such as user accounts, 
    group configurations, and authentication parameters.
    """,
    
    "pre_init_hook": "_auto_pre_init",
    "uninstall_hook":  "uninstall_hook",

    'author': "Softbox",
    'website': "Softbox.pk",

    # Categories can be used to filter modules in modules listing
    'category': 'Network/Authentication',
    'version': '18.0',

    # Dependencies
    'depends': ['base', "mail", "base_security_groups"],

    # Always loaded
    "data": [
        "security/ir.model.access.csv",
        "data/cron.xml",
        "views/radcheck.xml",
        "views/radgroupcheck.xml",
        "views/radgroupreply.xml",
        "views/radreply.xml",
        "views/radusrgroup.xml",
        "views/radpostauth.xml",
        "views/radacct.xml",
        "views/nas.xml",
        "views/nasreload.xml",
        
    ],

    # Only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],

    # License and other details
    'license': 'AGPL-3',  # Adjust as per your license type, e.g., AGPL-3, LGPL-3, etc.

    # Odoo Compatibility
    'application': True,
    'installable': True,
    'auto_install': False,
}