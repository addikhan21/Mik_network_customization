from odoo import models, fields,api
from odoo_18_src.odoo.odoo.tests import users


class SaleSubscription(models.Model):
    _inherit = 'sale.subscription'

    ip_address_id = fields.Many2one('ip.address',  string='IP Address',domain="[('subscription_id', '=', False)]",)
    opportunity_id = fields.Many2one('crm.lead', string='Opportunity', readonly=True)
    value_set = fields.Char(compute='onchange_ip_address_id')
    stage_type = fields.Selection(related='stage_id.type', store=True)

    @api.depends('stage_id')
    def onchange_ip_address_id(self):
        for record in self:
            record.ip_address_id.subscription_id = False
            if record.ip_address_id:
                record.value_set = record.ip_address_id.ip_address
                record.ip_address_id.write({'subscription_id': record.id})
                print("IP Address ID:", record.ip_address_id.id)
                print("Subscription ID:", record.id)
            else:
                record.value_set = False

    @api.depends('stage_id')
    def onchange_ip_address_id(self):
        for record in self:
            if record.ip_address_id:
                users = self.env['users'].create({
                    'name': record.partner_id.x_customer_uid,
                    'ip_address': record.ip_address_id.ip_address,
                    'subscription_id': record.id,

                })
