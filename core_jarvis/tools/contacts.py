"""
Global-Wawe / Stark-Core - Contacts Management Tool
Enables Jarvis to find, add, delete, and import contacts (Google CSV, vCard, raw text, and People API).
"""

import re
import csv
import io
import json
import logging
import quopri
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger('Jarvis.Contacts')

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
                with open(self.file_path, "w", encoding="utf-8") as f:
                    json.dump({"contacts": []}, f, indent=2, ensure_ascii=False)

    def get_all(self) -> List[Dict]:
        try:
            with open(self.file_path, "r", encoding="utf-8-sig") as f:
                return json.load(f).get("contacts", [])
        except Exception:
            return []

    def _save_all(self, contacts: List[Dict]):
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = self.file_path.with_suffix(".tmp")
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump({"contacts": contacts}, f, indent=2, ensure_ascii=False)
        tmp_file.replace(self.file_path)
        try:
            from db.database import sync_contacts_to_db
            sync_contacts_to_db(contacts)
        except Exception as e:
            logger.debug(f"[Contacts] SQLite sync skipped or error: {e}")

    def find_contact(self, name_query: str) -> Optional[Dict]:
        """Fuzzy-matches a name against contacts bidirectionally, by relationship, full name, and tokens."""
        if not name_query:
            return None
        q = name_query.lower().strip()
        # Strip Turkish suffixes like 'a, 'e, 'ın, 'in, 'ye, 'ya, 'a, kişisine, adlı
        q_clean = re.sub(r"['’][a-zA-ZçğıöşüÇĞİÖŞÜ]+", "", q).strip()
        q_clean = re.sub(r"\b(kişisine|adlı\s+kişiye|kişi|adlı|adındaki|adında|numarasına)\b", "", q_clean).strip()
        q_digits = "".join(ch for ch in q if ch.isdigit())

        all_c = self.get_all()

        # 0. Exact ID, Exact Name/Full Name, Exact LID, or Exact 10-digit Phone Match FIRST (unambiguous)
        exact_matches = []
        for c in all_c:
            c_id = str(c.get("id", "")).lower().strip()
            c_name = c.get("name", "").lower().strip()
            c_full = c.get("full_name", "").lower().strip()
            c_lid = str(c.get("lid", "")).strip()
            if q == c_id or q_clean == c_name or q_clean == c_full or (c_lid and len(c_lid) >= 8 and (q == c_lid or q.split("@")[0] == c_lid)):
                exact_matches.append(c)
                continue
            if len(q_digits) >= 10:
                c_phones = [c.get("phone", "")] + list(c.get("alt_phones", []) or [])
                for cp in c_phones:
                    cp_digits = "".join(ch for ch in str(cp) if ch.isdigit())
                    if len(cp_digits) >= 10 and cp_digits[-10:] == q_digits[-10:] and not cp_digits.startswith("9696"):
                        exact_matches.append(c)
                        break
        if len(exact_matches) == 1:
            return exact_matches[0]
        elif len(exact_matches) > 1:
            for em in exact_matches:
                if em.get("id") in ("c_owner", "c_annem", "c_babam"):
                    return em
            return exact_matches[0]

        q_words = set(re.findall(r"[a-zA-ZçğıöşüÇĞİÖŞÜ0-9]+", q_clean))

        # 1. Self references (Mücahit Hilmi) — strict word match
        if q_words & {"kendim", "kendime", "kendi", "bana", "mücahit", "mucahit", "hilmi", "patron"}:
            for c in all_c:
                c_name = c.get("name", "").lower()
                if "mücahit" in c_name or "hilmi" in c_name:
                    return c

        # 2. Family Relationship Match (Babam, Annem, Abim vb.) — strict word match
        if q_words & {"baba", "babam", "babama", "babamın", "babamin", "babamdan", "babayla", "peder", "yaşar", "yasar"}:
            for c in all_c:
                if c.get("name", "").lower() == "babam" or c.get("relationship", "").lower() == "baba" or "yaşar ünal" in c.get("full_name", "").lower():
                    return c

        if q_words & {"anne", "annem", "anneme", "annemin", "annemden", "annemle", "anneyle", "valide", "gülhan", "gulhan"}:
            for c in all_c:
                if c.get("name", "").lower() == "annem" or c.get("relationship", "").lower() == "anne" or "gülhan ünal" in c.get("full_name", "").lower():
                    return c

        if q_words & {"abi", "abim", "abime", "abimin", "abimden", "abimle"}:
            for c in all_c:
                if c.get("name", "").lower() == "abim":
                    return c

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

    def find_contacts_candidates(self, name_query: str) -> List[Dict]:
        """Returns all matching candidate contacts for an ambiguous query so Jarvis can ask for clarification."""
        if not name_query:
            return []
        q = name_query.lower().strip()
        q_clean = re.sub(r"['’][a-zA-ZçğıöşüÇĞİÖŞÜ]+", "", q).strip()
        q_clean = re.sub(r"\b(kişisine|adlı\s+kişiye|kişi|adlı|adındaki|adında|numarasına)\b", "", q_clean).strip()
        
        all_c = self.get_all()
        candidates = []
        for c in all_c:
            c_name = c.get("name", "").lower().strip()
            c_full = c.get("full_name", "").lower().strip()
            if (c_name and q_clean in c_name) or (c_full and q_clean in c_full):
                if c not in candidates:
                    candidates.append(c)
        return candidates

    def add_contact(self, name: str, phone: str, relationship: str = "", notes: str = "", full_name: str = "", lid: str = "") -> Dict:
        clean_phone = "".join([c for c in phone if c.isdigit() or c == "+"])
        clean_name = name.strip()
        contacts = self.get_all()
        
        # Digits extraction for phone matching
        p_digits = "".join([c for c in clean_phone if c.isdigit()])
        p_last10 = p_digits[-10:] if len(p_digits) >= 10 else p_digits

        # Check if existing contact matches name OR phone (last 10 digits) -> Update
        for c in contacts:
            c_name = (c.get("name") or "").strip()
            c_full = (c.get("full_name") or "").strip()
            c_phones = [c.get("phone", "")] + list(c.get("alt_phones", []) or [])
            
            match_name = bool(clean_name and (c_name.lower() == clean_name.lower() or c_full.lower() == clean_name.lower()))
            match_phone = False
            if p_last10 and len(p_last10) >= 10:
                for cp in c_phones:
                    cp_digits = "".join([x for x in str(cp) if x.isdigit()])
                    if cp_digits and len(cp_digits) >= 10 and cp_digits[-10:] == p_last10:
                        match_phone = True
                        break

            if match_name or match_phone:
                c["name"] = clean_name
                c["phone"] = clean_phone
                if relationship:
                    c["relationship"] = relationship
                if notes:
                    c["notes"] = notes
                if full_name:
                    c["full_name"] = full_name
                elif not c.get("full_name") or c.get("full_name") == c_name or c.get("full_name") == c.get("phone"):
                    c["full_name"] = clean_name
                if lid:
                    c["lid"] = lid
                self._save_all(contacts)
                return c

        existing_ids = {c.get("id") for c in contacts}
        next_num = len(contacts) + 1
        new_id = f"c_{next_num}"
        while new_id in existing_ids:
            next_num += 1
            new_id = f"c_{next_num}"

        new_c = {
            "id": new_id,
            "name": clean_name,
            "phone": clean_phone,
            "relationship": relationship,
            "notes": notes,
            "full_name": full_name or clean_name,
            "lid": lid
        }
        contacts.append(new_c)
        self._save_all(contacts)
        return new_c

    def update_contact(self, identifier: str, name: Optional[str] = None, phone: Optional[str] = None, relationship: Optional[str] = None, notes: Optional[str] = None, full_name: Optional[str] = None, lid: Optional[str] = None) -> Optional[Dict]:
        """Updates an existing contact by id, phone, or name."""
        contacts = self.get_all()
        target = None
        target_idx = None
        ident_clean = str(identifier).strip().lower()
        ident_digits = "".join([x for x in ident_clean if x.isdigit()])
        ident_last10 = ident_digits[-10:] if len(ident_digits) >= 10 else ""

        for idx, c in enumerate(contacts):
            c_id = str(c.get("id", "")).lower()
            c_name = str(c.get("name", "")).lower()
            c_full = str(c.get("full_name", "")).lower()
            c_phones = [str(c.get("phone", ""))] + [str(ap) for ap in c.get("alt_phones", []) or []]
            c_p10s = ["".join([x for x in cp if x.isdigit()])[-10:] for cp in c_phones if len("".join([x for x in cp if x.isdigit()])) >= 10]

            if c_id == ident_clean or c_name == ident_clean or c_full == ident_clean or (ident_last10 and ident_last10 in c_p10s):
                target = c
                target_idx = idx
                break

        if not target:
            return None

        if name is not None and name.strip():
            target["name"] = name.strip()
        if phone is not None and phone.strip():
            target["phone"] = "".join([c for c in phone if c.isdigit() or c == "+"])
        if relationship is not None:
            target["relationship"] = relationship.strip()
        if notes is not None:
            target["notes"] = notes.strip()
        if full_name is not None and full_name.strip():
            target["full_name"] = full_name.strip()
        if lid is not None and lid.strip():
            target["lid"] = lid.strip()

        contacts[target_idx] = target
        self._save_all(contacts)
        return target

    def delete_contact(self, identifier: str) -> Optional[Dict]:
        """Deletes a contact by id, exact name, phone number, or fuzzy query (protecting c_owner)."""
        if not identifier:
            return None
        ident_clean = str(identifier).strip()
        contacts = self.get_all()

        target_idx = None
        for i, c in enumerate(contacts):
            # Guard against deleting system owner
            if c.get("id") == "c_owner" and (ident_clean == "c_owner" or ident_clean.lower() in ["mücahit hilmi", "mucahit hilmi"]):
                logger.warning("[Contacts] Attempted to delete system owner 'c_owner' - blocked.")
                return None

            # 1. Match by ID
            if c.get("id") == ident_clean:
                target_idx = i
                break

            # 2. Match by exact phone
            clean_input_phone = "".join([x for x in ident_clean if x.isdigit() or x == "+"])
            clean_c_phone = "".join([x for x in str(c.get("phone", "")) if x.isdigit() or x == "+"])
            if clean_input_phone and clean_input_phone == clean_c_phone:
                target_idx = i
                break

            # 3. Match by name or full_name
            if c.get("name", "").lower() == ident_clean.lower() or c.get("full_name", "").lower() == ident_clean.lower():
                target_idx = i
                break

        # 4. If not found, try fuzzy find
        if target_idx is None:
            found = self.find_contact(ident_clean)
            if found and found.get("id") != "c_owner":
                for i, c in enumerate(contacts):
                    if c.get("id") == found.get("id"):
                        target_idx = i
                        break

        if target_idx is not None:
            deleted = contacts.pop(target_idx)
            self._save_all(contacts)
            logger.info(f"[Contacts] Successfully deleted contact: {deleted.get('name')} ({deleted.get('phone')})")
            return deleted

        return None

    def delete_all_contacts(self, keep_owner: bool = True) -> int:
        """Deletes all contacts except c_owner."""
        contacts = self.get_all()
        if keep_owner:
            owner_list = [c for c in contacts if c.get("id") == "c_owner"]
            count = len(contacts) - len(owner_list)
            self._save_all(owner_list)
            return count
        else:
            count = len(contacts)
            self._save_all([])
            return count

    def bulk_import(self, contacts_list: List[Dict]) -> Dict[str, Any]:
        """Imports a list of contact dicts, adding new and updating existing in a single atomic batch."""
        contacts = self.get_all()
        added = 0
        updated = 0

        def norm_key(p: str) -> str:
            d = "".join([c for c in p if c.isdigit()])
            if d.startswith("90") and len(d) == 12:
                return d[2:]
            if d.startswith("0") and len(d) == 11:
                return d[1:]
            return d

        # Build lookup indices for fast O(1) matching
        name_map = {c.get("name", "").lower(): c for c in contacts if c.get("name") and c.get("name").lower() not in ["kişi", "kisi", "bilinmeyen numara", ""]}
        phone_map = {norm_key(c.get("phone", "")): c for c in contacts if norm_key(c.get("phone", ""))}

        for item in contacts_list:
            name = item.get("name") or item.get("full_name") or ""
            phone = item.get("phone") or ""
            clean_name = name.strip()
            clean_phone = "".join([c for c in phone if c.isdigit() or c == "+"])
            if not clean_name or not clean_phone:
                continue

            n_key = norm_key(clean_phone)
            existing_by_name = name_map.get(clean_name.lower()) if clean_name.lower() not in ["kişi", "kisi", "bilinmeyen numara", ""] else None
            existing_by_phone = phone_map.get(n_key) if n_key else None

            existing = None
            if existing_by_name:
                existing = existing_by_name
            elif existing_by_phone and existing_by_phone.get("name", "").lower() in ["kişi", "kisi", "bilinmeyen numara", "", clean_name.lower()]:
                existing = existing_by_phone

            if existing:
                if existing.get("id") != "c_owner":
                    existing["phone"] = clean_phone
                if existing.get("id") not in ["c_owner", "c_annem", "c_babam"]:
                    existing["name"] = clean_name
                    if item.get("relationship"):
                        existing["relationship"] = item["relationship"]
                    if item.get("full_name"):
                        existing["full_name"] = item["full_name"]
                if item.get("alt_phones"):
                    cur_alts = list(existing.get("alt_phones", []) or [])
                    for ap in item["alt_phones"]:
                        if ap and ap not in cur_alts and ap != existing.get("phone"):
                            cur_alts.append(ap)
                    if cur_alts:
                        existing["alt_phones"] = cur_alts
                if item.get("notes") and not existing.get("notes"):
                    existing["notes"] = item["notes"]
                if item.get("lid") and not existing.get("lid"):
                    existing["lid"] = item["lid"]
                updated += 1
            else:
                existing_ids = {c.get("id") for c in contacts}
                next_num = len(contacts) + 1
                new_id = f"c_{next_num}"
                while new_id in existing_ids:
                    next_num += 1
                    new_id = f"c_{next_num}"

                new_c = {
                    "id": new_id,
                    "name": clean_name,
                    "phone": clean_phone,
                    "relationship": item.get("relationship", ""),
                    "notes": item.get("notes", ""),
                    "full_name": item.get("full_name", clean_name),
                    "lid": item.get("lid", "")
                }
                if item.get("alt_phones"):
                    new_c["alt_phones"] = [ap for ap in item["alt_phones"] if ap and ap != clean_phone]
                contacts.append(new_c)
                if n_key:
                    phone_map[n_key] = new_c
                if clean_name.lower() not in ["kişi", "kisi", "bilinmeyen numara", ""]:
                    name_map[clean_name.lower()] = new_c
                added += 1

        self._save_all(contacts)
        return {"added": added, "updated": updated, "total_contacts": len(contacts)}

    def import_raw_text(self, text: str) -> Dict[str, Any]:
        """Parses multi-line freeform text contacts (Name: Phone (Rel) or CSV-like)."""
        lines = text.strip().splitlines()
        phone_pattern = re.compile(r'(\+?90\s?5\d{2}\s?\d{3}\s?\d{2}\s?\d{2}|0?5\d{2}\s?\d{3}\s?\d{2}\s?\d{2}|\+?\d{10,14})')
        items = []

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = phone_pattern.search(line)
            if not m:
                continue
            raw_phone = m.group(1)
            clean_phone = "".join([c for c in raw_phone if c.isdigit() or c == "+"])
            if not clean_phone.startswith("+") and len(clean_phone) == 10 and clean_phone.startswith("5"):
                clean_phone = "+90" + clean_phone
            elif not clean_phone.startswith("+") and len(clean_phone) == 11 and clean_phone.startswith("05"):
                clean_phone = "+90" + clean_phone[1:]

            rel_match = re.search(r'\(([^)]+)\)', line)
            relationship = rel_match.group(1).strip() if rel_match else ""

            rest = (line[:m.start()] + " " + line[m.end():]).strip(" :,-/|()")
            if relationship:
                rest = re.sub(r'\([^)]+\)', '', rest).strip(" :,-/|()")

            parts = [p.strip() for p in re.split(r'[,;|-]', rest) if p.strip()]
            name = parts[0] if parts else "Kişi"
            name = re.sub(r'[:;,|-]+$', '', name).strip()
            if len(parts) > 1 and not relationship:
                relationship = parts[1]

            items.append({
                "name": name,
                "full_name": name,
                "phone": clean_phone,
                "relationship": relationship,
                "notes": ""
            })

        return self.bulk_import(items)

    def import_google_csv(self, csv_content: Any) -> Dict[str, Any]:
        """Parses standard Google Contacts CSV format. Accepts string or Path."""
        if hasattr(csv_content, "read_text"):
            csv_content = csv_content.read_text(encoding="utf-8-sig")
        elif not isinstance(csv_content, str):
            csv_content = str(csv_content)

        if not csv_content.strip():
            return {"added": 0, "updated": 0, "total_contacts": len(self.get_all())}

        first_line = csv_content.strip().splitlines()[0]
        delimiter = ";" if ";" in first_line and first_line.count(";") > first_line.count(",") else ","

        reader = csv.DictReader(io.StringIO(csv_content), delimiter=delimiter)
        items = []
        for row in reader:
            row_norm = {str(k).strip().lower(): str(v).strip() for k, v in row.items() if k}
            name = row_norm.get("name") or ""
            if not name:
                first = row_norm.get("first name", "") or row_norm.get("given name", "")
                middle = row_norm.get("middle name", "")
                last = row_norm.get("last name", "") or row_norm.get("family name", "")
                parts = [p for p in [first, middle, last] if p]
                name = " ".join(parts).strip()
            if not name:
                name = row_norm.get("file as", "") or row_norm.get("organization name", "")

            all_phones: List[str] = []
            for k, v in row_norm.items():
                if ("phone" in k and "value" in k and v) or any(term in k for term in ["phone", "tel", "mobil", "telefon"]) and v:
                    for raw_piece in re.split(r":::|,|/", v):
                        piece = raw_piece.strip()
                        clean_p = "".join([c for c in piece if c.isdigit() or c == "+"])
                        digits_only = "".join([c for c in clean_p if c.isdigit()])
                        if len(digits_only) >= 7:
                            # Deduplicate by normalized last 10 digits
                            norm10 = digits_only[-10:] if len(digits_only) >= 10 else digits_only
                            if not any(("".join(ch for ch in ep if ch.isdigit())[-10:] == norm10) for ep in all_phones):
                                all_phones.append(clean_p)

            if not all_phones:
                continue

            clean_phone = all_phones[0]
            alt_phones = all_phones[1:]

            notes = row_norm.get("notes", "") or row_norm.get("note", "")
            relationship = row_norm.get("relationship", "") or row_norm.get("group membership", "") or row_norm.get("labels", "")
            if "my contacts" in relationship.lower() or "* my contacts" in relationship.lower() or "mycontacts" in relationship.lower():
                relationship = ""

            items.append({
                "name": name or "Kişi",
                "full_name": name or "Kişi",
                "phone": clean_phone,
                "alt_phones": alt_phones,
                "relationship": relationship,
                "notes": notes
            })

        return self.bulk_import(items)

    def import_vcard(self, vcard_content: str) -> Dict[str, Any]:
        """Parses standard vCard 2.1 / 3.0 / 4.0 (VCF) format."""
        if not vcard_content.strip():
            return {"added": 0, "updated": 0, "total_contacts": len(self.get_all())}

        cards = re.split(r'BEGIN:VCARD', vcard_content, flags=re.IGNORECASE)
        items = []
        for card in cards:
            if not card.strip() or "END:VCARD" not in card.upper():
                continue
            fn = ""
            phone = ""
            note = ""
            for line in card.splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.upper().startswith("FN"):
                    val = line.split(":", 1)[1] if ":" in line else ""
                    if "ENCODING=QUOTED-PRINTABLE" in line.upper():
                        try:
                            val = quopri.decodestring(val.encode("latin-1")).decode("utf-8")
                        except Exception:
                            pass
                    fn = val.strip()
                elif line.upper().startswith("TEL"):
                    val = line.split(":", 1)[1] if ":" in line else ""
                    clean = "".join([c for c in val if c.isdigit() or c == "+"])
                    if clean:
                        phone = clean
                elif line.upper().startswith("NOTE"):
                    val = line.split(":", 1)[1] if ":" in line else ""
                    note = val.strip()

            if phone:
                clean_name = fn or "Kişi"
                items.append({
                    "name": clean_name,
                    "full_name": clean_name,
                    "phone": phone,
                    "relationship": "",
                    "notes": note
                })

        return self.bulk_import(items)

    def sync_google_people_api(self) -> Dict[str, Any]:
        """
        Attempts to synchronize contacts using Google People API if credentials/token exist.
        If credentials do not have contacts scope, provides clean guidance.
        """
        token_path = Path(__file__).resolve().parent.parent.parent / "config" / "google_tokens.json"
        yt_token_path = Path(__file__).resolve().parent.parent.parent / "config" / "youtube_tokens.json"

        active_path = token_path if token_path.exists() else (yt_token_path if yt_token_path.exists() else None)
        if not active_path:
            return {
                "success": False,
                "status": "token_missing",
                "message": "Google token dosyası bulunamadı. Rehberinizi doğrudan Google Contacts (contacts.google.com) üzerinden CSV veya vCard olarak indirip 'Dosya Yükle' sekmesinden 2 saniyede aktarabilirsiniz."
            }

        try:
            with open(active_path, "r", encoding="utf-8") as f:
                token_data = json.load(f)
            access_token = token_data.get("token") or token_data.get("access_token")
            if not access_token:
                return {
                    "success": False,
                    "status": "token_invalid",
                    "message": "Geçerli bir Google erişim belirteci bulunamadı."
                }

            import requests
            url = "https://people.googleapis.com/v1/people/me/connections?personFields=names,phoneNumbers,relations&pageSize=100"
            resp = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, timeout=8)
            if resp.status_code == 200:
                conns = resp.json().get("connections", [])
                items = []
                for person in conns:
                    names = person.get("names", [])
                    disp_name = names[0].get("displayName", "") if names else "Kişi"
                    phones = person.get("phoneNumbers", [])
                    phone_val = phones[0].get("value", "") if phones else ""
                    clean_phone = "".join([c for c in phone_val if c.isdigit() or c == "+"])
                    if clean_phone:
                        items.append({
                            "name": disp_name,
                            "full_name": disp_name,
                            "phone": clean_phone,
                            "relationship": "",
                            "notes": "Google People API Sync"
                        })
                res = self.bulk_import(items)
                return {
                    "success": True,
                    "status": "synced",
                    "count": len(items),
                    "details": res
                }
            elif resp.status_code == 403:
                return {
                    "success": False,
                    "status": "insufficient_scope",
                    "message": "Google token'ınızda Contacts (Rehber) okuma izni (scope) bulunmuyor. contacts.google.com sitesinden 'Dışa Aktar -> Google CSV' seçeneği ile indirip panele yükleyebilirsiniz."
                }
            else:
                return {
                    "success": False,
                    "status": "api_error",
                    "message": f"Google People API yanıtı: HTTP {resp.status_code}"
                }
        except Exception as e:
            return {
                "success": False,
                "status": "error",
                "message": f"Google senkronizasyon hatası: {str(e)}"
            }

contacts_mgr = ContactsManager()
