import hashlib
"""
Global Wave - Automated High-CTR Thumbnail Engine (Faz 5)
Generates 1280x720 YouTube thumbnails engineered for maximum Click-Through-Rate (CTR).
Features:
1. Pexels Landscape Photo integration with cinematic color grading.
2. High-contrast typography with heavy outline, drop-shadow, and gradient darkening.
3. 4 High-CTR Presets: danger_red, curiosity_yellow, split_compare, record_stats.
4. Mobile-optimized readability (guaranteed readable on 5-inch phone screens).
"""
import math
import os
import random
import re
import requests
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

from config.settings import load_settings, ASSETS_DIR, OUTPUT_DIR, TEMP_WORKSPACE

THUMBNAILS_DIR = OUTPUT_DIR / "thumbnails"
THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)

PRESETS = {
    "danger_red": {
        "primary_color": (255, 42, 42),       # High-alert red
        "secondary_color": (255, 255, 255),   # Crisp white
        "outline_color": (0, 0, 0),
        "badge_bg": (220, 20, 20),
        "badge_text": "CRITICAL"
    },
    "curiosity_yellow": {
        "primary_color": (255, 235, 0),      # Electric yellow
        "secondary_color": (255, 255, 255),
        "outline_color": (10, 10, 10),
        "badge_bg": (255, 215, 0),
        "badge_text": "UNSOLVED"
    },
    "split_compare": {
        "primary_color": (0, 225, 255),      # Cyan electric
        "secondary_color": (255, 80, 80),    # Contrasting coral
        "outline_color": (0, 0, 0),
        "badge_bg": (0, 150, 255),
        "badge_text": "VS"
    },
    "record_stats": {
        "primary_color": (50, 255, 120),     # Neon matrix green
        "secondary_color": (255, 255, 255),
        "outline_color": (0, 0, 0),
        "badge_bg": (0, 180, 80),
        "badge_text": "RECORD"
    }
}

def get_font(size: int = 72) -> ImageFont.FreeTypeFont:
    """Finds the best bold font on Windows or falls back gracefully."""
    font_candidates = [
        "C:\\Windows\\Fonts\\impact.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf",
        str(ASSETS_DIR / "fonts" / "BeVietnamPro-Bold.ttf"),
        "C:\\Windows\\Fonts\\segoeuib.ttf"
    ]
    for p in font_candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()

def fetch_pexels_photo(query_str: str, api_key: str, out_path: str) -> bool:
    """Fetches high-res landscape photograph from Pexels."""
    url = f"https://api.pexels.com/v1/search?query={requests.utils.quote(query_str)}&orientation=landscape&per_page=8"
    headers = {"Authorization": api_key}
    try:
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            photos = data.get("photos", [])
            if photos:
                photo = random.choice(photos[:4])
                img_url = photo.get("src", {}).get("large2x") or photo.get("src", {}).get("large")
                if img_url:
                    img_resp = requests.get(img_url, timeout=15)
                    if img_resp.status_code == 200:
                        with open(out_path, "wb") as f:
                            f.write(img_resp.content)
                        return True
    except Exception as e:
        print(f"[WARN] Pexels photo query failed: {e}")
    return False

def generate_procedural_background(width: int = 1280, height: int = 720, base_color=(15, 20, 35)) -> Image.Image:
    """Creates a dark cinematic radial gradient background."""
    img = Image.new("RGB", (width, height), color=base_color)
    draw = ImageDraw.Draw(img)
    center_x, center_y = width // 2, height // 2
    max_radius = int(math.hypot(center_x, center_y))

    for r in range(max_radius, 0, -15):
        alpha = int(60 * (1 - r / max_radius))
        col = (
            min(255, base_color[0] + alpha),
            min(255, base_color[1] + int(alpha * 1.2)),
            min(255, base_color[2] + int(alpha * 1.8))
        )
        draw.ellipse(
            [center_x - r, center_y - r, center_x + r, center_y + r],
            fill=col
        )
    return img.filter(ImageFilter.GaussianBlur(radius=15))

def generate_thumbnail(
    topic: str,
    out_path: str = None,
    style_preset: str = "danger_red",
    custom_bg_path: str = None,
    preset: str = None
) -> str:
    """
    Main thumbnail generation pipeline.
    Creates 1280x720 thumbnail with high CTR typography and contrast.
    """
    width, height = 1280, 720
    effective_preset_name = preset or style_preset or "danger_red"
    preset = PRESETS.get(effective_preset_name, PRESETS["danger_red"])
    settings = load_settings()
    pexels_key = settings.get("pexels_api_key", "")

    # 1. Base Image
    base_img = None
    if custom_bg_path and os.path.exists(custom_bg_path):
        try:
            base_img = Image.open(custom_bg_path).convert("RGB")
        except Exception:
            base_img = None

    if base_img is None and pexels_key:
        clean_kw = re.sub(r'[^a-zA-Z0-9\s]', '', topic).strip()[:30]
        kw_hash = hashlib.sha256(clean_kw.encode("utf-8")).hexdigest()[:10]
        temp_photo = os.path.join(TEMP_WORKSPACE, f"thumb_bg_{kw_hash}.jpg")
        if fetch_pexels_photo(clean_kw, pexels_key, temp_photo):
            try:
                base_img = Image.open(temp_photo).convert("RGB")
            except Exception:
                base_img = None

    if base_img is None:
        base_img = generate_procedural_background(width, height)
    else:
        # Resize & Crop to 1280x720
        base_img = base_img.resize((width, height), Image.Resampling.LANCZOS)
        # Increase contrast and slight saturation for cinematic pop
        enhancer = ImageEnhance.Contrast(base_img)
        base_img = enhancer.enhance(1.25)
        color_enhancer = ImageEnhance.Color(base_img)
        base_img = color_enhancer.enhance(1.2)

    # 2. Add Darkening Vignette Layer on Left/Bottom (Ensures Text Legibility)
    vignette = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    vdraw = ImageDraw.Draw(vignette)
    for x in range(width):
        # Darker on the left half where text sits
        factor = max(0.0, 1.0 - (x / (width * 0.75)))
        alpha = int(180 * factor)
        vdraw.line([(x, 0), (x, height)], fill=(0, 0, 0, alpha))
    base_img = Image.alpha_composite(base_img.convert("RGBA"), vignette).convert("RGB")

    draw = ImageDraw.Draw(base_img)

    # 3. Format Punchy Title (Max 3 lines, high impact words)
    clean_words = topic.upper().split()
    lines = []
    current_line = []
    for w in clean_words:
        current_line.append(w)
        if len(" ".join(current_line)) > 16:
            if len(current_line) > 1:
                current_line.pop()
                lines.append(" ".join(current_line))
                current_line = [w]
            else:
                lines.append(" ".join(current_line))
                current_line = []
    if current_line:
        lines.append(" ".join(current_line))
    lines = lines[:3]  # Max 3 lines

    font_size = 84 if len(lines) <= 2 else 72
    font = get_font(font_size)

    # 4. Draw Badge (e.g. CRITICAL / UNSOLVED)
    badge_text = preset.get("badge_text", "FACTS")
    badge_font = get_font(34)
    badge_x, badge_y = 60, 50
    badge_w = int(draw.textlength(badge_text, font=badge_font)) + 36
    badge_h = 52
    draw.rectangle(
        [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h],
        fill=preset["badge_bg"]
    )
    draw.text((badge_x + 18, badge_y + 8), badge_text, font=badge_font, fill=(255, 255, 255))

    # 5. Render Title Lines with Heavy Stroke & Drop Shadow
    start_y = 140
    line_spacing = font_size + 16

    for idx, line in enumerate(lines):
        color = preset["primary_color"] if idx == 0 else preset["secondary_color"]
        pos_x = 60
        pos_y = start_y + (idx * line_spacing)

        # Drop shadow
        draw.text((pos_x + 6, pos_y + 6), line, font=font, fill=(0, 0, 0), stroke_width=8, stroke_fill=(0, 0, 0))
        # Main text with bold outline
        draw.text((pos_x, pos_y), line, font=font, fill=color, stroke_width=6, stroke_fill=preset["outline_color"])

    # 6. Save Final Image
    if not out_path:
        topic_hash = hashlib.sha256(topic.encode("utf-8")).hexdigest()[:10]
        out_name = f"thumb_{topic_hash}_{random.randint(100, 999)}.jpg"
        out_path = str(THUMBNAILS_DIR / out_name)

    base_img.save(out_path, format="JPEG", quality=92)
    print(f"[THUMBNAIL] Generated high-CTR thumbnail ({style_preset}): {out_path}")
    return out_path
