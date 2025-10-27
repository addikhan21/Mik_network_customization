{
    'name': 'Crm Customization',
    'version': '18.0',
    'category': 'CRM',
    'summary': 'CRM customizations with additional fields',
    'depends': ['crm', 'inventory_ext','stock'],
    'data': [
        'data/ir_sequence_data.xml',
        'security/ir.model.access.csv',
        'views/crm_lead_ext.xml',
        'views/res_partner_ext.xml',
    ],
    'installable': True,
    'auto_install': False,
}