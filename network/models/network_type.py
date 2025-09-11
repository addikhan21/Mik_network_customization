from odoo import models, fields, api

class NetworkType(models.Model):
    _name = 'network.type'
    _description = 'Network Type'
    _rec_name = "type"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    type = fields.Char(string='Type', required=True)