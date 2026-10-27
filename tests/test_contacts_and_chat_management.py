"""
Test Suite for Contacts Management, Address Book Import (CSV/vCard/Text), and Chat Clearing
"""

import unittest
import json
import tempfile
from pathlib import Path
try:
    from fastapi.testclient import TestClient
    from web.server import app
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    TestClient = None
    app = None

from core_jarvis.tools.contacts import ContactsManager
from core_jarvis.jarvis_brain import jarvis_brain

class TestContactsAndChatManagement(unittest.TestCase):
    def setUp(self):
        # Create a temporary contacts file for clean isolation
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_file = Path(self.temp_dir.name) / "contacts_test.json"
        initial_data = {
            "contacts": [
                {
                    "id": "c_owner",
                    "name": "Mücahit Hilmi",
                    "phone": "+905518477838",
                    "relationship": "Sistem Sahibi",
                    "notes": "Sahip"
                },
                {
                    "id": "c_test1",
                    "name": "Kemal",
                    "phone": "+905321112233",
                    "relationship": "Arkadaş",
                    "notes": "Test"
                }
            ]
        }
        with open(self.temp_file, "w", encoding="utf-8-sig") as f:
            json.dump(initial_data, f, indent=2, ensure_ascii=False)
            
        self.mgr = ContactsManager(file_path=self.temp_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_add_and_delete_contact(self):
        # 1. Add contact
        added = self.mgr.add_contact("Selim", "05441234567", relationship="İş")
        self.assertIsNotNone(added)
        self.assertEqual(added["name"], "Selim")
        self.assertEqual(added["phone"], "05441234567")

        # 2. Verify in all
        all_c = self.mgr.get_all()
        names = [c["name"] for c in all_c]
        self.assertIn("Selim", names)

        # 3. Delete contact by name
        deleted = self.mgr.delete_contact("Selim")
        self.assertIsNotNone(deleted)
        self.assertEqual(deleted["name"], "Selim")

        # 4. Verify no longer present
        all_c_after = self.mgr.get_all()
        names_after = [c["name"] for c in all_c_after]
        self.assertNotIn("Selim", names_after)

    def test_system_owner_protected_from_deletion(self):
        deleted = self.mgr.delete_contact("c_owner")
        self.assertIsNone(deleted)
        deleted_by_name = self.mgr.delete_contact("Mücahit Hilmi")
        self.assertIsNone(deleted_by_name)
        
        all_c = self.mgr.get_all()
        ids = [c["id"] for c in all_c]
        self.assertIn("c_owner", ids)

    def test_bulk_import_raw_text(self):
        text_data = """
        Barış Manço: 0532 999 88 77 (Sanatçı)
        Cem Karaca, +905421112233, Müzisyen
        """
        res = self.mgr.import_raw_text(text_data)
        self.assertGreaterEqual(res["added"], 2)
        
        found_baris = self.mgr.find_contact("Barış")
        self.assertIsNotNone(found_baris)
        self.assertIn("05329998877", found_baris["phone"])

    def test_import_google_csv(self):
        csv_data = """Name,Given Name,Family Name,Phone 1 - Type,Phone 1 - Value,Notes
Orhan Veli,Orhan,Veli,Mobile,0533 555 44 33,Şair
"""
        res = self.mgr.import_google_csv(csv_data)
        self.assertGreaterEqual(res["added"], 1)
        found = self.mgr.find_contact("Orhan Veli")
        self.assertIsNotNone(found)
        self.assertEqual(found["phone"], "05335554433")

    def test_import_vcard(self):
        vcf_data = """BEGIN:VCARD
VERSION:3.0
FN:Attila İlhan
TEL;TYPE=CELL:0542 333 22 11
NOTE:Yazar
END:VCARD
"""
        res = self.mgr.import_vcard(vcf_data)
        self.assertGreaterEqual(res["added"], 1)
        found = self.mgr.find_contact("Attila")
        self.assertIsNotNone(found)
        self.assertIn("05423332211", found["phone"])

    def test_jarvis_brain_clear_chat_command(self):
        jarvis_brain.conversation_history = [
            {"role": "user", "content": "Merhaba"},
            {"role": "assistant", "content": "Emrinizdeyim"}
        ]
        res = jarvis_brain.process_message("sohbeti temizle")
        self.assertEqual(res.get("action_taken"), "chat_cleared")
        self.assertEqual(len(jarvis_brain.conversation_history), 0)

    @unittest.skipUnless(HAS_FASTAPI, "FastAPI not installed in current test environment")
    def test_api_endpoints_contacts_and_chat_clear(self):
        from web.server import LOCAL_SESSION_TOKEN
        client = TestClient(app)
        headers = {"X-Local-Token": LOCAL_SESSION_TOKEN}
        
        # 1. POST /api/jarvis/contacts
        add_res = client.post("/api/jarvis/contacts", json={
            "name": "BirimTestKişisi",
            "phone": "05551239988",
            "relationship": "Test"
        }, headers=headers)
        self.assertEqual(add_res.status_code, 200)
        self.assertTrue(add_res.json().get("status") == "success")

        # 2. DELETE /api/jarvis/contacts/{identifier}
        del_res = client.delete("/api/jarvis/contacts/BirimTestKişisi", headers=headers)
        self.assertEqual(del_res.status_code, 200)
        self.assertEqual(del_res.json().get("status"), "success")

        # 3. POST /api/jarvis/chat/clear
        clear_res = client.post("/api/jarvis/chat/clear", headers=headers)
        self.assertEqual(clear_res.status_code, 200)
        self.assertEqual(clear_res.json().get("status"), "success")

    def test_import_google_csv_and_sqlite_sync(self):
        csv_data = """First Name,Middle Name,Last Name,Phone 1 - Value
MehmetTest,,ÖzcanTest,0532 999 88 77 ::: 0532-999-8877
ZeynepTest,,KayaTest,+90544 111 22 33
"""
        res = self.mgr.import_google_csv(csv_data)
        self.assertEqual(res["added"], 2)
        found = self.mgr.find_contact("MehmetTest")
        self.assertIsNotNone(found)
        self.assertIn("05329998877", found["phone"])

        # Verify SQLite synchronization
        from db.database import get_all_contacts_from_db
        db_contacts = get_all_contacts_from_db()
        self.assertGreaterEqual(len(db_contacts), 2)

    def test_add_contact_updates_existing_matching_phone(self):
        """Verifies adding a contact with the same phone updates in place instead of creating duplicates."""
        # Add initial raw phone contact
        c1 = self.mgr.add_contact("05334180028", "05334180028", lid="93815356534937")
        self.assertEqual(c1["name"], "05334180028")

        # Now add real named contact with same phone
        c2 = self.mgr.add_contact("Furkan Oda Yurt", "05334180028", relationship="Oda Arkadaşı")
        self.assertEqual(c2["name"], "Furkan Oda Yurt")
        self.assertEqual(c2["relationship"], "Oda Arkadaşı")
        self.assertEqual(c2["lid"], "93815356534937")

        # Total contacts with this phone must be strictly 1
        all_c = self.mgr.get_all()
        furkan_matches = [c for c in all_c if "5334180028" in c.get("phone", "")]
        self.assertEqual(len(furkan_matches), 1)
        self.assertEqual(furkan_matches[0]["name"], "Furkan Oda Yurt")

    def test_update_contact_by_identifier(self):
        """Verifies explicit contact updates by ID or phone."""
        self.mgr.add_contact("Eski İsim", "05559876543")
        updated = self.mgr.update_contact("05559876543", name="Yeni İsim", relationship="Kanka", notes="Borsa uzmanı")
        self.assertIsNotNone(updated)
        self.assertEqual(updated["name"], "Yeni İsim")
        self.assertEqual(updated["relationship"], "Kanka")
        self.assertEqual(updated["notes"], "Borsa uzmanı")

    def test_close_friend_persona_delegation(self):
        """Verifies that a close friend (e.g. Furkan) gets a casual, non-robotic, friend-tailored response."""
        res = jarvis_brain.generate_delegate_reply(
            sender_name="Furkan Oda Yurt",
            incoming_text="borsa borunu tutturdum bende alt cot ta yavaş kalıyot ama sıkış var aralığa bitirirzzz",
            chat_history=[
                {"from_me": False, "text": "borsa borunu tutturdum bende"},
                {"from_me": False, "text": "alt cot ta yavaş kalıyot"}
            ]
        )
        self.assertNotIn("Merhabalar Sayın", res)
        self.assertNotIn("ben Mücahit'in yapay zeka asistanı JARVIS", res)
        self.assertTrue(len(res) > 5)

    def test_ai_delegate_owner_intervention_detection(self):
        """Verifies that owner manual messaging cancels pending delegate auto-replies."""
        from core_jarvis.whatsapp_daemon import whatsapp_daemon
        import time

        target_key = whatsapp_daemon._get_canonical_target_key("905334180028@s.whatsapp.net", "05334180028", "Furkan")
        self.assertEqual(target_key, "5334180028")

        # Simulate owner sending a message
        whatsapp_daemon._owner_active_chats[target_key] = time.time()
        self.assertLess(time.time() - whatsapp_daemon._owner_active_chats[target_key], 2.0)


if __name__ == "__main__":
    unittest.main()
