"""
Global Wave YouTube Shorts Studio & LTX-2 Video Router
Handles video generation tasks, LTX-2 status monitoring, and VRAM-aware story pipelines.
"""

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from core_jarvis.tools.studio_bridge import studio_bridge
from core_jarvis.logger import get_logger
from web.schemas import StudioGenerateVideoRequest, StudioStoryRequest

logger = get_logger("Jarvis.Router.Studio")
router = APIRouter(prefix="/api/jarvis/studio", tags=["Global Wave Studio & LTX-2"])


@router.get("/status")
async def api_jarvis_studio_status():
    """Returns LTX-2 render status, GPU availability, and directory paths."""
    summary = await run_in_threadpool(studio_bridge.get_ltx_status_summary)
    paths = await run_in_threadpool(studio_bridge.get_studio_paths)
    is_rendering = studio_bridge.is_ltx_rendering()
    return {"status": "success", "summary": summary, "paths": paths, "is_rendering": is_rendering}


@router.post("/generate_video")
async def api_jarvis_studio_generate(request: Request):
    """Triggers an automated LTX-2 prompt-to-video render pipeline."""
    payload = await request.json() if request.headers.get("content-length") else {}
    prompt = payload.get("prompt", "A cinematic drone shot of a futuristic cyberpunk city at night with neon lights, photorealistic, 4k")
    res = await run_in_threadpool(studio_bridge.trigger_ltx_video, prompt=prompt)
    return res


@router.post("/story")
async def api_jarvis_studio_story(request: Request):
    """Generates an end-to-end cinematic multi-scene story with LTX-2."""
    payload = await request.json() if request.headers.get("content-length") else {}
    scene = payload.get("scene")
    all_scenes = bool(payload.get("all_scenes", True))
    res = await run_in_threadpool(studio_bridge.trigger_story_generator, scene=scene, all_scenes=all_scenes)
    return res
