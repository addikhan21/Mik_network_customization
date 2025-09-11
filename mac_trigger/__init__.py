# -*- coding: utf-8 -*-
import logging
_logger = logging.getLogger(__name__)

def create_radius_triggers(env):
    try:
        cr = env.cr
        # Create unique constraint on radcheck
        cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS unique_calling_station_id 
            ON radcheck (attribute, value) 
            WHERE attribute = 'Calling-Station-Id';
        """)
        
        # Create trigger function
        cr.execute("""
            CREATE OR REPLACE FUNCTION bind_mac_to_user()
            RETURNS TRIGGER AS $$
            BEGIN
                IF NEW.acctstoptime IS NULL THEN
                    INSERT INTO radcheck (username, attribute, op, value)
                    VALUES (
                        NEW.username,
                        'Calling-Station-Id',
                        ':=',
                        NEW.callingstationid
                    )
                    ON CONFLICT (attribute, value) 
                    WHERE attribute = 'Calling-Station-Id' 
                    DO NOTHING;
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        # Attach trigger to radacct table
        cr.execute("""
            DROP TRIGGER IF EXISTS tr_bind_mac_on_session_start ON radacct;
            CREATE TRIGGER tr_bind_mac_on_session_start
            AFTER INSERT ON radacct
            FOR EACH ROW
            EXECUTE FUNCTION bind_mac_to_user();
        """)
        _logger.info("FreeRADIUS MAC Binding triggers created successfully!")
    except Exception as e:
        _logger.error("Error creating triggers: %s", str(e))

def drop_radius_triggers(env):
    try:
        cr = env.cr
        cr.execute("DROP TRIGGER IF EXISTS tr_bind_mac_on_session_start ON radacct;")
        cr.execute("DROP FUNCTION IF EXISTS bind_mac_to_user();")
        cr.execute("DROP INDEX IF EXISTS unique_calling_station_id;")
        _logger.info("FreeRADIUS MAC Binding triggers removed!")
    except Exception as e:
        _logger.error("Error dropping triggers: %s", str(e))