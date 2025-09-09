# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, tools

_logger = logging.getLogger(__name__)

class RadiusPostAuth(models.Model):
    """Model to hold data from the radpostauth table"""
    _name = 'radius.postauth'
    _description = 'Radius Post Authentication Data'
    _auto = False  # Indicates this is based on a database view
    _order = 'authdate desc'  # Default ordering

    id = fields.Char(string="ID", help="Primary Key", readonly=True)
    username = fields.Char(string="User Name", help="User associated with the authentication attempt", readonly=True)
    pass_ = fields.Char(string="Password", help="Password used during authentication", readonly=True)
    reply = fields.Char(string="Reply", help="Reply message from the RADIUS server", readonly=True)
    called_station_id = fields.Char(string="Called Station ID", help="MAC address of the access point", readonly=True)
    calling_station_id = fields.Char(string="Calling Station ID", help="MAC address or phone number of the client", readonly=True)
    authdate = fields.Datetime(string="Authentication Date", help="Date and time of authentication", readonly=True)
    class_ = fields.Char(string="Class", help="Class associated with the session", readonly=True)

    def init(self):
        """Create or replace the view for Radius Post Authentication"""
        tools.drop_view_if_exists(self._cr, 'radius_postauth')
        query = """
            CREATE OR REPLACE VIEW radius_postauth AS (
                SELECT
                    radpostauth.id AS id,
                    radpostauth.username AS username,
                    radpostauth.pass AS pass_,
                    radpostauth.reply AS reply,
                    radpostauth.calledstationid AS called_station_id,
                    radpostauth.callingstationid AS calling_station_id,
                    radpostauth.authdate AS authdate,
                    radpostauth.class AS class_
                FROM radpostauth
            );
        """
        self._cr.execute(query)
