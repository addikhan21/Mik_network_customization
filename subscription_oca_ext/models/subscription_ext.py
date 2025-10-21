from odoo import models, fields

class SaleSubscription(models.Model):
    _inherit = 'sale.subscription'

    ip_address_ids = fields.One2many('ip.address', 'subscription_id', string='IP Addresses')