"""
JARVIS WhatsApp & Contacts Management Router
Handles real-time Baileys socket integration, QR code generation, contact sync, and chat history.
"""

import json
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from typing import Optional, List

from core_jarvis.whatsapp_daemon import whatsapp_daemon, INBOX_FILE
from core_jarvis.tools.contacts import contacts_mgr
from core_jarvis.tools.whatsapp_tool import whatsapp_tool
from core_jarvis.logger import get_logger
from web.schemas import WhatsAppSendRequest, WhatsAppImportRequest

logger = get_logger("Jarvis.Router.WhatsApp")
router = APIRouter(prefix="/api/jarvis", tags=["WhatsApp & Contacts"])


# ---------------------------------------------------------------------------
# WhatsApp Core & QR Status
# ---------------------------------------------------------------------------
@router.get("/whatsapp/qr_status")
async def api_jarvis_whatsapp_qr_status():
    """Returns real-time Baileys socket connectivity and base64 QR code."""
    st = whatsapp_daemon.get_status()
    return {"status": "success", **st}


@router.post("/whatsapp/reconnect_sync")
async def api_jarvis_whatsapp_reconnect_sync(request: Request):
    """Triggers an active reconnection and inbox sync without resetting session unless force_reset=True."""
    force_reset = False
    try:
        data = await request.json()
        force_reset = bool(data.get("force_reset", False))
    except Exception:
        pass
    res = await run_in_threadpool(whatsapp_daemon.reconnect_and_sync, force_reset=force_reset)
    return {"status": "success" if res.get("success") else "error", "result": res}


@router.post("/whatsapp/import_chat_export")
async def api_jarvis_whatsapp_import_chat_export(payload: WhatsAppImportRequest):
    """Imports raw exported WhatsApp chat logs into episodic memory graph."""
    res = await run_in_threadpool(whatsapp_daemon.import_chat_export, payload.contact_name, payload.content)
    return {"status": "success" if res.get("success") else "error", "result": res}


# ---------------------------------------------------------------------------
# Contacts Management
# ---------------------------------------------------------------------------
@router.get("/contacts")
async def api_jarvis_contacts():
    """Returns the full list of recognized contacts."""
    return {"status": "success", "contacts": contacts_mgr.get_all()}


@router.post("/contacts")
async def api_jarvis_add_contact(request: Request):
    """Adds a new contact with name, phone, relationship, and notes."""
    data = await request.json()
    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    relationship = data.get("relationship", "").strip()
    notes = data.get("notes", "").strip()
    full_name = data.get("full_name", "").strip()
    if not name or not phone:
        return JSONResponse({"status": "error", "message": "İsim ve telefon bilgisi zorunludur."}, status_code=status.HTTP_400_BAD_REQUEST)
    contact = await run_in_threadpool(contacts_mgr.add_contact, name, phone, relationship, notes, full_name)
    return {"status": "success", "contact": contact}


@router.delete("/contacts/{identifier}")
async def api_jarvis_delete_contact(identifier: str):
    """Deletes a contact by identifier (cannot delete system owner)."""
    deleted = await run_in_threadpool(contacts_mgr.delete_contact, identifier)
    if deleted:
        return {"status": "success", "deleted": deleted}
    return JSONResponse({"status": "error", "message": "Kişi bulunamadı veya sistem sahibi silinemez."}, status_code=status.HTTP_404_NOT_FOUND)


@router.post("/contacts/import")
async def api_jarvis_import_contacts(request: Request):
    """Imports contacts from raw text or structured lists."""
    data = await request.json()
    raw_text = data.get("text", "")
    contacts_list = data.get("contacts", [])
    if contacts_list:
        res = await run_in_threadpool(contacts_mgr.bulk_import, contacts_list)
    elif raw_text:
        res = await run_in_threadpool(contacts_mgr.import_raw_text, raw_text)
    else:
        return JSONResponse({"status": "error", "message": "İçe aktarılacak kişi verisi bulunamadı."}, status_code=status.HTTP_400_BAD_REQUEST)
    return {"status": "success", "result": res}


@router.post("/contacts/import_file")
async def api_jarvis_import_file(request: Request):
    """Imports contacts from uploaded .vcf, .csv, or raw text files."""
    form = await request.form()
    upload = form.get("file")
    if not upload:
        return JSONResponse({"status": "error", "message": "Dosya seçilmedi."}, status_code=status.HTTP_400_BAD_REQUEST)
    content = await upload.read()
    filename = upload.filename.lower() if upload.filename else ""
    text = content.decode("utf-8", errors="replace")
    if filename.endswith(".vcf") or "begin:vcard" in text.lower():
        res = await run_in_threadpool(contacts_mgr.import_vcard, text)
    elif filename.endswith(".csv") or "," in text or ";" in text:
        res = await run_in_threadpool(contacts_mgr.import_google_csv, text)
    else:
        res = await run_in_threadpool(contacts_mgr.import_raw_text, text)
    return {"status": "success", "result": res}


@router.get("/contacts/google_sync")
async def api_jarvis_contacts_google_sync():
    """Synchronizes contacts with Google People API if configured."""
    res = await run_in_threadpool(contacts_mgr.sync_google_people_api)
    return {"status": "success" if res.get("success") else "warning", "result": res}


# ---------------------------------------------------------------------------
# Chats & Messaging
# ---------------------------------------------------------------------------
@router.get("/chats")
async def api_jarvis_chats():
    """Returns the overview summary of active WhatsApp chat threads."""
    overview = await run_in_threadpool(whatsapp_daemon.get_chats_overview)
    return {"status": "success", "chats": overview}


@router.get("/chats/{identifier}/messages")
async def api_jarvis_chat_messages(identifier: str):
    """Returns chat message history for a specific phone/JID."""
    history = await run_in_threadpool(whatsapp_daemon.get_chat_history, identifier)
    return {"status": "success", "messages": history}


@router.post("/chats/{identifier}/read")
async def api_jarvis_chat_read(identifier: str):
    """Marks a conversation as read."""
    await run_in_threadpool(whatsapp_daemon.mark_chat_read, identifier)
    return {"status": "success"}


@router.post("/chats/{identifier}/send")
async def api_jarvis_chat_send(identifier: str, request: Request):
    """Sends a WhatsApp message to target recipient with safety check."""
    data = await request.json()
    text = data.get("text") or data.get("message", "")
    text = text.strip()
    if not text:
        return JSONResponse({"status": "error", "message": "Mesaj metni zorunludur."}, status_code=status.HTTP_400_BAD_REQUEST)

    contact = contacts_mgr.find_contact(identifier)
    phone = contact["phone"] if contact else identifier
    name = contact["name"] if contact else identifier
    res = await run_in_threadpool(whatsapp_tool.send_message_to_phone, phone, text, recipient_name=name)
    return {"status": "success" if res.get("success") else "error", "result": res}


@router.delete("/chats/{identifier}")
async def api_jarvis_delete_chat(identifier: str):
    """Clears message history for a specific chat."""
    count = await run_in_threadpool(whatsapp_daemon.clear_chat, identifier)
    return {"status": "success", "cleared_messages": count}


@router.post("/message/delete")
async def api_jarvis_message_delete(request: Request):
    """Deletes a specific message from WhatsApp."""
    data = await request.json()
    jid = data.get("jid", "")
    msg_id = data.get("message_id", "")
    everyone = data.get("everyone", True)
    res = await run_in_threadpool(whatsapp_daemon.delete_message, jid, msg_id, everyone=everyone)
    return {"status": "success", "result": res}


@router.get("/inbox/check_new")
async def api_jarvis_inbox_check_new(since: float = 0):
    """Polls for new unread WhatsApp messages since a timestamp."""
    overview = whatsapp_daemon.get_chats_overview()
    new_msgs = []
    since_norm = whatsapp_daemon._normalize_timestamp(since)
    if INBOX_FILE.exists():
        try:
            with open(INBOX_FILE, "r", encoding="utf-8-sig") as f:
                inbox = json.load(f)
            for m in inbox:
                m_ts = whatsapp_daemon._normalize_timestamp(m.get("timestamp", 0))
                if m_ts > since_norm and not m.get("from_me") and m.get("unread"):
                    new_msgs.append(m)
        except Exception as e:
            logger.debug(f"[WhatsAppRouter] Inbox read error: {e}")
    return {"status": "success", "overview": overview, "new_messages": new_msgs}


# ---------------------------------------------------------------------------
# WhatsApp Automation & AI Delegate Settings
# ---------------------------------------------------------------------------
@router.get("/settings/whatsapp_auto_dispatch")
async def api_jarvis_get_auto_dispatch():
    from core_jarvis.jarvis_brain import jarvis_brain
    return {"status": "success", "auto_dispatch": jarvis_brain.auto_dispatch_whatsapp}


@router.post("/settings/whatsapp_auto_dispatch")
async def api_jarvis_set_auto_dispatch(request: Request):
    data = await request.json()
    enabled = bool(data.get("enabled", False))
    from core_jarvis.jarvis_brain import jarvis_brain
    val = jarvis_brain.set_auto_dispatch_whatsapp(enabled)
    return {"status": "success", "auto_dispatch": val}


@router.get("/settings/ai_delegate")
async def api_jarvis_get_ai_delegate():
    return {
        "status": "success",
        "active": whatsapp_daemon.ai_delegate_active,
        "targets": whatsapp_daemon.ai_delegate_targets,
        "logs": whatsapp_daemon.ai_delegate_logs
    }


@router.post("/settings/ai_delegate")
async def api_jarvis_set_ai_delegate(request: Request):
    data = await request.json()
    action = data.get("action", "toggle")
    target = data.get("target")
    if action == "enable":
        whatsapp_daemon.enable_ai_delegate(target)
    elif action == "disable":
        logs = whatsapp_daemon.disable_ai_delegate()
        return {"status": "success", "active": False, "logs": logs}
    elif action == "toggle":
        if whatsapp_daemon.ai_delegate_active:
            logs = whatsapp_daemon.disable_ai_delegate()
            return {"status": "success", "active": False, "logs": logs}
        else:
            whatsapp_daemon.enable_ai_delegate(target)
    return {
        "status": "success",
        "active": whatsapp_daemon.ai_delegate_active,
        "targets": whatsapp_daemon.ai_delegate_targets
    }
