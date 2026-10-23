"""
Global-Wawe / Stark-Core - Contacts Management Tool
Enables Jarvis to find contacts by name, full name, nickname, or relationship.
"""

import re
import logging
logger = logging.getLogger('Jarvis.Contacts')
import json
from pathlib import Path
from typing import Optional, List, Dict

CONTACTS_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "contacts.json"

class ContactsManager:
    def __init__(self, file_path: Path = CONTACTS_FILE):
        self.file_path = file_path
        self._ensure_file()

    def _ensure_file(self):
        if not self.file_path.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            example_file = self.file_path.parent / "contacts.example.json"
            if example_file.exists():
                import shutil
                shutil.copy(example_file, self.file_path)
            else:
                with open(self.file_path, "w", encoding="utf-8-sig") as f:
                    json.dump({"contacts": []}, f, indent=2, ensure_ascii=False)

    def get_all(self) -> List[Dict]:
        try:
            with open(self.file_path, "r", encoding="utf-8-sig") as f:
                return json.load(f).get("contacts", [])
        except Exception:
            return []

    def find_contact(self, name_query: str) -> Optional[Dict]:
        """Fuzzy-matches a name against contacts bidirectionally, by relationship, full name, and tokens."""
        if not name_query:
            return None
        q = name_query.lower().strip()
        # Strip Turkish suffixes like 'a, 'e, 'ın, 'in, 'ye, 'ya, 'a, kişisine, adlı
        q_clean = re.sub(r"['’][a-zA-ZçğıöşüÇĞİÖŞÜ]+", "", q).strip()
        q_clean = re.sub(r"\b(kişisine|adlı\s+kişiye|kişi|adlı|adındaki|adında|numarasına)\b", "", q_clean).strip()
        
        all_c = self.get_all()

        # 0. Self references (Mücahit Hilmi)
        if any(term in q_clean for term in ["kendim", "kendi", "bana", "benim", "mücahit", "hilmi", "patron"]):
            for c in all_c:
                c_name = c.get("name", "").lower()
                if "mücahit" in c_name or "hilmi" in c_name:
                    return c

        # 1. Family Relationship Match (Babam, Annem, Kardeşim vb.)
        if any(term in q_clean for term in ["baba", "babam", "babama", "peder", "yaşar", "yasar"]):
            for c in all_c:
                if c.get("name", "").lower() == "babam" or c.get("relationship", "").lower() == "baba" or "yaşar" in c.get("full_name", "").lower():
                    return c

        if any(term in q_clean for term in ["anne", "annem", "anneme", "valide"]):
            for c in all_c:
                if c.get("name", "").lower() == "annem" or c.get("relationship", "").lower() == "anne":
                    return c

        # 2. Check for exact matches first (unambiguous)
        exact_matches = []
        for c in all_c:
            c_name = c.get("name", "").lower().strip()
            c_full = c.get("full_name", "").lower().strip()
            if q_clean == c_name or q_clean == c_full:
                exact_matches.append(c)
        if len(exact_matches) == 1:
            return exact_matches[0]

        # 3. Bidirectional substring match with ambiguity protection
        sub_matches = []
        for c in all_c:
            c_name = c.get("name", "").lower().strip()
            c_full = c.get("full_name", "").lower().strip()
            if (c_name and q_clean in c_name) or (c_full and q_clean in c_full):
                if c not in sub_matches:
                    sub_matches.append(c)
        if len(sub_matches) == 1:
            return sub_matches[0]
        elif len(sub_matches) > 1:
            # Multiple distinct contacts match the partial query -> prevent incorrect dispatch
            logger.warning(f"[Contacts] Ambiguous query '{name_query}' matched {len(sub_matches)} contacts: {[c.get('name') for c in sub_matches]}")
            return None

        # 4. Token overlap with stopword removal
        q_tokens = set(re.findall(r'\w+', q_clean))
        token_matches = []
        for c in all_c:
            c_tokens = set(re.findall(r'\w+', c.get("name", "").lower())) | set(re.findall(r'\w+', c.get("full_name", "").lower()))
            shared = (q_tokens & c_tokens) - {"bey", "hanım", "hanim", "whatsapp", "wp", "adlı", "kişi", "kişisine"}
            if shared and c not in token_matches:
                token_matches.append(c)
                
        if len(token_matches) == 1:
            return token_matches[0]
        elif len(token_matches) > 1:
            logger.warning(f"[Contacts] Ambiguous token query '{name_query}' matched {len(token_matches)} contacts.")
            return None

        return None

    def add_contact(self, name: str, phone: str, relationship: str = "", notes: str = "", full_name: str = "", lid: str = "") -> Dict:
        clean_phone = "".join([c for c in phone if c.isdigit() or c == "+"])
        clean_name = name.strip()
        contacts = self.get_all()
        
        # Check if existing contact matches name -> Update
        for c in contacts:
            if c["name"].lower() == clean_name.lower():
                c["name"] = clean_name
                c["phone"] = clean_phone
                if relationship:
                    c["relationship"] = relationship
                if notes:
                    c["notes"] = notes
                if full_name:
                    c["full_name"] = full_name
                if lid:
                    c["lid"] = lid
                with open(self.file_path, "w", encoding="utf-8-sig") as f:
                    json.dump({"contacts": contacts}, f, indent=2, ensure_ascii=False)
                return c

        new_c = {
            "id": f"c_{len(contacts) + 1}",
            "name": clean_name,
            "phone": clean_phone,
            "relationship": relationship,
            "notes": notes,
            "full_name": full_name or clean_name,
            "lid": lid
        }
        contacts.append(new_c)
        with open(self.file_path, "w", encoding="utf-8-sig") as f:
            json.dump({"contacts": contacts}, f, indent=2, ensure_ascii=False)
        return new_c

contacts_mgr = ContactsManager()
