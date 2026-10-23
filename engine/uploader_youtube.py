import uuid
import threading
UPLOAD_LOCK = threading.RLock()
"""
Global Wave - Official YouTube Data API v3 Uploader Engine (Faz 2)
1. Desktop OAuth 2.0 Loopback Flow.
2. Persistent token caching in config/youtube_tokens.json.
3. 100% Real Live Channel Profile & Uploads Inspection.
4. Resumable chunked upload with custom #Shorts metadata, tags, and privacy control.
"""
import os
import json
import time
import requests
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
CLIENT_SECRET_FILE = CONFIG_DIR / "client_secret.json"
TOKEN_FILE = CONFIG_DIR / "youtube_tokens.json"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly"
]

def get_credentials() -> Credentials | None:
    creds = None
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except Exception as e:
            print(f"[WARN] Failed to load cached tokens: {e}")
            
    if creds and creds.expired and creds.refresh_token:
        try:
            print("[YOUTUBE] Refreshing expired OAuth access token...")
            creds.refresh(Request())
            with open(TOKEN_FILE, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
        except Exception as e:
            print(f"[WARN] Token refresh failed: {e}. Removing stale token file.")
            try:
                if TOKEN_FILE.exists():
                    TOKEN_FILE.unlink()
            except Exception:
                pass
            creds = None
            
    return creds

def clear_cached_tokens() -> bool:
    """Removes cached youtube_tokens.json file to force clean re-authorization."""
    try:
        if TOKEN_FILE.exists():
            TOKEN_FILE.unlink()
            print("[YOUTUBE] Stale tokens cleared.")
        return True
    except Exception as e:
        print(f"[WARN] Could not delete token file: {e}")
        return False

def get_auth_diagnostic() -> dict:
    """Detailed diagnostic status for UI onboarding and troubleshooting."""
    secret_exists = CLIENT_SECRET_FILE.exists()
    project_id = ""
    client_id_preview = ""
    
    if secret_exists:
        try:
            with open(CLIENT_SECRET_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                inst = data.get("installed", {}) or data.get("web", {})
                project_id = inst.get("project_id", "")
                cid = inst.get("client_id", "")
                client_id_preview = cid[:24] + "..." if len(cid) > 24 else cid
        except Exception as e:
            print(f"[WARN] Error reading client secrets: {e}")
            
    token_exists = TOKEN_FILE.exists()
    profile = get_channel_profile()
    is_connected = bool(profile and profile.get("is_connected"))
    
    # Direct Google Cloud helper URLs
    proj_query = f"?project={project_id}" if project_id else ""
    return {
        "client_secret_exists": secret_exists,
        "client_secret_path": str(CLIENT_SECRET_FILE),
        "project_id": project_id or "Bilinmeyen Proje",
        "client_id_preview": client_id_preview,
        "token_exists": token_exists,
        "is_connected": is_connected,
        "channel_profile": profile if is_connected else None,
        "urls": {
            "google_cloud_console": f"https://console.cloud.google.com/{proj_query}",
            "enable_youtube_api": f"https://console.cloud.google.com/apis/library/youtube.googleapis.com{proj_query}",
            "oauth_consent_screen": f"https://console.cloud.google.com/apis/credentials/consent{proj_query}",
            "credentials_page": f"https://console.cloud.google.com/apis/credentials{proj_query}",
            "test_users_guide": f"https://console.cloud.google.com/apis/credentials/consent{proj_query}"
        }
    }

def run_oauth_flow() -> Credentials:
    if not CLIENT_SECRET_FILE.exists():
        raise FileNotFoundError(f"Client secrets file not found at {CLIENT_SECRET_FILE}")
        
    # Clear any stale token before launching fresh server
    clear_cached_tokens()
    
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_FILE), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")
    
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(creds.to_json())
        
    print(f"[YOUTUBE] Successfully authorized and saved tokens to {TOKEN_FILE}")
    return creds

def get_youtube_service():
    creds = get_credentials()
    if not creds or not creds.valid:
        raise PermissionError("YouTube channel not authorized yet. Run OAuth flow first.")
    return build("youtube", "v3", credentials=creds)

def get_channel_profile() -> dict | None:
    """Fetch 100% real live profile info of the authorized YouTube channel from Google."""
    try:
        service = get_youtube_service()
        req = service.channels().list(mine=True, part="snippet,contentDetails,statistics")
        resp = req.execute()
        items = resp.get("items", [])
        if not items:
            return None
            
        c = items[0]
        snippet = c.get("snippet", {})
        stats = c.get("statistics", {})
        content_details = c.get("contentDetails", {})
        uploads_playlist = content_details.get("relatedPlaylists", {}).get("uploads", "")
        
        return {
            "channel_id": c.get("id"),
            "title": snippet.get("title", "My Channel"),
            "custom_url": snippet.get("customUrl", "@channel"),
            "published_at": snippet.get("publishedAt", ""),
            "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url") or snippet.get("thumbnails", {}).get("medium", {}).get("url") or snippet.get("thumbnails", {}).get("default", {}).get("url", ""),
            "subscriber_count": int(stats.get("subscriberCount", 0)),
            "video_count": int(stats.get("videoCount", 0)),
            "view_count": int(stats.get("viewCount", 0)),
            "uploads_playlist": uploads_playlist,
            "is_connected": True
        }
    except Exception as e:
        return {"is_connected": False, "error": str(e)}

def get_channel_live_videos() -> list:
    """Fetch actual list of videos uploaded on YouTube for this channel."""
    try:
        profile = get_channel_profile()
        if not profile or not profile.get("is_connected"):
            return []
            
        uploads_id = profile.get("uploads_playlist")
        if not uploads_id:
            return []
            
        service = get_youtube_service()
        req = service.playlistItems().list(
            playlistId=uploads_id,
            part="snippet,status",
            maxResults=20
        )
        resp = req.execute()
        items = resp.get("items", [])
        
        videos = []
        for it in items:
            snippet = it.get("snippet", {})
            res_id = snippet.get("resourceId", {})
            vid_id = res_id.get("videoId")
            if vid_id:
                videos.append({
                    "video_id": vid_id,
                    "title": snippet.get("title"),
                    "published_at": snippet.get("publishedAt"),
                    "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
                    "youtube_url": f"https://youtu.be/{vid_id}"
                })
        return videos
    except Exception as e:
        print(f"[WARN] Failed to fetch live channel videos: {e}")
        return []

from datetime import datetime, timezone, timedelta
import random

HISTORY_FILE = CONFIG_DIR / "upload_history.json"

def _load_upload_history_unlocked() -> list:
    """Reads upload history without locking (must be called within UPLOAD_LOCK)."""
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[WARN] Failed to read upload history: {e}")
        return []

def _save_upload_history_unlocked(history: list):
    """Atomically writes upload history to disk (must be called within UPLOAD_LOCK)."""
    try:
        temp_history = HISTORY_FILE.with_suffix(".tmp")
        with open(temp_history, "w", encoding="utf-8") as f:
            json.dump(history[-100:], f, indent=2, ensure_ascii=False)
        temp_history.replace(HISTORY_FILE)
    except Exception as e:
        print(f"[WARN] Failed to write upload history atomically: {e}")

def check_daily_upload_limit(max_per_day: int = 4) -> tuple[bool, int]:
    """Check how many videos were uploaded or are actively uploading today with re-entrant thread safety."""
    with UPLOAD_LOCK:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        history = _load_upload_history_unlocked()
        active_today = [
            h for h in history
            if isinstance(h, dict) and h.get("date") == today and h.get("status", "completed") in ["completed", "uploading"]
        ]
        count = len(active_today)
        return count < max_per_day, count

def reserve_daily_upload_slot(max_per_day: int = 4) -> tuple[bool, int, str]:
    """Atomically verifies the daily limit and reserves a slot before upload starts. Returns (can_upload, count, res_id)."""
    with UPLOAD_LOCK:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        history = _load_upload_history_unlocked()
        active_today = [
            h for h in history
            if isinstance(h, dict) and h.get("date") == today and h.get("status", "completed") in ["completed", "uploading"]
        ]
        count = len(active_today)
        if count >= max_per_day:
            return False, count, ""

        res_id = str(uuid.uuid4())[:8]
        history.append({
            "reservation_id": res_id,
            "status": "uploading",
            "date": today,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        _save_upload_history_unlocked(history)
        return True, count + 1, res_id

def release_upload_reservation(reservation_id: str):
    """Frees a reservation slot when upload fails or is aborted."""
    if not reservation_id:
        return
    with UPLOAD_LOCK:
        history = _load_upload_history_unlocked()
        for h in history:
            if isinstance(h, dict) and h.get("reservation_id") == reservation_id:
                h["status"] = "failed"
                h["failed_at"] = datetime.now(timezone.utc).isoformat()
                break
        _save_upload_history_unlocked(history)

def complete_upload_reservation(reservation_id: str, video_id: str, title: str):
    """Confirms reservation as a successfully completed YouTube upload."""
    with UPLOAD_LOCK:
        history = _load_upload_history_unlocked()
        matched = False
        if reservation_id:
            for h in history:
                if isinstance(h, dict) and h.get("reservation_id") == reservation_id:
                    h["status"] = "completed"
                    h["video_id"] = video_id
                    h["title"] = title
                    h["completed_at"] = datetime.now(timezone.utc).isoformat()
                    matched = True
                    break
        if not matched:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            history.append({
                "reservation_id": reservation_id or str(uuid.uuid4())[:8],
                "status": "completed",
                "video_id": video_id,
                "title": title,
                "date": today,
                "completed_at": datetime.now(timezone.utc).isoformat()
            })
        _save_upload_history_unlocked(history)

def record_upload(video_id: str, title: str):
    """Backward compatible wrapper for complete_upload_reservation."""
    complete_upload_reservation("", video_id, title)

def set_thumbnail(video_id: str, thumbnail_path: str) -> bool:
    """Sets custom thumbnail for uploaded YouTube video via YouTube Data API v3."""
    if not os.path.exists(thumbnail_path):
        print(f"[WARN] Thumbnail file not found: {thumbnail_path}")
        return False
    try:
        service = get_youtube_service()
        media = MediaFileUpload(thumbnail_path, mimetype="image/jpeg", resumable=True)
        req = service.thumbnails().set(videoId=video_id, media_body=media)
        req.execute()
        print(f"[YOUTUBE] Successfully set custom thumbnail for video {video_id}")
        return True
    except Exception as e:
        print(f"[WARN] Failed to set thumbnail for {video_id}: {e}")
        return False

def schedule_publish(video_id: str, delay_hours: int) -> bool:
    """
    Schedules a private video to go public automatically after delay_hours.
    Explicit delay_hours (> 0) is mandatory; no unsafe silent default.
    """
    if delay_hours <= 0:
        raise ValueError("Zamanlanmış yayınlama için açık bir pozitif gecikme (delay_hours > 0) belirtilmelidir.")
    try:
        service = get_youtube_service()
        pub_time = datetime.now(timezone.utc) + timedelta(hours=delay_hours)
        iso_str = pub_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        
        body = {
            "id": video_id,
            "status": {
                "privacyStatus": "private",
                "publishAt": iso_str
            }
        }
        req = service.videos().update(part="status", body=body)
        resp = req.execute()
        print(f"[YOUTUBE] Video {video_id} scheduled to publish at {iso_str}")
        return True
    except Exception as e:
        print(f"[WARN] Failed to schedule publish for {video_id}: {e}")
        return False

def generate_seo_metadata(topic: str, persona_id: str = "us_hustler") -> dict:
    """Generates high-CTR title, descriptive text, and high-ranking tags using Ollama."""
    from config.settings import load_settings
    settings = load_settings()
    model = settings.get("fast_model", "qwen3:8b")
    ollama_url = f"{settings['ollama_host'].rstrip('/')}/api/chat"

    prompt = f"""You are an elite YouTube SEO specialist.
Topic: {topic}
Persona: {persona_id}

Create high-CTR YouTube metadata in JSON format:
{{
  "title": "Short punchy title with high curiosity (under 80 chars)",
  "description": "Engaging 3-paragraph YouTube description with timestamps, keywords, and hashtags",
  "tags": ["15", "relevant", "high-volume", "search", "tags"]
}}
Output RAW JSON ONLY.
"""
    try:
        resp = requests.post(ollama_url, json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "format": "json",
            "stream": False
        }, timeout=30)
        return json.loads(resp.json().get("message", {}).get("content", "{}"))
    except Exception:
        return {
            "title": f"{topic}",
            "description": f"{topic}\n\nProduced by Global Wave AI Agency OS.\n#Documentary #Viral #Knowledge",
            "tags": ["Documentary", "Knowledge", "GlobalWave", "Viral", "History", "Science"]
        }

def get_warmup_checklist() -> list:
    """Returns the 7-day channel warmup safety protocol."""
    return [
        {"day": "Day 1-2", "task": "Organic browsing: Watch 15-20 mins in your niche, like 2 videos, write 1 thoughtful comment."},
        {"day": "Day 3-4", "task": "Profile setup: Add high-resolution banner, logo, custom channel handle, and detailed about bio."},
        {"day": "Day 5", "task": "Channel security: Enable 2-Factor Authentication and link phone recovery."},
        {"day": "Day 6", "task": "Unlisted test: Upload 1 test video as Unlisted or Private to check Content-ID & audio clearance."},
        {"day": "Day 7", "task": "First Public Release: Publish first high-retention video using 3-hour private delay buffer."}
    ]

def upload_short_video(
    video_path: str,
    title: str,
    description: str = "",
    tags: list = None,
    privacy_status: str = "private",  # Safe default: private first
    category_id: str = "28",
    thumbnail_path: str = None,
    auto_schedule: bool = False,      # Explicit user consent required for scheduled release
    delay_hours: int = 0,             # Default 0 (NO automatic public publishing)
    is_made_for_kids: bool = False,
    is_shorts: bool = True
) -> dict:
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
        
    # Atomically verify limit and reserve slot before upload begins
    can_upload, today_count, res_id = reserve_daily_upload_slot(max_per_day=4)
    if not can_upload:
        raise RuntimeError(f"Günlük maksimum güvenli yükleme sınırına ({today_count}/4) ulaşıldı. Kanal güvenliği ve spam koruması için işlem durduruldu.")

    try:
        service = get_youtube_service()
        
        clean_title = title.strip()
        if is_shorts:
            if "#Shorts" not in clean_title and "#shorts" not in clean_title:
                clean_title = f"{clean_title} #Shorts"
            if len(clean_title) > 100:
                clean_title = clean_title[:92] + " #Shorts"
        else:
            if len(clean_title) > 100:
                clean_title = clean_title[:97] + "..."
            
        if not description:
            tag_suffix = "#Shorts #Viral #AI" if is_shorts else "#Documentary #Knowledge #DeepDive"
            description = f"{clean_title}\n\nAutonomous documentary created by Global Wave AI Agency OS.\n{tag_suffix}"
        else:
            if is_shorts and "#Shorts" not in description:
                description = f"{description}\n\n#Shorts"

        default_tags = ["Shorts", "YouTube Shorts"] if is_shorts else ["Documentary", "Full Video", "Analysis"]
        default_tags += ["AI", "Technology", "Knowledge"]
        all_tags = list(set((tags or []) + default_tags))[:25]
        
        body = {
            "snippet": {
                "title": clean_title,
                "description": description,
                "tags": all_tags,
                "categoryId": category_id
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": bool(is_made_for_kids)
            }
        }
        
        print(f"[YOUTUBE] Initializing safe resumable upload for: '{clean_title}' (Privacy: {privacy_status})...")
        media = MediaFileUpload(
            video_path,
            chunksize=1024 * 1024 * 2,
            resumable=True,
            mimetype="video/mp4"
        )
        
        request = service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                print(f"[YOUTUBE] Uploading... {pct}%")
                
        video_id = response.get("id")
        video_url = f"https://youtu.be/{video_id}"
        print(f"[YOUTUBE] Upload SUCCESS! Video ID: {video_id} -> {video_url}")

        complete_upload_reservation(res_id, video_id, clean_title)

        # Optional custom thumbnail
        if thumbnail_path and os.path.exists(thumbnail_path):
            set_thumbnail(video_id, thumbnail_path)

        # Automatic delayed publish ONLY if explicit consent (auto_schedule=True) and delay_hours > 0
        publish_scheduled = False
        scheduled_at = None
        if auto_schedule and delay_hours > 0 and privacy_status == "private":
            ok = schedule_publish(video_id, delay_hours=delay_hours)
            publish_scheduled = ok
            if ok:
                pub_time = datetime.now(timezone.utc) + timedelta(hours=delay_hours)
                scheduled_at = pub_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        
        return {
            "status": "success",
            "video_id": video_id,
            "url": video_url,
            "title": response.get("snippet", {}).get("title"),
            "privacy": privacy_status,
            "publish_scheduled": publish_scheduled,
            "scheduled_publish_time": scheduled_at,
            "scheduled_delay_hours": delay_hours if (auto_schedule and privacy_status == "private") else 0
        }
    except Exception as e:
        release_upload_reservation(res_id)
        raise e
