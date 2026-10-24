"""
Global-Wawe / Stark-Core - Local AI & Container Infrastructure Manager (Section F)
Manages:
1. Docker Containers & Daemon Health (docker ps discovery)
2. Ollama Local Model Catalog & Active Execution Monitoring
3. Cost-Aware Dynamic Model Router (Zero-Cost Local 7B/8B Priority vs Deep/Cloud fallback)
4. Hardware Safety Gates before High-Compute Tasks
"""

import os
import json
import shutil
import subprocess
import requests
import logging
from typing import Dict, Any, List, Optional

from config.settings import load_settings

logger = logging.getLogger("Jarvis.InfraTool")

class InfraTool:
    def __init__(self):
        pass

    def check_docker_status(self) -> Dict[str, Any]:
        """
        Inspects Docker daemon and active containers.
        """
        docker_bin = shutil.which("docker")
        if not docker_bin:
            return {
                "installed": False,
                "running": False,
                "containers": [],
                "summary": "Docker bu makinede yüklü değil veya PATH'te bulunamadı."
            }

        try:
            res = subprocess.run(
                ["docker", "ps", "--format", "{{json .}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if res.returncode == 0:
                containers = []
                for line in res.stdout.strip().splitlines():
                    if line.strip():
                        try:
                            containers.append(json.loads(line.strip()))
                        except Exception:
                            pass
                return {
                    "installed": True,
                    "running": True,
                    "container_count": len(containers),
                    "containers": containers,
                    "summary": f"Docker aktif. Çalışan konteyner sayısı: {len(containers)}."
                }
            else:
                return {
                    "installed": True,
                    "running": False,
                    "containers": [],
                    "summary": "Docker Desktop kurulu ancak daemon çalışmıyor."
                }
        except subprocess.TimeoutExpired:
            return {"installed": True, "running": False, "summary": "Docker yanıt vermedi (Zaman aşımı)."}
        except Exception as e:
            return {"installed": True, "running": False, "summary": f"Docker hatası: {str(e)}"}

    def get_ollama_models(self) -> Dict[str, Any]:
        """
        Discovers installed local Ollama models and running instances.
        """
        settings = load_settings()
        host = settings.get("ollama_host", "http://127.0.0.1:11434").rstrip("/")

        try:
            r = requests.get(f"{host}/api/tags", timeout=3)
            if r.status_code == 200:
                models = r.json().get("models", [])
                formatted = [
                    {
                        "name": m.get("name"),
                        "size_gb": round(m.get("size", 0) / (1024 ** 3), 2),
                        "modified_at": m.get("modified_at")
                    }
                    for m in models
                ]
                return {
                    "online": True,
                    "host": host,
                    "model_count": len(formatted),
                    "models": formatted,
                    "summary": f"Ollama çevrimiçi. {len(formatted)} adet yerel model hazır."
                }
            else:
                return {"online": False, "host": host, "models": [], "summary": "Ollama servisi yanıt vermedi."}
        except Exception:
            return {
                "online": False,
                "host": host,
                "models": [],
                "summary": "Ollama servisine bağlanılamadı (127.0.0.1:11434 kapalı)."
            }

    def route_model_for_task(self, task_type: str, context_length_est: int = 2000) -> Dict[str, Any]:
        """
        Picks the optimal model matching task difficulty while keeping API cost strictly at $0.00.
        """
        settings = load_settings()
        fast_local = settings.get("fast_model", "qwen3:8b")
        deep_local = settings.get("default_model", "qwen3:14b")

        # Rules:
        # 1. Routine classification, short scripts, daily tasks -> Fast 8B local ($0)
        # 2. Coding, diff inspection -> qwen2.5-coder:7b or fast_local ($0)
        # 3. 16min documentary or deep research -> deep local ($0) or explicit API request
        task_lower = task_type.lower()
        if any(k in task_lower for k in ["code", "coding", "yazılım", "test", "kod", "diff", "programlama"]):
            chosen = "qwen2.5-coder:7b"
            tier = "Local Coding Specialist"
        elif any(k in task_lower for k in ["documentary", "belgesel", "longform", "deep_research"]):
            chosen = deep_local
            tier = "Local Deep Model"
        else:
            chosen = fast_local
            tier = "Local Fast Utility"

        return {
            "task_type": task_type,
            "chosen_model": chosen,
            "model_tier": tier,
            "cost_usd": 0.0,
            "is_local": True,
            "reason": f"$0 maliyetli yerel donanım optimizasyonu uygulandı ({chosen})."
        }


infra_tool = InfraTool()
