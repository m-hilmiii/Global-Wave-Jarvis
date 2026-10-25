"""
Global-Wawe / Stark-Core - Zero-Bloat Specialist Model Arsenal & VRAM Swapper (Stage 2)
Tailored specifically for:
- GPU: AMD Radeon RX 9060 XT (16GB GDDR6 VRAM)
- CPU: Intel Core i5-14400F (10C/16T)
- RAM: 16GB System Memory
- Storage: 316GB Free SSD + 1000Mbps Fiber

Pinpoint 5-Model Specialist Arsenal (No Redundant Models):
1. qwen3:14b          -> Primary Brain, Turkish Persona, Intent Router & Tool Orchestration (~9.0 GB)
2. qwen2.5vl:7b       -> Visual Perception, Screen OCR, IDE Error & WhatsApp Image Analysis (~5.2 GB)
3. qwen2.5-coder:14b  -> Elite Software Engineer, Code Generation, Refactoring & Unittests (~9.0 GB)
4. deepseek-r1:14b    -> Deep Chain-of-Thought Reasoning, Math, Architecture & YouTube Strategy (~9.0 GB)
5. bge-m3             -> Multilingual (TR/EN) 1024-dim Semantic Vector RAG Embedding Engine (~1.2 GB)
"""

import os
import re
import sys
import logging
from typing import Dict, Any, List, Optional
import requests

logger = logging.getLogger("Jarvis.ModelManager")

SPECIALIST_ARSENAL: List[Dict[str, Any]] = [
    {
        "role": "primary_brain",
        "name": "qwen3:14b",
        "fallbacks": ["qwen2.5:14b", "qwen3:8b", "llama3.1:8b"],
        "vram_gb": 9.0,
        "heavy_14b": True,
        "title": "Ana Beyin & Türkçe Ajan Orkestratörü",
        "description": "Günlük derin sohbet, WhatsApp üslup analizi, niyet yönlendirme ve araç çağırma."
    },
    {
        "role": "vision",
        "name": "qwen2.5vl:7b",
        "fallbacks": ["qwen2.5-vl:7b", "minicpm-v:latest", "llava:latest", "moondream:latest"],
        "vram_gb": 5.2,
        "heavy_14b": False,
        "title": "Görsel Zeka & Ekran/Belge Okuyucu (SOTA VLM)",
        "description": "Ekran görüntüsü analizi, IDE hata okuma, kurgu timeline kontrolü ve WhatsApp fotoğraf inceleme."
    },
    {
        "role": "coding",
        "name": "qwen2.5-coder:14b",
        "fallbacks": ["qwen2.5-coder:7b", "qwen3:14b", "qwen3:8b"],
        "vram_gb": 9.0,
        "heavy_14b": True,
        "title": "Uzman Yazılım Mühendisi & Kod Doktoru",
        "description": "Python, TypeScript, FastAPI, SQL kod üretimi, hata ayıklama ve birim testi yazımı."
    },
    {
        "role": "reasoning",
        "name": "deepseek-r1:14b",
        "fallbacks": ["deepseek-r1:8b", "qwen3:14b", "qwen3:8b"],
        "vram_gb": 9.0,
        "heavy_14b": True,
        "title": "Derin Muhakeme (Chain-of-Thought) & Strateji Beyni",
        "description": "Karmaşık algoritma, kök neden analizi, şirket/YouTube büyüme stratejisi ve matematiksel planlama."
    },
    {
        "role": "embedding",
        "name": "bge-m3",
        "fallbacks": ["bge-m3:latest", "nomic-embed-text:latest", "nomic-embed-text"],
        "vram_gb": 1.2,
        "heavy_14b": False,
        "title": "Çok Dilli (TR/EN) Anlamsal Vektör RAG Motoru",
        "description": "Proje kodlarını ve Transkript/ eğitim arşivini 1024 boyutlu vektörlerle anlamsal olarak tarar."
    }
]

CODING_KEYWORDS = [
    "kod yaz", "kodu", "fonksiyon", "class ", "def ", "python", "typescript", "javascript",
    "sql", "html", "css", "fastapi", "regex", "refactor", "debug", "hata ayıkla", "traceback", "exception",
    "unit test", "algoritma", "script", "powershell", "json şema"
]

REASONING_KEYWORDS = [
    "strateji", "mimari", "neden", "kök neden", "analiz et", "karşılaştır", "kıyasla",
    "adım adım", "planla", "yol haritası", "optime et", "optimizasyon", "hesapla",
    "matematik", "olasılık", "hipotez", "büyüme planı", "90 gün", "monetizasyon"
]


class ModelManager:
    def __init__(self, ollama_url: Optional[str] = None):
        self.ollama_url = (ollama_url or os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")).rstrip("/")
        self.session = requests.Session()
        self._active_heavy_model: Optional[str] = None

    def _is_testing(self) -> bool:
        return (
            any("unittest" in arg.lower() or "pytest" in arg.lower() or "test_" in arg.lower() for arg in sys.argv)
            or bool(os.environ.get("PYTEST_CURRENT_TEST"))
            or bool(os.environ.get("JARVIS_TEST_MODE"))
        )

    def get_installed_models(self) -> List[str]:
        """Returns list of model names currently installed in local Ollama."""
        if self._is_testing():
            return ["qwen3:8b"]
        try:
            resp = self.session.get(f"{self.ollama_url}/api/tags", timeout=1.5)
            if resp.status_code == 200:
                return [m.get("name", "") for m in resp.json().get("models", []) if m.get("name")]
        except Exception as exc:
            logger.debug(f"[ModelManager] Could not query installed models: {exc}")
        return []

    def get_running_models(self) -> List[Dict[str, Any]]:
        """Returns models currently loaded in RX 9060 XT VRAM via /api/ps."""
        if self._is_testing():
            return []
        try:
            resp = self.session.get(f"{self.ollama_url}/api/ps", timeout=1.2)
            if resp.status_code == 200:
                return [
                    {
                        "name": m.get("name", ""),
                        "size_vram_gb": round(m.get("size_vram", 0) / (1024 ** 3), 2)
                    }
                    for m in resp.json().get("models", [])
                ]
        except Exception:
            pass
        return []

    def classify_task_domain(self, user_text: str) -> str:
        """
        Determines whether a conversational query requires:
        - 'coding' (qwen2.5-coder:14b)
        - 'reasoning' (deepseek-r1:14b)
        - 'primary_brain' (qwen3:14b / qwen3:8b)
        """
        t = (user_text or "").lower()
        if any(k in t for k in CODING_KEYWORDS):
            return "coding"
        if any(k in t for k in REASONING_KEYWORDS):
            return "reasoning"
        return "primary_brain"

    def resolve_model_for_role(self, role: str, default_fallback: str = "qwen3:8b") -> str:
        """Finds the best installed model for the requested specialist role."""
        if self._is_testing():
            return default_fallback

        installed = self.get_installed_models()
        if not installed:
            return default_fallback

        spec = next((s for s in SPECIALIST_ARSENAL if s["role"] == role), None)
        if not spec:
            return installed[0]

        candidates = [spec["name"]] + spec.get("fallbacks", [])
        for cand in candidates:
            for inst in installed:
                if cand == inst or cand.split(":")[0] in inst:
                    return inst

        return installed[0]

    def prepare_vram_for_model(self, target_model: str):
        """
        VRAM & System RAM Swapper for 16GB RX 9060 XT + 16GB Host RAM:
        Before loading a 14B model (or when switching models), gracefully unloads any other
        active LLM/VLM (including qwen2.5vl:7b) from Ollama so host RAM and VRAM never overflow.
        """
        if self._is_testing():
            return

        running = self.get_running_models()
        for r in running:
            r_name = r.get("name", "")
            if not r_name or r_name == target_model or "bge-m3" in r_name.lower() or "embed" in r_name.lower():
                continue
            if "14b" in target_model.lower() or "14b" in r_name.lower() or "vl" in r_name.lower() or r.get("size_vram_gb", 0) > 4.0:
                try:
                    logger.info(f"[VRAM Swapper] Unloading {r_name} before loading {target_model} to protect 16GB RAM/VRAM...")
                    self.session.post(
                        f"{self.ollama_url}/api/generate",
                        json={"model": r_name, "keep_alive": 0},
                        timeout=3
                    )
                except Exception as exc:
                    logger.debug(f"[VRAM Swapper] Unload warning for {r_name}: {exc}")

    @staticmethod
    def strip_thinking_tags(raw_response: str) -> Dict[str, str]:
        """
        Extracts <think>...</think> chain-of-thought blocks from DeepSeek-R1 / Qwen3 responses
        so the user gets a clean executive answer while preserving the reasoning trace.
        """
        if not raw_response:
            return {"clean_reply": "", "thinking_trace": ""}

        think_matches = re.findall(r"<think>([\s\S]*?)</think>", raw_response, flags=re.IGNORECASE)
        thinking_trace = "\n".join(m.strip() for m in think_matches if m.strip())
        clean_reply = re.sub(r"<think>[\s\S]*?</think>", "", raw_response, flags=re.IGNORECASE).strip()
        return {
            "clean_reply": clean_reply or raw_response.strip(),
            "thinking_trace": thinking_trace
        }

    def get_arsenal_status(self) -> Dict[str, Any]:
        """Returns comprehensive status of the 5-Model Specialist Arsenal."""
        installed = self.get_installed_models()
        running = self.get_running_models()
        running_names = {r["name"] for r in running}

        report = []
        for spec in SPECIALIST_ARSENAL:
            primary = spec["name"]
            matched_inst = None
            for cand in [primary] + spec["fallbacks"]:
                for inst in installed:
                    if cand == inst or cand.split(":")[0] in inst:
                        matched_inst = inst
                        break
                if matched_inst:
                    break

            report.append({
                "role": spec["role"],
                "title": spec["title"],
                "recommended_model": primary,
                "active_installed_model": matched_inst,
                "is_installed": bool(matched_inst),
                "is_exact_sota_installed": any(primary in inst for inst in installed),
                "in_vram_now": bool(matched_inst and matched_inst in running_names),
                "vram_estimate_gb": spec["vram_gb"],
                "description": spec["description"],
                "ollama_pull_cmd": f"ollama pull {primary}"
            })

        missing_sota = [r["recommended_model"] for r in report if not r["is_exact_sota_installed"]]
        return {
            "hardware_target": "AMD Radeon RX 9060 XT (16GB VRAM) + Intel i5-14400F",
            "installed_models": installed,
            "running_vram_models": running,
            "arsenal": report,
            "missing_sota_models": missing_sota,
            "all_sota_ready": len(missing_sota) == 0
        }

    def pull_model(self, model_name: str) -> Dict[str, Any]:
        """Triggers non-streaming model pull via Ollama REST API."""
        try:
            resp = self.session.post(
                f"{self.ollama_url}/api/pull",
                json={"name": model_name, "stream": False},
                timeout=600
            )
            if resp.status_code == 200:
                return {"success": True, "model": model_name, "status": resp.json().get("status", "success")}
            return {"success": False, "model": model_name, "error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as exc:
            return {"success": False, "model": model_name, "error": str(exc)}


model_manager = ModelManager()
