{
    'name': 'Subscription IP Management Extension',
    'version': '18.0',
    'category': 'Subscription',
    'depends': ['subscription_oca'],
    'data': [
        'security/ir.model.access.csv',
        'views/ip_address_views.xml',
        'views/subscription_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}