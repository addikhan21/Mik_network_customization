from requests.auth import HTTPBasicAuth
from markupsafe import Markup
from datetime import date, datetime
import urllib3
import mysql.connector
import logging

_logger = logging.getLogger(__name__)


import ipaddress
import paramiko
import requests
import json
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class NetworkNAS(models.Model):
    _name = "network.nas"
    _description = "Network Nas"
    _rec_name = "nasname"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    nasname = fields.Char(string="NAS IP", index=True, required=True)
    shortname = fields.Char(string="NAS Name", required=True)
    type = fields.Many2one("network.type", string="Type", required=True)
    ports = fields.Integer(string="Ports", required=True)
    secret = fields.Char(string="Secret", required=True)
    server = fields.Char(string="Server")
    community = fields.Char(string="Community")
    description = fields.Text(string="Description")
    nas_master_id = fields.Many2one("nas", store=True)
    show_secret_toggle = fields.Boolean(string="Show Secret", default=False)
    user_count = fields.Integer(string="users", compute="_compute_user_count")
    master_record_status = fields.Selection(
        [("linked", "Record Linked"), ("unlinked", "Record Unlinked")],
        default="unlinked",
        string="Master Record",
        compute="_compute_record_status",
    )
    service_status = fields.Text(string="Service Status", readonly=True)
    # Nas details
    architecture_name = fields.Char(string="Architecture Name", readonly=True)
    board_name = fields.Char(string="Board Name", readonly=True)
    build_time = fields.Datetime(string="Build Time", readonly=True)

    nas_build_time = fields.Char(string="Build Time", readonly=True)
    cpu = fields.Char(string="CPU", readonly=True)
    cpu_count = fields.Integer(string="CPU Count", readonly=True)
    cpu_load = fields.Float(string="CPU Load (%)", readonly=True)
    platform = fields.Char(string="Platform", readonly=True)
    uptime = fields.Char(string="Uptime", readonly=True)
    version = fields.Char(string="Version", readonly=True)
    # nas api configuration
    nas_api_username = fields.Char(string="NAS API Username")
    nas_api_password = fields.Char(string="NAS API Password")
    nas_ip = fields.Char(string="NAS IP")
    vlans_count = fields.Integer(string="VLANs", compute="_compute_vlans_count")
    # Franchise_ids
    franchise_user_ids = fields.Many2many("res.users", string="Franchise Users", readonly=True)

    # Memory in GIBS
    cpu_frequency = fields.Integer(string="CPU Frequency (MHz)", readonly=True)
    free_hdd_space = fields.Integer(string="Free HDD Space (Bytes)", readonly=True)
    total_memory = fields.Integer(string="Total Memory (Bytes)", readonly=True)
    total_hdd_space = fields.Integer(string="Total HDD Space (Bytes)", readonly=True)
    free_memory = fields.Integer(string="Free Memory (Bytes)", readonly=True)

    cpu_frequency_mhz = fields.Float(string="CPU Frequency (MHz)", readonly=True)
    free_hdd_space_Gib = fields.Float(string="Free HDD Space (GiB)", readonly=True)
    total_memory_Gib = fields.Float(string="Total Memory (GiB)", readonly=True)
    total_hdd_space_Gib = fields.Float(string="Total HDD Space (GiB)", readonly=True)
    free_memory_Gib = fields.Float(string="Free Memory (GiB)", readonly=True)

    def action_fill_graph(self):
        """
        Fills the local_graph_id field for users with the given hostname.
        """
        self.ensure_one()
        db_config = {
            "host": "103.167.163.206",
            "user": "cactiuser",
            "password": "1122",
            "database": "cactidb",
        }
        # Fetch all users associated with the NAS and grouped by username
        nas_users = (
            self.env["radius.users"]
            .search([("nas_id", "=", self.id), ("local_graph_id", "=", None)])
            .grouped("username")
        )
        # print(f"==>> nas_users: {nas_users}")

        # conn = mysql.connector.connect(host="103.167.163.206", user="cactiuser", password="1122", database="cactidb")
        query = """
            SELECT 
                g.local_graph_id,
                h.hostname,
                SUBSTRING_INDEX(g.title_cache, 'pppoe-', -1) AS username
            FROM 
                graph_templates_graph g
            JOIN 
                graph_local gl ON g.local_graph_id = gl.id
            JOIN 
                host_graph hg ON gl.host_id = hg.host_id
            JOIN 
                host h ON hg.host_id = h.id
            WHERE 
                h.hostname = %s
                AND g.title_cache LIKE '%%pppoe%%'
            GROUP BY 
                g.local_graph_id, h.hostname
            ORDER BY 
                g.local_graph_id
        """

        # Open a new cursor and manage transactions manually
        hostname = self.nasname
        conn = None
        cursor = None
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute(query, (hostname,))
            results = cursor.fetchall()

            if not results:
                raise UserError(_("No matching records found for hostname: %s") % hostname)

            # Process and update `radius.user` records
            updated_count = 0
            for local_graph_id, hostname, username in results:
                user = nas_users.get(username)
                if user:
                    # Update the local_graph_id field
                    user.write({"local_graph_id": local_graph_id})
                    updated_count += 1
                else:
                    _logger.warning("No matching radius.user found for username: %s", username)

            if updated_count == 0:
                raise UserError(_("No users were updated. Ensure username mappings are correct."))

            _logger.info("Successfully updated %d users with local_graph_id.", updated_count)
        except mysql.connector.Error as e:
            _logger.error("MySQL Error: %s", e, exc_info=True)
            raise UserError(_("An error occurred while connecting to the MySQL database: %s") % e)
        except Exception as e:
            _logger.error("Unexpected Error: %s", e, exc_info=True)
            raise UserError(_("An unexpected error occurred: %s") % e)
        finally:
            if cursor:
                try:
                    cursor.close()
                    _logger.info("Cursor closed successfully.")
                except Exception as e:
                    _logger.warning("Failed to close cursor: %s", e)
            if conn:
                try:
                    conn.close()
                    _logger.info("Connection closed successfully.")
                except Exception as e:
                    _logger.warning("Failed to close connection: %s", e)

    @api.constrains("ports")
    def check_ports(self):
        if self.ports < 1 or self.ports > 65535:
            raise ValidationError(_("Ports must be between 1 and 65535."))

    # def _compute_display_name(self):
    #     for rec in self:
    #         if rec.shortname and rec.nasname:
    #             rec.display_name = f"{rec.shortname}-{rec.nasname}"
    #         else:
    #             rec.display_name = _("New")

    def _compute_record_status(self):
        for record in self:
            if record.nas_master_id:
                print(record.nas_master_id)
                record.master_record_status = "linked"
            else:
                record.master_record_status = "unlinked"

    def generate_nas_vlans(self):
        if self.env["network.vlan"].search_count([("nas_id", "=", self.id)]) > 0:
            raise ValidationError(_("VLANs are already generated for this NAS."))
        vals = []
        for i in range(1, 4095):
            vals.append({"name": str(i), "nas_id": self.id})
        self.env["network.vlan"].create(vals)

    def _compute_vlans_count(self):
        for rec in self:
            rec.vlans_count = self.env["network.vlan"].search_count([("nas_id", "=", rec.id)])

    def get_vlans_(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "VLANs",
            "view_mode": "tree,form",
            "res_model": "network.vlan",
            # "target": "new",
            "domain": [("nas_id", "=", self.id)],
            "context": {"create": False},
        }


    
    def get_master_record(self):
        self.ensure_one()
        if not self.nas_master_id:
            raise ValidationError(
                _(
                    "This Nas Record is not present in Radius Nas.\n Please Archive this record and create new.",
                )
            )
        else:
            return {
                "type": "ir.actions.act_window",
                "name": "Radius Linked - Master Nas",
                "view_mode": "form",
                "res_model": "nas",
                "res_id": self.nas_master_id.id if self.nas_master_id else False,
                "target": "new",
                "domain": [],
                "context": "{'create': False , 'open': False, 'edit': False}",
            }

    def _compute_user_count(self):
        for record in self:
            record.user_count = 500
            # record.user_count = self.env["radius.users"].sudo().search_count([("nas_id", "=", record.id)])

    def get_users(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Nas Linked - Users",
            "view_mode": "tree",
            "res_model": "radius.users",
            "domain": [("nas_id", "=", self.id)],
            "target": "new",
            "context": "{'create': False , 'open': False, 'edit': False}",
        }

    @api.onchange("nasname")
    def validation_ip(self):
        if self.nasname and not self.ip_address_check(self.nasname):
            raise ValidationError(
                _(
                    "IP Address %(ip)s is not valid!",
                    ip=self.nasname,
                )
            )

    def ip_address_check(self, ip):
        try:
            ipaddress.ip_address(ip)
            return True

        except ValueError:
            return False

    def toggle_show_secret(self):
        for record in self:
            record.show_secret_toggle = not record.show_secret_toggle

    # ------------------
    # SSH Executor
    # ------------------
    def action_ssh_executor(self, operation, flag):
        try:
            # Fetch system parameters for SSH connection
            ip = self.env["ir.config_parameter"].sudo().get_param("remote.radius.ip")
            user = self.env["ir.config_parameter"].sudo().get_param("remote.radius.user")
            password = self.env["ir.config_parameter"].sudo().get_param("remote.radius.password")
            service = self.env["ir.config_parameter"].sudo().get_param("remote.radius.service.name")

            if not ip or not user or not password or not service:
                raise UserError("Please configure SSH credentials in System Parameters. \nGo to settings and service")

            # Establish SSH connection
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=str(ip), username=str(user), password=str(password))

            # Command Execution
            print(f"sudo systemctl {operation} {service} --no-pager")
            # service_command = f'sudo systemctl status freeradius --no-pager'
            # stdin, stdout, stderr = ssh.exec_command(service_command)
            service_command = f"sudo systemctl {operation} {service} --no-pager"
            stdin, stdout, stderr = ssh.exec_command(service_command)

            # Capture the output and check for errors
            output = stdout.read().decode("utf-8").strip()
            error = stderr.read().decode("utf-8").strip()

            if error:
                self.service_status = f"Error {operation}ing service '{service}': {error}"
                ssh.close()
                raise ValidationError(_(f"Error restarting service '{service}': {error}"))

            else:
                self.service_status = (
                    f"{(str(service)).capitalize()} Service {operation}ed successfully.\n\n {str(output)}"
                )
                ssh.close()
                self.message_post(
                    body=Markup(
                        f"""
                <div class="alert alert-{flag}" role="alert">
                    <b>Action:</b> {(operation).capitalize()}<br>
                    <b>Service:</b> {(str(service)).capitalize()}<br>
                    <b>Command Executed:</b> sudo systemctl {operation} {service} --no-pager<br>
                    <b>Executed by:</b> {self.env.user.name}<br>
                    <b>Date Time:</b> <i>{fields.Datetime.now()}</i><br>
                </div>
                """
                    )
                )

                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "type": "success",
                        "title": _(f"{(str(service)).capitalize()} Service {operation}ed"),
                        "message": _(f"{(str(service)).capitalize()} Service {operation}ed successfully."),
                        "sticky": False,
                        "next": {"type": "ir.actions.act_window_close"},
                    },
                }

        except paramiko.AuthenticationException:
            self.service_status = "Authentication failed. Please check your SSH credentials."
            raise ValidationError(_("Authentication failed. Please check your SSH credentials."))
        except paramiko.SSHException as e:
            self.service_status = f"SSH connection error: {str(e)}"
            raise ValidationError(_(f"SSH connection error: {str(e)}"))
        except Exception as e:
            self.service_status = f"Connection failed: {str(e)}"
            raise ValidationError(_(f"Connection failed: {str(e)}"))

    # ------------------
    # Start Freeradius
    # ------------------
    def action_radius_start(self):
        res = self.action_ssh_executor("start", "success")
        return res

    # ------------------
    # Restart Freeradius
    # ------------------
    def action_radius_restart(self):
        res = self.action_ssh_executor("restart", "warning")
        return res

    # ------------------
    # Stop Freeradius
    # ------------------
    def action_radius_stop(self):
        res = self.action_ssh_executor("stop", "danger")
        return res

    # ------------------
    # Inquire Freeradius Status
    # ------------------
    def action_check_radius_status(self):
        res = self.action_ssh_executor("status", "info")
        return res

    # ------------------
    # Clear Status
    # ------------------
    def action_clear_status(self):
        self.service_status = ""

    # ------------------
    # CREATE METHOD
    # ------------------
    @api.model_create_multi
    def create(self, vals_list):

        res = super(NetworkNAS, self).create(vals_list)
        for vals in res:

            nas_data = {
                "nasname": vals["nasname"],
                "shortname": vals["shortname"],
                "type": "other" if vals.type.type == "MikroTik" else vals.type.type,
                "ports": vals["ports"],
                "secret": vals["secret"],
                "server": vals["server"],
                "community": vals["community"],
                "description": vals["description"],
            }

            # Create record in Radius Manager model NAS
            nas_record = self.env["nas"].create(nas_data)

            # Link the created nas_record with the current record
            vals.nas_master_id = nas_record.id

        return res

    # ------------------
    # WRITE METHOD
    # ------------------
    def write(self, vals):
        res = super(NetworkNAS, self).write(vals)

        nas_fields = ["nasname", "shortname", "type", "ports", "secret", "server", "community", "description"]
        filtered_vals = {key: vals[key] for key in vals if key in nas_fields}
        if filtered_vals and self.nas_master_id:
            if "type" in filtered_vals:
                # Handling Many2one field for `type`
                if self.type:
                    if self.type.type == "MikroTik":
                        filtered_vals["type"] = "other"
                    else:
                        filtered_vals["type"] = self.type.type

            # Write the filtered values to the linked `nas` record
            self.nas_master_id.write(filtered_vals)

        return res

    # ------------------
    # UNLINK METHOD
    # ------------------

    def unlink(self):
        for record in self:
            if record.nas_master_id:
                record.nas_master_id.unlink()
        return super(NetworkNAS, self).unlink()

    def delete_user(self, user_id):
        """
        Restart the user from the NAS.
        """
        urllib3.disable_warnings()
        if not self.nas_api_username or not self.nas_api_password or not self.nas_ip:
            raise ValidationError(_("Please provide NAS API credentials."))
        if self.type.type == "MikroTik":
            base_url = f"https://{self.nas_ip}/rest/ppp/active/{user_id}"
            # params = {
            # # "dynamic": "true",
            # # ".proplist": [".id", "address", "interface","type"],
            # ".query": [f"name=<pppoe-{user_id}>", "#"]
            #  }
            # params = json.dumps(params)
            try:
                response = requests.delete(
                    base_url,
                    auth=HTTPBasicAuth(self.nas_api_username, self.nas_api_password),
                    timeout=30,
                    verify=False,
                )

                if response.status_code == 204:
                    return {
                        "type": "ir.actions.client",
                        "tag": "display_notification",
                        "params": {
                            "type": "success",
                            "title": _("Success"),
                            "message": _("User Router Restarted successfully."),
                            "sticky": False,
                            "next": {"type": "ir.actions.act_window_close"},
                        },
                    }
                # nas_data = json.loads(response.text)
                # # print(f"==>> type(data): {type(nas_data)}")
                # print(json.dumps(nas_data, indent=4))
                # # print()
                # response.raise_for_status()
                else:
                    return {
                        "type": "ir.actions.client",
                        "tag": "display_notification",
                        "params": {
                            "type": "danger",
                            "title": _("error"),
                            "message": _("User not found"),
                            "sticky": False,
                            "next": {"type": "ir.actions.act_window_close"},
                        },
                    }
            except requests.exceptions.RequestException as e:
                # print(e)
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "type": "danger",
                        "title": _("Error"),
                        "message": _(str(e)),
                        "sticky": False,
                        "next": {"type": "ir.actions.act_window_close"},
                    },
                }
        else:
            raise ValidationError(_("NAS Type not supported for user deletion."))

    def get_nas_data(self):
        """
        Fetch data from NAS API and return the result as JSON.
        :return: JSON response
        """
        # NAS Username *
        # api
        # NAS Password *
        # 123456
        # API Port *
        # 8728
        # Incoming Port *
        # 3799
        urllib3.disable_warnings()
        if not self.nas_api_username or not self.nas_api_password or not self.nas_ip:
            raise ValidationError(_("Please provide NAS API credentials."))
        if self.type.type == "MikroTik":
            base_url = f"https://{self.nas_ip}/rest/system/resource"
            headers = {
                "Content-Type": "application/json",
            }
            # params = {
            #     "dynamic": "true",
            #     # ".proplist": [".id", "address", "interface", "dynamic", "type"],
            # }

            try:
                response = requests.get(
                    base_url,
                    headers=headers,
                    auth=HTTPBasicAuth(self.nas_api_username, self.nas_api_password),
                    # params=params,
                    timeout=30,
                    verify=False,
                )
                response.raise_for_status()

                nas_data = json.loads(response.text)
                # print(f"==>> type(data): {type(nas_data)}")
                # print(json.dumps(nas_data, indent=4))
                # date_format = "%b/%d/%Y %H:%M:%S"
                # Parse and store the data
                # for nas_data in data:  # Assuming the response is a list
                values = {
                    "architecture_name": nas_data.get("architecture-name"),
                    "board_name": nas_data.get("board-name"),
                    "nas_build_time": nas_data.get("build-time", ""),
                    "cpu": nas_data.get("cpu"),
                    "cpu_count": int(nas_data.get("cpu-count", 0)),
                    "cpu_frequency_mhz": int(nas_data.get("cpu-frequency", 0)),
                    "cpu_load": float(nas_data.get("cpu-load", 0)),
                    "free_hdd_space_Gib": int(nas_data.get("free-hdd-space", 0)) / (1024**3),
                    "free_memory_Gib": int(nas_data.get("free-memory", 0)) / (1024**3),
                    "platform": nas_data.get("platform"),
                    "total_hdd_space_Gib": int(nas_data.get("total-hdd-space", 0)) / (1024**3),
                    "total_memory_Gib": int(nas_data.get("total-memory", 0)) / (1024**3),
                    "uptime": nas_data.get("uptime"),
                    "version": nas_data.get("version"),
                }

                print(f"==>> values: {values}")
                # Create or update record
                self.update(values)

                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "type": "success",
                        "title": _("Success"),
                        "message": _("Data fetched successfully."),
                        "sticky": False,
                        "next": {"type": "ir.actions.act_window_close"},
                    },
                }
            except requests.exceptions.RequestException as e:
                # print(e)
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "type": "danger",
                        "title": _("Error"),
                        "message": _(str(e)),
                        "sticky": False,
                        "next": {"type": "ir.actions.act_window_close"},
                    },
                }
            # return {"error": str(e)}

        else:
            raise ValidationError(_("NAS Type not supported for API data retrieval."))
