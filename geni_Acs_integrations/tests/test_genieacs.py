"""
Test Cases for GenieACS Integration Module
==========================================

These tests use ``unittest.mock`` to simulate GenieACS API responses
without requiring a live GenieACS server. All HTTP calls are mocked.

Run tests with:
    ./odoo-bin -d <db_name> -i geni_Acs_integrations --test-enable --stop-after-init
"""

import json
from unittest.mock import patch, Mock
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestGenieACSIntegrations(TransactionCase):
    """Test suite for the GenieACS integration module."""

    def setUp(self):
        """Set up test data: config parameters, NAS, OLT, and User records."""
        super().setUp()

        # Configure GenieACS credentials
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("genieacs.url", "http://test-genieacs:7557")
        ICP.set_param("genieacs.username", "admin")
        ICP.set_param("genieacs.password", "admin123")

        # Create a network type if needed
        network_type = self.env["network.type"].search([], limit=1)
        if not network_type:
            network_type = self.env["network.type"].create({
                "type": "MikroTik",
            })

        # Create NAS
        self.nas = self.env["network.nas"].create({
            "nasname": "10.0.0.1",
            "shortname": "test_nas",
            "ports": 3799,
            "secret": "testing123",
            "type": network_type.id,
        })

        # Create OLT
        self.olt = self.env["network.olt"].create({
            "name": "Test OLT Huawei",
            "ip_address": "10.0.0.2",
            "brand": "Huawei",
            "location": "Main Datacenter",
            "nas_id": self.nas.id,
        })

        # Create a test internet user
        self.user = self.env["users"].create({
            "name": "Test PPPoE User",
            "username": "test_ppp_user",
            "password": "userpass123",
            "nas_id": self.nas.id,
        })

    # -------------------------------------------------------------------------
    # OLT ↔ NAS Relationship Tests
    # -------------------------------------------------------------------------

    def test_01_olt_creation(self):
        """Test that OLT record is created with correct fields."""
        self.assertEqual(self.olt.name, "Test OLT Huawei")
        self.assertEqual(self.olt.brand, "Huawei")
        self.assertEqual(self.olt.nas_id, self.nas)

    def test_02_olt_nas_one2many_relation(self):
        """Test that NAS correctly shows linked OLTs via One2many."""
        self.assertIn(self.olt, self.nas.olt_ids)
        self.assertEqual(len(self.nas.olt_ids), 1)

    def test_03_multiple_olts_per_nas(self):
        """Test that a NAS can have multiple OLTs."""
        olt2 = self.env["network.olt"].create({
            "name": "Test OLT ZTE",
            "brand": "ZTE",
            "nas_id": self.nas.id,
        })
        self.assertEqual(len(self.nas.olt_ids), 2)
        self.assertIn(olt2, self.nas.olt_ids)

    # -------------------------------------------------------------------------
    # GenieACS Credentials Tests
    # -------------------------------------------------------------------------

    def test_04_missing_genieacs_url_raises_error(self):
        """Test that missing GenieACS URL raises ValidationError."""
        self.env["ir.config_parameter"].sudo().set_param("genieacs.url", False)
        with self.assertRaises(ValidationError):
            self.user.action_fetch_cpe_device()

    # -------------------------------------------------------------------------
    # Fetch CPE Device Tests
    # -------------------------------------------------------------------------

    @patch("odoo.addons.geni_Acs_integrations.models.users.requests.get")
    def test_05_fetch_cpe_device_success(self, mock_get):
        """Test successfully fetching CPE device from GenieACS."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = [
            {
                "_id": "00236A-TestRouter-00001",
                "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1."
                "WANPPPConnection.1.Username": {
                    "_value": "test_ppp_user",
                },
            }
        ]
        mock_get.return_value = mock_response

        result = self.user.action_fetch_cpe_device()
        self.assertEqual(self.user.genieacs_device_id, "00236A-TestRouter-00001")
        self.assertEqual(result["params"]["type"], "success")

    @patch("odoo.addons.geni_Acs_integrations.models.users.requests.get")
    def test_06_fetch_cpe_device_not_found(self, mock_get):
        """Test that non-matching username raises ValidationError."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = [
            {
                "_id": "00236A-OtherDevice-99999",
                "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1."
                "WANPPPConnection.1.Username": {
                    "_value": "some_other_user",
                },
            }
        ]
        mock_get.return_value = mock_response

        with self.assertRaises(ValidationError):
            self.user.action_fetch_cpe_device()

    @patch("odoo.addons.geni_Acs_integrations.models.users.requests.get")
    def test_07_fetch_cpe_device_empty_response(self, mock_get):
        """Test that empty device list raises ValidationError."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        with self.assertRaises(ValidationError):
            self.user.action_fetch_cpe_device()

    # -------------------------------------------------------------------------
    # Reboot CPE Tests
    # -------------------------------------------------------------------------

    @patch("odoo.addons.geni_Acs_integrations.models.users.requests.post")
    def test_08_reboot_cpe_success(self, mock_post):
        """Test reboot task sends correct payload to GenieACS."""
        self.user.genieacs_device_id = "00236A-TestRouter-00001"

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = self.user.action_reboot_cpe()
        self.assertEqual(result["params"]["type"], "success")

        # Verify the POST call
        call_args = mock_post.call_args
        self.assertIn("tasks", call_args[0][0])
        self.assertIn("connection_request", call_args[0][0])
        self.assertEqual(call_args[1]["json"], {"name": "reboot"})

    def test_09_reboot_without_device_id_fails(self):
        """Test that reboot without device ID raises ValidationError."""
        self.user.genieacs_device_id = False
        with self.assertRaises(ValidationError):
            self.user.action_reboot_cpe()

    # -------------------------------------------------------------------------
    # Factory Reset CPE Tests
    # -------------------------------------------------------------------------

    @patch("odoo.addons.geni_Acs_integrations.models.users.requests.post")
    def test_10_factory_reset_cpe_success(self, mock_post):
        """Test factory reset sends correct payload to GenieACS."""
        self.user.genieacs_device_id = "00236A-TestRouter-00001"

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = self.user.action_factory_reset_cpe()
        self.assertEqual(result["params"]["type"], "success")
        self.assertEqual(
            mock_post.call_args[1]["json"],
            {"name": "factoryReset"},
        )

    # -------------------------------------------------------------------------
    # Push Password to CPE Tests
    # -------------------------------------------------------------------------

    @patch("odoo.addons.geni_Acs_integrations.models.users.requests.post")
    def test_11_push_password_success(self, mock_post):
        """Test pushing PPP credentials uses setParameterValues task."""
        self.user.genieacs_device_id = "00236A-TestRouter-00001"

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = self.user.action_push_password_to_cpe()
        self.assertEqual(result["params"]["type"], "success")

        # Verify the setParameterValues payload
        payload = mock_post.call_args[1]["json"]
        self.assertEqual(payload["name"], "setParameterValues")
        self.assertEqual(len(payload["parameterValues"]), 2)

        # Check username param
        username_param = payload["parameterValues"][0]
        self.assertIn("Username", username_param[0])
        self.assertEqual(username_param[1], "test_ppp_user")
        self.assertEqual(username_param[2], "xsd:string")

        # Check password param
        password_param = payload["parameterValues"][1]
        self.assertIn("Password", password_param[0])
        self.assertEqual(password_param[1], "userpass123")
        self.assertEqual(password_param[2], "xsd:string")

    def test_12_push_password_without_device_id_fails(self):
        """Test push password without device ID raises ValidationError."""
        self.user.genieacs_device_id = False
        with self.assertRaises(ValidationError):
            self.user.action_push_password_to_cpe()

    # -------------------------------------------------------------------------
    # Refresh CPE Params Tests
    # -------------------------------------------------------------------------

    @patch("odoo.addons.geni_Acs_integrations.models.users.requests.post")
    def test_13_refresh_cpe_params_success(self, mock_post):
        """Test refreshObject task sends empty objectName."""
        self.user.genieacs_device_id = "00236A-TestRouter-00001"

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = self.user.action_refresh_cpe_params()
        self.assertEqual(result["params"]["type"], "success")

        payload = mock_post.call_args[1]["json"]
        self.assertEqual(payload["name"], "refreshObject")
        self.assertEqual(payload["objectName"], "")

    # -------------------------------------------------------------------------
    # Test GenieACS Connection (Settings) Tests
    # -------------------------------------------------------------------------

    @patch("odoo.addons.geni_Acs_integrations.models.res_config_settings.requests.get")
    def test_14_test_connection_success(self, mock_get):
        """Test that Test Connection button returns success notification."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = [{"_id": "device1"}, {"_id": "device2"}]
        mock_get.return_value = mock_response

        settings = self.env["res.config.settings"].create({
            "genieacs_url": "http://test-genieacs:7557",
            "genieacs_username": "admin",
            "genieacs_password": "admin123",
        })
        result = settings.action_test_genieacs_connection()
        self.assertEqual(result["params"]["type"], "success")
        self.assertIn("successful", result["params"]["message"])

    @patch("odoo.addons.geni_Acs_integrations.models.res_config_settings.requests.get")
    def test_15_test_connection_failure(self, mock_get):
        """Test that connection failure returns danger notification."""
        import requests as req
        mock_get.side_effect = req.exceptions.ConnectionError("Connection refused")

        settings = self.env["res.config.settings"].create({
            "genieacs_url": "http://bad-server:7557",
        })
        result = settings.action_test_genieacs_connection()
        self.assertEqual(result["params"]["type"], "danger")

    # -------------------------------------------------------------------------
    # Task Queued (HTTP 202) Tests
    # -------------------------------------------------------------------------

    @patch("odoo.addons.geni_Acs_integrations.models.users.requests.post")
    def test_16_task_queued_202_response(self, mock_post):
        """Test HTTP 202 response indicates task queued for next inform."""
        self.user.genieacs_device_id = "00236A-TestRouter-00001"

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        result = self.user.action_reboot_cpe()
        self.assertEqual(result["params"]["type"], "success")
        self.assertIn("queued", result["params"]["message"])
