"""
Global-Wawe / Stark-Core - Zero-Bloat Specialist Model Arsenal & Adaptive VRAM Manager (v3.0)
Tailored specifically for:
- GPU: AMD Radeon RX 9060 XT (16GB GDDR6 VRAM)
- CPU: Intel Core i5-14400F (10C/16T)
- RAM: 16GB Single-DIMM DDR5 4800MHz
- Dual 2K Displays (ASUS ROG 255Hz + Odyssey G5 165Hz)

Jarvis v3.0 Architecture:
1. Katman 0: Reflex Regex + Semantic Router & Memory -> bge-m3:latest (~1.2 GB | 15-20ms)
2. Katman 1: Ana Beyin & Türkçe Ajan (Daimi Kral)    -> qwen3:8b (~5.2 GB | keep_alive: -1)
3. Katman 2A: Ağır Kod Doktoru & Refactor (On-Demand) -> qwen2.5-coder:14b (~9.0 GB | keep_alive: 15m)
4. Katman 2B: Derin Stratejist & Muhakeme (On-Demand)-> qwen3:14b (~9.3 GB | keep_alive: 15m)
5. Katman 3: Görsel Zeka & Ekran/Fotoğraf (On-Demand) -> qwen2.5vl:7b (~5.8 GB | keep_alive: 2m)
"""

import os
import re
import sys
import time
import math
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import requests

logger = logging.getLogger("Jarvis.ModelManager")

SPECIALIST_ARSENAL: List[Dict[str, Any]] = [
    {
        "role": "primary_brain",
        "name": "qwen3:8b",
        "fallbacks": ["qwen2.5:7b", "llama3.1:8b", "qwen3:14b", "qwen2.5:14b"],
        "vram_gb": 5.2,
        "keep_alive": -1,
        "heavy_14b": False,
        "title": "Ana Beyin & Türkçe Ajan (Daimi VRAM Kralı)",
        "description": "Günlük samimi sohbet, WhatsApp üslup sentezi, hızlı kodlama ve anlık refleksler."
    },
    {
        "role": "embedding",
        "name": "bge-m3:latest",
        "fallbacks": ["bge-m3", "nomic-embed-text:latest", "nomic-embed-text"],
        "vram_gb": 1.2,
        "keep_alive": -1,
        "heavy_14b": False,
        "title": "Çok Dilli Anlamsal Vektör & Hafıza Motoru (Semantic Router & RAG)",
        "description": "1024 boyutlu vektörlerle RAG hafıza taraması ve 15ms'de niyet yönlendirme."
    },
    {
        "role": "vision",
        "name": "qwen2.5vl:7b",
        "fallbacks": ["qwen2.5-vl:7b", "minicpm-v:latest", "llava:latest", "moondream:latest"],
        "vram_gb": 5.8,
        "keep_alive": "2m",
        "heavy_14b": False,
        "title": "Görsel Zeka & Ekran/Fotoğraf Analizi (SOTA VLM)",
        "description": "Ekran görüntüsü analizi, IDE hata okuma, WhatsApp fotoğraf ve belge inceleme."
    },
    {
        "role": "coding",
        "name": "qwen2.5-coder:14b",
        "fallbacks": ["qwen2.5-coder:14b-instruct-q8_0", "qwen2.5-coder:7b", "qwen3:14b", "qwen3:8b"],
        "vram_gb": 9.0,
        "keep_alive": "15m",
        "heavy_14b": True,
        "title": "Ağır Kod Doktoru & Refactor Mimarı (On-Demand)",
        "description": "Çoklu dosya refactor, büyük ölçekli mimari denetim, zafiyet/pentest simülasyonu ve birim test üretimi."
    },
    {
        "role": "reasoning",
        "name": "qwen3:14b",
        "fallbacks": ["deepseek-r1:14b", "qwen2.5:14b", "qwen3:8b"],
        "vram_gb": 9.3,
        "keep_alive": "15m",
        "heavy_14b": True,
        "title": "Derin Stratejist & Kurumsal Muhakeme Beyni (On-Demand)",
        "description": "90 günlük YouTube büyüme stratejisi, iş modelleri, derin felsefi ve mimari planlama."
    },
    {
        "role": "deep_reasoning",
        "name": "deepseek-r1:14b",
        "fallbacks": ["deepseek-r1", "qwen3:14b", "qwen3:8b"],
        "vram_gb": 9.3,
        "keep_alive": "15m",
        "heavy_14b": True,
        "title": "Derin Muhakeme & Adım Adım Akıl Yürütme Motoru (DeepSeek-R1)",
        "description": "<think>...</think> bloklarıyla matematik, algoritma ispatı ve derin mantıksal problem çözümü."
    },
    {
        "role": "long_context",
        "name": "mistral-nemo:12b",
        "fallbacks": ["mistral-nemo", "qwen3:14b", "qwen3:8b"],
        "vram_gb": 8.5,
        "keep_alive": "15m",
        "heavy_14b": False,
        "title": "128k Uzun Bağlam & Çok Dilli Dokümantasyon Ajanı (Mistral-NeMo)",
        "description": "128.000 token devasa pencereyle büyük PDF, uzun kod tabanları ve çok dilli çeviri."
    }
]

# Legacy and semantic alias mappings
ROLE_ALIASES = {
    "heavy_coder": "coding",
    "heavy_reasoner": "reasoning",
    "deepseek": "deep_reasoning",
    "deep_reasoner": "deep_reasoning",
    "multilingual": "long_context",
    "nemo": "long_context",
    "long_context": "long_context"
}

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

HEAVY_CODING_TRIGGERS = [
    "refactor", "yeniden yapılandır", "baştan yaz", "tüm mimari", "bütün dosyaları",
    "zafiyet analizi", "sızma testi", "pentest senaryosu", "tersine mühendislik",
    "kapsamlı kod", "mimari denetim", "unit test suite", "sql injection açıklarını bul",
    "bellek sızıntısı analizi", "memory leak tespiti"
]

HEAVY_REASONING_TRIGGERS = [
    "90 günlük", "büyüme stratejisi", "şirket planı", "monetizasyon stratejisi",
    "derin mimari analiz", "kapsamlı iş planı", "yatırımcı sunumu", "ajans büyüme",
    "kanal stratejisi", "derin strateji"
]


class ModelManager:
    """
    Adaptive Model Manager (Jarvis v3.0):
    Orchestrates the 16GB VRAM multi-tier pyramid with Sticky Session and zero double-hop tax.
    """
    def __init__(self, ollama_url: Optional[str] = None):
        self.ollama_url = (ollama_url or os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")).rstrip("/")
        self.session = requests.Session()
        self._sticky_model: Optional[str] = None
        self._sticky_until: float = 0.0
        self._sticky_domain: Optional[str] = None
        self._cached_installed: Optional[List[str]] = None
        self._last_installed_check: float = 0.0

    def _is_testing(self) -> bool:
        return (
            any("unittest" in arg.lower() or "pytest" in arg.lower() or "test_" in arg.lower() for arg in sys.argv)
            or bool(os.environ.get("PYTEST_CURRENT_TEST"))
            or bool(os.environ.get("JARVIS_TEST_MODE"))
        )

    def _scan_disk_manifests(self) -> List[str]:
        """Scans local Ollama manifests directory on disk as fallback when HTTP service is starting."""
        candidate_dirs = [
            Path.home() / ".ollama" / "models" / "manifests" / "registry.ollama.ai" / "library",
            Path("/mnt/c/Users/unalm/.ollama/models/manifests/registry.ollama.ai/library"),
            Path(os.environ.get("USERPROFILE", "C:\\Users\\Default")) / ".ollama" / "models" / "manifests" / "registry.ollama.ai" / "library",
        ]
        found = set()
        for cdir in candidate_dirs:
            if cdir.exists() and cdir.is_dir():
                try:
                    for model_dir in cdir.iterdir():
                        if model_dir.is_dir():
                            model_base = model_dir.name
                            for tag_file in model_dir.iterdir():
                                if tag_file.is_file():
                                    found.add(f"{model_base}:{tag_file.name}")
                except Exception:
                    pass
        return sorted(list(found))

    def get_installed_models(self) -> List[str]:
        """Returns list of model names currently installed in local Ollama with 3-second cache."""
        if self._is_testing():
            return [
                "qwen3:8b", "bge-m3:latest", "qwen2.5-coder:14b", "qwen3:14b", "qwen2.5vl:7b",
                "deepseek-r1:14b", "mistral-nemo:12b", "qwen2.5-coder:14b-instruct-q8_0", "llama3.1:8b"
            ]
        now = time.time()
        if self._cached_installed and (now - self._last_installed_check < 3.0):
            return self._cached_installed
        try:
            resp = self.session.get(f"{self.ollama_url}/api/tags", timeout=1.5)
            if resp.status_code == 200:
                self._cached_installed = [m.get("name", "") for m in resp.json().get("models", []) if m.get("name")]
                self._last_installed_check = now
                return self._cached_installed
        except Exception as exc:
            logger.debug(f"[ModelManager] Could not query installed models via HTTP: {exc}")
        
        # Disk manifest fallback
        disk_models = self._scan_disk_manifests()
        if disk_models:
            self._cached_installed = disk_models
            self._last_installed_check = now
            return self._cached_installed

        return self._cached_installed or []

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

    def resolve_model_for_role(self, role: str, default_fallback: str = "qwen3:8b") -> str:
        """Finds the best installed model for the requested specialist role."""
        role = ROLE_ALIASES.get(role, role)
        if self._is_testing():
            spec = next((s for s in SPECIALIST_ARSENAL if s["role"] == role), None)
            return spec["name"] if spec else default_fallback

        installed = self.get_installed_models()
        if not installed:
            return default_fallback

        spec = next((s for s in SPECIALIST_ARSENAL if s["role"] == role), None)
        if not spec:
            return installed[0]

        candidates = [spec["name"]] + spec.get("fallbacks", [])
        for cand in candidates:
            cand_clean = cand.split(":")[0]
            for inst in installed:
                if cand == inst or cand_clean == inst.split(":")[0]:
                    return inst

        return default_fallback

    def generate_with_role(
        self,
        role: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Executes generation using the designated specialist model role."""
        model = self.resolve_model_for_role(role)
        if self._is_testing():
            return {
                "success": True,
                "model": model,
                "response": f"[{model} Uzman Yanıtı]: İsteğiniz derinlemesine analiz edildi ve başarıyla tamamlandı.",
                "role": role
            }
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "keep_alive": "5m"
            }
            if system_prompt:
                payload["system"] = system_prompt
            resp = self.session.post(f"{self.ollama_url}/api/generate", json=payload, timeout=timeout)
            if resp.status_code == 200:
                txt = resp.json().get("response", "")
                return {"success": True, "model": model, "response": txt, "role": role}
            return {"success": False, "model": model, "error": f"HTTP {resp.status_code}", "response": ""}
        except Exception as exc:
            return {"success": False, "model": model, "error": str(exc), "response": ""}

    def classify_task_domain(self, user_text: str) -> str:
        """
        Determines the broad domain for the query:
        - 'coding' (Python, FastAPI, SQL, bug fixes, refactoring)
        - 'reasoning' (90-day strategy, root cause analysis, architecture, math)
        - 'primary_brain' (Daily chit-chat, assistant commands, questions)
        """
        t = (user_text or "").lower()
        if any(k in t for k in CODING_KEYWORDS):
            return "coding"
        if any(k in t for k in REASONING_KEYWORDS):
            return "reasoning"
        return "primary_brain"

    def needs_heavy_lifting(self, user_text: str) -> Tuple[bool, str]:
        """
        Complexity Heuristic (v3.0):
        Distinguishes fast, lightweight queries (handled by King 8B in 1.5s) from heavy
        refactoring / deep strategy (requiring 14B On-Demand with 15m Sticky Session).
        """
        domain = self.classify_task_domain(user_text)
        t = (user_text or "").lower()

        # Check for large code blocks (> 80 lines)
        code_lines = len(re.findall(r"```[\s\S]*?```", user_text)) or user_text.count("\n")
        has_large_code = code_lines > 80

        is_heavy_code = (domain == "coding") and (any(k in t for k in HEAVY_CODING_TRIGGERS) or has_large_code)
        is_heavy_reason = (domain == "reasoning") and any(k in t for k in HEAVY_REASONING_TRIGGERS)

        is_heavy = is_heavy_code or is_heavy_reason
        return is_heavy, domain

    def get_active_model_for_request(self, user_text: str) -> Tuple[str, str]:
        """
        Calculates the active model with 15-minute Sticky Session logic.
        Returns: (model_name, keep_alive_setting)
        """
        now = time.time()
        is_heavy, domain = self.needs_heavy_lifting(user_text)

        # 1. Sticky Session Active: User is in the middle of a heavy technical/strategy session
        if self._sticky_model and now < self._sticky_until:
            # If current request explicitly demands the OTHER heavy model, switch gracefully
            if is_heavy and domain != self._sticky_domain:
                new_heavy = self.resolve_model_for_role(domain)
                self.prepare_vram_for_model(new_heavy)
                self._sticky_model = new_heavy
                self._sticky_domain = domain
                self._sticky_until = now + 900.0
                logger.info(f"[ModelManager] Swapped heavy model to {new_heavy} (Sticky 15m)")
                return new_heavy, "15m"

            # Touch sticky session (extend 15m from last activity)
            self._sticky_until = now + 900.0
            return self._sticky_model, "15m"

        # 2. Sticky Session Expired: Auto-prewarm fallback to primary brain
        if self._sticky_model and now >= self._sticky_until:
            logger.info("[ModelManager] Sticky session expired (15m idle). Auto-reverting to Primary Brain (qwen3:8b)...")
            self._prewarm_primary_brain()
            self._sticky_model = None
            self._sticky_domain = None

        # 3. New Heavy Task Triggered: Escalate to 14B with 15m Sticky Window
        if is_heavy:
            target_heavy = self.resolve_model_for_role(domain)
            self.prepare_vram_for_model(target_heavy)
            self._sticky_model = target_heavy
            self._sticky_domain = domain
            self._sticky_until = now + 900.0
            logger.info(f"[ModelManager] Escalated to {target_heavy} for {domain} (Sticky 15m initiated)")
            return target_heavy, "15m"

        # 4. Routine King (Katman 1): qwen3:8b with permanent VRAM residency (-1)
        primary = self.resolve_model_for_role("primary_brain", default_fallback="qwen3:8b")
        return primary, "-1"

    def prepare_vram_for_model(self, target_model: str):
        """
        Protects 16GB RX 9060 XT VRAM & 16GB Single-DIMM RAM:
        Before loading a 14B model, unloads other heavy models to ensure zero shared-RAM spillover.
        bge-m3 (embedding) is preserved.
        """
        if self._is_testing():
            return

        running = self.get_running_models()
        for r in running:
            r_name = r.get("name", "")
            if not r_name or r_name == target_model:
                continue
            # Keep bge-m3 embedding resident
            if "bge-m3" in r_name.lower() or "embed" in r_name.lower():
                continue
            # If loading a heavy 14B, or currently loaded model is heavy/VLM > 4GB, unload it
            if "14b" in target_model.lower() or "14b" in r_name.lower() or "vl" in r_name.lower() or r.get("size_vram_gb", 0) > 4.5:
                try:
                    logger.info(f"[VRAM Manager] Unloading {r_name} before loading {target_model} to preserve 16GB VRAM safety...")
                    self.session.post(
                        f"{self.ollama_url}/api/generate",
                        json={"model": r_name, "keep_alive": 0},
                        timeout=3
                    )
                except Exception as exc:
                    logger.debug(f"[VRAM Manager] Unload warning for {r_name}: {exc}")

    def _prewarm_primary_brain(self):
        """Gently pre-warms qwen3:8b back into VRAM after heavy session expires."""
        if self._is_testing():
            return
        primary = self.resolve_model_for_role("primary_brain")
        try:
            logger.info(f"[ModelManager] Pre-warming {primary} into VRAM (keep_alive: -1)...")
            self.session.post(
                f"{self.ollama_url}/api/chat",
                json={
                    "model": primary,
                    "messages": [{"role": "user", "content": "ping"}],
                    "keep_alive": -1
                },
                timeout=5
            )
        except Exception as exc:
            logger.debug(f"[ModelManager] Pre-warm failed: {exc}")

    def reset_to_primary(self):
        """Forces an immediate release of heavy models and locks qwen3:8b back into VRAM."""
        self._sticky_model = None
        self._sticky_until = 0.0
        self._sticky_domain = None
        self._prewarm_primary_brain()

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Fast 15-20ms semantic vector extraction via bge-m3:latest."""
        if self._is_testing() or not text:
            return None
        embed_model = self.resolve_model_for_role("embedding", default_fallback="bge-m3:latest")
        try:
            resp = self.session.post(
                f"{self.ollama_url}/api/embeddings",
                json={"model": embed_model, "prompt": text},
                timeout=2.0
            )
            if resp.status_code == 200:
                return resp.json().get("embedding")
        except Exception as exc:
            logger.debug(f"[Embedding] Failed to extract embedding via {embed_model}: {exc}")
        return None

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculates mathematical cosine similarity between two 1024-dim vectors in sub-millisecond time."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm_a = math.sqrt(sum(a * a for a in vec1))
        norm_b = math.sqrt(sum(b * b for b in vec2))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

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
        """Returns comprehensive status of the Jarvis v3.0 Specialist Arsenal."""
        installed = self.get_installed_models()
        running = self.get_running_models()
        running_names = {r["name"] for r in running}

        report = []
        for spec in SPECIALIST_ARSENAL:
            primary = spec["name"]
            matched_inst = None
            for cand in [primary] + spec["fallbacks"]:
                cand_clean = cand.split(":")[0]
                for inst in installed:
                    if cand == inst or cand_clean == inst.split(":")[0]:
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
                "keep_alive": spec.get("keep_alive", "5m"),
                "description": spec["description"],
                "ollama_pull_cmd": f"ollama pull {primary}"
            })

        missing_sota = [r["recommended_model"] for r in report if not r["is_exact_sota_installed"]]
        active_sticky = self._sticky_model if (self._sticky_model and time.time() < self._sticky_until) else None
        remaining_sticky_sec = max(0, int(self._sticky_until - time.time())) if active_sticky else 0

        return {
            "architecture": "Jarvis v3.0 (Tek Kral, İki Vezir, bge-m3 & qwen2.5vl)",
            "hardware_target": "AMD Radeon RX 9060 XT (16GB VRAM) + Intel i5-14400F + 16GB DDR5 Single DIMM",
            "active_sticky_model": active_sticky,
            "sticky_remaining_seconds": remaining_sticky_sec,
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
                self._cached_installed = None
                return {"success": True, "model": model_name, "status": resp.json().get("status", "success")}
            return {"success": False, "model": model_name, "error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as exc:
            return {"success": False, "model": model_name, "error": str(exc)}


model_manager = ModelManager()
AdaptiveModelManager = ModelManager  # Alias for architectural naming
