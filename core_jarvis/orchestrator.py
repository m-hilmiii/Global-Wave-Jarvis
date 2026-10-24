"""
Global-Wawe / Stark-Core - Master Orchestrator & Specialist Agent Mesh
Implements Section 4 of the Jarvis Vision:
1. Main JARVIS (Executive Orchestrator: Intent understanding, planning, delegation, reporting)
2. SystemSpecialist (Windows, hardware telemetry, processes, PowerShell whitelist, backup/rollback)
3. CodeSpecialist (Code inspection, unit tests, git diff/status, test-driven self-correction)
4. ContentSpecialist (Global Wave video pipeline: Production -> QC -> Publish staging)
5. ResearchSpecialist (Web/Docs research with prompt injection armor)
"""

import os
import subprocess
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from core_jarvis.permission_guard import permission_guard, PermissionLevel
from core_jarvis.tools.system_tool import system_tool
from core_jarvis.reality_memory import reality_memory
from core_jarvis.autonomous_engine import autonomous_engine

logger = logging.getLogger("Jarvis.Orchestrator")
WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent

# ==============================================================================
# 1. SystemSpecialist
# ==============================================================================
class SystemSpecialist:
    """Manages Windows OS, hardware telemetry (i5-14400F + AMD RX 9060 XT), processes and backups."""

    def diagnose_system(self) -> Dict[str, Any]:
        telemetry = system_tool.get_hardware_telemetry()
        cpu_load = telemetry["cpu"]["usage_percent"]
        ram_pct = telemetry["ram"]["usage_percent"]
        disk_pct = telemetry["disk"]["usage_percent"]

        health_issues = []
        if cpu_load > 85.0:
            health_issues.append(f"Yüksek CPU kullanımı: %{cpu_load}")
        if ram_pct > 85.0:
            health_issues.append(f"Kritik RAM doluluğu: %{ram_pct} ({telemetry['ram']['used_gb']}GB / {telemetry['ram']['total_gb']}GB)")
        if disk_pct > 90.0:
            health_issues.append(f"C: Sürücüsü neredeyse dolu: %{disk_pct}")

        status = "healthy" if not health_issues else "warning"
        return {
            "status": status,
            "issues": health_issues,
            "telemetry": telemetry,
            "summary": (
                "Sistem normal çalışıyor. Donanım kaynakları stabil."
                if status == "healthy" else
                f"Sistemde dikkat gerektiren noktalar: {', '.join(health_issues)}"
            )
        }

    def run_safe_command(self, cmd: str, confirmed: bool = False) -> Dict[str, Any]:
        return system_tool.run_safe_powershell(command=cmd, confirmed_by_user=confirmed)

    def backup_file(self, rel_path: str, note: str = "pre_edit") -> Dict[str, Any]:
        return system_tool.create_snapshot(relative_path=rel_path, note=note)

    def rollback_file(self, snapshot_file: str, rel_dest: str, confirmed: bool = False) -> Dict[str, Any]:
        return system_tool.rollback_snapshot(snapshot_file=snapshot_file, relative_dest_path=rel_dest, confirmed_by_user=confirmed)

    def check_docker(self) -> Dict[str, Any]:
        from core_jarvis.tools.infra_tool import infra_tool
        return infra_tool.check_docker_status()

    def get_ai_models(self) -> Dict[str, Any]:
        from core_jarvis.tools.infra_tool import infra_tool
        return infra_tool.get_ollama_models()


# ==============================================================================
# 2. CodeSpecialist
# ==============================================================================
class CodeSpecialist:
    """Inspects code, runs unit tests, analyzes git diffs, and enforces verified changes."""

    def run_tests(self, test_path: str = "tests") -> Dict[str, Any]:
        guard_res = permission_guard.evaluate_action("run_unit_tests", confirmed_by_user=False)
        if not guard_res["allowed"]:
            return {"success": False, "error": guard_res["reason"]}

        start = time.time()
        try:
            res = subprocess.run(
                ["python", "-m", "unittest", "discover", "-s", test_path, "-p", "test_*.py"],
                capture_output=True,
                text=True,
                cwd=str(WORKSPACE_DIR),
                timeout=45
            )
            passed = res.returncode == 0
            return {
                "success": passed,
                "returncode": res.returncode,
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip(),
                "elapsed_seconds": round(time.time() - start, 2),
                "summary": "Tüm birim testleri başarıyla geçti." if passed else "Bazı testler başarısız oldu!"
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Test çalıştırması 45 saniyede zaman aşımına uğradı."}
        except Exception as e:
            return {"success": False, "error": f"Test motoru hatası: {str(e)}"}

    def get_git_diff(self) -> Dict[str, Any]:
        guard_res = permission_guard.evaluate_action("git_diff", confirmed_by_user=False)
        if not guard_res["allowed"]:
            return {"success": False, "error": guard_res["reason"]}

        try:
            res = subprocess.run(
                ["git", "diff", "--stat"],
                capture_output=True, text=True, cwd=str(WORKSPACE_DIR), timeout=5
            )
            return {
                "success": True,
                "diff_stat": res.stdout.strip() or "Değişiklik yok (Clean workspace)"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# ==============================================================================
# 3. ContentSpecialist (Global Wave / formerly Zenvia Media)
# ==============================================================================
class ContentSpecialist:
    """Oversees the Global Wave video engine across 3 phases: 1. Production, 2. QC, 3. Publishing."""

    def check_pipeline_status(self) -> Dict[str, Any]:
        from config.settings import load_settings, get_ffmpeg_bin, get_ffprobe_bin
        tokens = load_settings()
        ffmpeg_bin = get_ffmpeg_bin()
        ffprobe_bin = get_ffprobe_bin()

        return {
            "engine": "Global Wave Video Factory v3.1/v5.0",
            "ffmpeg_ready": bool(ffmpeg_bin),
            "ffprobe_ready": bool(ffprobe_bin),
            "pexels_configured": bool(tokens.get("pexels_api_key")),
            "hardware_accel": "AMD AMF / DirectML (AMD Radeon RX 9060 XT compatible)",
            "output_dir": str(WORKSPACE_DIR / "output")
        }

    def produce_draft(self, topic: str, target_duration: str = "45s", orientation: str = "vertical", persona_id: str = "us_hustler") -> Dict[str, Any]:
        from engine.content_pipeline import content_pipeline
        return content_pipeline.stage_1_produce_draft(
            topic=topic,
            target_duration=target_duration,
            orientation=orientation,
            persona_id=persona_id
        )

    def run_qc(self, video_path: str, script_data: Dict[str, Any]) -> Dict[str, Any]:
        from engine.content_pipeline import content_pipeline
        return content_pipeline.stage_2_quality_control(video_path=video_path, script_data=script_data)

    def stage_publish(self, video_path: str, title: str, description: str, tags: List[str], confirmed: bool = False, privacy_status: str = "private") -> Dict[str, Any]:
        from engine.content_pipeline import content_pipeline
        return content_pipeline.stage_3_prepare_and_publish(
            video_path=video_path,
            title=title,
            description=description,
            tags=tags,
            confirmed_by_user=confirmed,
            privacy_status=privacy_status
        )


# ==============================================================================
# 4. ResearchSpecialist
# ==============================================================================
class ResearchSpecialist:
    """Conducts web and documentation research with prompt-injection filtering."""

    def sanitize_untrusted_content(self, raw_text: str) -> str:
        """
        Strips and neutralizes prompt-injection attempts from untrusted web sources.
        """
        from core_jarvis.tools.browser_research_tool import browser_research_tool
        return browser_research_tool.sanitize_untrusted_text(raw_text)

    def research_topic(self, query: str, auto_note: bool = True) -> Dict[str, Any]:
        """
        Searches web, extracts sanitized snippets and archives to executive notes if requested.
        """
        from core_jarvis.tools.browser_research_tool import browser_research_tool
        return browser_research_tool.conduct_research_and_archive(topic=query, auto_note=auto_note)

    def compare_models(self, category: str = "coding") -> Dict[str, Any]:
        """
        Evaluates models specifically for Intel i5-14400F + AMD Radeon RX 9060 XT + 16GB RAM.
        """
        from core_jarvis.tools.browser_research_tool import browser_research_tool
        return browser_research_tool.compare_hardware_models(category=category)

    def fetch_page(self, url: str) -> Dict[str, Any]:
        """
        Fetches an article/doc URL and extracts clean sanitized text.
        """
        from core_jarvis.tools.browser_research_tool import browser_research_tool
        return browser_research_tool.fetch_page_content(url=url)


# ==============================================================================
# 5. AssistantSpecialist (Personal Assistant, Daily Planner, Tasks, Notes)
# ==============================================================================
class AssistantSpecialist:
    """Manages daily briefings, calendar reminders, tasks, and quick executive notes."""

    def get_briefing(self) -> Dict[str, Any]:
        from core_jarvis.personal_assistant import personal_assistant
        return personal_assistant.get_daily_briefing()

    def add_task(self, title: str, priority: str = "normal", due_date: Optional[str] = None) -> Dict[str, Any]:
        from core_jarvis.personal_assistant import personal_assistant
        return personal_assistant.add_task(title=title, priority=priority, due_date=due_date)

    def complete_task(self, task_id: str) -> Dict[str, Any]:
        from core_jarvis.personal_assistant import personal_assistant
        return personal_assistant.complete_task(task_id=task_id)

    def add_reminder(self, title: str, datetime_iso: str, lead_minutes: int = 15) -> Dict[str, Any]:
        from core_jarvis.personal_assistant import personal_assistant
        return personal_assistant.add_reminder(title=title, datetime_iso=datetime_iso, lead_minutes=lead_minutes)

    def add_note(self, title: str, content: str, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        from core_jarvis.personal_assistant import personal_assistant
        return personal_assistant.add_note(title=title, content=content, tags=tags)


# ==============================================================================
# 6. Master JARVIS Orchestrator
# ==============================================================================
class JarvisOrchestrator:
    def __init__(self):
        self.system = SystemSpecialist()
        self.code = CodeSpecialist()
        self.content = ContentSpecialist()
        self.research = ResearchSpecialist()
        self.assistant = AssistantSpecialist()
        from core_jarvis.task_coordinator import task_coordinator
        self.coordinator = task_coordinator
        self.engine = autonomous_engine
        self.memory = reality_memory

    def handle_intent(self, user_prompt: str, confirmed_by_user: bool = False) -> Dict[str, Any]:
        """
        High-level intent classifier and specialist dispatcher.
        """
        prompt_lower = user_prompt.lower().strip()

        # 0. Personal Assistant Briefing & Agenda ("Jarvis, bugün ne yapmam gerekiyor?")
        if any(k in prompt_lower for k in ["bugün ne yapmam gerekiyor", "bugün ne yapmalıyım", "ajandam", "günlük plan", "günlük brifing", "görevlerim"]):
            briefing = self.assistant.get_briefing()
            return {
                "specialist": "AssistantSpecialist",
                "intent": "daily_briefing",
                "speak_text": briefing.get("executive_briefing_text"),
                "result": briefing
            }

        # Quick Task Add
        if "görev ekle" in prompt_lower or "yapılacak ekle" in prompt_lower:
            task_title = user_prompt.split(":", 1)[1].strip() if ":" in user_prompt else user_prompt
            res = self.assistant.add_task(title=task_title, priority="normal")
            return {
                "specialist": "AssistantSpecialist",
                "intent": "add_task",
                "result": res
            }

        # Quick Note Add
        if "not al" in prompt_lower or "not ekle" in prompt_lower:
            note_content = user_prompt.split(":", 1)[1].strip() if ":" in user_prompt else user_prompt
            res = self.assistant.add_note(title="Hızlı Not", content=note_content)
            return {
                "specialist": "AssistantSpecialist",
                "intent": "add_note",
                "result": res
            }

        # 1. 'Kaldığımız yerden devam et' (Truth-over-Memory context restoration)
        if any(k in prompt_lower for k in ["kaldığımız yerden", "nerede kaldık", "durum nedir", "resume"]):
            return {
                "specialist": "RealityMemory",
                "intent": "resume_context",
                "result": self.memory.resume_context()
            }

        # 2. 'Bilgisayarım neden yavaşladı / sistem durumu / kaynaklar'
        if any(k in prompt_lower for k in ["yavaşladı", "kaynak", "cpu", "ram", "gpu", "sıcaklık", "donanım", "telemetri"]) and "model" not in prompt_lower:
            return {
                "specialist": "SystemSpecialist",
                "intent": "diagnose_system",
                "result": self.system.diagnose_system()
            }

        # 3. 'Testleri çalıştır / kod durumu / diff'
        if any(k in prompt_lower for k in ["test çalıştır", "testleri çalıştır", "unit test", "kod durumu"]):
            return {
                "specialist": "CodeSpecialist",
                "intent": "run_tests",
                "result": self.code.run_tests()
            }

        if any(k in prompt_lower for k in ["git diff", "değişiklikler", "ne değişti"]):
            return {
                "specialist": "CodeSpecialist",
                "intent": "get_git_diff",
                "result": self.code.get_git_diff()
            }

        # 4. 'Global Wave / Video Üretimi veya Durumu'
        if any(k in prompt_lower for k in ["video üret", "shorts üret", "içerik üret", "fikir hazırla"]):
            # Extract topic if present (e.g., 'video üret: Yapay zeka devrimi' or 'shorts hazırla: Bitcoin')
            topic = "Geleceğin Yapay Zeka Teknolojileri"
            if ":" in user_prompt:
                topic = user_prompt.split(":", 1)[1].strip()
            return {
                "specialist": "ContentSpecialist",
                "intent": "produce_draft",
                "topic": topic,
                "result": self.content.produce_draft(topic=topic, target_duration="45s")
            }

        if any(k in prompt_lower for k in ["video motoru", "global wave", "zenvia", "içerik fabrikası"]):
            return {
                "specialist": "ContentSpecialist",
                "intent": "check_pipeline_status",
                "result": self.content.check_pipeline_status()
            }

        # 5. Infrastructure: Docker & Local AI Models
        if any(k in prompt_lower for k in ["docker", "konteyner"]):
            return {
                "specialist": "SystemSpecialist",
                "intent": "check_docker",
                "result": self.system.check_docker()
            }

        if any(k in prompt_lower for k in ["yerel model", "ollama model", "hangi modeller"]):
            return {
                "specialist": "SystemSpecialist",
                "intent": "get_ai_models",
                "result": self.system.get_ai_models()
            }

        if any(k in prompt_lower for k in ["aktif görevler", "arka plan işleri", "görev kuyruğu", "iş durumu"]):
            return {
                "specialist": "TaskCoordinator",
                "intent": "list_jobs",
                "result": self.coordinator.list_jobs()
            }

        # 6. Autonomous Web & Documentation Research
        if any(k in prompt_lower for k in ["araştır", "araştırma", "web'de ara", "internette ara", "dokümantasyon"]):
            query = user_prompt.split(":", 1)[1].strip() if ":" in user_prompt else user_prompt
            res = self.research.research_topic(query=query, auto_note=True)
            return {
                "specialist": "ResearchSpecialist",
                "intent": "research_topic",
                "query": query,
                "speak_text": res.get("summary_text"),
                "result": res
            }

        if any(k in prompt_lower for k in ["model karşılaştır", "modelleri karşılaştır", "donanım modeli", "en iyi model", "model kıyasla"]):
            cat = "coding"
            if "reasoning" in prompt_lower or "akıl" in prompt_lower or "mantık" in prompt_lower:
                cat = "reasoning"
            elif "genel" in prompt_lower or "agent" in prompt_lower:
                cat = "general"
            res = self.research.compare_models(category=cat)
            return {
                "specialist": "ResearchSpecialist",
                "intent": "compare_models",
                "category": cat,
                "speak_text": res.get("executive_summary"),
                "result": res
            }

        # Default: Fallback to General Autonomous Query or Brain
        return {
            "specialist": "ExecutiveJarvis",
            "intent": "general_query",
            "message": "Niyet anlaşıldı. Bu görev için uygun uzman ajan devrede.",
            "reality_state": self.memory.sync_with_reality()
        }


orchestrator = JarvisOrchestrator()
