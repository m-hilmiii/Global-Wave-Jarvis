"""
Global Wave - Material Engine (Multi-Tier Dual Search: Pexels + Pixabay + Local B-Roll)
Enhanced with Laya System 1 Semantic B-Roll Routing.
"""
import os
import re
import random
import subprocess
import requests
import hashlib
from pathlib import Path
from config.settings import load_settings, get_ffmpeg_bin, ASSETS_DIR, TEMP_WORKSPACE
from engine.laya_decision_engine import laya_engine

CACHE_DIR = TEMP_WORKSPACE / "pexels_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
FALLBACK_DIR = ASSETS_DIR / "fallback_broll"
LOCAL_BROLL_DIR = ASSETS_DIR / "local_broll"
LOCAL_BROLL_DIR.mkdir(parents=True, exist_ok=True)

FILLER_WORDS = {
    "vertical", "4k", "cinematic", "dark", "dramatic", "video", "footage",
    "hd", "macro", "ultra", "screen", "background", "retro", "aesthetic"
}

def sanitize_keyword(keyword: str) -> str:
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', keyword).strip().lower()
    words = [w for w in cleaned.split() if w not in FILLER_WORDS]
    if not words:
        words = cleaned.split()
    if not words:
        return "technology"
    return " ".join(words[:2])

def search_local_broll(keyword: str) -> str | None:
    if not LOCAL_BROLL_DIR.exists():
        return None
    videos = [f for f in LOCAL_BROLL_DIR.iterdir() if f.suffix.lower() in [".mp4", ".mov", ".mkv"]]
    if not videos:
        return None

    kw_tokens = set(keyword.lower().split())
    for v in videos:
        name_lower = v.name.lower()
        if any(token in name_lower for token in kw_tokens):
            print(f"[MATERIAL] Local b-roll match found for '{keyword}': {v.name}")
            return str(v)

    return None

def query_pexels_api(query_str: str, pexels_api_key: str, offset: int = 0, orientation: str = "portrait") -> str | None:
    pexels_orient = "landscape" if orientation in ["landscape", "horizontal"] else "portrait"
    url = f"https://api.pexels.com/videos/search?query={requests.utils.quote(query_str)}&orientation={pexels_orient}&size=medium&per_page=10"
    headers = {"Authorization": pexels_api_key}
    
    try:
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code != 200:
            return None
        data = resp.json()
        videos = data.get("videos", [])
        if not videos:
            return None
            
        pick_pool = videos[offset:offset+4] if offset < len(videos) else videos
        if not pick_pool:
            pick_pool = videos
        video = random.choice(pick_pool)
        files = video.get("video_files", [])
        
        is_landscape = (pexels_orient == "landscape")
        
        # 1. Look for high-res matching aspect ratio
        for vf in files:
            w = vf.get("width") or 0
            h = vf.get("height") or 0
            if is_landscape and w > h and w >= 1280:
                return vf.get("link")
            elif not is_landscape and h > w and h >= 1080:
                return vf.get("link")
                
        # 2. Look for any matching aspect ratio
        for vf in files:
            w = vf.get("width") or 0
            h = vf.get("height") or 0
            if is_landscape and w > h:
                return vf.get("link")
            elif not is_landscape and h > w:
                return vf.get("link")
                
        return files[0].get("link") if files else None
    except Exception as e:
        print(f"[WARN] Pexels query error for '{query_str}': {e}")
        return None

def query_pixabay_api(query_str: str, pixabay_api_key: str = None, orientation: str = "portrait") -> str | None:
    if not pixabay_api_key:
        return None
    url = f"https://pixabay.com/api/videos/?key={pixabay_api_key}&q={requests.utils.quote(query_str)}&per_page=6"
    try:
        resp = requests.get(url, timeout=12)
        if resp.status_code != 200:
            return None
        data = resp.json()
        hits = data.get("hits", [])
        if not hits:
            return None
        hit = random.choice(hits[:3])
        videos = hit.get("videos", {})
        chosen = videos.get("medium") or videos.get("small") or videos.get("large")
        if chosen and "url" in chosen:
            return chosen["url"]
        return None
    except Exception as e:
        print(f"[WARN] Pixabay query error for '{query_str}': {e}")
        return None

from urllib.parse import urlparse

ALLOWED_VIDEO_DOMAINS = (
    "pexels.com",
    "pixabay.com",
    "akamaized.net",
    "cloudfront.net",
    "images.pexels.com",
    "player.vimeo.com"
)
MAX_CLIP_BYTES = 50 * 1024 * 1024  # 50MB max limit per B-roll clip

def download_video_cached(url: str, keyword: str, force_refresh: bool = False, orientation: str = "portrait") -> str:
    """Downloads a video clip safely with domain validation, size bounding, and atomic file write."""
    # 1. URL Domain validation
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if not any(hostname == d or hostname.endswith("." + d) for d in ALLOWED_VIDEO_DOMAINS):
        raise ValueError(f"Güvenlik kısıtlaması: Onaylanmamış medya CDN alan adı ({hostname}) üzerinden indirme engellendi.")

    orient_prefix = "land" if orientation in ["landscape", "horizontal"] else "port"
    clean_kw = re.sub(r'[^a-zA-Z0-9_]', '_', sanitize_keyword(keyword))[:25]
    url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    out_path = CACHE_DIR / f"clip_{orient_prefix}_{clean_kw}_{url_hash}.mp4"
    
    if out_path.exists() and not force_refresh and out_path.stat().st_size > 1024:
        return str(out_path)

    # 2. Stream with byte bounding
    resp = requests.get(url, stream=True, timeout=25)
    resp.raise_for_status()
    
    # Check Content-Length if present
    cl = resp.headers.get("content-length")
    if cl and int(cl) > MAX_CLIP_BYTES:
        raise ValueError(f"Medya dosyası boyutu ({int(cl)/(1024*1024):.1f}MB) maksimum sınırı (50MB) aşıyor.")

    tmp_out = out_path.with_suffix(".tmp")
    downloaded = 0
    try:
        with open(tmp_out, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 128):
                if chunk:
                    downloaded += len(chunk)
                    if downloaded > MAX_CLIP_BYTES:
                        raise ValueError("Medya dosyası akış sırasında 50MB sınırını aştı; indirme durduruldu.")
                    f.write(chunk)
        tmp_out.replace(out_path)
    finally:
        if tmp_out.exists():
            try:
                tmp_out.unlink()
            except Exception:
                pass
            
    return str(out_path)

def get_clip_for_scene(
    scene_id: int,
    visual_keyword: str,
    required_duration: float,
    task_temp_dir: str,
    force_refresh: bool = False,
    orientation: str = "portrait"
) -> str:
    routed_query = laya_engine.route_broll_keyword(visual_keyword, default_kw=visual_keyword)
    clean_kw = sanitize_keyword(routed_query)
    
    settings = load_settings()
    pexels_key = settings.get("pexels_api_key", "")
    pixabay_key = settings.get("pixabay_api_key", "")
    
    # Tier 1: Local B-Roll
    local_hit = search_local_broll(clean_kw)
    if local_hit:
        return local_hit

    # Tier 2: Pexels API
    if pexels_key:
        offset = random.randint(1, 3) if force_refresh else 0
        print(f"[MATERIAL/LAYA] Querying Pexels ({orientation}) with query: '{clean_kw}'")
        video_url = query_pexels_api(clean_kw, pexels_key, offset=offset, orientation=orientation)
        if video_url:
            try:
                return download_video_cached(video_url, clean_kw, force_refresh=force_refresh, orientation=orientation)
            except Exception as e:
                print(f"[WARN] Failed to download Pexels clip: {e}")

    # Tier 3: Pixabay API Fallback
    if pixabay_key:
        print(f"[MATERIAL/LAYA] Pixabay fallback query: '{clean_kw}'")
        pixabay_url = query_pixabay_api(clean_kw, pixabay_key, orientation=orientation)
        if pixabay_url:
            try:
                return download_video_cached(pixabay_url, f"pixabay_{clean_kw}", force_refresh=force_refresh, orientation=orientation)
            except Exception as e:
                print(f"[WARN] Failed to download Pixabay clip: {e}")

    # Tier 4: Fallback directory
    if FALLBACK_DIR.exists():
        fb_clips = [f for f in FALLBACK_DIR.iterdir() if f.suffix.lower() in [".mp4", ".mov", ".mkv"]]
        if fb_clips:
            chosen = random.choice(fb_clips)
            print(f"[MATERIAL] Using fallback library b-roll: {chosen.name}")
            return str(chosen)

    # Tier 5: Procedural FFmpeg motion generator
    out_clip = os.path.join(task_temp_dir, f"procedural_{scene_id}.mp4")
    return _generate_procedural_motion_clip(clean_kw, required_duration, out_clip, orientation=orientation)

def _generate_procedural_motion_clip(keyword: str, duration: float, out_path: str, orientation: str = "portrait") -> str:
    ffmpeg_bin = get_ffmpeg_bin()
    res = "1920x1080" if orientation in ["landscape", "horizontal"] else "1080x1920"
    vf = (
        f"color=c=0x0a0c10:s={res}:r=30,"
        f"drawtext=text='{keyword.upper()}':fontcolor=0x40ffffff:fontsize=76:x=(w-text_w)/2:y=(h-text_h)/2-100:font=Arial Black,"
        "noise=alls=15:allf=t+u"
    )
    cmd = [
        ffmpeg_bin, "-y",
        "-f", "lavfi",
        "-i", vf,
        "-t", f"{duration:.3f}",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        out_path
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    return out_path