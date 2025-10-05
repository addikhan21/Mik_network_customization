from odoo import models, fields, api,_


class ProductTemplateEXT(models.Model):
    _inherit = 'product.template'

    is_data_package = fields.Boolean(string='Is Data Package',)
    is_data_package_configured = fields.Boolean(string='Is Data Package Configured', default=False)
    is_isp_configured = fields.Boolean('Is Isp Configured', default=True, compute='_compute_is_isp_configured', store=True, readonly=False)

    def _compute_is_isp_configured(self):
        pass

    @api.model_create_multi
    def create(self, vals_list):
        res = super(ProductTemplateEXT, self).create(vals_list)

        for template in res:
            # Prevent recursive creation
            if not template.product_variant_id.service_group_id:
                self.env['service.group'].create({
                    'name': template.name,
                    'duration': '1',
                    'product_id': template.product_variant_id.id,
                })
        return res