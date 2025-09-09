from odoo import models, fields, api

class RadReply(models.Model):
    _name = 'radreply'
    _description = 'RADIUS Reply'
    _log_access = False
    _rec_name = 'username'

    username = fields.Char(string='UserName', index=True, required=True)
    attribute = fields.Char(string='Attribute', index=True, required=True)
    op = fields.Char(string='Operator', default="=", size=2, required=True)
    value = fields.Char(string='Value', required=True)