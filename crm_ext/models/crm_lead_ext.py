from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    phone = fields.Char(string='Phone Number', required=True)
    contact_name = fields.Char(string='Full Name', required=True)
    hardware_required = fields.Boolean(string='Is Hardware Required')
    data_package_id = fields.Many2one(
        'product.product',
        string='Data Package',
        required=True,
        domain=[('is_isp_service', '=', True)]
    )

    is_hard_equipment_ids = fields.One2many(
        'equipment.line',
        'equipment_line_id',
        string='Is Network Equipment',
        required=True,
    )

    @api.model
    def _generate_customer_uid(self):
        seq = self.env.ref('crm_ext.seq_customer_uid', raise_if_not_found=False)
        if not seq:
            seq = self.env['ir.sequence'].sudo().create({
                'name': 'Customer UID Sequence',
                'implementation': 'standard',
                'prefix': 'CUS-',
                'padding': 6,
            })
        return seq.next_by_id()

    def action_set_won_rainbowman(self):
        """Override to add validation and automation when marking lead as won"""
        self.ensure_one()
        # if self.stage_id.is_won
        # Validation checks before marking as won
        partner = self.partner_id
        if not partner:
            raise ValidationError(_('Lead is Won but no related contact is set. Please set Contact first.'))

        if not self.data_package_id:
            raise ValidationError(_('Hardware equipment is required but not specified.'))

        if self.hardware_required and not self.is_hard_equipment_ids:
            raise ValidationError(_('Hardware equipment is required but not specified.'))

        # Generate customer UID if not exists
        if not partner.x_customer_uid:
            uid_value = self._generate_customer_uid()
            partner.sudo().write({'x_customer_uid': uid_value})
            self.message_post(
                body=_('Customer UID %s created and assigned to contact %s') % (uid_value, partner.display_name))
        else:
            uid_value = partner.x_customer_uid

        # Create customer locations if not exists
        if not partner.internal_location_id:
            partner.sudo()._create_customer_locations(partner, uid_value)
            self.message_post(
                body=_('Internal locations created for contact %s (UID: %s)') % (partner.display_name, uid_value))

        # Call parent method to handle won logic and rainbowman
        return super(CrmLead, self).action_set_won_rainbowman()


class EquipmentLineExt(models.Model):
    _name = 'equipment.line'

    quantity = fields.Integer('Quantity')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    equipment_line_id = fields.Many2one('crm.lead', string='Equipment')
