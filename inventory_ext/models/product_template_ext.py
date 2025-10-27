from odoo import models, fields, api,_


class ProductTemplateEXT(models.Model):
    _inherit = 'product.template'

    is_isp_service = fields.Boolean(string='Is Isp Service',readonly=True, default=False)
    is_data_package_configured = fields.Boolean(string='Is Data Package Configured', default=False)
    is_isp_equipment = fields.Boolean('Is Isp equipment', default=False, compute='_compute_is_isp_configured', store=True, readonly=False)

    def _compute_is_isp_configured(self):
        pass

