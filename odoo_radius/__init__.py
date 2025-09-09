# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def _auto_pre_init(env):
    query = """
             /*
* Table structure for table 'radacct'
*
*/    
    CREATE TABLE IF NOT EXISTS radacct (
       RadAcctId               bigserial PRIMARY KEY,
       AcctSessionId           text NOT NULL,
       AcctUniqueId            text NOT NULL UNIQUE,
       UserName                text,
       Realm                   text,
       NASIPAddress            inet NOT NULL,
       NASPortId               text,
       NASPortType             text,
       AcctStartTime           timestamp with time zone,
       AcctUpdateTime          timestamp with time zone,
       AcctStopTime            timestamp with time zone,
       AcctInterval            bigint,
       AcctSessionTime         bigint,
       AcctAuthentic           text,
       ConnectInfo_start       text,
       ConnectInfo_stop        text,
       AcctInputOctets         bigint,
       AcctOutputOctets        bigint,
       CalledStationId         text,
       CallingStationId        text,
       AcctTerminateCause      text,
       ServiceType             text,
       FramedProtocol          text,
       FramedIPAddress         inet,
       FramedIPv6Address       inet,
       FramedIPv6Prefix        inet,
       FramedInterfaceId       text,
       DelegatedIPv6Prefix     inet,
       Class                   text
);

    -- For use by update-, stop- and simul_* queries
    CREATE INDEX radacct_active_session_idx ON radacct (AcctUniqueId) WHERE AcctStopTime IS NULL;

    -- For use by on-off-
    CREATE INDEX radacct_bulk_close ON radacct (NASIPAddress, AcctStartTime) WHERE AcctStopTime IS NULL;

    -- and for common statistic queries:
    CREATE INDEX radacct_start_user_idx ON radacct (AcctStartTime, UserName);

    -- and for Class
    CREATE INDEX radacct_calss_idx ON radacct (Class);

    CREATE TABLE IF NOT EXISTS radpostauth (
       id                      bigserial PRIMARY KEY,
       username                text NOT NULL,
       pass                    text,
       reply                   text,
       CalledStationId         text,
       CallingStationId        text,
       authdate                timestamp with time zone NOT NULL default now(),
       Class                   text);
    CREATE INDEX radpostauth_username_idx ON radpostauth (username);
    CREATE INDEX radpostauth_class_idx ON radpostauth (Class);

        """
    env.cr.execute(query)
    _logger.info("Table 'radacct' created successfully.")


def uninstall_hook(env):
    """Drop tables and indexes when the module is uninstalled."""
    # List of tables to drop
    tables_to_drop = [
        "radacct",
        "radpostauth",
    ]

    # Drop indexes related to the 'radacct' table
    indexes_to_drop = [
        "radacct_active_session_idx",
        "radacct_bulk_close",
        "radacct_start_user_idx",
        "radacct_calss_idx",
        "radpostauth_username_idx",
        "radpostauth_class_idx",
    ]

    # Dropping indexes
    for index in indexes_to_drop:
        try:
            env.cr.execute(f"DROP INDEX IF EXISTS {index};")
            _logger.info("Index '%s' dropped successfully.", index)
        except Exception as e:
            _logger.error("Failed to drop index '%s': %s", index, str(e))

    # Dropping tables
    for table in tables_to_drop:
        try:
            env.cr.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
            _logger.info("Table '%s' dropped successfully.", table)
        except Exception as e:
            _logger.error("Failed to drop table '%s': %s", table, str(e))

from . import models
from . import controllers