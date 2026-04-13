from odoo import models, fields

class NetworkNAS(models.Model):
    _inherit = "network.nas"

    olt_ids = fields.One2many("network.olt", "nas_id", string="OLTs")
