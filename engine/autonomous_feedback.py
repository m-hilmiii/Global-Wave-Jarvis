"""
Global Wave - Autonomous Feedback & Persona Intelligence Engine (Modül 4)
Powered by Laya System 1 Decision Engine + Ollama System 2 Synthesis.
"""
import os
import json
import requests
from datetime import datetime
from pathlib import Path
from config.settings import load_settings, CONFIG_DIR
from engine.uploader_youtube import get_youtube_service
from engine.laya_decision_engine import laya_engine

REPORTS_DIR = CONFIG_DIR / "channel_reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_REPORT = {
    "channel_id": "default",
    "channel_title": "Mücahit Hilmi",
    "generated_at": datetime.now().isoformat(),
    "is_simulated": True,
    "source": "demo_baseline",
    "sample_size": 0,
    "sentiment_score": 94,
    "sentiment_summary": "İzleyiciler yüksek tempolu, gizem ve teknoloji odaklı anlatımı çok beğeniyor.",
    "audience_demands": [
        "Hızlı ve şaşırtıcı yapay zeka & bilim kurgu gerçekleri",
        "Mühendislik ve uzay felaketlerinin perde arkası",
        "Kısa ve net 0-3 saniye çarpıcı kanca cümleleri"
    ],
    "strengths": [
        "MrBeast tarzı sarı karaoke altyazı akışı",
        "ShortGPT mikro whoosh geçiş sesleri dikkati taze tutuyor",
        "Ses tonu dinamik ve profesyonel"
    ],
    "weaknesses_to_avoid": [
        "Açılışta 'Merhaba arkadaşlar' gibi klişe girişler yapma",
        "Aynı konu üzerinde 8 saniyeden fazla durma",
        "Görsellerde konuyla alakasız genel stoklar kullanma"
    ],
    "persona_tuning": {
        "humor_level": "Hafif sarkastik, zeki",
        "energy_level": "9/10 Yüksek tempolu ve merak uyandırıcı",
        "catchphrase": "İşte kimsenin anlatmadığı o gerçek..."
    },
    "seo_keywords": [
        "YouTube Shorts", "Uzay Felaketleri", "Yapay Zeka", "Mühendislik Sırları", "Teknoloji"
    ],
    "decision_engine": "Laya System 1 (ModernBERT/mmBERT) + Ollama"
}

def get_report_path(channel_id: str) -> Path:
    safe_id = "".join([c for c in channel_id if c.isalnum() or c in ("-", "_")])
    return REPORTS_DIR / f"report_{safe_id}.json"

def get_channel_report(channel_id: str = "default") -> dict:
    path = get_report_path(channel_id)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to load channel report: {e}")
    return DEFAULT_REPORT

def fetch_youtube_comments(channel_id: str, max_comments: int = 30) -> tuple:
    comments = []
    is_real = False
    try:
        service = get_youtube_service()
        req = service.search().list(
            channelId=channel_id,
            part="id,snippet",
            order="date",
            maxResults=5,
            type="video"
        )
        resp = req.execute()
        items = resp.get("items", [])
        
        for item in items:
            video_id = item.get("id", {}).get("videoId")
            if not video_id:
                continue
            try:
                c_req = service.commentThreads().list(
                    videoId=video_id,
                    part="snippet",
                    maxResults=10,
                    textFormat="plainText"
                )
                c_resp = c_req.execute()
                for c_item in c_resp.get("items", []):
                    top_c = c_item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                    t_val = top_c.get("textDisplay", "").strip()
                    if t_val:
                        comments.append(t_val)
                        is_real = True
            except Exception:
                pass
    except Exception as e:
        print(f"[INFO] YouTube API comment fetch note: {e} (Using bootstrap sample comments)")

    if not comments:
        comments = [
            "Bu roket patlaması videosu harika olmuş, uzay istasyonu kazasını da yapar mısın?",
            "Ses tonu ve kelime kelime yanan altyazı inanılmaz akıcı, tebrikler!",
            "Kısa ve öz anlatmışsınız, gereksiz uzatmamışsınız elinize sağlık.",
            "Yapay zeka sırları hakkında da bir shorts gelsin lütfen!",
            "Girişteki ses efekti harikaydı, videodan gözümü alamadım."
        ]
        meta = {
            "source": "sample_bootstrap",
            "is_simulated": True,
            "sample_size": len(comments)
        }
    else:
        meta = {
            "source": "youtube_live_api",
            "is_simulated": False,
            "sample_size": len(comments)
        }
    return comments[:max_comments], meta

def run_feedback_analysis(channel_id: str, channel_title: str = "Mücahit Hilmi") -> dict:
    comments, comment_meta = fetch_youtube_comments(channel_id)
    print(f"[FEEDBACK] Running Laya System 1 Decision Analysis on {len(comments)} comments...")
    
    # 1. Tier 1: Laya Decision Engine
    laya_insights = laya_engine.analyze_comments(comments)
    sentiment_score = laya_insights.get("sentiment_score", 92)
    demands = laya_insights.get("demands", [])
    complaints = laya_insights.get("complaints", [])

    # 2. Tier 2: Ollama Synthesis
    settings = load_settings()
    ollama_host = settings.get("ollama_host", "http://127.0.0.1:11434")
    model = settings.get("default_model", "qwen3:14b")

    prompt = f"""Kanal: {channel_title}
Analiz Edilen Yorum Sayısı: {len(comments)}
Laya Olasılık Skoru: %{sentiment_score} Pozitif
İzleyici Talepleri: {json.dumps(demands, ensure_ascii=False)}
İzleyici Eleştirileri: {json.dumps(complaints, ensure_ascii=False)}

GÖREV: Bu verilere dayanarak kanal için JSON formatında 'Kanal İçerik Raporu' oluştur.
SADECE JSON döndür:
{{
  "sentiment_summary": "1 cümlelik izleyici özeti",
  "audience_demands": ["Talep 1", "Talep 2", "Talep 3"],
  "strengths": ["Güçlü yön 1", "Güçlü yön 2"],
  "weaknesses_to_avoid": ["Kaçınılacak hata 1", "Kaçınılacak hata 2"],
  "persona_tuning": {{
    "humor_level": "Sarkastik ve zeki",
    "energy_level": "9/10 Tempolu ve merak uyandırıcı",
    "catchphrase": "İşte kimsenin anlatmadığı o gerçek..."
  }},
  "seo_keywords": ["Yapay Zeka", "Uzay", "Teknoloji", "YouTube Shorts"]
}}"""

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.2}
    }

    report = None
    try:
        resp = requests.post(f"{ollama_host}/api/chat", json=payload, timeout=20)
        if resp.status_code == 200:
            parsed = json.loads(resp.json().get("message", {}).get("content", "{}"))
            report = parsed
    except Exception as e:
        print(f"[INFO] Ollama synthesis skipped ({e}), assembling direct Laya report.")

    if not report:
        report = {
            "sentiment_summary": f"İzleyici sadakati yüksek (%{sentiment_score}); anlatım temposu ve karaoke altyazı akışı takdir topluyor.",
            "audience_demands": demands if demands else DEFAULT_REPORT["audience_demands"],
            "strengths": [
                "Karaoke altyazı temposu ve dinamik seslendirme izleyiciyi ekranda tutuyor.",
                "ShortGPT geçiş ses efektleri retention oranını artırıyor."
            ],
            "weaknesses_to_avoid": complaints if complaints else DEFAULT_REPORT["weaknesses_to_avoid"],
            "persona_tuning": DEFAULT_REPORT["persona_tuning"],
            "seo_keywords": DEFAULT_REPORT["seo_keywords"]
        }

    report["sentiment_score"] = sentiment_score
    report["channel_id"] = channel_id
    report["channel_title"] = channel_title
    report["generated_at"] = datetime.now().isoformat()
    report["is_simulated"] = comment_meta["is_simulated"]
    report["source"] = comment_meta["source"]
    report["sample_size"] = comment_meta["sample_size"]
    report["decision_engine"] = "Laya v0.3.21 System 1"

    path = get_report_path(channel_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"[FEEDBACK] Report generated and saved for {channel_title} (Score: %{sentiment_score})")
    return report