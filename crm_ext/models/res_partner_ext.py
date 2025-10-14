from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartnerExt(models.Model):
    _inherit = 'res.partner'

    x_customer_uid = fields.Char(string='Customer UID', copy=False, index=True)
    internal_location_id = fields.Many2one('stock.location', string='Customer Internal Location', )
    parent_storage_location_id = fields.Many2one('stock.location',
                                                 string='Customer Storage (view)', )

    @api.model
    def _create_customer_locations(self, partner, uid_value):
        """
        Create a parent view location and a child internal location for the
        partner.
        Returns child_internal_location record.
        """
        parent_storage = self.env.ref('crm_ext.internal_storage')
        StockLocation = self.env['stock.location']
        # Determine name and codes
        partner_uid_value = uid_value
        child_name = f'{partner_uid_value}'


        child_vals = {
            'name': child_name,
            'usage': 'internal',
            'location_id': parent_storage.id,
        }
        child = StockLocation.create(child_vals)
        # Link on partner
        partner.write({
            'internal_location_id': child.id,
        })
        return child
