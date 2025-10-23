# -*- coding: utf-8 -*-
{
    'name': "users",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'base_import','mail', "base_security_groups"],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/record_rule.xml',
        'wizards/users_wizard.xml',
        'wizards/edit_profile.xml',
        'wizards/edit_package.xml',
        'wizards/edit_vlan.xml',
        'views/views.xml',
        # 'views/distributors_views.xml',
        # 'views/admins_views.xml',
        'views/recharge_history_views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    
}

