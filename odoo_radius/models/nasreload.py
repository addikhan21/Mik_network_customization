from odoo import models, fields, api

class NASReload(models.Model):
    _name = 'nasreload'
    _description = 'NAS Reload'
    _log_access = False
    _rec_name = "nas_ip_address"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    nas_ip_address = fields.Char(string='NAS IP Address', required=True)
    reload_time = fields.Datetime(string='Reload Time', required=True)
    

