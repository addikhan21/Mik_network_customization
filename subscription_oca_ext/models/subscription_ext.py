from odoo import models, fields,api
from odoo.exceptions import AccessError, UserError, ValidationError


class SaleSubscription(models.Model):
    _inherit = 'sale.subscription'

    ip_address_id = fields.Many2one('ip.address',  string='IP Address',domain="[('subscription_id', '=', False)]",)
    opportunity_id = fields.Many2one('crm.lead', string='Opportunity', readonly=True)
    value_set = fields.Char(string='Value Set')
    stage_type = fields.Selection(related='stage_id.type', store=True)

    @api.onchange('stage_id')
    def onchange_ip_address_id(self):
        for record in self:
            if record.stage_id.type != 'pre':

                record.create_users()

    def create_users(self):
        for record in self:
            if record.id:
                users = self.env['users'].search([('id_subscription', '=', record.id)], limit=1)
                recrd_id = record.id
            else:
                users = self.env['users'].search([('id_subscription', '=', record.id.origin)], limit=1)
                recrd_id = record.id.origin
            if not users:
                users = self.env['users'].create({
                    'name': record.partner_id.name,
                    'username': record.partner_id.x_customer_uid,
                    'password': record.partner_id.x_customer_uid,
                    'email': record.partner_id.email,
                    'mobile': record.partner_id.mobile,
                    'address': record.delivery_address(),
                    'id_subscription': recrd_id,
                    'opportunity_id': record.opportunity_id.id if record.opportunity_id else False,
                })
            if record.ip_address_id:
                record.value_set = record.ip_address_id.ip_address
                record.ip_address_id.write({'subscription_id': record.id})
                users.write({'id_address': record.ip_address_id.ip_address})


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
