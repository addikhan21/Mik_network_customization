from odoo import models, fields

class SaleSubscription(models.Model):
    _inherit = 'sale.subscription'

    ip_address_id = fields.Many2one('ip.address',  string='IP Address')