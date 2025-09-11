from odoo import models, fields, api, _
import ipaddress
import paramiko
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    remote_radius_service_name = fields.Char(
        string="Remote Service Name",
        default="freeradius",
        config_parameter='remote.radius.service.name',
        help="Name of the service through which activity is performed."
    )
    
    remote_radius_ip = fields.Char(
        string="Remote Radius IP",
        config_parameter='remote.radius.ip',
        help="IP address of the Free Radius"
    )

    remote_radius_user = fields.Char(
        string="Remote Radius User",
        config_parameter='remote.radius.user',
        help="Username to access the remote service"
    )

    remote_radius_password = fields.Char(
        string="Remote Radius Password",
        config_parameter='remote.radius.password',
        help="Password to access the remote service"
    )
    
    
    @api.constrains('remote_radius_ip')
    def validation_ip(self):
        if self.remote_radius_ip and not self.ip_address_check(self.remote_radius_ip):
            raise ValidationError(
                _(
                    "IP Address %(ip)s is not valid!",
                    ip=self.remote_radius_ip,
                )
            )

    def ip_address_check(self, ip):
        try:
            ipaddress.ip_address(ip)
            return True

        except ValueError:
            return False
        
        
    # ------------------
    # Inquire Freeradius Status
    # ------------------   
    def action_check_radius_status(self):
        try:
            ip = self.remote_radius_ip
            user = self.remote_radius_user
            password = self.remote_radius_password
            service = self.remote_radius_service_name

            if not ip or not user or not password or not service:
                raise ValidationError("Please configure SSH credentials in System Parameters. Donot Forget to add Service!")
            

            # Establish SSH connection
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=ip,
                username=user,
                password=password
            )

            # Check if the SSH connection is successful
            message = f"Connection to {ip} was successful."
            ssh.close()

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'title': _('SSH Connection Test'),
                    'message': _(message),
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }

        except paramiko.AuthenticationException:
            raise ValidationError(_("Authentication failed. Please check your SSH credentials."))
        except paramiko.SSHException as e:
            raise ValidationError(_("SSH connection error: %s") % str(e))
        except Exception as e:
            raise ValidationError(_("Connection failed: %s") % str(e))


    
    
    
    
