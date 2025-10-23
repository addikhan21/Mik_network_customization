from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
# from email_validator import validate_email, EmailNotValidError
from markupsafe import Markup
from datetime import date, timedelta
# import phonenumbers

import logging

_logger = logging.getLogger(__name__)

class UpdateUserProfile(models.TransientModel):
    _name = 'users.package.wizard'
    _description = 'User Package'

    @api.model
    def get_field_selection(self):
        model_fields = self.env["users"].fields_get()
        return [(field, model_fields[field]["string"]) for field in model_fields]

    field_to_update = fields.Selection(
        selection="get_field_selection", string="Field Name"
    )

    user_id = fields.Many2one("users", string="User")
    
    # expiry_date = fields.Datetime(realted="user_id.expiry_date", string="Expiry Date")

    package_id = fields.Many2one("package.line", string="Package")
    releated_nas_id = fields.Many2one("nas", string="Related Nas Id")
    distributor_id = fields.Many2one("distributors", string="Distributor")

    field_value = fields.Many2one("package.line", domain="[('dealer_id', '=', distributor_id )]", string="New Value")
    field_value_nas_id = fields.Many2one("nas", string="Nas Id")
    
    
    def check_access(self):
        if not self.env.user.has_group('base_security_groups.group_admin'):
            if self.env.user.distributor_id.id != self.distributor_id.id:
                raise UserError(_("⛔ Sorry superhero, your powers don't work here! Only admins have the special cape for this. 🦸‍♂️"))
        return True
    
    
    @api.onchange('field_value')
    def _compute_field_value_nas_id(self):
        for record in self:
            if record.field_value:
                #record.field_value_nas_id = record.field_value.package_id.nas_id.id
                record.field_value_nas_id = record.distributor_id.nas_id.id
                
    
    @api.onchange('user_id')
    def _compute_user_details(self):
        for record in self:
            if record.user_id:
                record.package_id = record.user_id.package_id
                record.distributor_id = record.user_id.distributor_id.id
                #record.releated_nas_id = record.package_id.package_id.nas_id.id
                record.releated_nas_id = record.distributor_id.nas_id.id
                
                
    def action_update_package(self):
        self.check_access()
        
        if self.user_id and  self.field_value :
            
            existing_record = self.env["radusergroup"].sudo().search([
                ("username", "=", self.user_id.username),
                ("groupname", "=", self.user_id.package_id.package_name)
            ], limit=1)
            
            existing_nas = self.env['radcheck'].search([
                 ("username", "=", self.user_id.username),
                ('attribute', '=', 'NAS-IP-Address')
            ], limit=1)
            
            if existing_nas:
                existing_nas.sudo().write({
                    'value': self.field_value_nas_id.nasname
                })
            else:
                self.env['radcheck'].sudo().create({
                    'username': self.user_id.username,
                    'attribute': 'NAS-IP-Address',
                    'op': '==',
                    'value': self.field_value_nas_id.nasname,
                })
            
            
            if existing_record:
                
                existing_record.sudo().write({
                    "groupname": self.field_value.package_name,
                    "priority": 1
                })
                self.user_id.radusergroup_id = existing_record.id
                
            else:
                
                radusergroup = self.env["radusergroup"].sudo().create({
                    "username": self.user_id.username,
                    "groupname": self.field_value.package_name,
                    "priority": 1
                })
                self.user_id.radusergroup_id = radusergroup.id
                
            self.user_id.package_id = self.field_value
            
            self.user_id.message_post(
                body=Markup(
                    f"""
                    <div class="text-muted" role="alert">
                        <i class="fa fa-check-circle text-success"></i>Package Entry {existing_record and 'Updated' or 'Created'}<br>
                        <b><i class="fa fa-user"></i> Username:</b> {self.user_id.username}<br>
                        <b><i class="fa fa-cube"></i> Package:</b> {self.field_value.package_name}<br>
                        <b><i class="fa fa-server"></i> NAS:</b> {self.field_value_nas_id.nasname}<br>
                        <b><i class="fa fa-check-circle"></i> Status:</b> {'Updated' if existing_record else 'Created'}<br>
                        <b> Updated by:</b> {self.env.user.name}<br>
                        <b> Date:</b> <i>{fields.Datetime.now()}</i><br>
                    </div>
                    """
                )
            )
            
            if self.releated_nas_id != self.field_value_nas_id:
                
                #this is to unlink vlans
                self.user_id.write({'vlan_id': False})
                vlan_record = self.env['radcheck'].sudo().search([
                    ('username', '=', self.user_id.username),
                    ('attribute', '=', 'NAS-Port-Id')
                ], limit=1)
    
                if vlan_record:
                    vlan_record.sudo().unlink()
                
                self.user_id.message_post(
                body=Markup(
                    f"""
                    <div class="alert alert-danger" role="alert">
                        <b>Vlans </b><i>for this user were removed beacuse of NAS conflict.</i><br>
                        <b>Make Sure to assign vlans again</b>
                    </div>
                    """
                )
            )
            
        else:
            if not self.field_value:
                raise ValidationError(_("New Package cannot be empty"))
            elif not self.user_id:
                raise ValidationError(_("No Active ID Found in Context"))

        return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'title': _('Successful'),
                    'message': _("Record Updated Successfully"),
                    'sticky': True,
                    'next': {'type': 'ir.actions.act_window_close'},
                }}
            