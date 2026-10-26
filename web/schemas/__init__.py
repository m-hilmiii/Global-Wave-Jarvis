"""
JARVIS Pydantic Request & Response Schemas
Provides strict type-checking, automatic JSON validation, and clean OpenAPI specifications.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


# ---------------------------------------------------------------------------
# Chat & Intent Schemas
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Kullanıcı metin veya komut girdisi.")
    voice_response: bool = Field(default=False, description="Yanıtın seslendirilip seslendirilmeyeceği.")
    session_id: str = Field(default="owner_web_luxury", description="Oturum veya istemci kimliği.")


class DraftConfirmRequest(BaseModel):
    draft_id: Optional[str] = Field(default=None, description="Onaylanacak taslak kimliği.")


class DraftCancelRequest(BaseModel):
    draft_id: Optional[str] = Field(default=None, description="İptal edilecek taslak kimliği.")


class OrchestratorDispatchRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Orkestratöre iletilecek üst düzey görev yönergesi.")
    confirmed: bool = Field(default=False, description="Kullanıcı ön onayı.")


# ---------------------------------------------------------------------------
# Voice & Audio Schemas
# ---------------------------------------------------------------------------
class VoiceSpeakRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Seslendirilecek Türkçe metin.")
    voice: str = Field(default="tr-TR-AhmetNeural", description="Seçilen nöral ses profili.")
    speed: float = Field(default=1.05, ge=0.5, le=2.0, description="Konuşma hızı çarpanı.")


class VoiceCommandRequest(BaseModel):
    text: str = Field(..., min_length=1, description="İşlenecek sesli komut metni.")
    voice: str = Field(default="tr-TR-AhmetNeural", description="Yanıt için ses profili.")


# ---------------------------------------------------------------------------
# System & Hardware Schemas
# ---------------------------------------------------------------------------
class PowerShellRequest(BaseModel):
    command: str = Field(..., min_length=1, description="Çalıştırılacak güvenli PowerShell komutu.")
    confirmed: bool = Field(default=False, description="Güvenlik izin onayı.")


class AppLaunchRequest(BaseModel):
    app_name: str = Field(..., min_length=1, description="Başlatılacak uygulama adı (örn. chrome, spotify, discord).")
    args: Optional[List[str]] = Field(default_factory=list, description="Uygulamaya iletilecek parametreler.")


class ModelRouteRequest(BaseModel):
    model: str = Field(..., min_length=1, description="Hedef AI uzman modeli (örn. qwen3:8b, qwen2.5:14b).")


# ---------------------------------------------------------------------------
# WhatsApp Schemas
# ---------------------------------------------------------------------------
class WhatsAppSendRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Gönderilecek WhatsApp mesaj metni.")


class WhatsAppImportRequest(BaseModel):
    contact_name: str = Field(..., min_length=1, description="Kişi veya grup adı.")
    content: str = Field(..., min_length=1, description="İçe aktarılacak WhatsApp dışa aktarım metni.")


# ---------------------------------------------------------------------------
# Global Wave Studio Schemas
# ---------------------------------------------------------------------------
class StudioGenerateVideoRequest(BaseModel):
    topic: str = Field(..., min_length=1, description="Üretilecek YouTube Short konusu.")
    style: str = Field(default="luxury", description="Görsel ve anlatım stili.")
    count: int = Field(default=1, ge=1, le=5, description="Üretilecek video sayısı.")


class StudioStoryRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="LTX-2 video hikaye senaryosu.")
    confirmed: bool = Field(default=False, description="VRAM tahsis onayı.")
