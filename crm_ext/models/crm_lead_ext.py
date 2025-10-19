from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    phone = fields.Char(string='Phone Number', required=True)
    contact_name = fields.Char(string='Full Name', required=True)
    otc = fields.Char(string='OTC',)
    service_charges= fields.Char(string='Service Charges')
    hardware_required = fields.Boolean(string='Is Hardware Required')
    data_package_id = fields.Many2one(
        'product.product',
        string='Data Package',
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
        else:
            self._create_subscription_and_order()

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

        if self.hardware_required and not self.is_hard_equipment_ids:
            raise ValidationError(_('Hardware equipment is required but not specified.'))
        elif self.hardware_required and self.is_hard_equipment_ids:
            self._create_delivery_order(self.is_hard_equipment_ids)


        if self.otc or self.service_charges:
            self._create_sale_order_with_charges()

        # Call parent method to handle won logic and rainbowman
        return super(CrmLead, self).action_set_won_rainbowman()

    def _create_sale_order_with_charges(self):
        """Create sale order with OTC and Service Charges products"""
        order_lines = []
        if self.otc:
            otc_product = self.env.ref('crm_ext.otc')
            order_lines.append((0, 0, {
                'product_id': otc_product.product_variant_id.id,
                'price_unit': float(self.otc),
            }))

        if self.service_charges:
            service_product = self.env.ref('crm_ext.service_charges')
            order_lines.append((0, 0, {
                'product_id': service_product.product_variant_id.id,
                'price_unit': float(self.service_charges),
            }))
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'opportunity_id': self.id,
        })


        sale_order.write({'order_line': order_lines})

        sale_order.action_confirm()

        if sale_order.state == 'sale':
            sale_order._create_invoices()


        self.message_post(
            body=_('Sale order %s created with charges') % sale_order.name)

    def _create_delivery_order(self, equipment_lines):
        """Create delivery order for hardware equipment"""
        if not equipment_lines:
            return
        
        # Check if delivery order already exists for this lead
        existing_delivery = self.env['stock.picking'].search([
            ('opportunity_id', '=', self.id),
            ('state', '!=', 'cancel')
        ])
        if existing_delivery:
            return

        delivery_order = self.env['stock.picking'].create({
            'partner_id': self.partner_id.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.partner_id.internal_location_id.id,
            'opportunity_id': self.id
        })

        for equipment in equipment_lines:
            self.env['stock.move'].create({
                'name': equipment.product_id.name,
                'product_id': equipment.product_id.id,
                'product_uom_qty': equipment.quantity,
                'product_uom': equipment.product_id.uom_id.id,
                'picking_id': delivery_order.id,
                'location_id': delivery_order.location_id.id,
            })
        delivery_order.action_confirm()

        self.message_post(body=_('Delivery order %s created for hardware equipment') % delivery_order.name)

    def _create_subscription_and_order(self):
        order_lines = []
        if self.data_package_id:
            order_lines.append((0, 0, {
                'product_id': self.data_package_id.id,
            }))
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'opportunity_id': self.id,
        })

        sale_order.write({'order_line': order_lines})

        sale_order.action_confirm()
        if sale_order.state == 'sale':
            subscription = self.env['sale.subscription'].create({
                'partner_id': self.partner_id.id,
                'template_id': self.env['sale.subscription.template'].search([('name', '=', 'subscription_oca')]).id,
                'pricelist_id': self.env['product.pricelist'].search([('id', '=', 1)]).id,
                'opportunity_id':self.id,
                'sale_order_id': sale_order.id,
            })
            # sale_order.subscription_id = subscription.id



class EquipmentLineExt(models.Model):
    _name = 'equipment.line'

    quantity = fields.Integer('Quantity')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    equipment_line_id = fields.Many2one('crm.lead', string='Equipment')
