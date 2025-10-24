import re
from netmiko import ConnectHandler
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, Command, _
from odoo.exceptions import ValidationError, UserError
# from email_validator import validate_email, EmailNotValidError
# import phonenumbers
import calendar
from datetime import date, timedelta
from markupsafe import Markup
import logging

_logger = logging.getLogger(__name__)


class Users(models.Model):
    """
    This model is used to store users
    """

    _name = "users"
    _description = "Internet Users"
    _rec_name = "username"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _sql_constraints = [
        ("unique_username", "UNIQUE(username)", "Username must be unique!")
    ]

    name = fields.Char("Name", required=True)
    username = fields.Char(string="Username", required=True)
    password = fields.Char(string="Password", required=True)
    email = fields.Char(string="Email", required=False)
    mobile = fields.Char(string="Mobile", required=False)
    address = fields.Char(string="Address", required=False)
    subscription_id = fields.Many2one("sale.subscription", string="Subscription")
    id_address = fields.Char(string="ID Address", required=True)
    opportunity_id = fields.Many2one('crm.lead', string='Opportunity', readonly=True)


    distributor_id = fields.Many2one(
        "distributors",
        string="Distributor",
        index=True,
        # required=True,
    )

    # master_dealer_id = fields.Many2one(
    #     related="distributor_id.master_dealer_id", store=True
    # )
    # dealer_id = fields.Many2one(related="distributor_id.dealer_id", index=True, store=True)
    distributor_name = fields.Char(
         store=True, string="Distributor Name"
    )
    distributor_type = fields.Selection(
        related="distributor_id.distributor_type", store=True
    )
    package_id = fields.Many2one(
        "package.line",

        string="Package",
        index=True,
        # required=True,
    )
    # package_name = fields.Char(
    #     related="package_id.package_name", store=True, string="Package Name"
    # )
    package_distributor = fields.Many2one(
        "distributors", related="package_id.dealer_id", string="Package Distributor"
    )
    nas_id = fields.Many2one(
        related="package_id.package_id", store=True, string="NAS ID"
    )
    # nas_id = fields.Many2one(
    #     related="distributor_id.nas_id", store=True, string="NAS ID"
    # )
    # vlan_id = fields.Many2one(
    #     "vlans",
    #     domain="[ ('nas_id','=',nas_id)]",
    #     string="VLAN",
    # )
    vlan_id = fields.Many2one(
        "res.users",
        domain="[ ('nas_id','=',nas_id)]",
        string="VLAN",
    )
    # mac_address = fields.Char(string="MAC Address", compute="_compute_mac_address")  # Original compute field
    mac_address = fields.Char(string="MAC Address")

    expiry_date = fields.Datetime(
        string="Expiry Date Time", default=lambda self: fields.Datetime.now()
    )
    # expiry_date_char = fields.Char(
    #     string="Expiry Date", compute="_compute_expiry_date_char", default="Unknown"
    # )  # Original compute field
    expiry_date_char = fields.Char(
        string="Expiry Date", default="Unknown"
    )
    radusergroup_id = fields.Many2one("radusergroup", string="Related Radusergroup")
    # uptime = fields.Char(
    #     string="Uptime", compute="_compute_uptime", default="Unknown", store=False
    # )  # Original compute field
    uptime = fields.Char(
        string="Uptime", default="Unknown", store=False
    )

    ip_history = fields.Html(
        string="IP History", readonly=True
    )

    # current_status = fields.Selection(
    #     [
    #         ("online", "Online"),
    #         ("offline", "Offline"),
    #         ("indeterminate", "Indeterminate"),
    #         ("unknown", "Unknown"),
    #     ],
    #     string="Current Status",
    #     compute="_compute_current_status",
    #     search="_search_current_status",
    # )  # Original compute field
    current_status = fields.Selection(
        [
            ("online", "Online"),
            ("offline", "Offline"),
            ("indeterminate", "Indeterminate"),
            ("unknown", "Unknown"),
        ],
        string="Current Status",
        search="_search_current_status",
    )
    # activation_status = fields.Selection(
    #     [("active", "Active"), ("inactive", "Inactive"), ("unknown", "Unknown")],
    #     string="Activation Status",
    #     compute="_compute_activation_status",
    # )  # Original compute field
    activation_status = fields.Selection(
        [("active", "Active"), ("inactive", "Inactive"), ("unknown", "Unknown")],
        string="Activation Status",
    )
    # conection_status = fields.Selection(
    #     [("active", "Active"), ("expired", "Expired")],
    #     string="Connection Status",
    #     compute="_compute_connection_status",
    #     search="_search_connection_status",
    # )  # Original compute field
    conection_status = fields.Selection(
        [("active", "Active"), ("expired", "Expired")],
        string="Connection Status",
        search="_search_connection_status",
    )

    # recharge_count = fields.Integer(
    #     compute="_compute_total_recharges", string="Recharge Count"
    # )  # Original compute field
    recharge_count = fields.Integer(
        string="Recharge Count"
    )
    # radcheck_count = fields.Integer(
    #     string="Radcheck Count", compute="_compute_radcheck_count"
    # )  # Original compute field
    radcheck_count = fields.Integer(
        string="Radcheck Count"
    )
    
    #Enable / Disable
    is_disable = fields.Boolean(
        string="Disable",
        default=False,
        help="Disable User",
    )

    # CNIC
    cnic = fields.Char(string="CNIC")
    cnic_front = fields.Image(
        string="Front",
        max_width=1024,
        max_height=1024,
        verify_resolution=True,
        help="Upload front side of CNIC",
    )

    cnic_back = fields.Image(
        string="Back",
        max_width=1024,
        max_height=1024,
        verify_resolution=True,
        help="Upload back side of CNIC",
    )

    # can_access = fields.Boolean(compute="_compute_access")  # Original compute field
    can_access = fields.Boolean()

    @api.depends("expiry_date")
    def _compute_expiry_date_char(self):
        for record in self:
            if record.expiry_date:
                record.expiry_date_char = record.expiry_date.strftime("%d %b %Y %H:%M")

    @api.depends()  # Empty depends will recalculate every time
    def _compute_access(self):
        for record in self:
            is_admin = self.env.user.has_group("base_security_groups.group_admin")
            is_distributor = self.env.user.distributor_id.id == record.distributor_id.id
            record.can_access = not (is_admin or is_distributor)

    @api.depends()
    def _compute_mac_address(self):
        self.ensure_one()
        query = """
            SELECT callingstationid
            FROM radacct
            WHERE username = %s
            AND acctstoptime IS NULL
            LIMIT 1
        """
        if self.username:
            self.env.cr.execute(query, (self.username,))
            result = self.env.cr.fetchone()
            if result and result[0]:
                self.mac_address = result[0]
            else:
                self.mac_address = None

    def _compute_uptime(self):
        self.ensure_one()
        self.uptime = "0d 0h 0m"
        query = """
            SELECT 
            COALESCE(
                CONCAT(
                    EXTRACT(DAY FROM NOW() - acctstarttime)::INTEGER, 'd ',
                    EXTRACT(HOUR FROM NOW() - acctstarttime)::INTEGER, 'h ',
                    EXTRACT(MINUTE FROM NOW() - acctstarttime)::INTEGER, 'm'
                ),
                '0d 0h 0m'
            ) as uptime
        FROM radacct 
        WHERE username = %s 
            AND acctstoptime IS NULL 
        LIMIT 1
        """

        if self.username:
            self.env.cr.execute(query, (self.username,))
            result = self.env.cr.fetchone()

            if result and result[0]:
                self.uptime = result[0]
            else:
                self.uptime = "0d 0h 0m"
        else:
            self.uptime = "0d 0h 0m"

    # def _search_activation_status(self, operator, value):
    #     query = """
    #     SELECT ru.id,
    #         CASE
    #             WHEN ru.expiry_date > NOW() THEN 'active'
    #             WHEN ru.expiry_date <= NOW() THEN 'inactive'
    #             WHEN ru.expiry_date IS NULL THEN 'unknown'
    #         END as status
    #     FROM users ru
    #     """
    #     self.env.cr.execute(query)
    #     results = self.env.cr.fetchall()

    #     matching_ids = []
    #     for record_id, status in results:
    #         if operator == "=" and status == value:
    #             matching_ids.append(record_id)
    #         elif operator == "!=" and status != value:
    #             matching_ids.append(record_id)

    #     return [("id", "in", matching_ids)]

    def _search_connection_status(self, operator, value):
        valid_operators = {"=", "!="}
        if operator not in valid_operators:
            return []

        query = """
            SELECT ru.id 
            FROM users ru
            WHERE CASE
                WHEN ru.expiry_date > NOW() THEN 'active'
                WHEN ru.expiry_date <= NOW() THEN 'inactive'
                WHEN ru.expiry_date IS NULL THEN 'unknown'
            END {} %s
        """.format(
            "=" if operator == "=" else "!="
        )

        self.env.cr.execute(query, (value,))
        ids = [r[0] for r in self.env.cr.fetchall()]
        return [("id", "in", ids)]

    def _compute_activation_status(self):
        self.ensure_one()
        if self.username:
            query = """
                SELECT reply
                FROM radpostauth 
                WHERE username = %s
                ORDER BY authdate DESC
                LIMIT 1
            """
            self.env.cr.execute(query, (self.username,))
            result = self.env.cr.fetchone()

            if result and result[0] == "Access-Accept":
                self.activation_status = "active"
            else:
                self.activation_status = "inactive"
        else:
            self.activation_status = "unknown"

    def _compute_current_status(self):
        # Single optimized query that handles all cases
        query = """
            SELECT u.id,
                CASE 
                    WHEN u.username IS NULL THEN 'unknown'
                    WHEN COUNT(r.username) = 0 THEN 'offline'
                    WHEN COUNT(r.username) = 1 THEN 'online'
                    ELSE 'indeterminate'
                END as status
            FROM users u
            LEFT JOIN radacct r ON u.username = r.username 
                AND r.acctstoptime IS NULL
            WHERE u.id IN %s
            GROUP BY u.id, u.username
        """
        self.env.cr.execute(query, (tuple(self.ids),))
        status_map = dict(self.env.cr.fetchall())

        # Update records directly
        for record in self:
            record.current_status = status_map.get(record.id, "unknown")

    def _search_current_status(self, operator, value):
        valid_operators = {"=", "!="}
        if operator not in valid_operators:
            return []

        query = """
            SELECT ru.id 
            FROM users ru
            LEFT JOIN (
                SELECT username, COUNT(*) as session_count
                FROM radacct 
                WHERE acctstoptime IS NULL
                GROUP BY username
            ) ra ON ru.username = ra.username
            WHERE 
                CASE
                    WHEN ra.session_count IS NULL THEN 'offline'
                    WHEN ra.session_count = 1 THEN 'online'
                    WHEN ru.username IS NULL THEN 'unknown'
                    ELSE 'indeterminate'
                END {} %s
        """.format(
            "=" if operator == "=" else "!="
        )

        self.env.cr.execute(query, (value,))
        ids = [r[0] for r in self.env.cr.fetchall()]
        return [("id", "in", ids)]

    # def _search_current_status(self, operator, value):

    #     # print("Operator:", operator)
    #     # print("Value:",expiry_date value)

    #     query = """
    #     SELECT ru.id,
    #         CASE
    #             WHEN COUNT(ra.username) = 0 THEN 'offline'
    #             WHEN COUNT(ra.username) = 1 THEN 'online'
    #             WHEN ra.username IS NULL THEN 'unknown'
    #             ELSE 'indeterminate'
    #         END as status
    #     FROM users ru
    #     LEFT JOIN radacct ra ON ru.username = ra.username
    #         AND ra.acctstoptime IS NULL
    #     GROUP BY ru.id, ra.username
    #     """
    #     self.env.cr.execute(query)
    #     results = self.env.cr.fetchall()

    #     matching_ids = []
    #     for record_id, status in results:
    #         if operator == "=" and status == value:
    #             matching_ids.append(record_id)
    #         elif operator == "!=" and status != value:
    #             matching_ids.append(record_id)
    #     return [("id", "in", matching_ids)]

    # def _compute_current_status(self):

    #     # Step 1: Get all usernames in a list
    #     usernames = [user.username for user in self]

    #     # Step 2: Create a dictionary to store results
    #     results = {}
    #     # Step 3: Execute query for all users at once
    #     if usernames:
    #         query = """
    #             SELECT username, COUNT(*)
    #             FROM radacct
    #             WHERE username = ANY(%s)
    #             AND acctstoptime IS NULL
    #             GROUP BY username
    #         """
    #         self.env.cr.execute(query, (usernames,))
    #         results = dict(self.env.cr.fetchall())

    #     # Step 4: Process each record
    #     for record in self:
    #         if not record.username:
    #             record.current_status = "unknown"
    #             continue

    #         active_sessions = results.get(record.username, 0)
    #         if active_sessions == 0:
    #             record.current_status = "offline"
    #         elif active_sessions == 1:
    #             record.current_status = "online"
    #         else:
    #             record.current_status = "indeterminate"

    @api.onchange("distributor_id")
    def _onchange_distributor_id(self):
        self.package_id = False
        self.vlan_id = False

    @api.depends("distributor_id")
    def _compute_total_recharges(self):
        for record in self:
            total = self.env["recharge.history"].search_count(
                [("user_id", "=", record.id)]
            )
            record.recharge_count = total

    def _compute_radcheck_count(self):
        for record in self:
            record.radcheck_count = self.env["radcheck"].search_count(
                [("username", "=", record.username)]
            )

    def action_view_total_recharges(self):
        return {
            "name": "Recharge History",
            "type": "ir.actions.act_window",
            "res_model": "recharge.history",
            "view_mode": "tree,form",
            "domain": [("user_id", "=", self.id)],
        }

    @api.model_create_multi
    def create(self, vals_list):
        """
        Creates a complete user profile with all related records:
        - RADIUS authentication entries
        """

        res = super().create(vals_list)
        # for record in res:
        #     record.create_radcheck_entry()
        #     record.create_radusergroup_entry()
        #     if record.vlan_id:
        #         record.vlan_id.is_assigned_to_user = True

        return res

    def create_radusergroup_entry(self):
        """
        Create RADIUS user group entry for the user using the username and package name.
        The user group entry is used to map the user to a specific package.
        """

        if self.username and self.package_id:
            radusergroup_vals = {
                "username": self.username,
                # "groupname": self.package_name,
                "priority": 1,
            }
            radusergroup = self.env["radusergroup"].sudo().create(radusergroup_vals)
            self.radusergroup_id = radusergroup.id
        return True

    def create_radcheck_entry(self):
        """
        Create RADIUS authentication entries for the user using the username and password.
        These entries contain the user's password and expiration date.
        """

        if self.username and self.password and self.nas_id:
            radcheck_vals = [
                {
                    "username": self.username,
                    "attribute": "Cleartext-Password",  # cleartext-password
                    "op": ":=",
                    "value": self.password,
                },
                {
                    "username": self.username,
                    "attribute": "NAS-IP-Address",  # nas-binding
                    "op": "==",
                    "value": self.nas_id.nasname,
                },
                {
                    "username": self.username,
                    "attribute": "Simultaneous-Use",  # simultaneous-use
                    "op": ":=",
                    "value": 1,
                },
                {
                    "username": self.username,
                    "attribute": "Expiration",
                    "op": ":=",
                    "value": self.expiry_date_char,
                },
                
            ]
           

            # Making Vlan Biniding Optional.
            if self.vlan_id:
                radcheck_vals.append(
                    {
                        "username": self.username,
                        "attribute": "NAS-Port-Id",  # vlan-binding
                        "op": "==",
                        "value": self.vlan_id.name,
                    }
                )
            self.env["radcheck"].sudo().create(radcheck_vals)

        else:
            raise ValidationError(
                _("Username, Password, Expiry Date and NAS ID are required!")
            )

        return True

    def action_view_radcheck(self):
        """
        Action to open the tree view of the related radcheck records.
        The domain filter will show only the radcheck records that are associated
        with the current user.
        """
        return {
            "name": "Radcheck",
            "view_mode": "tree",
            "res_model": "radcheck",
            "type": "ir.actions.act_window",
            "domain": [("username", "=", self.username)],
            "target": "new",
            "context": {"create": False, "delete": False, "update": False},
        }
        
    def action_disable_user(self):
        for record in self:
            reject_values = {
                "username": record.username,
                "attribute": "Auth-Type",
                "op": ":=",
                "value": "Reject",
            }
            self.env["radcheck"].sudo().create(reject_values)
            query = """   
            update radacct  set acctstoptime = acctstarttime
            WHERE username = %s AND acctstoptime IS NULL;
            """
            self.env.cr.execute(query, (self.username,))
            record.is_disable = True
            return {
                "type": "ir.actions.client",
                "tag": "reload",
                }
            
    def action_enable_user(self):
        for record in self: 
            existing_auth_type = self.env["radcheck"].sudo().search([("username", "=", record.username),("attribute", "=", "Auth-Type"),],limit=1, )
            if existing_auth_type:
                existing_auth_type.unlink()
                record.is_disable = False
                return {
                    "type": "ir.actions.client",
                    'tag': 'reload',
                    }
            
            
            

    def action_release_mac(self):
        self.ensure_one()
        if self.mac_address:
            self.mac_address = False

        existing_mac_address = (
            self.env["radcheck"]
            .sudo()
            .search(
                [
                    ("username", "=", self.username),
                    ("attribute", "=", "Calling-Station-Id"),
                ],
                limit=1,
            )
        )
        if existing_mac_address:
            existing_mac_address.unlink()

        if existing_mac_address:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "MAC Address Released!",
                    "message": "Mac Address Released Successfully!",
                    "type": "success",
                    "sticky": False,
                },
            }

        else:
            raise ValidationError(_("No MAC Address Found!"))

    def action_comming_soon(self):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Coming Soon!",
                "message": "Function will be built soon!",
                "type": "warning",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _compute_connection_status(self):
        now = fields.Datetime.now() + timedelta(hours=5)
        # now = fields.Datetime.now()
        for record in self:
            if record.expiry_date and record.expiry_date > now:
                record.conection_status = "active"
            else:
                record.conection_status = "expired"
                


    def action_refresh_connection(self):
        """
        Action to refresh the connection of the user.
        """
        self.ensure_one()
        if self.username:
            query = """   
            DELETE FROM radacct  
            WHERE username = %s AND acctstoptime IS NULL;
            """
            self.env.cr.execute(query, (self.username,))
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "User Refreshed Successfully!",
                    "message": "Ask User to restart their router device!",
                    "type": "success",
                    "sticky": False,
                    "next": {"type": "ir.actions.act_window_close"},
                },
            }
        else:
            raise ValidationError(_("Username is required!"))

    def get_last_ten_ips(self):
        query = """
            SELECT DISTINCT 
                framedipaddress, 
                acctsessionid,
                acctstarttime,
                 acctstoptime,
    acctterminatecause
            FROM radacct 
            WHERE username = %s 
            ORDER BY acctstarttime DESC 
            LIMIT 5
        """
        self.env.cr.execute(query, [self.username])
        results = self.env.cr.dictfetchall()

        html_content = ['<div class=" justify-content-center ">']

        for record in results:
            formatted_date = record["acctstarttime"]
            html_content.append(
                f"""<div class="mb-3 rounded shadow-sm ">
    <div class="card-header bg-light d-flex justify-content-between">
        <div>
            <i class="fa fa-shield me-2"></i>
            <strong>Session {record['acctsessionid']}</strong>
        </div>
        <span class="badge bg-info text-white mt-2">{record['acctterminatecause']}</span>
    </div>
    
    <div class="card-body">
        <div class="row">
            <div class="col-md-6">
                <div class="mb-2">
                    <i class="fa fa-wifi text-primary me-2"></i>
                    <strong class="text-primary">{record['framedipaddress']}</strong>
                </div>
            </div>
            <div class="col-md-6">
                <div class="text-end">
                    <div class="text-success mb-1">
                        <i class="fa fa-play-circle me-1"></i>Start: {record['acctstarttime']}
                    </div>
                    <div class="text-danger mb-1">
                        <i class="fa fa-stop-circle me-1"></i>End: {record['acctstoptime']}
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
               
            """
            )

        html_content.append("</div>")

        data = "".join(html_content)
        self.ip_history = data


class PackageLine(models.Model):
    _name = "package.line"
    _description = "Package Line"
    _order = "sequence"

    sequence = fields.Integer("Sequence", default=1)
    package_id = fields.Many2one("package.line", string="Package")
    nas_id = fields.Char( string="NAS")
    package_name = fields.Char(string="Package Name")
    package_price = fields.Float(string="Package Price")
    package_speed = fields.Char(string="Package Speed")
    dealer_id = fields.Many2one("distributors", string="Dealer")
