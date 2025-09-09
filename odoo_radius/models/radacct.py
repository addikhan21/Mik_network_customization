# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _,tools
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class RadiusAccounting(models.Model):
    """Model to hold data from the radacct table"""
    _name = 'radius.accounting'
    _description = 'Radius Accounting Data'
    _auto = False  # Indicates this is based on a database view
    _order = 'acct_stop_time desc'  # Default ordering

    rad_acct_id = fields.Char(string="RadAcct ID", help="Primary Key", readonly=True)
    acct_session_id = fields.Char(string="Session ID", help="Session ID", readonly=True)
    acct_unique_id = fields.Char(string="Unique ID", help="Unique session identifier", readonly=True)
    username = fields.Char(string="User Name", help="User associated with the session", readonly=True)
    realm = fields.Char(string="Realm", help="Realm associated with the session", readonly=True)
    nas_ip_address = fields.Char(string="NAS IP Address", help="NAS IP Address", readonly=True)
    nas_port_id = fields.Char(string="NAS Port ID", help="NAS Port ID", readonly=True)
    nas_port_type = fields.Char(string="NAS Port Type", help="NAS Port Type", readonly=True)
    acct_start_time = fields.Datetime(string="Session Start Time", help="Start of the session", readonly=True)
    acct_update_time = fields.Datetime(string="Last Update Time", help="Last time the session was updated", readonly=True)
    acct_stop_time = fields.Datetime(string="Session Stop Time", help="End of the session", readonly=True)
    acct_interval = fields.Integer(string="Session Interval", help="Interval of the session", readonly=True)
    acct_session_time = fields.Integer(string="Session Duration", help="Total session time in seconds", readonly=True)
    acct_authentic = fields.Char(string="Authentication Type", help="Authentication type for the session", readonly=True)
    connect_info_start = fields.Char(string="Connect Info Start", help="Connection info at start", readonly=True)
    connect_info_stop = fields.Char(string="Connect Info Stop", help="Connection info at stop", readonly=True)
    acct_input_octets = fields.Integer(string="Input Octets", help="Total input octets for the session", readonly=True)
    acct_output_octets = fields.Integer(string="Output Octets", help="Total output octets for the session", readonly=True)
    called_station_id = fields.Char(string="Called Station ID", help="MAC address of the access point", readonly=True)
    calling_station_id = fields.Char(string="Calling Station ID", help="MAC address or phone number of the client", readonly=True)
    acct_terminate_cause = fields.Char(string="Terminate Cause", help="Reason for session termination", readonly=True)
    service_type = fields.Char(string="Service Type", help="Service type associated with the session", readonly=True)
    framed_protocol = fields.Char(string="Framed Protocol", help="Framed Protocol used in the session", readonly=True)
    framed_ip_address = fields.Char(string="Framed IP Address", help="IP address assigned to the user", readonly=True)
    framed_ipv6_address = fields.Char(string="Framed IPv6 Address", help="IPv6 address assigned to the user", readonly=True)
    framed_ipv6_prefix = fields.Char(string="Framed IPv6 Prefix", help="IPv6 prefix assigned to the user", readonly=True)
    framed_interface_id = fields.Char(string="Framed Interface ID", help="Framed Interface ID", readonly=True)
    delegated_ipv6_prefix = fields.Char(string="Delegated IPv6 Prefix", help="Delegated IPv6 prefix", readonly=True)
    class_ = fields.Char(string="Class", help="Class associated with the session", readonly=True)

    def init(self):
        """Create or replace the view for Radius Accounting"""
        tools.drop_view_if_exists(self._cr, 'radius_accounting')
        query = """
            CREATE OR REPLACE VIEW radius_accounting AS (
                SELECT 
                    radacct.radacctid AS id,
                    radacct.radacctid AS rad_acct_id,
                    radacct.acctsessionid AS acct_session_id,
                    radacct.acctuniqueid AS acct_unique_id,
                    radacct.username AS username,
                    radacct.realm AS realm,
                    radacct.nasipaddress AS nas_ip_address,
                    radacct.nasportid AS nas_port_id,
                    radacct.nasporttype AS nas_port_type,
                    radacct.acctstarttime AS acct_start_time,
                    radacct.acctupdatetime AS acct_update_time,
                    radacct.acctstoptime AS acct_stop_time,
                    radacct.acctinterval AS acct_interval,
                    radacct.acctsessiontime AS acct_session_time,
                    radacct.acctauthentic AS acct_authentic,
                    radacct.connectinfo_start AS connect_info_start,
                    radacct.connectinfo_stop AS connect_info_stop,
                    radacct.acctinputoctets AS acct_input_octets,
                    radacct.acctoutputoctets AS acct_output_octets,
                    radacct.calledstationid AS called_station_id,
                    radacct.callingstationid AS calling_station_id,
                    radacct.acctterminatecause AS acct_terminate_cause,
                    radacct.servicetype AS service_type,
                    radacct.framedprotocol AS framed_protocol,
                    radacct.framedipaddress AS framed_ip_address,
                    radacct.framedipv6address AS framed_ipv6_address,
                    radacct.framedipv6prefix AS framed_ipv6_prefix,
                    radacct.framedinterfaceid AS framed_interface_id,
                    radacct.delegatedipv6prefix AS delegated_ipv6_prefix,
                    radacct.class AS class_
                FROM radacct
            );
        """
        self._cr.execute(query)

    @api.model
    def _cron_cleanup_multiple_sessions(self):
        """
        Cron job to clean up multiple active sessions.
        Updates acctstoptime for duplicate sessions where it's NULL.
        """
        query = """
            WITH duplicate_sessions AS (
                SELECT username, COUNT(*) as session_count
                FROM radacct 
                WHERE acctstoptime IS NULL
                GROUP BY username
                HAVING COUNT(*) > 1
            )
            UPDATE radacct ra
            SET acctstoptime = NOW()
            FROM duplicate_sessions ds
            WHERE ra.username = ds.username 
            AND ra.acctstoptime IS NULL
            AND ra.acctstarttime != (
                SELECT MAX(acctstarttime)
                FROM radacct
                WHERE username = ra.username
                AND acctstoptime IS NULL
            )
        """
        self.env.cr.execute(query)


    @api.model
    def _cron_cleanup_expired_sessions(self):
        """
        Cron job to clean up expired sessions.
        Updates acctstoptime for all active sessions where expiry date is less than current time.
        """
        query = """
            UPDATE radacct 
            SET acctstoptime = NOW()
            WHERE acctstoptime IS NULL 
            AND username IN (
                SELECT username
                FROM radcheck 
                WHERE attribute = 'Expiration'
                AND TO_TIMESTAMP(value, 'DD Mon YYYY HH24:MI') < NOW()
            )
        """
        self.env.cr.execute(query)

            
        
        
        
        
        
