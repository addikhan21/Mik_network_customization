# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class ServiceGroup(models.Model):
    _name = 'service.group'
    _description = 'Service Group'
    _rec_name = "name"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'The name of the service group must be unique!')
    ]

    name = fields.Char('name', required=True)
    attributes_ids = fields.One2many('service.group.lines', 'group_id', string='attributes')
    atributtes_count = fields.Integer(string='Attributes Count', compute='_compute_attributes_count')
    product_id = fields.Many2one('product.product', string='Related Product')
    nas_id = fields.Many2one('network.nas', string='NAS ID')
    nas_ids = fields.Many2many('network.nas', string='NAS IDs')
    duration = fields.Integer(string='Duration(Days)', default=1, required=True)
    franchise_user_ids = fields.Many2many(
        "res.users", string="Franchise Users", readonly=True
    )
    
    
    def action_view_product(self):
        """
    Action to open the form view of the related product.

    Returns:
        An action dictionary to open the form view of the related product.
    """

        self.ensure_one()
        return {
            'name': _('Related Product'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'product.product',
            'res_id': self.product_id.id,
            'target': 'new',
        }


    def create(self, vals_list):
        """
        Create a new service group.

        When creating a service group, it also creates a product with the same name
        and type 'service', and links the created product to the service group.
        """
        service_group = super(ServiceGroup, self).create(vals_list)
        if 'product_id' not in vals_list:
        # Create a product with the same name
            product = self.env['product.product'].create({
                'name': service_group.name,
                'type': 'service',
                'sale_ok': True,
                'purchase_ok': False,
                'service_group_id': service_group.id,
            })
            service_group.product_id = product.id
        return service_group

    def unlink(self):
        """
        Override unlink to delete related service.group.lines records and the associated product
        before deleting the service.group.
        """
        for group in self:
            group.attributes_ids.unlink()
            if group.product_id:
                group.product_id.unlink()

        return super(ServiceGroup, self).unlink()


    def _compute_attributes_count(self):
        for group in self:
            group.atributtes_count = len(group.attributes_ids)
    def acction_view_attributes(self):
        """
        Action to open the tree view of the attributes of the service group.   
        It returns an action that opens the tree view of the service group lines
        with the domain set to filter only the attributes of the current service
        group.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Attributes',
            'view_mode': 'tree',
            'res_model': 'service.group.lines',
            'domain': [('group_id', '=', self.id)],
            'context': "{'create': False , 'open': False, 'edit': False}",
            'help': _('This screen shows the attributes of the service group.'),
            'target': 'new',
        }

class ServiceGroupLines(models.Model):
    _name = 'service.group.lines'
    _description = 'Service Group Lines'
    _rec_name = "attribute"

    group_id = fields.Many2one('service.group', string='Service Group',
                               required=True, ondelete='cascade')
    attribute = fields.Char(string='Attribute', index=True, required=True)
    op = fields.Char(string='Operator', default="==", size=2, required=True)
    value = fields.Char(string='Value', required=True)
    master_id = fields.Many2one("radgroupcheck")
    replygroup_master_id = fields.Many2one("radgroupreply")

    def action_view_record(self):
        """
        Open the radgroupreply record that is referenced by the master_id.
        If master_id is not set, open the current record.
        """
        self.ensure_one()
        if self.replygroup_master_id:
            return {
                "type": "ir.actions.act_window",
                "name": "Radgroupcheck Record",
                "res_model": "radgroupreply",
                "view_mode": "form",
                "res_id": self.replygroup_master_id.id,
                "target": "new",
                "context": {"create": False, "edit": False},         
            }

    # ------------------
    # CREATE METHOD
    # ------------------
    @api.model_create_multi
    def create(self, vals_list):

        """
        Override the create method to add custom logic when creating records.
        This method creates a new radgroupreply record with the same attribute
        values as the current record, and then links the newly created record
        with the current record by setting the master_id field.
        """

        res = super(ServiceGroupLines, self).create(vals_list)
        radgroupreply_model = self.env["radgroupreply"]
        for record in res:
            group_data = {
                "groupname": record.group_id.name,
                "attribute": record.attribute,
                "op": record.op,
                "value": record.value,
            }
            radgroupreply_record = radgroupreply_model.create(group_data)
            record.replygroup_master_id = radgroupreply_record.id
        return res

    # ------------------
    # WRITE METHOD
    # ------------------
    def write(self, vals):

        """
        Override the write method to update related radgroupreply records.
        This method updates the radgroupreply record linked to the current record
        using the master_id field with the same attribute values.
        """
        res = super(ServiceGroupLines, self).write(vals)

        relevant_fields = {"attribute", "op", "value"}
        update_data = {field: vals[field] for field in relevant_fields if field in vals}

        if update_data and self.replygroup_master_id:
            self.replygroup_master_id.write(update_data)
        return res

    # ------------------
    # UNLINK METHOD
    # ------------------
    def unlink(self):
        """
        Override the unlink method to also delete the related radgroupreply record.
        This method first checks if the current record has a master_id set, and if
        so, it deletes the related radgroupreply record before deleting the current
        record.
        """
        for record in self:
            if record.replygroup_master_id:
                record.replygroup_master_id.unlink()
        return super(ServiceGroupLines, self).unlink()
