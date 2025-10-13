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

        StockLocation = self.env['stock.location']
        # Determine name and codes
        partner_uid_value = uid_value
        parent_name = f'Customer Storage - {partner_uid_value}'
        child_name = f'Customer Internal Location - {partner_uid_value}'
        parent_ref_code = f'cust_storage_{uid_value}'
        child_ref_code = f'cust_internal_{uid_value}'
        # Create parent view location
        parent_vals = {
            'name': parent_name,
            'usage': 'view',
        }
        parent = StockLocation.create(parent_vals)
        # Create child internal location under parent
        child_vals = {
            'name': child_name,
            'usage': 'internal',
        }
        child = StockLocation.create(child_vals)
        # Link on partner
        partner.write({
            'internal_location_id': child.id,
            'parent_storage_location_id': parent.id,
        })
        return child
