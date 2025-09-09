from odoo import models, fields, api

class RadGroupReply(models.Model):
    _name = 'radgroupreply'
    _description = 'RADIUS Group Reply'
    _log_access = False
    _rec_name = 'groupname'

    groupname = fields.Char(string='GroupName', index=True, required=True)
    attribute = fields.Char(string='Attribute', index=True, required=True)
    op = fields.Char(string='Operator', default="=", size=2, required=True)
    value = fields.Char(string='Value', required=True)
    