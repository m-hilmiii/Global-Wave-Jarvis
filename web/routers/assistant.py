"""
JARVIS Assistant, Research, Vision & Content Pipeline Router
Handles personal briefing, tasks, notes, semantic search, vision inspections, and background daemon operations.
"""

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from typing import Optional, List, Dict, Any

from core_jarvis.personal_assistant import personal_assistant
from core_jarvis.task_coordinator import task_coordinator
from core_jarvis.tools.browser_research_tool import browser_research_tool
from core_jarvis.tools.knowledge_indexer import knowledge_indexer
from core_jarvis.tools.vision_tool import vision_tool
from core_jarvis.daemon_manager import daemon_manager
from engine.content_pipeline import content_pipeline
from core_jarvis.logger import get_logger

logger = get_logger("Jarvis.Router.Assistant")
router = APIRouter(prefix="/api/jarvis", tags=["Assistant & Pipelines"])


# ---------------------------------------------------------------------------
# Personal Assistant & Task Management
# ---------------------------------------------------------------------------
@router.get("/assistant/briefing")
async def api_jarvis_assistant_briefing():
    data = await run_in_threadpool(personal_assistant.get_daily_briefing)
    return {"status": "success", "briefing": data}


@router.get("/assistant/tasks")
async def api_jarvis_assistant_tasks(status: Optional[str] = None):
    data = await run_in_threadpool(personal_assistant.get_tasks, status=status)
    return {"status": "success", "tasks": data}


@router.post("/assistant/tasks")
async def api_jarvis_assistant_add_task(request: Request):
    payload = await request.json()
    title = payload.get("title", "").strip()
    priority = payload.get("priority", "normal")
    due_date = payload.get("due_date")
    category = payload.get("category", "general")
    if not title:
        return JSONResponse({"status": "error", "message": "Başlık gereklidir."}, status_code=status.HTTP_400_BAD_REQUEST)
    data = await run_in_threadpool(personal_assistant.add_task, title=title, priority=priority, due_date=due_date, category=category)
    return {"status": "success", "result": data}


@router.post("/assistant/tasks/{task_id}/complete")
async def api_jarvis_assistant_complete_task(task_id: str):
    data = await run_in_threadpool(personal_assistant.complete_task, task_id)
    return {"status": "success" if data.get("success") else "error", "result": data}


@router.get("/assistant/reminders")
async def api_jarvis_assistant_reminders():
    data = await run_in_threadpool(personal_assistant.get_reminders)
    return {"status": "success", "reminders": data}


@router.post("/assistant/reminders")
async def api_jarvis_assistant_add_reminder(request: Request):
    payload = await request.json()
    title = payload.get("title", "").strip()
    datetime_iso = payload.get("datetime_iso", "")
    lead_minutes = int(payload.get("lead_minutes", 15))
    recurring = payload.get("recurring")
    if not title or not datetime_iso:
        return JSONResponse({"status": "error", "message": "Başlık ve tarih zorunludur."}, status_code=status.HTTP_400_BAD_REQUEST)
    data = await run_in_threadpool(personal_assistant.add_reminder, title=title, datetime_iso=datetime_iso, lead_minutes=lead_minutes, recurring=recurring)
    return {"status": "success", "result": data}


@router.get("/assistant/notes")
async def api_jarvis_assistant_notes():
    data = await run_in_threadpool(personal_assistant.get_notes)
    return {"status": "success", "notes": data}


@router.post("/assistant/notes")
async def api_jarvis_assistant_add_note(request: Request):
    payload = await request.json()
    title = payload.get("title", "").strip()
    content = payload.get("content", "").strip()
    tags = payload.get("tags", [])
    if not title or not content:
        return JSONResponse({"status": "error", "message": "Başlık ve içerik zorunludur."}, status_code=status.HTTP_400_BAD_REQUEST)
    data = await run_in_threadpool(personal_assistant.add_note, title=title, content=content, tags=tags)
    return {"status": "success", "result": data}


# ---------------------------------------------------------------------------
# Background Jobs
# ---------------------------------------------------------------------------
@router.get("/jobs")
async def api_jarvis_jobs(status: Optional[str] = None):
    jobs = await run_in_threadpool(task_coordinator.list_jobs, status=status)
    return {"status": "success", "jobs": jobs}


@router.get("/jobs/{job_id}")
async def api_jarvis_job_detail(job_id: str):
    job = await run_in_threadpool(task_coordinator.get_job, job_id)
    if not job:
        return JSONResponse({"status": "error", "message": "İş bulunamadı."}, status_code=status.HTTP_404_NOT_FOUND)
    return {"status": "success", "job": job}


@router.post("/jobs/{job_id}/cancel")
async def api_jarvis_job_cancel(job_id: str):
    res = await run_in_threadpool(task_coordinator.cancel_job, job_id)
    return {"status": "success" if res.get("success") else "error", "result": res}


# ---------------------------------------------------------------------------
# Content Production Pipeline
# ---------------------------------------------------------------------------
@router.post("/content/produce")
async def api_jarvis_content_produce(request: Request):
    payload = await request.json()
    topic = payload.get("topic", "").strip()
    target_duration = payload.get("target_duration", "45s")
    orientation = payload.get("orientation", "vertical")
    persona_id = payload.get("persona_id", "us_hustler")
    if not topic:
        return JSONResponse({"status": "error", "message": "Konu (topic) zorunludur."}, status_code=status.HTTP_400_BAD_REQUEST)
    res = await run_in_threadpool(
        content_pipeline.stage_1_produce_draft,
        topic=topic,
        target_duration=target_duration,
        orientation=orientation,
        persona_id=persona_id
    )
    return {"status": "success" if res.get("success") else "error", "result": res}


@router.post("/content/qc")
async def api_jarvis_content_qc(request: Request):
    payload = await request.json()
    video_path = payload.get("video_path", "").strip()
    script_data = payload.get("script_data", {})
    if not video_path:
        return JSONResponse({"status": "error", "message": "video_path zorunludur."}, status_code=status.HTTP_400_BAD_REQUEST)
    res = await run_in_threadpool(content_pipeline.stage_2_quality_control, video_path, script_data)
    return {"status": "success" if res.get("success") else "error", "result": res}


@router.post("/content/publish")
async def api_jarvis_content_publish(request: Request):
    payload = await request.json()
    video_path = payload.get("video_path", "").strip()
    title = payload.get("title", "").strip()
    description = payload.get("description", "").strip()
    tags = payload.get("tags", [])
    confirmed = bool(payload.get("confirm", False))
    privacy_status = payload.get("privacy_status", "private")
    if not video_path or not title:
        return JSONResponse({"status": "error", "message": "video_path ve title zorunludur."}, status_code=status.HTTP_400_BAD_REQUEST)
    res = await run_in_threadpool(
        content_pipeline.stage_3_prepare_and_publish,
        video_path=video_path,
        title=title,
        description=description,
        tags=tags,
        confirmed_by_user=confirmed,
        privacy_status=privacy_status
    )
    return {"status": "success" if res.get("success") else "error", "result": res}


# ---------------------------------------------------------------------------
# Web Research & RAG Knowledge Engine
# ---------------------------------------------------------------------------
@router.post("/research/query")
async def api_jarvis_research_query(request: Request):
    payload = await request.json()
    query = payload.get("query", "").strip()
    auto_note = payload.get("auto_note", True)
    if not query:
        return JSONResponse({"status": "error", "message": "query zorunludur."}, status_code=status.HTTP_400_BAD_REQUEST)
    res = await run_in_threadpool(browser_research_tool.conduct_research_and_archive, query, auto_note=auto_note)
    return {"status": "success", "research": res}


@router.post("/research/hardware-models")
async def api_jarvis_research_models(request: Request):
    payload = await request.json()
    category = payload.get("category", "coding")
    res = await run_in_threadpool(browser_research_tool.compare_hardware_models, category=category)
    return {"status": "success", "comparison": res}


@router.post("/research/fetch")
async def api_jarvis_research_fetch(request: Request):
    payload = await request.json()
    url = payload.get("url", "").strip()
    if not url:
        return JSONResponse({"status": "error", "message": "url zorunludur."}, status_code=status.HTTP_400_BAD_REQUEST)
    res = await run_in_threadpool(browser_research_tool.fetch_page_content, url=url)
    return {"status": "success" if res.get("success") else "error", "page": res}


@router.post("/knowledge/search")
async def api_jarvis_knowledge_search(request: Request):
    payload = await request.json()
    query = payload.get("query", "").strip()
    top_k = payload.get("top_k", 5)
    file_filter = payload.get("file_filter")
    if not query:
        return JSONResponse({"status": "error", "message": "query zorunludur."}, status_code=status.HTTP_400_BAD_REQUEST)
    res = await run_in_threadpool(knowledge_indexer.search, query, top_k=top_k, file_filter=file_filter)
    return {"status": "success", "results": res}


@router.post("/knowledge/index")
async def api_jarvis_knowledge_index(request: Request):
    payload = {}
    try:
        payload = await request.json()
    except Exception:
        pass
    force = payload.get("force", False)
    res = await run_in_threadpool(knowledge_indexer.index_workspace, force=force)
    return {"status": "success" if res.get("success") else "error", "index": res}


@router.post("/knowledge/summarize")
async def api_jarvis_knowledge_summarize(request: Request):
    payload = await request.json()
    file_path = payload.get("file_path", "").strip()
    if not file_path:
        return JSONResponse({"status": "error", "message": "file_path zorunludur."}, status_code=status.HTTP_400_BAD_REQUEST)
    res = await run_in_threadpool(knowledge_indexer.summarize_document, file_path=file_path)
    return {"status": "success" if res.get("success") else "error", "document": res}


@router.get("/knowledge/stats")
async def api_jarvis_knowledge_stats():
    res = await run_in_threadpool(knowledge_indexer.get_index_stats)
    return {"status": "success", "stats": res}


# ---------------------------------------------------------------------------
# Computer Vision & Screen Analysis
# ---------------------------------------------------------------------------
@router.post("/vision/inspect")
async def api_jarvis_vision_inspect(request: Request):
    payload = {}
    try:
        payload = await request.json()
    except Exception:
        pass
    prompt = payload.get("prompt", "Ekrandaki içeriği açıkla")
    mode = payload.get("mode", "general")
    res = await run_in_threadpool(vision_tool.analyze_screen, user_prompt=prompt, mode=mode)
    return {"status": "success" if res.get("success") else "error", "vision": res}


@router.get("/vision/capture")
async def api_jarvis_vision_capture():
    res = await run_in_threadpool(vision_tool.capture_screen)
    return {"status": "success" if res.get("success") else "error", "capture": res}


# ---------------------------------------------------------------------------
# Daemon & System Lifecycle
# ---------------------------------------------------------------------------
@router.get("/daemon/status")
async def api_jarvis_daemon_status():
    res = await run_in_threadpool(daemon_manager.get_status)
    return {"status": "success", "daemon": res}


@router.post("/daemon/shortcut")
async def api_jarvis_daemon_shortcut():
    res = await run_in_threadpool(daemon_manager.create_desktop_shortcut)
    return {"status": "success" if res.get("success") else "error", "result": res}


@router.post("/daemon/startup")
async def api_jarvis_daemon_startup(request: Request):
    payload = {}
    try:
        payload = await request.json()
    except Exception:
        pass
    enabled = payload.get("enabled", True)
    if enabled:
        res = await run_in_threadpool(daemon_manager.install_windows_startup)
    else:
        res = await run_in_threadpool(daemon_manager.uninstall_windows_startup)
    return {"status": "success" if res.get("success") else "error", "result": res}


# ---------------------------------------------------------------------------
# Autonomous Engine & Special Arsenal
# ---------------------------------------------------------------------------
@router.get("/models/arsenal")
async def api_jarvis_models_arsenal():
    from core_jarvis.tools.model_manager import model_manager
    status = await run_in_threadpool(model_manager.get_arsenal_status)
    return {"status": "success", **status}


@router.post("/autonomous/execute")
async def api_jarvis_autonomous_execute(request: Request):
    payload = await request.json()
    task = payload.get("task", "")
    dry_run = payload.get("dry_run", False)
    from core_jarvis.autonomous_engine import autonomous_engine
    res = await run_in_threadpool(autonomous_engine.execute_autonomous_cycle, task=task, dry_run=dry_run)
    return {"status": "success", "result": res}


@router.get("/project/resume")
async def api_jarvis_project_resume():
    from core_jarvis.reality_memory import reality_memory
    ctx = await run_in_threadpool(reality_memory.resume_context)
    return {"status": "success", "context": ctx}
