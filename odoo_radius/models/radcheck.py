from odoo import models, fields, api

class RadCheck(models.Model):
    _name = 'radcheck'
    _description = 'RADIUS Check'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'username'
    _log_access = False

    username = fields.Char(string='UserName', index=True, required=True)
    attribute = fields.Char(string='Attribute', default="Cleartext-Password", 
                            index=True, required=True)
    op = fields.Char(string='Operator', default=":=", size=2, required=True)
    value = fields.Char(string='Value', required=True)
