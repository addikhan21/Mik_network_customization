"""
GenieACS Integration - Users Model Extension
=============================================

Extends the ``users`` model with GenieACS CPE device management capabilities.

GenieACS API Reference:
    https://docs.genieacs.com/en/latest/api-reference.html

Endpoints Used:
    - GET /devices/?query=<query>
        Search for CPE devices by ConnectionRequestUsername or PPPUsername.
    - POST /devices/<device_id>/tasks?connection_request
        Enqueue a task and trigger an immediate connection request.

Task Types Used:
    - reboot: Reboots the CPE device.
    - factoryReset: Factory resets the CPE device.
    - setParameterValues: Pushes parameter changes (e.g. WiFi password)
      to the CPE device via TR-069.
    - getParameterValues: Reads parameter values from the CPE device.
    - refreshObject: Refreshes the entire device object tree.

TR-069 Parameter Paths (Huawei EG8145V5 / InternetGatewayDevice):
    These are the confirmed paths from the device's parameter tree.
    The device uses TR-098 (InternetGatewayDevice) root, NOT TR-181 (Device).

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
from datetime import datetime
from urllib.parse import quote

from markupsafe import Markup
from odoo import models, fields, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TR-069 Parameter Path Constants
# ---------------------------------------------------------------------------
# Primary paths confirmed from Huawei EG8145V5 device tree (webdownload.txt).
# Fallback paths provided for TR-181 (Device.*) based devices.

# Device identification — used for matching CPE to Odoo user
MATCH_PATHS = [
    # Primary: Huawei uses ConnectionRequestUsername as the CPE identifier
    "InternetGatewayDevice.ManagementServer.ConnectionRequestUsername",
    # Fallback: TR-098 PPPoE username
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1."
    "WANPPPConnection.1.Username",
    # Fallback: TR-098 PPPoE username on second WAN connection
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.2."
    "WANPPPConnection.1.Username",
    # Fallback: TR-181 PPP interface username
    "Device.PPP.Interface.1.Username",
]

# Credential paths — used for pushing username/password to CPE.
#
# IMPORTANT — verified against the Huawei EG8145V5 device sheet:
#   • WANConnectionDevice.1 has WANIPConnection only (IPoE, no PPP).
#   • WANConnectionDevice.2/.3 have WANPPPConnection containers but
#     they expose NO child parameters (Username/Password not present).
#   • The only writable username/password paths on this device are
#     under ManagementServer (ConnectionRequestUsername, etc.).
#
# Priority order:
#   1. ManagementServer.ConnectionRequestUsername/Password (confirmed, writable)
#   2. ManagementServer.Username/Password                 (confirmed, writable)
#   3. WANPPPConnection fallbacks for other device models
#   4. TR-181 Device.PPP fallback for newer devices

# PPPoE credential paths — ordered by most common on Huawei EG8145V5.
# WANConnectionDevice.1 is IPoE (WANIPConnection), PPPoE is on .2 or .3.
CPE_USERNAME_PATHS = [
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.2.WANPPPConnection.1.Username",
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.3.WANPPPConnection.1.Username",
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.Username",
    "Device.PPP.Interface.1.Username",
]
CPE_PASSWORD_PATHS = [
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.2.WANPPPConnection.1.Password",
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.3.WANPPPConnection.1.Password",
    "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.Password",
    "Device.PPP.Interface.1.Password",
]

# ---------------------------------------------------------------------------
# CPE Details — paths to extract for the HTML summary table.
# Organised by display section. Each entry is (label, tr069_path).
# ---------------------------------------------------------------------------
CPE_DETAIL_SECTIONS = [
    ("Device Information", [
        ("Manufacturer", "DeviceID.Manufacturer"),
        ("Product Class", "DeviceID.ProductClass"),
        ("Serial Number", "DeviceID.SerialNumber"),
        ("OUI", "DeviceID.OUI"),
        ("Hardware Version",
         "InternetGatewayDevice.DeviceInfo.HardwareVersion"),
        ("Software Version",
         "InternetGatewayDevice.DeviceInfo.SoftwareVersion"),
        ("Spec Version",
         "InternetGatewayDevice.DeviceInfo.SpecVersion"),
        ("Provisioning Code",
         "InternetGatewayDevice.DeviceInfo.ProvisioningCode"),
    ]),
    ("Management Server", [
        ("Connection Request URL",
         "InternetGatewayDevice.ManagementServer.ConnectionRequestURL"),
        ("Connection Request Username",
         "InternetGatewayDevice.ManagementServer.ConnectionRequestUsername"),
        ("Periodic Inform",
         "InternetGatewayDevice.ManagementServer.PeriodicInformEnable"),
        ("Inform Interval (s)",
         "InternetGatewayDevice.ManagementServer.PeriodicInformInterval"),
        ("Parameter Key",
         "InternetGatewayDevice.ManagementServer.ParameterKey"),
    ]),
    ("WAN Connection", [
        ("External IP Address",
         "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1."
         "WANIPConnection.1.ExternalIPAddress"),
        ("WAN MAC Address",
         "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1."
         "WANIPConnection.1.MACAddress"),
    ]),
    ("WiFi — 2.4 GHz", [
        ("SSID",
         "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.SSID"),
        ("Key / Passphrase",
         "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1."
         "KeyPassphrase"),
    ]),
    ("WiFi — 5 GHz", [
        ("SSID",
         "InternetGatewayDevice.LANDevice.1.WLANConfiguration.5.SSID"),
        ("Key / Passphrase",
         "InternetGatewayDevice.LANDevice.1.WLANConfiguration.5."
         "KeyPassphrase"),
    ]),
    ("LAN Hosts", [
        ("Host 1 — Name",
         "InternetGatewayDevice.LANDevice.1.Hosts.Host.1.HostName"),
        ("Host 1 — IP",
         "InternetGatewayDevice.LANDevice.1.Hosts.Host.1.IPAddress"),
        ("Host 1 — MAC",
         "InternetGatewayDevice.LANDevice.1.Hosts.Host.1.MACAddress"),
    ]),
]


def _extract_value(device_data, path):
    """Safely extract a parameter value from a GenieACS device dict.

    GenieACS stores parameter values in two possible formats:
        - Flat: ``{"_value": "some_value", "_type": "xsd:string", ...}``
        - Top-level key in DeviceID sub-object (plain string).

    Args:
        device_data (dict): Raw device JSON from GenieACS API.
        path (str): Dot-separated TR-069 parameter path.

    Returns:
        str: The extracted value, or empty string if not found.
    """
    node = device_data
    # Walk nested dict for dotted paths
    parts = path.split(".")
    for part in parts:
        if isinstance(node, dict):
            node = node.get(part)
        else:
            return ""
    if node is None:
        return ""
    if isinstance(node, dict):
        return str(node.get("_value", ""))
    return str(node)


def _build_cpe_html(device_data):
    """Build a styled HTML table summarising the CPE device parameters.

    The table uses the same ``table table-striped`` styling as the existing
    User Details / Service Details tables in the form view. Each logical
    section gets a coloured header row for visual separation.

    Args:
        device_data (dict): Raw device JSON returned by the GenieACS API.

    Returns:
        str: HTML string ready to be stored in an ``Html`` field.
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    rows = []
    for section_title, params in CPE_DETAIL_SECTIONS:
        # Section header row
        rows.append(
            '<tr style="background-color: #e9ecef;">'
            '<td colspan="2" style="font-weight: 700; padding: 8px 12px; '
            'color: #495057; font-size: 13px; letter-spacing: 0.5px;">'
            f'<i class="fa fa-angle-right me-1"></i> {section_title}</td>'
            "</tr>"
        )
        for label, path in params:
            value = _extract_value(device_data, path)
            display_value = value if value else (
                '<span style="color:#adb5bd; font-style:italic;">—</span>'
            )
            rows.append(
                "<tr>"
                f'<td style="padding: 6px 12px; width: 40%; color: #6c757d;'
                f' font-size: 13px;">{label}</td>'
                f'<td style="padding: 6px 12px; font-size: 13px;'
                f' font-family: monospace;">{display_value}</td>'
                "</tr>"
            )

    table_rows = "\n".join(rows)

    html = f"""
    <div style="font-family: inherit;">
        <div style="display: flex; justify-content: space-between;
                    align-items: center; margin-bottom: 8px;
                    padding: 6px 12px; background: #f0f4f8;
                    border-radius: 4px;">
            <span style="font-size: 12px; color: #6c757d;">
                <i class="fa fa-clock-o me-1"></i>
                Last Synced: <strong>{timestamp}</strong>
            </span>
        </div>
        <table class="table table-striped"
               style="margin-bottom: 0; border-collapse: collapse;
                      width: 100%;">
            <thead>
                <tr style="background-color: #17a2b8; color: #fff;">
                    <th style="padding: 8px 12px; font-size: 13px;
                               width: 40%;">Parameter</th>
                    <th style="padding: 8px 12px; font-size: 13px;">Value</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>
    """
    return html


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

    cpe_details_html = fields.Html(
        string="CPE Details",
        readonly=True,
        sanitize=False,
        help="Auto-generated summary of CPE device parameters "
             "fetched from GenieACS. Updated on 'Fetch CPE' or "
             "'Refresh CPE Details'.",
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
            dict: Response containing status code and headers for chatter logging.

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
                  "   - The ConnectionRequestUsername on the CPE matches "
                  "this user's username '%s'",
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
            status_code = response.status_code
            device_status = response.reason if response.reason else "Unknown"
            
            _logger.info(
                "GenieACS Task '%s' sent successfully for device %s (HTTP %s - %s)",
                task_name, self.genieacs_device_id, status_code, device_status,
            )

            # Return response info for chatter logging
            return {
                "status_code": status_code,
                "device_status": device_status,
                "task_name": task_name,
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

    def _fetch_device_from_genieacs(self):
        """Fetch devices from GenieACS matching this user's username.

        Queries GenieACS using ConnectionRequestUsername first, then
        falls back to a full scan with PPPoE path matching.

        Returns:
            tuple: (matched_device dict or None, total_devices int)

        Raises:
            ValidationError: On connection/API errors or no devices found.
        """
        self.ensure_one()
        url, user, pwd = self._get_genieacs_credentials()
        auth = self._get_genieacs_auth(user, pwd)

        # Query directly by ConnectionRequestUsername (most efficient)
        query = json.dumps({
            "InternetGatewayDevice.ManagementServer.ConnectionRequestUsername._value": self.username
        })
        api_url = f"{url}/devices/?query={quote(query, safe='')}"

        try:
            _logger.info("GenieACS Fetch CPE → GET %s", api_url)
            response = requests.get(api_url, auth=auth, timeout=15)
            response.raise_for_status()
            devices = response.json()

            matched_device = devices[0] if devices and isinstance(devices, list) else None

            if not matched_device:
                # Fallback: fetch all and scan PPPoE username paths
                fallback_url = f"{url}/devices/?query={quote(json.dumps({}), safe='')}"
                _logger.info("GenieACS Fetch CPE fallback → GET %s", fallback_url)
                fb_resp = requests.get(fallback_url, auth=auth, timeout=15)
                fb_resp.raise_for_status()
                all_devices = fb_resp.json() or []
                for device in all_devices:
                    for path in MATCH_PATHS:
                        val = _extract_value(device, path)
                        if val and val == self.username:
                            matched_device = device
                            break
                    if matched_device:
                        break
                return matched_device, len(all_devices)

            return matched_device, 1

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
                  "Please contact your system administrator with this "
                  "error message.",
                  str(e))
            )

    # -------------------------------------------------------------------------
    # Public Actions
    # -------------------------------------------------------------------------

    def action_fetch_cpe_device(self):
        """Fetch the CPE device from GenieACS and populate CPE details.

        Searches devices using:
            1. ConnectionRequestUsername (primary — confirmed on Huawei)
            2. WANPPPConnection.1.Username (TR-098 fallback)
            3. Device.PPP.Interface.1.Username (TR-181 fallback)

        On success, stores the device ID and builds the CPE details
        HTML summary table.
        """
        self.ensure_one()
        result = self._fetch_device_from_genieacs()
        matched_device, total_devices = result

        if matched_device:
            self.genieacs_device_id = matched_device.get("_id")
            self.cpe_details_html = _build_cpe_html(matched_device)
            _logger.info(
                "GenieACS: Matched device %s for user %s",
                self.genieacs_device_id, self.username,
            )
            self.message_post(body=Markup(
                f'<div class="alert alert-success" role="alert">'
                f'<i class="fa fa-link me-1"></i> <b>Fetch CPE</b> — Device linked successfully<br>'
                f'<b>Device ID:</b> {self.genieacs_device_id}<br>'
                f'<b>Username:</b> {self.username}<br>'
                f'<b>HTTP Status:</b> <span class="badge bg-success">200 OK</span><br>'
                f'<b>By:</b> {self.env.user.name} &nbsp; <i>{fields.Datetime.now()}</i>'
                f'</div>'
            ))
            return {"type": "ir.actions.client", "tag": "reload"}
        else:
            raise ValidationError(
                _("No CPE device found matching username '%s'.\n\n"
                  "GenieACS has %s device(s) registered, but none match "
                  "this username.\n\n"
                  "Checked TR-069 paths:\n"
                  "• ManagementServer.ConnectionRequestUsername\n"
                  "• WANPPPConnection.1.Username\n"
                  "• Device.PPP.Interface.1.Username\n\n"
                  "Possible causes:\n"
                  "• The CPE router does not have the correct username "
                  "configured\n"
                  "• The username on the CPE is different from '%s'\n"
                  "• The CPE has not sent an Inform yet\n\n"
                  "How to fix:\n"
                  "1. Login to the CPE router admin panel\n"
                  "2. Check Management Server → ConnectionRequestUsername "
                  "matches '%s'\n"
                  "3. If credentials were just changed, reboot the CPE\n"
                  "4. Wait for the next Inform (or push a Connection "
                  "Request)\n"
                  "5. Try 'Fetch CPE' again",
                  self.username, total_devices,
                  self.username, self.username)
            )

    def action_refresh_cpe_details(self):
        """Refresh the CPE details HTML by re-fetching from GenieACS.

        If the device is already linked, fetches fresh data for that
        specific device. Otherwise, performs a full search like Fetch CPE.
        """
        self.ensure_one()
        url, user, pwd = self._get_genieacs_credentials()
        auth = self._get_genieacs_auth(user, pwd)

        if self.genieacs_device_id:
            # Fetch specific device by ID
            api_url = f"{url}/devices/?query=" + quote(
                json.dumps({"_id": self.genieacs_device_id}), safe=""
            )
            try:
                _logger.info(
                    "GenieACS Refresh CPE Details → GET %s", api_url
                )
                response = requests.get(api_url, auth=auth, timeout=15)
                response.raise_for_status()
                devices = response.json()
                if devices and isinstance(devices, list) and len(devices) > 0:
                    self.cpe_details_html = _build_cpe_html(devices[0])
                    self.message_post(body=Markup(
                        f'<div class="alert alert-info" role="alert">'
                        f'<i class="fa fa-refresh me-1"></i> <b>Refresh CPE Details</b> — Details refreshed successfully<br>'
                        f'<b>Device ID:</b> {self.genieacs_device_id}<br>'
                        f'<b>HTTP Status:</b> <span class="badge bg-success">{response.status_code} {response.reason}</span><br>'
                        f'<b>By:</b> {self.env.user.name} &nbsp; <i>{fields.Datetime.now()}</i>'
                        f'</div>'
                    ))
                    return {
                        "type": "ir.actions.client",
                        "tag": "display_notification",
                        "params": {
                            "title": _("GenieACS"),
                            "message": _(
                                "CPE details refreshed successfully."
                            ),
                            "type": "success",
                            "sticky": False,
                        },
                    }
                else:
                    raise ValidationError(
                        _("Device '%s' no longer found in GenieACS.\n\n"
                          "The device may have been removed. "
                          "Try 'Fetch CPE' to re-link.",
                          self.genieacs_device_id)
                    )
            except requests.exceptions.ConnectionError:
                raise ValidationError(
                    _("Cannot connect to GenieACS at %s.", url)
                )
            except requests.exceptions.Timeout:
                raise ValidationError(
                    _("GenieACS request timed out at %s.", url)
                )
            except ValidationError:
                raise
            except Exception as e:
                _logger.exception("Error refreshing CPE details")
                raise ValidationError(
                    _("Error refreshing CPE details: %s", str(e))
                )
        else:
            # No device linked yet — do a full fetch
            return self.action_fetch_cpe_device()

    def action_reboot_cpe(self):
        result = self._post_genieacs_task({"name": "reboot"})
        status_badge = 'success' if result['status_code'] == 200 else 'warning'
        self.message_post(body=Markup(
            f'<div class="alert alert-warning" role="alert">'
            f'<i class="fa fa-power-off me-1"></i> <b>Reboot CPE</b> — Task sent via GenieACS<br>'
            f'<b>Device ID:</b> {self.genieacs_device_id}<br>'
            f'<b>HTTP Status:</b> <span class="badge bg-{status_badge}">{result["status_code"]} {result["device_status"]}</span><br>'
            f'<b>By:</b> {self.env.user.name} &nbsp; <i>{fields.Datetime.now()}</i>'
            f'</div>'
        ))
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_factory_reset_cpe(self):
        result = self._post_genieacs_task({"name": "factoryReset"})
        status_badge = 'success' if result['status_code'] == 200 else 'warning'
        self.message_post(body=Markup(
            f'<div class="alert alert-danger" role="alert">'
            f'<i class="fa fa-eraser me-1"></i> <b>Factory Reset CPE</b> — Task sent via GenieACS<br>'
            f'<b>Device ID:</b> {self.genieacs_device_id}<br>'
            f'<b>HTTP Status:</b> <span class="badge bg-{status_badge}">{result["status_code"]} {result["device_status"]}</span><br>'
            f'<b>By:</b> {self.env.user.name} &nbsp; <i>{fields.Datetime.now()}</i>'
            f'</div>'
        ))
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_push_password_to_cpe(self):
        """Push PPPoE username and password to the CPE router via GenieACS.

        First fetches current WAN parameter values to detect which
        WANConnectionDevice has an active PPPoE connection, then pushes
        credentials only to the confirmed paths.
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

        # Build parameterValues for all known PPPoE paths.
        # GenieACS will apply whichever paths exist on the device and
        # return a fault for paths that don't exist — this is expected
        # behaviour and does NOT cause the overall task to fail.
        param_values = []
        for upath, ppath in zip(CPE_USERNAME_PATHS, CPE_PASSWORD_PATHS):
            param_values.append([upath, self.username, "xsd:string"])
            param_values.append([ppath, self.password, "xsd:string"])

        _logger.info(
            "GenieACS: Pushing PPPoE credentials to CPE %s for user %s",
            self.genieacs_device_id, self.username,
        )
        result = self._post_genieacs_task({"name": "setParameterValues", "parameterValues": param_values})
        
        pwd = self.password
        half = len(pwd) // 2
        masked_pwd = '•' * half + pwd[half:]
        pushed_paths = '<br>'.join(
            f'&nbsp;&nbsp;• {u} = <code>{self.username}</code><br>'
            f'&nbsp;&nbsp;• {p} = <code>{masked_pwd}</code>'
            for u, p in zip(CPE_USERNAME_PATHS, CPE_PASSWORD_PATHS)
        )
        status_badge = 'success' if result['status_code'] == 200 else 'warning'
        self.message_post(body=Markup(
            f'<div class="alert alert-info" role="alert">'
            f'<i class="fa fa-upload me-1"></i> <b>Push Credentials</b> — Sent to CPE via GenieACS<br>'
            f'<b>Device ID:</b> {self.genieacs_device_id}<br>'
            f'<b>Username:</b> {self.username}<br>'
            f'<b>Password:</b> <code>{masked_pwd}</code><br>'
            f'<b>HTTP Status:</b> <span class="badge bg-{status_badge}">{result["status_code"]} {result["device_status"]}</span><br>'
            f'<b>Paths pushed:</b><br>{pushed_paths}<br>'
            f'<b>By:</b> {self.env.user.name} &nbsp; <i>{fields.Datetime.now()}</i>'
            f'</div>'
        ))
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_refresh_cpe_params(self):
        """Refresh all parameters from the CPE device via GenieACS.

        GenieACS Task API:
            POST /devices/<device_id>/tasks?connection_request
            Body: {"name": "refreshObject", "objectName": ""}

        An empty objectName refreshes the entire device tree.
        After the refresh task is sent, we also update the local
        CPE details HTML.
        """
        result = self._post_genieacs_task({"name": "refreshObject", "objectName": ""})
        try:
            self.action_refresh_cpe_details()
        except Exception:
            pass
        status_badge = 'success' if result['status_code'] == 200 else 'warning'
        self.message_post(body=Markup(
            f'<div class="alert alert-info" role="alert">'
            f'<i class="fa fa-sync me-1"></i> <b>Refresh CPE Params</b> — Parameters refreshed via GenieACS<br>'
            f'<b>Device ID:</b> {self.genieacs_device_id}<br>'
            f'<b>HTTP Status:</b> <span class="badge bg-{status_badge}">{result["status_code"]} {result["device_status"]}</span><br>'
            f'<b>By:</b> {self.env.user.name} &nbsp; <i>{fields.Datetime.now()}</i>'
            f'</div>'
        ))
        return {"type": "ir.actions.client", "tag": "reload"}
