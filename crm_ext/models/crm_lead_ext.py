from odoo import models, fields


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    phone = fields.Char(string='Phone Number' , required=True)
    contact_name = fields.Char(string='Full Name' , required=True)
    hardware_required = fields.Boolean(string='Hardware Required')
    data_package_id = fields.Many2one(
        'product.template',
        string='Data Package',
        required=True,
        domain=[('is_data_package', '=', True),('is_data_package_configured', '=', True)]
    )

    is_network_equipment_ids = fields.One2many(
        'product.template',
        'opportunity_id',
        string='Is Network Equipment',
        required=True,
        domain=[('is_isp_configured', '=', True)]
    )