from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StockPickingExt(models.Model):
    _inherit = 'stock.picking'

    opportunity_id = fields.Many2one('crm.lead', string='Opportunity', readonly=True)