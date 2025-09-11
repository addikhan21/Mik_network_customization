# -*- coding: utf-8 -*-
{
    'name': 'FreeRADIUS MAC Binding',
    'version': '18.0',
    'author': 'Softbox',
    'category': 'Services',
    'summary': 'Automatically bind MAC addresses to users on RADIUS session start',
    'depends': ['base'],
    'post_init_hook': 'create_radius_triggers',
    'uninstall_hook': 'drop_radius_triggers',
    'installable': True,
    'application': False,
}