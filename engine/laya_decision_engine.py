"""
Global Wave - System 1 Decision Engine (Powered by Laya v0.3.21)
Hybrid Pattern: Deterministic Hard Rules + Multilingual Decision Model.
1. Instant Audience Feedback & Comment Triage (<0.8s for 30 comments)
2. Semantic B-Roll Stock Video Category Routing (Turkish script -> High-resolution Pexels/Pixabay tags)
3. Pre-flight Video Script Quality & Hook Auditing
"""
import os
import time
import re
import threading
from typing import List, Dict, Any, Optional

BROLL_CATEGORIES = {
    "artificial intelligence robotics": "yapay zeka, kodlama, robot, sunucu, siber, yazilim, teknoloji, gelecek, veri, algoritma",
    "financial crypto market": "kripto, bitcoin, borsa, hisse, para, zenginlik, grafik, yukselis, ticaret, dolar, ekonomi",
    "deep space cosmos": "uzay, gezegen, karadelik, roket, galaksi, yildizlar, nasa, astronot, evren, teleskop",
    "luxury urban lifestyle": "luks araba, sehir, metropol, gokdelen, gece hayati, basari, zengin, spor araba, penthouse",
    "cinematic nature landscape": "doga, orman, selale, dag, deniz, okyanus, firtina, gun batimi, manzara, vahsi doga",
    "dramatic human emotion": "insan yuzu, saskinlik, heyecan, korku, odaklanma, konusma, kararlilik, gozler, stres",
    "ancient history mystery": "tarih, antik, piramit, savas, roma, misir, imparatorluk, gizem, arkeoloji, mitoloji",
    "modern science laboratory": "bilim, laboratuvar, mikroskop, deney, dna, arastirma, kimya, asi, tip, bulus",
    "cyber security hacker": "hacker, guvenlik, sifre, karanlik oda, ekranlar, terminal, matrix, kod, sizinti"
}

class LayaDecisionEngine:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(LayaDecisionEngine, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.router = None
        self.agent = None
        self.is_ready = False
        self._init_error = None
        self._load_agent()
        self._initialized = True

    def _load_agent(self):
        try:
            from laya import Router
            self.router = Router(default="multilingual")
            self.agent = self.router.load("multilingual")
            self.is_ready = True
            print("[LAYA] System 1 Decision Engine successfully initialized (Multilingual mmBERT-base).")
        except Exception as e:
            self._init_error = str(e)
            print(f"[WARN] Laya Decision Engine failed to load, falling back to rule heuristics: {e}")
            self.is_ready = False

    def _hard_rule_broll(self, text: str) -> Optional[str]:
        """Awesome-Jev Guardrail Pattern: Instant exact rule match with strict word boundaries to prevent substring collisions."""
        t = text.lower()
        rules = [
            (r"\b(yapay zeka|ai|robot|sunucu|yazılım|yazilim|kodlama)\b", "artificial intelligence robotics"),
            (r"\b(kripto|bitcoin|borsa|para|grafik|hisse|finans)\b", "financial crypto market"),
            (r"\b(uzay|gezegen|karadelik|roket|galaksi|astronot)\b", "deep space cosmos"),
            (r"\b(lüks|luks|spor araba|gökdelen|gokdelen|penthouse)\b", "luxury urban lifestyle"),
            (r"\b(orman|şelale|selale|okyanus|doğa|doga)\b", "cinematic nature landscape"),
            (r"\b(piramit|antik|gladyatör|gladyator|tarih|imparatorluk)\b", "ancient history mystery"),
            (r"\b(hacker|siber|şifre|sifre|sızıntı|sizinti)\b", "cyber security hacker"),
            (r"\b(laboratuvar|dna|mikroskop|aşı|asi)\b", "modern science laboratory"),
        ]
        for pattern, category in rules:
            if re.search(pattern, t):
                return category
        return None

    def route_broll_keyword(self, scene_text: str, default_kw: str = "technology") -> str:
        """
        Hybrid Semantic Tag Resolution:
        1. Exact Rule Gating (~0 ms)
        2. Laya System 1 Neural Choice (~20 ms)
        """
        if not scene_text or not scene_text.strip():
            return default_kw

        rule_match = self._hard_rule_broll(scene_text)
        if rule_match:
            return rule_match

        if self.is_ready and self.agent:
            try:
                questions = {
                    "category": {
                        "type": "choice",
                        "instructions": "Bu video sahnesi icin en uygun gorsel stok video kategorisi hangisidir?",
                        "criteria": BROLL_CATEGORIES
                    }
                }
                res = self.agent.system_one(scene_text.strip(), questions, lang="tr")
                ans = res.get("answers", {}).get("category", {})
                choice = ans.get("choice")
                if choice and choice in BROLL_CATEGORIES:
                    return choice
            except Exception as e:
                print(f"[LAYA] B-Roll routing error: {e}")

        return default_kw

    def analyze_comments(self, comments: List[str]) -> Dict[str, Any]:
        """
        Processes batch of YouTube comments (<1s for 30 comments).
        Returns aggregated sentiment score, top audience demands, and complaints.
        """
        if not comments:
            return {
                "sentiment_score": 90,
                "positive_count": 0,
                "negative_count": 0,
                "demands": [],
                "complaints": []
            }

        cleaned = [c.strip() for c in comments if c and len(c.strip()) > 3]
        if not cleaned:
            cleaned = comments

        if not self.is_ready or not self.agent:
            return self._heuristic_comment_analysis(cleaned)

        questions = {
            "sentiment": {
                "type": "choice",
                "instructions": "Izleyici duygusu nedir?",
                "criteria": {
                    "positive": "begeni, ovgu, tebrik, tesekkur, bayildim, super, harika, efsane, devam",
                    "negative": "elestiri, sikayet, sorun, kotu, ses duyulmuyor, berbat, begenmedim, sikici",
                    "neutral": "soru, oneri, normal, merak"
                }
            },
            "has_request": {
                "type": "noul",
                "instructions": "Izleyici yeni bir video konusu, icerik veya ozellik talep ediyor mu?"
            },
            "has_complaint": {
                "type": "noul",
                "instructions": "Izleyici videonun bir kismindan (ses, hiz, gorsel) sikayetci mi?"
            }
        }

        try:
            results = self.agent.predict_batch(cleaned, questions, lang="tr")
            pos_count = 0
            neg_count = 0
            neu_count = 0
            demands = []
            complaints = []

            for comment, res in zip(cleaned, results):
                answers = res.get("answers", {})
                sentiment = answers.get("sentiment", {}).get("choice", "neutral")
                req_prob = answers.get("has_request", {}).get("noul", 0.0)
                comp_prob = answers.get("has_complaint", {}).get("noul", 0.0)

                if sentiment == "positive":
                    pos_count += 1
                elif sentiment == "negative":
                    neg_count += 1
                else:
                    neu_count += 1

                if req_prob >= 0.40:
                    demands.append({"text": comment, "score": round(req_prob, 2)})
                if comp_prob >= 0.45 or sentiment == "negative":
                    complaints.append({"text": comment, "score": round(comp_prob, 2)})

            total = max(1, pos_count + neg_count + neu_count)
            sentiment_score = int(round(((pos_count + 0.5 * neu_count) / total) * 100))
            sentiment_score = max(50, min(99, sentiment_score))

            demands.sort(key=lambda x: x["score"], reverse=True)
            complaints.sort(key=lambda x: x["score"], reverse=True)

            return {
                "sentiment_score": sentiment_score,
                "positive_count": pos_count,
                "negative_count": neg_count,
                "neutral_count": neu_count,
                "demands": [d["text"] for d in demands[:4]],
                "complaints": [c["text"] for c in complaints[:3]],
                "engine": "laya_system_one_multilingual"
            }
        except Exception as e:
            print(f"[LAYA] Batch comment analysis failed: {e}, falling back to heuristic")
            return self._heuristic_comment_analysis(cleaned)

    def _heuristic_comment_analysis(self, comments: List[str]) -> Dict[str, Any]:
        pos_words = ["harika", "guzel", "tebrik", "eline saglik", "super", "efsane", "bayildim", "akici", "mukemmel"]
        # Contextual negative patterns: prevent isolated words like 'ses' or 'hizli' from poisoning positive comments
        neg_patterns = [
            r"\b(kotu|berbat|sikayet|anlasilmiyor|rezalet|berbat|duyulmuyor)\b",
            r"\b(ses\s+(kotu|berbat|kisik|anlasilmiyor|gelmiyor|duyulmuyor|cok kotu))\b",
            r"\b(cok\s+hizli|asiri\s+hizli|yetisemiyorum)\b",
        ]
        req_words = ["yap", "ceker misin", "gelsin", "lutfen", "istiyoruz", "anlat", "yeni video"]

        pos, neg = 0, 0
        demands, complaints = [], []
        for c in comments:
            low = c.lower()
            is_pos = any(w in low for w in pos_words)
            is_neg = any(re.search(pat, low) for pat in neg_patterns)
            
            if is_pos and not is_neg:
                pos += 1
            elif is_neg:
                neg += 1
                complaints.append(c)
                
            if any(w in low for w in req_words) and not is_neg:
                demands.append(c)

        total = max(1, len(comments))
        score = int(round(max(0.6, (pos + 1) / (pos + neg + 2)) * 100))
        return {
            "sentiment_score": min(98, score),
            "positive_count": pos,
            "negative_count": neg,
            "demands": demands[:3],
            "complaints": complaints[:2],
            "engine": "heuristic_fallback"
        }

# Global singleton
laya_engine = LayaDecisionEngine()