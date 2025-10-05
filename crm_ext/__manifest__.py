{
    'name': 'Crm Customization',
    'version': '18.0',
    'category': 'CRM',
    'summary': 'CRM customizations with additional fields',
    'depends': ['crm', 'inventory_ext'],
    'data': [
        'views/crm_lead_ext.xml',
    ],
    'installable': True,
    'auto_install': False,
}