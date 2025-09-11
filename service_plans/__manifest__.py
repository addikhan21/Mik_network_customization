# -*- coding: utf-8 -*-
{
    'name': "Services",

    'summary': "Manage service plans and their configurations in Odoo",

    'description': """
        The Services module provides tools for managing various service plans, 
        their attributes, and configurations directly within Odoo. 
        
        Key Features:
        - Service plan management
        - Dynamic configuration of service attributes
        - Integration with Odoo's messaging system
    """,

    'author': "Softbox",
    'website': "https://www.softbox.pk",

    # Categories can be used to filter modules in the module listing
    'category': 'Network/Management',
    'version': '18.0',

    # Dependencies required for this module
    'depends': [
        'base',  
        'mail' ,
        # 'odoo_radius',
        'stock',
        "network",
        "base_security_groups"
    ],

    # Data files loaded during module installation
    "data": [
        "security/ir.model.access.csv",
        "views/service_group.xml",
        'views/product_views.xml',  
    ],

    # Files loaded only in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],

    # Additional technical details
    'license': 'AGPL-3',
    'application': True,   
    'installable': True,   
    'auto_install': False  
}
