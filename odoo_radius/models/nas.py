from odoo import models, fields, api

class NAS(models.Model):
    _name = 'nas'
    _description = 'NAS'
    _rec_name = 'nasname'
    _log_access = False
    _inherit = ["mail.thread", "mail.activity.mixin"]

    nasname = fields.Char(string='NAS Name', index=True, required=True)
    shortname = fields.Char(string='Short Name', required=True)
    type = fields.Char(string='Type', default="other", required=True)
    ports = fields.Integer(string='Ports')
    secret = fields.Char(string='Secret', required=True)
    server = fields.Char(string='Server')
    community = fields.Char(string='Community')
    description = fields.Text(string='Description')
    