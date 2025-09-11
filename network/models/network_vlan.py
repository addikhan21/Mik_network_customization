# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class NetworkVlan(models.Model):
    _name = "network.vlan"
    _description = "NetworkVlan"

    name = fields.Char("Vlan")
    nas_id = fields.Many2one("network.nas", "NAS ID")
    complete_name = fields.Char("Complete Name", compute="_compute_complete_name")
    
    

    @api.depends("name", "nas_id")
    def _compute_complete_name(self):
        for rec in self:
            if rec.nas_id and rec.name:

                rec.complete_name = f"VLAN-{rec.name}-{rec.nas_id.nasname}"

            else:
                rec.complete_name = _("New")

    def _compute_display_name(self):
        for rec in self:
            if rec.nas_id and rec.name:
                rec.display_name = f"{rec.name}-{rec.nas_id.nasname}"
            else:
                rec.display_name = _("New")
