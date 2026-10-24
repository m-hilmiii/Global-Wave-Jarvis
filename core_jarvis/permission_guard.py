"""
Global-Wawe / Stark-Core - Strict 4-Level Permission Guard
Implements the Master Architecture Security Model:
- Level 1 (Automatic): Read-only discovery, logs, telemetry, tests.
- Level 2 (Bounded): Workspace alterations, video/audio generation, backups.
- Level 3 (Explicit Confirmation): Git push, live dispatch, WhatsApp sending, YouTube publishing.
- Level 4 (Strictly Forbidden): Bypassing firewalls, leaking credentials, privilege escalation.
"""

import enum
import logging
import time
from typing import Dict, Any, Optional, List

logger = logging.getLogger("Jarvis.Security")

class PermissionLevel(enum.IntEnum):
    LEVEL_1_AUTO = 1
    LEVEL_2_BOUNDED = 2
    LEVEL_3_CONFIRMED = 3
    LEVEL_4_FORBIDDEN = 4

class PermissionGuard:
    def __init__(self):
        self.audit_trail: List[Dict[str, Any]] = []

        self.action_registry = {
            # Level 1: Automatic
            "read_logs": PermissionLevel.LEVEL_1_AUTO,
            "read_files": PermissionLevel.LEVEL_1_AUTO,
            "file_read": PermissionLevel.LEVEL_1_AUTO,
            "index_knowledge": PermissionLevel.LEVEL_1_AUTO,
            "system_telemetry": PermissionLevel.LEVEL_1_AUTO,
            "system_powershell_safe": PermissionLevel.LEVEL_1_AUTO,
            "git_diff": PermissionLevel.LEVEL_1_AUTO,
            "web_research": PermissionLevel.LEVEL_1_AUTO,
            "run_unit_tests": PermissionLevel.LEVEL_1_AUTO,
            "check_inbox": PermissionLevel.LEVEL_1_AUTO,
            "get_contacts": PermissionLevel.LEVEL_1_AUTO,
            "wol_discovery": PermissionLevel.LEVEL_1_AUTO,

            # Level 2: Predefined Bounded Actions
            "generate_script": PermissionLevel.LEVEL_2_BOUNDED,
            "generate_video": PermissionLevel.LEVEL_2_BOUNDED,
            "synthesize_voice": PermissionLevel.LEVEL_2_BOUNDED,
            "create_thumbnail": PermissionLevel.LEVEL_2_BOUNDED,
            "add_contact": PermissionLevel.LEVEL_2_BOUNDED,
            "import_contacts": PermissionLevel.LEVEL_2_BOUNDED,
            "workspace_backup": PermissionLevel.LEVEL_2_BOUNDED,
            "file_modify_workspace": PermissionLevel.LEVEL_2_BOUNDED,
            "git_commit": PermissionLevel.LEVEL_2_BOUNDED,

            # Level 3: Explicit Confirmation Required (Human-in-the-Loop)
            "git_push": PermissionLevel.LEVEL_3_CONFIRMED,
            "whatsapp_send": PermissionLevel.LEVEL_3_CONFIRMED,
            "youtube_upload": PermissionLevel.LEVEL_3_CONFIRMED,
            "delete_contact": PermissionLevel.LEVEL_3_CONFIRMED,
            "clear_chat": PermissionLevel.LEVEL_3_CONFIRMED,
            "wol_dispatch": PermissionLevel.LEVEL_3_CONFIRMED,
            "paid_api_call": PermissionLevel.LEVEL_3_CONFIRMED,
            "system_powershell_sensitive": PermissionLevel.LEVEL_3_CONFIRMED,
            "system_process_kill": PermissionLevel.LEVEL_3_CONFIRMED,
            "workspace_rollback": PermissionLevel.LEVEL_3_CONFIRMED,
            "file_permanent_delete": PermissionLevel.LEVEL_3_CONFIRMED,

            # Level 4: Strictly Forbidden
            "disable_firewall": PermissionLevel.LEVEL_4_FORBIDDEN,
            "leak_tokens": PermissionLevel.LEVEL_4_FORBIDDEN,
            "bypass_auth": PermissionLevel.LEVEL_4_FORBIDDEN,
            "delete_system_owner": PermissionLevel.LEVEL_4_FORBIDDEN,
            "modify_system_kernel": PermissionLevel.LEVEL_4_FORBIDDEN,
            "system_powershell_forbidden": PermissionLevel.LEVEL_4_FORBIDDEN
        }

    def evaluate_action(self, action_name: str, confirmed_by_user: bool = False, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Evaluates whether an action can proceed based on the 4-level model.
        """
        level = self.action_registry.get(action_name, PermissionLevel.LEVEL_3_CONFIRMED)

        record = {
            "timestamp": time.time(),
            "action": action_name,
            "level": int(level),
            "level_name": level.name,
            "confirmed_by_user": confirmed_by_user,
            "allowed": False,
            "reason": ""
        }

        # Level 4 is always rejected
        if level == PermissionLevel.LEVEL_4_FORBIDDEN:
            record["allowed"] = False
            record["reason"] = f"GÜVENLİK İHLALİ: '{action_name}' Seviye 4 (Kesinlikle Yasak) sınıfındadır ve asla yürütülemez."
            logger.critical(f"[PermissionGuard] Blocked Level 4 action: {action_name}")

        # Level 3 requires explicit confirmation
        elif level == PermissionLevel.LEVEL_3_CONFIRMED:
            if confirmed_by_user:
                record["allowed"] = True
                record["reason"] = f"Seviye 3 onaylandı: '{action_name}' için açık kullanıcı onayı alındı."
            else:
                record["allowed"] = False
                record["reason"] = f"ONAY BEKLİYOR: '{action_name}' Seviye 3 (Açık Onay / Human-in-the-Loop) gerektirir."

        # Level 2 is allowed within bounded workspace
        elif level == PermissionLevel.LEVEL_2_BOUNDED:
            record["allowed"] = True
            record["reason"] = f"Seviye 2 yürütüldü: '{action_name}' belirlenmiş çalışma alanı sınırları dahilinde."

        # Level 1 is automatically allowed
        elif level == PermissionLevel.LEVEL_1_AUTO:
            record["allowed"] = True
            record["reason"] = f"Seviye 1 yürütüldü: '{action_name}' otomatik keşif/okuma iznine sahip."

        self.audit_trail.append(record)
        if len(self.audit_trail) > 200:
            self.audit_trail.pop(0)

        return record

    def get_audit_trail(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self.audit_trail[-limit:]

permission_guard = PermissionGuard()
