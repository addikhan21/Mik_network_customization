from odoo import models, fields,api
from odoo.exceptions import AccessError, UserError, ValidationError
import uuid


class SaleSubscription(models.Model):
    _inherit = 'sale.subscription'

    ip_address_id = fields.Many2one('ip.address',  string='IP Address',domain="[('subscription_id', '=', False)]",)
    opportunity_id = fields.Many2one('crm.lead', string='Opportunity', readonly=True)
    value_set = fields.Char(compute='onchange_ip_address_id')
    stage_type = fields.Selection(related='stage_id.type', store=True)

    @api.depends('stage_id')
    def onchange_ip_address_id(self):
        for record in self:
            if record.stage_id.type == 'in_progress':
                if record.ip_address_id:
                    record.value_set = record.ip_address_id.ip_address
                    record.ip_address_id.write({'subscription_id': record.id})
                    print("IP Address ID:", record.ip_address_id.id)
                    print("Subscription ID:", record.id)
                    self.create_users()
                else:
                    record.value_set = False
                    raise ValidationError("No IP Address available for this subscription.")
            else:
                record.value_set = False

    def create_users(self):
        for record in self:
            users = self.env['users'].create({
                'name': record.partner_id.name,
                'username': record.partner_id.x_customer_uid,
                'password':str(uuid.uuid4()),
                'email': record.partner_id.email,
                'mobile': record.partner_id.mobile,
                'address': record.delivery_address(),
                'subscription_id': record.id,
                'opportunity_id': record.opportunity_id.id,
                'id_address': record.ip_address_id.ip_address,
            })
            if users:
                print("Users Created:", users)

    def delivery_address(self):
        for record in self:
            parts = [
                record.partner_id.street or '',
                record.partner_id.street2 or '',
                record.partner_id.city or '',
                record.partner_id.zip or '',
                record.partner_id.state_id.name or '',
                record.partner_id.country_id.name or ''
            ]
            address = ', '.join(filter(None, parts))
            return address
