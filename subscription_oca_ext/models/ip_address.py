import re
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class IpAddress(models.Model):
    _name = 'ip.address'
    _description = 'IP Address Management'
    _rec_name = 'ip_address'
    _sql_constraints = [
        ('unique_ip', 'UNIQUE(ip_address)', 'IP address must be unique!')
    ]

    ip_address = fields.Char(string='IP Address', required=True)
    ip_type = fields.Selection([
        ('ipv4', 'IPv4'),
        ('ipv6', 'IPv6')
    ], string='IP Type', compute='_compute_ip_type', store=True)
    subscription_id = fields.Many2one('sale.subscription', string='Subscription',readonly=True)
    subscription_state = fields.Many2one(string='Subscription States', related='subscription_id.stage_id', readonly=True,store=True)

    @api.depends('ip_address')
    def _compute_ip_type(self):
        ipv4_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        ipv6_pattern = r'^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|^::1$|^::$'

        for record in self:
            if record.ip_address:
                if re.match(ipv4_pattern, record.ip_address):
                    record.ip_type = 'ipv4'
                elif re.match(ipv6_pattern, record.ip_address):
                    record.ip_type = 'ipv6'

    @api.constrains('ip_address')
    def _check_ip_format(self):
        ipv4_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        ipv6_pattern = r'^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|^::1$|^::$'

        for record in self:
            if record.ip_address:
                if not (re.match(ipv4_pattern, record.ip_address) or re.match(ipv6_pattern, record.ip_address)):
                    raise ValidationError(_('Invalid IP address format. Please enter a valid IPv4 or IPv6 address.'))