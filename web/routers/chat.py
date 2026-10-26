"""
JARVIS Chat & Conversational Router
Handles chat interactions, draft approvals (HITL), and orchestrator task dispatches.
"""

import json
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.concurrency import run_in_threadpool

from core_jarvis.jarvis_brain import jarvis_brain
from core_jarvis.orchestrator import orchestrator
from core_jarvis.reality_memory import reality_memory
from core_jarvis.tools.voice_tool import voice_tool
from core_jarvis.logger import get_logger
from web.schemas import (
    ChatRequest,
    DraftConfirmRequest,
    DraftCancelRequest,
    OrchestratorDispatchRequest
)

logger = get_logger("Jarvis.Router.Chat")
router = APIRouter(prefix="/api/jarvis", tags=["Chat & Orchestrator"])


@router.post("/chat/stream")
async def api_jarvis_chat_stream(payload: ChatRequest):
    """
    Real-time Server-Sent Events (SSE) streaming endpoint for JARVIS chat.
    Streams token fragments with TTFT < 200ms and yields completion packet.
    """
    msg = payload.message.strip()
    if not msg:
        return JSONResponse({"status": "error", "message": "Mesaj boş olamaz."}, status_code=status.HTTP_400_BAD_REQUEST)

    def event_stream():
        for chunk_data in jarvis_brain.stream_message(msg):
            done = chunk_data.get("done", False)
            if done:
                final_reply = chunk_data.get("reply", "")
                final_speak = chunk_data.get("speak_text", final_reply)
                audio_url = None
                if payload.voice_response and final_speak:
                    try:
                        v_res = voice_tool.synthesize_speech(text=final_speak, voice_name="tr-TR-AhmetNeural")
                        if v_res.get("success"):
                            audio_url = v_res.get("audio_url")
                    except Exception as v_err:
                        logger.warning(f"Voice synthesis in stream completion failed: {v_err}")
                chunk_data["audio_url"] = audio_url

            yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/chat")
async def api_jarvis_chat(payload: ChatRequest):
    """Processes user queries via Qwen3 8B, handling intents, drafts, and voice responses."""
    msg = payload.message.strip()
    if not msg:
        return JSONResponse({"status": "error", "message": "Mesaj boş olamaz."}, status_code=status.HTTP_400_BAD_REQUEST)

    res = await run_in_threadpool(jarvis_brain.process_message, msg)
    reply = res.get("reply", "") if isinstance(res, dict) else str(res)
    speak_text = res.get("speak_text", "") if isinstance(res, dict) else reply
    audio_url = res.get("audio_url") if isinstance(res, dict) else None

    # Auto-synthesize voice if requested and not already provided
    if payload.voice_response and speak_text and not audio_url:
        try:
            v_res = await run_in_threadpool(voice_tool.synthesize_speech, text=speak_text, voice_name="tr-TR-AhmetNeural")
            if v_res.get("success") and v_res.get("audio_url"):
                audio_url = v_res.get("audio_url")
        except Exception as v_err:
            logger.warning(f"Auto voice synthesis failed: {v_err}")

    return {
        "status": "success",
        "reply": reply,
        "speak_text": speak_text,
        "audio_url": audio_url,
        "result": res
    }


@router.post("/draft/confirm")
async def api_jarvis_draft_confirm(payload: DraftConfirmRequest):
    """Confirms and dispatches a pending HITL draft (e.g., WhatsApp message)."""
    draft_id = payload.draft_id
    if not draft_id:
        return JSONResponse(
            {"status": "error", "message": "Geçerli ve açık bir taslak kimliği (draft_id) belirtilmelidir."},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    res = await run_in_threadpool(jarvis_brain.confirm_pending_draft, draft_id)
    action = res.get("action_taken") if isinstance(res, dict) else None

    if action == "whatsapp_dispatched":
        return {"status": "success", "result": res}
    elif action in ["no_draft", "draft_expired", "invalid_draft_id", "already_sending"]:
        return JSONResponse({"status": "error", "result": res}, status_code=status.HTTP_400_BAD_REQUEST)
    else:
        return JSONResponse({"status": "error", "result": res}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("/draft/cancel")
async def api_jarvis_draft_cancel(payload: DraftCancelRequest):
    """Cancels a pending HITL draft."""
    draft_id = payload.draft_id
    if not draft_id:
        return JSONResponse(
            {"status": "error", "message": "Geçerli ve açık bir taslak kimliği (draft_id) belirtilmelidir."},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    res = await run_in_threadpool(jarvis_brain.cancel_pending_draft, draft_id)
    return {"status": "success", "result": res}


@router.get("/reality/state")
async def api_jarvis_reality_state():
    """Returns the persistent state and context from episodic reality memory."""
    data = await run_in_threadpool(reality_memory.resume_context)
    return {"status": "success", "reality": data}


@router.post("/chat/clear")
async def api_jarvis_chat_clear():
    """Clears conversation history and pending drafts."""
    def _clear():
        jarvis_brain.conversation_history.clear()
        with jarvis_brain.draft_lock:
            jarvis_brain.pending_drafts.clear()
            jarvis_brain.latest_draft_id = None
    await run_in_threadpool(_clear)
    return {"status": "success", "message": "JARVIS sohbet geçmişi ve taslakları temizlendi."}


@router.post("/orchestrator/dispatch")
async def api_jarvis_orchestrator_dispatch(payload: OrchestratorDispatchRequest):
    """Dispatches a high-level intent to the multi-agent orchestrator."""
    prompt = payload.prompt.strip()
    if not prompt:
        return JSONResponse({"status": "error", "message": "Yönerge (prompt) zorunludur."}, status_code=status.HTTP_400_BAD_REQUEST)

    res = await run_in_threadpool(orchestrator.handle_intent, prompt, payload.confirmed)
    return {"status": "success", "result": res}
