from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
# from email_validator import validate_email, EmailNotValidError
from markupsafe import Markup
# import phonenumbers

import logging

_logger = logging.getLogger(__name__)

class UpdateUserProfile(models.TransientModel):
    _name = 'users.profile.wizard'
    _description = 'User Profile'

    user_id = fields.Many2one('users', string="User")
    distributor_id = fields.Many2one(related="user_id.distributor_id", string="Distributor")
    name = fields.Char("Name")
    email = fields.Char(string="Email",)
    mobile = fields.Char(string="Mobile",)
    address = fields.Char(string="Address",)
    
    new_name = fields.Char("Name", required=True)
    new_email = fields.Char(string="Email",)
    new_mobile = fields.Char(string="Mobile",)
    new_address = fields.Char(string="Address",)
    
    
    @api.onchange('user_id')
    def _compute_user_details(self):
        for record in self:
            if record.user_id:
                record.name = record.user_id.name
                record.email = record.user_id.email
                record.mobile = record.user_id.mobile
                record.address = record.user_id.address
                record.new_name = record.user_id.name
                record.new_email = record.user_id.email
                record.new_mobile = record.user_id.mobile
                record.new_address = record.user_id.address

                
    def check_access(self):
        if not self.env.user.has_group('base_security_groups.group_admin'):
            if self.env.user.distributor_id.id != self.distributor_id.id:
                raise UserError(_("⛔ Sorry superhero, your powers don't work here! Only admins have the special cape for this. 🦸‍♂️"))
        return True
                
    # @api.constrains("new_email")
    # def _check_email(self):
    #     for record in self:
    #         if record.new_email:
    #             try:
    #                 validate_email(record.new_email)
    #             except EmailNotValidError:
    #                 raise ValidationError(_("Invalid email format"))

    # @api.constrains("new_mobile")
    # def _check_phone(self):
    #     for record in self:
    #         if record.new_mobile:
    #             try:
    #                 phone_number = phonenumbers.parse(record.new_mobile, "PK")  # PK for Pakistan
    #                 if not phonenumbers.is_valid_number(phone_number):
    #                     raise ValidationError(_("Invalid mobile number format"))
    #             except phonenumbers.NumberParseException:
    #                 raise ValidationError(_("Invalid mobile number format"))
                
                
    def write_records(self):
        self.check_access()
        if self.user_id:
            self.user_id.update({
                'name': self.new_name,
                'email': self.new_email,
               'mobile': self.new_mobile,
                'address': self.new_address,})
            
            self.user_id.message_post(
                    body=Markup(
                        f"""
                        <div class="text-muted" colspan='2' role="alert">
                            <i class="fa fa-check-circle text-success"></i> Profile Updated<br>
                        
                            <b><i class="fa fa-user"></i> Name:</b> {self.new_name}<br>
                            <b><i class="fa fa-envelope"></i> Email:</b> {self.new_email}<br>
                            <b><i class="fa fa-phone"></i> Mobile:</b> {self.new_mobile}<br>
                            <b><i class="fa fa-map-marker"></i> Address:</b> {self.new_address}<br>
                            <b>Executed by:</b> {self.env.user.name}<br>
                            <b></i>Date</b> <i>{fields.Datetime.now()}</i><br>
                            
                        </div>
                        """
                    )
                )
        else:
            raise ValidationError(_("User not found"))

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
            