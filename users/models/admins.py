from odoo import models, fields, api
from datetime import timedelta, date


class Distributors(models.Model):
    _inherit = "admins"

    user_count = fields.Integer(related="distributor_id.user_count", string="Users")
    total_users = fields.Integer(related="distributor_id.total_users", string="Total Users")
    expires_soon_count = fields.Integer(compute="_compute_expires_soon_count")
    expired_count = fields.Integer(compute="_compute_expired_count")
    new_users_count = fields.Integer(compute="_compute_new_users_count")
    
    # def _compute_new_users_count(self):
    #     for admin in self:
    #         distributors_list = ""
    #         # if admin.distributor_type == "master_dealer":
    #         #     distributors_list = (
    #         #         self.env["distributors"]
    #         #         .search([("master_dealer_id", "=", admin.distributor_id.id)])
    #         #         .ids
    #         #     )
    #
    #         elif admin.distributor_type == "dealer":
    #             distributors_list = (
    #                 self.env["distributors"]
    #                 .search([("dealer_id", "=", admin.distributor_id.id)])
    #                 .ids
    #             )
    #
    #         elif self.distributor_type == "sub_dealer":
    #             distributors_list = [admin.distributor_id.id]
    #
    #
    #         admin.new_users_count = self.env["users"].search_count(
    #             [
    #                 ("distributor_id", "in",distributors_list),
    #                 ("expiry_date", "<", date.today() + timedelta(days=30)),
    #             ]
    #         )
            
    # def action_view_new_users(self):
    #     self.ensure_one()
    #     distributors_list = ""
    #     if self.distributor_type == "master_dealer":
    #         distributors_list = (
    #             self.env["distributors"]
    #             .search([("master_dealer_id", "=", self.distributor_id.id)])
    #             .ids
    #         )
    #
    #     elif self.distributor_type == "dealer":
    #         distributors_list = (
    #             self.env["distributors"]
    #             .search([("dealer_id", "=", self.distributor_id.id)])
    #             .ids
    #         )
    #
    #     elif self.distributor_type == "sub_dealer":
    #         distributors_list = [self.distributor_id.id]
            
        # return {
        #     "type": "ir.actions.act_window",
        #     "name": "New Users",
        #     "view_mode": "dealer_id",
        #     "res_model": "users",
        #     "domain": [
        #         ("distributor_id", "in",distributors_list),
        #         ("expiry_date", "<", date.today() + timedelta(days=30)),
        #     ],
        #     "context": {
        #         "search_default_distributor_id": 1,
        #         "group_by": ["distributor_id"],
        #         "default_distributor_id": self.distributor_id.id,
        #         "create": False,
        #         "open": False,
        #         "delete": False,
        #         "edit": False,
        #     },
        # }

    def _compute_expired_count(self):
        for admin in self:
            
            admin.expired_count = self.env["users"].search_count(
                [
                    ("distributor_id", "=", admin.distributor_id.id),
                    ("expiry_date", "<", fields.Datetime.now()),
                ]
            )

    def action_view_expired_users(self):
        self.ensure_one()
        # return {
        #     "type": "ir.actions.act_window",
        #     "name": "Expired Users",
        #     "view_mode": "dealer_id,form",
        #     "res_model": "users",
        #     "domain": [
        #         ("distributor_id", "=", self.distributor_id.id),
        #         ("expiry_date", "<", fields.Datetime.now()),
        #     ],
        #     "context": {
        #         "default_distributor_id": self.distributor_id.id,
        #         "create": False,
        #         "open": False,
        #         "delete": False,
        #         "edit": False,
        #     },
        # }

    def _compute_expires_soon_count(self):
        expiry_date = fields.Date.today() + timedelta(days=7)
        for admin in self:
            admin.expires_soon_count = self.env["users"].search_count(
                [
                    ("distributor_id", "=", admin.distributor_id.id),
                    ("expiry_date", "<=", expiry_date),
                    ("expiry_date", ">=", fields.Date.today()),
                ]
            )

    def action_view_expiring_soon_users(self):
        self.ensure_one()
        expiry_date = fields.Date.today() + timedelta(days=7)
        # return {
        #     "type": "ir.actions.act_window",
        #     "name": "Users Expiring Soon!",
        #     "view_mode": "dealer_id,form",
        #     "res_model": "users",
        #     "domain": [
        #         ("distributor_id", "=", self.distributor_id.id),
        #         ("expiry_date", "<=", expiry_date),
        #         ("expiry_date", ">=", fields.Date.today()),
        #     ],
        #     "context": {
        #         "default_distributor_id": self.distributor_id.id,
        #         "create": False,
        #         "open": False,
        #         "delete": False,
        #         "edit": False,
        #     },
        # }

    def action_view_users(self):
        self.ensure_one()
    #     return {
    #         "type": "ir.actions.act_window",
    #         "name": "Users",
    #         "view_mode": "dealer_id,form",
    #         "res_model": "users",
    #         "domain": [("distributor_id", "=", self.distributor_id.id)],
    #         "context": {
    #             "default_distributor_id": self.distributor_id.id,
    #             "create": False,
    #             "open": False,
    #             "delete": False,
    #             "edit": False,
    #         },
    # #     }
    #
    # # def action_view_total_users(self):
    # #     self.ensure_one()
    #     distributors_list = []
    #     if self.distributor_type == "master_dealer":
    #         distributors_list = (
    #             self.env["distributors"]
    #             .search([("master_dealer_id", "=", self.distributor_id.id)])
    #             .ids
    #         )
    #         distributors_list.append(self.distributor_id.id)
    #
    #     elif self.distributor_type == "dealer":
    #         distributors_list = (
    #             self.env["distributors"]
    #             .search([("dealer_id", "=", self.distributor_id.id)])
    #             .ids
    #         )
    #         distributors_list.append(self.distributor_id.id)
    #
    #     return {
    #         "type": "ir.actions.act_window",
    #         "name": "Users",
    #         "view_mode": "tree",
    #         "res_model": "users",
    #         "domain": [("distributor_id", "in", distributors_list)],
    #         "context": {
    #             "search_default_distributor_id": 1,
    #             "group_by": ["distributor_id"],
    #             "create": False,
    #             "open": False,
    #             "delete": False,
    #             "edit": False,
    #         },
    #     }
