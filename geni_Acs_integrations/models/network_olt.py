from odoo import models, fields

class NetworkOLT(models.Model):
    _name = "network.olt"
    _description = "Network OLT Device"
    _rec_name = "name"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="OLT Name", required=True, tracking=True)
    ip_address = fields.Char(string="IP Address", tracking=True)
    brand = fields.Selection(
        [("Huawei", "Huawei"), ("ZTE", "ZTE"), ("FiberHome", "FiberHome")],
        string="Brand",
        required=True,
        tracking=True,
        default="Huawei",
    )
    location = fields.Char(string="Location", tracking=True)
    nas_id = fields.Many2one("network.nas", string="NAS ID", required=True, tracking=True)
