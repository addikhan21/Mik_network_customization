from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from markupsafe import Markup

import logging

_logger = logging.getLogger(__name__)


class EditVlan(models.TransientModel):
    _name = "edit.vlan.wizard"
    _description = "Vlan Wizard"

    @api.model
    def get_field_selection(self):
        model_fields = self.env["users"].fields_get()
        return [(field, model_fields[field]["string"]) for field in model_fields]

    field_to_update = fields.Selection(
        selection="get_field_selection", string="Field Name"
    )

    user_id = fields.Many2one("users", string="User")

    vlan_id = fields.Many2one("vlans", string="Vlan ID")
    package_id = fields.Many2one("package.line", string="Package")
    package_nas_id = fields.Many2one("nas", string="Package Nas Id")
    distributor_id = fields.Many2one("distributors", string="Distributor")

    field_value = fields.Many2one(
        "vlans", string="New Value"
    )
    
    def check_access(self):
        if not self.env.user.has_group('base_security_groups.group_admin'):
            if self.env.user.distributor_id.id != self.distributor_id.id:
                raise UserError(_("⛔ Sorry superhero, your powers don't work here! Only admins have the special cape for this. 🦸‍♂️"))
        return True

    @api.onchange("user_id")
    def _compute_user_details(self):
        for record in self:
            if record.user_id:
                record.package_id = record.user_id.package_id
                record.distributor_id = record.user_id.distributor_id.id
                record.vlan_id = record.user_id.vlan_id
                # record.package_nas_id = record.package_id.package_id.nas_id.id
                record.package_nas_id = record.distributor_id.nas_id.id
                print( "NAS pACKAGE", (record.package_nas_id.id))
                

    def action_update_vlan(self):
        self.check_access()
        if self.user_id and self.field_value:

            self.user_id.vlan_id = self.field_value.id
            self.user_id.vlan_id.is_assigned_to_user = "Ture"

            existing_vlan = (
                self.env["radcheck"]
                .sudo()
                .search(
                    [
                        ("username", "=", self.user_id.username),
                        ("attribute", "=", "NAS-Port-Id"),
                    ],
                    limit=1,
                )
            )

            if existing_vlan:
                existing_vlan.sudo().write(
                    {
                        "value": self.field_value.name,
                    }
                )
            else:
                self.env["radcheck"].sudo().create(
                    {
                        "username": self.user_id.username,
                        "attribute": "NAS-Port-Id",
                        "value": self.field_value.name,
                        "op": "==",
                    }
                )

            self.user_id.message_post(
                body=Markup(
                    f"""
                    <div class="text-muted" role="alert">
                        <i class="fa fa-check-circle text-success"></i> VLAN {existing_vlan and 'Updated' or 'Created'}<br>
                        <b><i class="fa fa-user"></i> Username:</b> {self.user_id.username}<br>
                        <b><i class="fa fa-angle-double-up"></i> VLAN:</b> {self.field_value.name}<br>
                        <b><i class="fa fa-check-circle"></i> Status:</b> {'Updated' if existing_vlan else 'Created'}<br>
                        <b> Updated by:</b> {self.env.user.name}<br>
                        <b> Date:</b> {fields.Datetime.now()}<br>
                    </div>
                    """
                )
            )
            
        else:
            if not self.field_value:
                raise ValidationError(_("New Vlan cannot be empty"))
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
            
