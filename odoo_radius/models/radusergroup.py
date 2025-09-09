from odoo import models, fields, api

class RadUserGroup(models.Model):
    _name = 'radusergroup'
    _description = 'RADIUS User Group'
    _log_access = False
    _rec_name = 'username'

    username = fields.Char(string='UserName', index=True, required=True)
    groupname = fields.Char(string='GroupName', required=True)
    priority = fields.Integer(string='Priority', default=0)
    
    