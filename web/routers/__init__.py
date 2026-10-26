"""
JARVIS FastAPI Router Package
Exposes modular routers for chat, telemetry, whatsapp, voice, studio, and assistant operations.
"""

from web.routers.chat import router as chat_router
from web.routers.telemetry import router as telemetry_router
from web.routers.whatsapp import router as whatsapp_router
from web.routers.voice import router as voice_router
from web.routers.studio import router as studio_router
from web.routers.assistant import router as assistant_router

__all__ = [
    "chat_router",
    "telemetry_router",
    "whatsapp_router",
    "voice_router",
    "studio_router",
    "assistant_router"
]
