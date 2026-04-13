"""
GenieACS Integration - Settings Model Extension
================================================

Extends ``res.config.settings`` to store GenieACS NBI server credentials.
Adds a 'Test Connection' action button to verify connectivity.

GenieACS NBI (Northbound Interface) runs on port 7557 by default.
API Reference: https://docs.genieacs.com/en/latest/api-reference.html
"""

import logging
import requests

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    """Extends settings with GenieACS NBI connection parameters."""

    _inherit = "res.config.settings"

    genieacs_url = fields.Char(
        string="GenieACS URL",
        config_parameter="genieacs.url",
        help="Full URL of the GenieACS NBI API including port. "
             "Example: http://192.168.1.50:7557",
    )

    genieacs_username = fields.Char(
        string="GenieACS Username",
        config_parameter="genieacs.username",
        help="HTTP Basic Auth username for GenieACS NBI (optional).",
    )

    genieacs_password = fields.Char(
        string="GenieACS Password",
        config_parameter="genieacs.password",
        help="HTTP Basic Auth password for GenieACS NBI (optional).",
    )

    def action_test_genieacs_connection(self):
        """Test connectivity to the GenieACS NBI server.

        Makes a lightweight GET request to the /devices endpoint
        to verify the server is reachable and credentials are valid.

        Returns:
            dict: Odoo client action notification (success or danger).
        """
        self.ensure_one()
        url = self.genieacs_url
        if not url:
            raise ValidationError(
                _("Please enter the GenieACS URL before testing.")
            )

        url = url.rstrip("/")
        auth = (self.genieacs_username, self.genieacs_password) if self.genieacs_username else None

        try:
            _logger.info("Testing GenieACS connection to %s", url)
            # Use a simple GET /devices with a limit to minimize payload
            response = requests.get(
                f"{url}/devices/?query=%7B%7D",
                auth=auth,
                timeout=10,
            )
            response.raise_for_status()

            device_count = len(response.json()) if response.json() else 0
            message = _(
                "Connection successful! GenieACS is running at %s. "
                "Found %s device(s) in the database.",
                url, device_count,
            )
            _logger.info("GenieACS connection test passed: %s devices", device_count)

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("GenieACS Connection Test"),
                    "message": message,
                    "type": "success",
                    "sticky": False,
                    "next": {"type": "ir.actions.act_window_close"},
                },
            }

        except requests.exceptions.ConnectionError:
            message = _(
                "Cannot connect to GenieACS at %s. "
                "Please verify the server is running and the URL/port is correct.",
                url,
            )
            _logger.warning("GenieACS connection test failed: ConnectionError to %s", url)
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("GenieACS Connection Failed"),
                    "message": message,
                    "type": "danger",
                    "sticky": True,
                },
            }

        except requests.exceptions.Timeout:
            message = _(
                "Connection to GenieACS at %s timed out. "
                "The server may be overloaded or unreachable.",
                url,
            )
            _logger.warning("GenieACS connection test failed: Timeout to %s", url)
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("GenieACS Connection Timeout"),
                    "message": message,
                    "type": "danger",
                    "sticky": True,
                },
            }

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "Unknown"
            if status == 401:
                message = _(
                    "Authentication failed (HTTP 401). "
                    "Please check your GenieACS username and password."
                )
            else:
                message = _(
                    "GenieACS returned HTTP error %s. Response: %s",
                    status, str(e),
                )
            _logger.warning("GenieACS connection test failed: HTTP %s", status)
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("GenieACS Error"),
                    "message": message,
                    "type": "danger",
                    "sticky": True,
                },
            }

        except Exception as e:
            _logger.exception("Unexpected error during GenieACS connection test")
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("GenieACS Connection Failed"),
                    "message": _("Unexpected error: %s", str(e)),
                    "type": "danger",
                    "sticky": True,
                },
            }
