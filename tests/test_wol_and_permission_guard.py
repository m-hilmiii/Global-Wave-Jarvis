"""
Unit Tests for Wake-on-LAN (WOL) and 4-Level Permission Guard (Master Architecture v5.0)
"""

import unittest
from fastapi.testclient import TestClient

from core_jarvis.tools.wol_tool import wol_tool, WOLTool
from core_jarvis.permission_guard import permission_guard, PermissionLevel
from web.server import app, LOCAL_SESSION_TOKEN

class TestWOLAndPermissionGuard(unittest.TestCase):

    def test_clean_mac_valid_and_invalid(self):
        # Valid cases with colons, hyphens, lowercase
        self.assertEqual(WOLTool.clean_mac("9c:6b:00:b2:a2:0f"), "9C6B00B2A20F")
        self.assertEqual(WOLTool.clean_mac("9C-6B-00-B2-A2-0F"), "9C6B00B2A20F")
        self.assertEqual(WOLTool.clean_mac("9C6B00B2A20F"), "9C6B00B2A20F")

        # Invalid cases
        with self.assertRaises(ValueError):
            WOLTool.clean_mac("INVALID_MAC")
        with self.assertRaises(ValueError):
            WOLTool.clean_mac("00:11:22")

    def test_magic_packet_structure(self):
        mac = "9C:6B:00:B2:A2:0F"
        packet = wol_tool.create_magic_packet(mac)
        # Magic packet must be exactly 102 bytes: 6 bytes 0xFF + 16 * 6 bytes MAC
        self.assertEqual(len(packet), 102)
        self.assertTrue(packet.startswith(b"\xff" * 6))
        # Verify 16 occurrences of MAC bytes
        mac_bytes = bytes.fromhex("9C6B00B2A20F")
        self.assertEqual(packet[6:12], mac_bytes)
        self.assertEqual(packet[96:102], mac_bytes)

    def test_wol_identity_discovery(self):
        identity = wol_tool.get_host_wol_identity()
        self.assertIn("hostname", identity)
        self.assertIn("local_ip", identity)
        self.assertIn("primary_mac", identity)
        self.assertIn("bios_wol_instructions", identity)
        self.assertIn("wan_forwarding_guide", identity)
        self.assertTrue(len(identity["bios_wol_instructions"]) >= 3)

    def test_permission_level_1_auto(self):
        res = permission_guard.evaluate_action("system_telemetry", confirmed_by_user=False)
        self.assertTrue(res["allowed"])
        self.assertEqual(res["level"], PermissionLevel.LEVEL_1_AUTO)

    def test_permission_level_2_bounded(self):
        res = permission_guard.evaluate_action("generate_video", confirmed_by_user=False)
        self.assertTrue(res["allowed"])
        self.assertEqual(res["level"], PermissionLevel.LEVEL_2_BOUNDED)

    def test_permission_level_3_requires_confirmation(self):
        # Without confirmation -> Rejected
        res_unconfirmed = permission_guard.evaluate_action("git_push", confirmed_by_user=False)
        self.assertFalse(res_unconfirmed["allowed"])
        self.assertEqual(res_unconfirmed["level"], PermissionLevel.LEVEL_3_CONFIRMED)

        # With confirmation -> Allowed
        res_confirmed = permission_guard.evaluate_action("git_push", confirmed_by_user=True)
        self.assertTrue(res_confirmed["allowed"])

    def test_permission_level_4_strictly_forbidden(self):
        # Even with confirmation -> Blocked unconditionally
        res = permission_guard.evaluate_action("disable_firewall", confirmed_by_user=True)
        self.assertFalse(res["allowed"])
        self.assertEqual(res["level"], PermissionLevel.LEVEL_4_FORBIDDEN)
        self.assertIn("GÜVENLİK İHLALİ", res["reason"])

    def test_api_wol_endpoints(self):
        client = TestClient(app)
        headers = {"X-Local-Token": LOCAL_SESSION_TOKEN}

        # 1. GET /api/jarvis/wol/identity
        id_res = client.get("/api/jarvis/wol/identity", headers=headers)
        self.assertEqual(id_res.status_code, 200)
        self.assertTrue(id_res.json().get("status") == "success")
        self.assertIn("primary_mac", id_res.json()["wol_identity"])

        # 2. GET /api/jarvis/security/audit
        audit_res = client.get("/api/jarvis/security/audit", headers=headers)
        self.assertEqual(audit_res.status_code, 200)
        self.assertIn("audit_trail", audit_res.json())

if __name__ == "__main__":
    unittest.main()
