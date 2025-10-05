{
    'name': 'Inventory Customization',
    'version': '18.0',
    'category': 'Inventory',
    'summary': 'Inventory customizations with additional fields',
    'depends': ['base','hr_expense', 'product'],
    'data': [
        'data/ir_sequence.xml',
        'views/product_template_ext.xml',
    ],
    'installable': True,
    'auto_install': False,
}