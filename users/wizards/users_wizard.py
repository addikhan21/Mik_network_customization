from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from markupsafe import Markup

import logging

_logger = logging.getLogger(__name__)


class UpdateUser(models.TransientModel):
    _name = "users.wizard"
    _description = "User Wizard"

    # @api.model
    # def default_get(self, fields_list):
    #     res = super().default_get(fields_list)
    #     _logger.info("Context in wizard: %s", self._context)
    #     _logger.info("Active ID: %s", self._context.get('active_id'))
    #     _logger.info("Default values: %s", res)
    #     return res

    @api.model
    def get_field_selection(self):
        model_fields = self.env["users"].fields_get()
        return [(field, model_fields[field]["string"]) for field in model_fields]

    field_to_update = fields.Selection(
        selection="get_field_selection", string="Field Name"
    )

    user_id = fields.Many2one("users", string="User")
    distributor_id = fields.Many2one(related='user_id.distributor_id', string="Distributor")

    password = fields.Char(string="Password", readonly=True)

    field_value = fields.Char(string="New Value")

    @api.onchange("user_id")
    def _compute_password(self):
        for record in self:
            if record.user_id and record.field_to_update == "password":
                record.password = record.user_id.password
    
    
    def check_access(self):
        if not self.env.user.has_group('base_security_groups.group_admin'):
            if self.env.user.distributor_id.id != self.distributor_id.id:
                raise UserError(_("⛔ Sorry superhero, your powers don't work here! Only admins have the special cape for this. 🦸‍♂️"))
        return True
                


    def action_update_password(self):
        self.check_access()
        if self.field_value and self.user_id:
            radcheck_vals = {
                "username": self.user_id.username,
                "attribute": "Cleartext-Password",
                "op": ":=",
                "value": self.field_value,
            }

            existing_record = self.env["radcheck"].search(
                [
                    ("username", "=", self.user_id.username),
                    ("attribute", "=", "Cleartext-Password"),
                ],
                limit=1,
            )

            if existing_record:
                existing_record.sudo().write({"value": self.field_value})
                self.user_id.password = self.field_value
            else:
                self.env["radcheck"].sudo().create(radcheck_vals)
                self.user_id.password = self.field_value

            self.user_id.message_post(
                body=Markup(
                    f"""
                            <div class="text-muted" colspan='2' role="alert">
                                <i class="fa fa-check-circle text-success"></i><i>Password Entry {existing_record and 'Updated' or 'Created'}</i><br>
                                <b><i class="fa fa-user"></i> Username:</b> {self.user_id.username}<br>
                                <b><i class="fa fa-key"></i> Password:</b> {self.field_value}<br>
                                <b><i class="fa fa-check-circle"></i> Status:</b> {'Updated' if existing_record else 'Created'}<br>
                                <b> Executed by:</b> {self.env.user.name}<br>
                                <b> Date:</b> <i>{fields.Datetime.now()}</i><br>
                                
                            </div>
                        """
                )
            )

        else:

            if not self.field_value:
                raise ValidationError(_("New value cannot be empty"))

            elif not self.user_id:
                raise ValidationError(
                    _("No Active ID Found in Context.  Please try again")
                )

