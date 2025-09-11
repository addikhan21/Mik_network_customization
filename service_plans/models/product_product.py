from odoo import models, fields

class ProductProduct(models.Model):
    _inherit = 'product.product'

    service_group_id = fields.Many2one('service.group', string='Service Group')
    