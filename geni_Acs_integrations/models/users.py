"""
GenieACS Integration - Users Model Extension
=============================================

Extends the ``users`` model with GenieACS CPE device management capabilities.

GenieACS API Reference:
    https://docs.genieacs.com/en/latest/api-reference.html

Endpoints Used:
    - GET /devices/?query=<query>
        Search for CPE devices by PPPUsername.
    - POST /devices/<device_id>/tasks?connection_request
        Enqueue a task and trigger an immediate connection request.

Task Types Used:
    - reboot: Reboots the CPE device.
    - factoryReset: Factory resets the CPE device.
    - setParameterValues: Pushes parameter changes (e.g. WiFi password)
      to the CPE device via TR-069.
    - getParameterValues: Reads parameter values from the CPE device.
    - refreshObject: Refreshes the entire device object tree.

Important Notes:
    - The ``connection_request`` query parameter triggers immediate execution
      of the task. Without it, the task is queued until the next inform.
    - Device IDs in URLs must be percent-encoded (special characters like
      colons and slashes).
    - The GenieACS NBI default port is 7557.
"""

import json
import logging
import requests
from urllib.parse import quote

from odoo import models, fields, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class Users(models.Model):
    """Extends the users model with GenieACS CPE device management.

    Adds the ability to link an internet user to their CPE device
    in GenieACS, and perform remote management actions such as
    rebooting, factory resetting, and pushing configuration changes.
    """

    _inherit = "users"

    genieacs_device_id = fields.Char(
        string="GenieACS Device ID",
        help="The unique device identifier (_id) in GenieACS. "
             "Auto-populated by the 'Fetch CPE' action.",
    )

    # -------------------------------------------------------------------------
    # Private Helpers
    # -------------------------------------------------------------------------

    def _get_genieacs_credentials(self):
        """Retrieve GenieACS connection credentials from system parameters.

        Returns:
            tuple: (url, username, password) for the GenieACS NBI server.

        Raises:
            ValidationError: If the GenieACS URL is not configured.
        """
        ICP = self.env["ir.config_parameter"].sudo()
        url = ICP.get_param("genieacs.url")
        user = ICP.get_param("genieacs.username")
        pwd = ICP.get_param("genieacs.password")
        if not url:
            raise ValidationError(
                _("GenieACS URL is not configured.\n\n"
                  "How to fix:\n"
                  "1. Go to Network → Configurations → Settings\n"
                  "2. Scroll to 'GenieACS TR-069 Service' section\n"
                  "3. Enter your GenieACS NBI URL (e.g. http://192.168.1.50:7557)\n"
                  "4. Save the settings\n"
                  "5. Click 'Test GenieACS Connection' to verify")
            )
        return url.rstrip("/"), user, pwd

    def _get_genieacs_auth(self, user, pwd):
        """Build auth tuple for requests library.

        Args:
            user: GenieACS username (can be falsy).
            pwd: GenieACS password.

        Returns:
            tuple or None: Basic auth credentials or None if no username.
        """
        return (user, pwd) if user else None

    def _post_genieacs_task(self, task_payload, connection_request=True):
        """Post a task to GenieACS for this user's CPE device.

        This is the core method that sends task requests to the GenieACS
        NBI API endpoint:
            POST /devices/<device_id>/tasks?connection_request

        Args:
            task_payload (dict): The task JSON body. Must contain a ``name``
                key. See https://docs.genieacs.com/en/latest/api-reference.html#tasks
            connection_request (bool): If True, appends ``connection_request``
                query parameter to trigger immediate execution. If False,
                the task is queued until the device's next inform.

        Returns:
            dict: Odoo client action notification on success.

        Raises:
            ValidationError: If the device ID is not set or the API call fails.
        """
        self.ensure_one()
        if not self.genieacs_device_id:
            raise ValidationError(
                _("No CPE device linked to this user.\n\n"
                  "How to fix:\n"
                  "1. Click the 'Fetch CPE' button first to search GenieACS\n"
                  "2. If Fetch CPE also fails, verify:\n"
                  "   - The customer's CPE/ONT has ACS URL configured\n"
                  "   - The CPE has sent at least one Inform to GenieACS\n"
                  "   - The PPPoE username on the CPE matches this user's username '%s'",
                  self.username)
            )

        url, user, pwd = self._get_genieacs_credentials()
        # Percent-encode the device ID as per GenieACS docs
        encoded_id = quote(self.genieacs_device_id, safe="")
        api_url = f"{url}/devices/{encoded_id}/tasks"
        if connection_request:
            api_url += "?connection_request"

        auth = self._get_genieacs_auth(user, pwd)

        try:
            _logger.info(
                "GenieACS Task → POST %s | Payload: %s",
                api_url, json.dumps(task_payload),
            )
            response = requests.post(
                api_url, json=task_payload, auth=auth, timeout=15,
            )
            response.raise_for_status()

            task_name = task_payload.get("name", "unknown")
            _logger.info(
                "GenieACS Task '%s' sent successfully for device %s (HTTP %s)",
                task_name, self.genieacs_device_id, response.status_code,
            )

            # 200 = executed immediately, 202 = queued for next inform
            if response.status_code == 202:
                msg = _(
                    "Task '%s' has been queued. It will execute "
                    "when the CPE device contacts the ACS next.",
                    task_name,
                )
            else:
                msg = _(
                    "Task '%s' executed successfully on device %s.",
                    task_name, self.genieacs_device_id,
                )

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("GenieACS"),
                    "message": msg,
                    "type": "success",
                    "sticky": False,
                },
            }
        except requests.exceptions.ConnectionError:
            raise ValidationError(
                _("Cannot connect to GenieACS at %s.\n\n"
                  "Possible causes:\n"
                  "• GenieACS NBI service (genieacs-nbi) is not running\n"
                  "• Wrong URL or port configured (default NBI port is 7557)\n"
                  "• Firewall is blocking the connection\n\n"
                  "How to fix:\n"
                  "1. SSH into the GenieACS server\n"
                  "2. Run: sudo systemctl status genieacs-nbi\n"
                  "3. If stopped, run: sudo systemctl start genieacs-nbi\n"
                  "4. Verify port 7557 is open: curl http://localhost:7557/devices",
                  url)
            )
        except requests.exceptions.Timeout:
            raise ValidationError(
                _("GenieACS request timed out at %s.\n\n"
                  "Possible causes:\n"
                  "• GenieACS server is overloaded\n"
                  "• Network latency between Odoo and GenieACS is too high\n"
                  "• The CPE device is not responding to the connection request\n\n"
                  "How to fix:\n"
                  "1. Try again in a few seconds\n"
                  "2. Check GenieACS server load and MongoDB status\n"
                  "3. Go to Settings → Test GenieACS Connection to verify connectivity",
                  url)
            )
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else 'Unknown'
            if status == 401:
                msg = _("GenieACS authentication failed (HTTP 401).\n\n"
                        "How to fix:\n"
                        "1. Go to Network → Settings → GenieACS API Configuration\n"
                        "2. Verify the username and password are correct\n"
                        "3. Save and try again")
            elif status == 404:
                msg = _("Device not found in GenieACS (HTTP 404).\n\n"
                        "The device ID '%s' does not exist in GenieACS anymore.\n\n"
                        "How to fix:\n"
                        "1. The CPE may have been deleted from GenieACS\n"
                        "2. Click 'Fetch CPE' to re-link the device\n"
                        "3. Power-cycle the CPE to trigger a new Inform",
                        self.genieacs_device_id)
            else:
                msg = _("GenieACS returned HTTP error %s: %s", status, str(e))
            raise ValidationError(msg)
        except Exception as e:
            _logger.exception("Unexpected GenieACS error")
            raise ValidationError(
                _("Unexpected error communicating with GenieACS: %s", str(e))
            )

    # -------------------------------------------------------------------------
    # Public Actions
    # -------------------------------------------------------------------------

    def action_fetch_cpe_device(self):
        """Fetch the CPE device ID from GenieACS by matching PPPUsername.

        Makes a GET request to:
            GET /devices/?query={"_deviceId._ProductClass":"..."}

        The query searches for devices whose InternetGatewayDevice
        PPP username matches this user's username.
        """
        self.ensure_one()
        url, user, pwd = self._get_genieacs_credentials()
        auth = self._get_genieacs_auth(user, pwd)

        # Build the search query - common TR-069 parameter paths for PPP username
        query = json.dumps({"_id": {"$regex": ".*"}})
        api_url = f"{url}/devices/?query={query}"

        try:
            _logger.info("GenieACS Fetch CPE → GET %s", api_url)
            response = requests.get(api_url, auth=auth, timeout=15)
            response.raise_for_status()
            devices = response.json()

            if not devices or not isinstance(devices, list):
                raise ValidationError(
                    _("No devices found in GenieACS database.\n\n"
                      "This means no CPE/ONT device has ever contacted the GenieACS server.\n\n"
                      "How to fix:\n"
                      "1. Configure ACS URL on the CPE router:\n"
                      "   ACS URL = http://<genieacs-server-ip>:7547\n"
                      "2. Set Periodic Inform to 'Enabled' with interval 300 seconds\n"
                      "3. Reboot the CPE router\n"
                      "4. Wait 1-2 minutes for the first Inform to arrive\n"
                      "5. Verify in GenieACS UI that the device appears\n"
                      "6. Then try 'Fetch CPE' again")
                )

            # Search through devices for matching PPP username
            matched_device = None
            for device in devices:
                # Check common TR-069 PPP username parameter paths
                ppp_paths = [
                    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1."
                    "WANPPPConnection.1.Username",
                    "Device.PPP.Interface.1.Username",
                ]
                for path in ppp_paths:
                    param_data = device.get(path)
                    if isinstance(param_data, dict):
                        val = param_data.get("_value", "")
                    else:
                        val = param_data or ""
                    if val == self.username:
                        matched_device = device
                        break
                if matched_device:
                    break

            if matched_device:
                self.genieacs_device_id = matched_device.get("_id")
                _logger.info(
                    "GenieACS: Matched device %s for user %s",
                    self.genieacs_device_id, self.username,
                )
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("GenieACS"),
                        "message": _(
                            "Device '%s' found and linked successfully.",
                            self.genieacs_device_id,
                        ),
                        "type": "success",
                        "sticky": False,
                    },
                }
            else:
                raise ValidationError(
                    _("No CPE device found matching PPP username '%s'.\n\n"
                      "GenieACS has %s device(s) registered, but none match this username.\n\n"
                      "Possible causes:\n"
                      "• The CPE router does not have PPPoE credentials configured yet\n"
                      "• The PPPoE username on the CPE is different from '%s'\n"
                      "• The CPE is using a different WAN connection type (DHCP/Static)\n\n"
                      "How to fix:\n"
                      "1. Login to the CPE router admin panel\n"
                      "2. Check WAN settings → PPPoE username matches exactly '%s'\n"
                      "3. If credentials were just changed, reboot the CPE\n"
                      "4. Wait for the next Inform (or push a Connection Request)\n"
                      "5. Try 'Fetch CPE' again",
                      self.username, len(devices), self.username, self.username)
                )

        except requests.exceptions.ConnectionError:
            raise ValidationError(
                _("Cannot connect to GenieACS at %s.\n\n"
                  "How to fix:\n"
                  "1. Verify GenieACS NBI service is running (port 7557)\n"
                  "2. Check: sudo systemctl status genieacs-nbi\n"
                  "3. Check firewall is not blocking port 7557\n"
                  "4. Go to Settings → Test GenieACS Connection to diagnose",
                  url)
            )
        except requests.exceptions.Timeout:
            raise ValidationError(
                _("GenieACS at %s did not respond in time.\n\n"
                  "How to fix:\n"
                  "1. Check server load and MongoDB status\n"
                  "2. Try again in a few seconds\n"
                  "3. If persistent, increase timeout or check network routing",
                  url)
            )
        except ValidationError:
            raise
        except Exception as e:
            _logger.exception("Unexpected GenieACS error during CPE fetch")
            raise ValidationError(
                _("Unexpected error during CPE fetch: %s\n\n"
                  "Please contact your system administrator with this error message.",
                  str(e))
            )

    def action_reboot_cpe(self):
        """Reboot the CPE device via GenieACS.

        GenieACS Task API:
            POST /devices/<device_id>/tasks?connection_request
            Body: {"name": "reboot"}
        """
        return self._post_genieacs_task({"name": "reboot"})

    def action_factory_reset_cpe(self):
        """Factory reset the CPE device via GenieACS.

        GenieACS Task API:
            POST /devices/<device_id>/tasks?connection_request
            Body: {"name": "factoryReset"}
        """
        return self._post_genieacs_task({"name": "factoryReset"})

    def action_push_password_to_cpe(self):
        """Push the current PPPoE password to the CPE router via GenieACS.

        Uses the ``setParameterValues`` task to update the PPP password
        on the customer's router/ONT device.

        GenieACS Task API:
            POST /devices/<device_id>/tasks?connection_request
            Body: {
                "name": "setParameterValues",
                "parameterValues": [
                    ["InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.
                      WANPPPConnection.1.Password", "new_password", "xsd:string"]
                ]
            }

        Note:
            The TR-069 parameter path for PPP password varies by device
            manufacturer. The two most common paths are:
            - InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.
              WANPPPConnection.1.Password (TR-098 / older devices)
            - Device.PPP.Interface.1.Password (TR-181 / newer devices)
        """
        self.ensure_one()
        if not self.password:
            raise ValidationError(
                _("User password is empty. Cannot push to CPE.\n\n"
                  "How to fix:\n"
                  "1. Edit this user's password field first\n"
                  "2. Save the record\n"
                  "3. Then click 'Push Credentials' again")
            )

        # TR-098 path (most common for ISP ONT/CPE devices)
        ppp_password_path = (
            "InternetGatewayDevice.WANDevice.1."
            "WANConnectionDevice.1.WANPPPConnection.1.Password"
        )
        ppp_username_path = (
            "InternetGatewayDevice.WANDevice.1."
            "WANConnectionDevice.1.WANPPPConnection.1.Username"
        )

        task_payload = {
            "name": "setParameterValues",
            "parameterValues": [
                [ppp_username_path, self.username, "xsd:string"],
                [ppp_password_path, self.password, "xsd:string"],
            ],
        }

        _logger.info(
            "GenieACS: Pushing PPP credentials to CPE %s for user %s",
            self.genieacs_device_id, self.username,
        )
        return self._post_genieacs_task(task_payload)

    def action_refresh_cpe_params(self):
        """Refresh all parameters from the CPE device via GenieACS.

        GenieACS Task API:
            POST /devices/<device_id>/tasks?connection_request
            Body: {"name": "refreshObject", "objectName": ""}

        An empty objectName refreshes the entire device tree.
        """
        return self._post_genieacs_task({
            "name": "refreshObject",
            "objectName": "",
        })
