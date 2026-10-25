"""
Global-Wawe / Stark-Core - 7-Step Autonomous Execution Engine
Transforms high-level user goals into verified, safe, accountable actions:
1. Understand Goal
2. Form Plan
3. Check Permissions (via 4-Level Permission Guard)
4. Execute (via approved tools/specialists)
5. Verify (via tests, file state, or exit codes)
6. Fix or Stop (safe self-correction with retry limits)
7. Report (transparent summary of changes and remaining risks)
"""

import time
import logging
from typing import Dict, Any, List, Optional, Callable

from core_jarvis.permission_guard import permission_guard, PermissionLevel
from core_jarvis.reality_memory import reality_memory

logger = logging.getLogger("Jarvis.AutonomousEngine")

class AutonomousEngine:
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    def run_goal_loop(
        self,
        goal: str,
        plan_steps: List[Dict[str, Any]],
        executor_func: Callable[[Dict[str, Any]], Dict[str, Any]],
        verifier_func: Optional[Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]] = None,
        fixer_func: Optional[Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]] = None,
        user_confirmed: bool = False
    ) -> Dict[str, Any]:
        """
        Executes a multi-step plan following the strict 7-Step Autonomous Loop.
        """
        # Step 1: Understand Goal
        start_time = time.time()
        step_descriptions = [s.get("description", f"Step {i+1}") for i, s in enumerate(plan_steps)]
        active_task = reality_memory.set_active_task(name=goal, plan_steps=step_descriptions)

        execution_log: List[Dict[str, Any]] = []
        overall_success = True
        blocker = None

        logger.info(f"[AutonomousEngine] Starting goal: {goal} ({len(plan_steps)} steps)")

        # Step 2: Iterate through Planned Steps
        for step_idx, step in enumerate(plan_steps):
            step_action = step.get("action", "unspecified_action")
            step_desc = step.get("description", f"Adım {step_idx + 1}")
            requires_conf = step.get("requires_confirmation", False)
            confirmed = user_confirmed or not requires_conf

            step_record = {
                "step_index": step_idx + 1,
                "description": step_desc,
                "action": step_action,
                "status": "pending",
                "retries": 0,
                "permission_granted": False,
                "execution_result": None,
                "verification_result": None
            }

            # Step 3: Check Permissions
            guard_res = permission_guard.evaluate_action(
                action_name=step_action,
                confirmed_by_user=confirmed,
                context=step.get("context", {})
            )
            step_record["permission_level"] = guard_res["level"]
            step_record["permission_granted"] = guard_res["allowed"]

            if not guard_res["allowed"]:
                step_record["status"] = "blocked_permission"
                step_record["error"] = guard_res["reason"]
                execution_log.append(step_record)
                reality_memory.mark_task_failed(reason=f"İzin engeli: {guard_res['reason']}")
                return {
                    "goal": goal,
                    "success": False,
                    "blocked_at_step": step_idx + 1,
                    "reason": guard_res["reason"],
                    "requires_user_confirmation": guard_res["level"] == PermissionLevel.LEVEL_3_CONFIRMED,
                    "execution_log": execution_log,
                    "elapsed_seconds": round(time.time() - start_time, 2)
                }

            # Step 4: Execute & Step 5: Verify & Step 6: Fix or Stop
            attempts = 0
            step_success = False
            last_err = None

            while attempts < self.max_retries and not step_success:
                attempts += 1
                step_record["retries"] = attempts - 1

                # 4. Execute
                try:
                    exec_res = executor_func(step)
                    step_record["execution_result"] = exec_res
                except Exception as e:
                    exec_res = {"success": False, "error": str(e)}
                    step_record["execution_result"] = exec_res

                # 5. Verify
                if verifier_func:
                    try:
                        verif_res = verifier_func(step, exec_res)
                    except Exception as ve:
                        verif_res = {"verified": False, "error": f"Doğrulama hatası: {str(ve)}"}
                else:
                    # Default verification based on execution success
                    verif_res = {
                        "verified": exec_res.get("success", False),
                        "details": exec_res.get("stdout", "") or exec_res.get("message", "Executed")
                    }

                step_record["verification_result"] = verif_res

                if verif_res.get("verified", False):
                    step_success = True
                    step_record["status"] = "completed"
                    break

                # 6. Fix or Stop
                last_err = verif_res.get("error") or exec_res.get("error", "Doğrulama başarısız")
                logger.warning(f"[AutonomousEngine] Step {step_idx+1} failed verification (Attempt {attempts}/{self.max_retries}): {last_err}")

                if attempts < self.max_retries and fixer_func:
                    try:
                        fix_res = fixer_func(step, {"error": last_err, "attempt": attempts})
                        step_record["last_fix_attempt"] = fix_res
                    except Exception as fe:
                        logger.error(f"[AutonomousEngine] Fixer error: {fe}")

            if not step_success:
                overall_success = False
                step_record["status"] = "failed"
                step_record["error"] = f"Maksimum deneme sınırına ({self.max_retries}) ulaşıldı: {last_err}"
                execution_log.append(step_record)
                reality_memory.mark_task_failed(reason=step_record["error"])
                blocker = step_record["error"]
                break

            execution_log.append(step_record)
            reality_memory.update_task_step(step_index=step_idx, completed=True, result=exec_res)

        # Step 7: Report
        total_time = round(time.time() - start_time, 2)
        report = {
            "goal": goal,
            "success": overall_success,
            "completed_steps": sum(1 for s in execution_log if s.get("status") == "completed"),
            "total_steps": len(plan_steps),
            "execution_log": execution_log,
            "elapsed_seconds": total_time,
            "blocker": blocker,
            "summary": (
                f"Hedef '{goal}' başarıyla tamamlandı ({total_time} sn)."
                if overall_success else
                f"Hedef '{goal}' durduruldu. Engel: {blocker}"
            )
        }

        # Sync reality to make sure memory is ground truth
        reality_memory.sync_with_reality()
        return report

    def decompose_goal_into_steps(self, goal: str, max_steps: int = 5) -> List[Dict[str, Any]]:
        """
        Decomposes a compound natural language goal into executable specialist steps
        (capped at max_steps=5 to prevent infinite loops).
        """
        g_low = goal.lower()
        steps: List[Dict[str, Any]] = []

        if any(k in g_low for k in ["git diff", "ne değişti", "değişiklik", "git durum"]):
            steps.append({
                "action": "git_status",
                "tool": "git_diff",
                "description": "Çalışma alanındaki Git değişikliklerini incele"
            })
        if any(k in g_low for k in ["test", "birim test", "doğrula"]):
            steps.append({
                "action": "run_tests",
                "tool": "code_tests",
                "description": "Proje birim testlerini çalıştır ve doğrula"
            })
        if any(k in g_low for k in ["sistem durum", "telemetri", "donanım", "ram", "vram"]):
            steps.append({
                "action": "get_telemetry",
                "tool": "system_status",
                "description": "Donanım, RAM ve VRAM telemetrisini oku"
            })
        if any(k in g_low for k in ["ekran", "görüntü", "hataya bak"]):
            steps.append({
                "action": "file_read",
                "tool": "screen_inspect",
                "description": "Aktif ekran görüntüsünü yakala ve Qwen2.5-VL ile analiz et"
            })
        if any(k in g_low for k in ["araştır", "web", "internet"]):
            steps.append({
                "action": "web_search",
                "tool": "web_research",
                "query": goal,
                "description": f"Web araştırması yürüt: {goal[:50]}"
            })
        if any(k in g_low for k in ["brifing", "ajanda", "günlük özet"]):
            steps.append({
                "action": "get_daily_briefing",
                "tool": "daily_briefing",
                "description": "Günlük yönetici brifingini derle"
            })
        if any(k in g_low for k in ["not al", "notlara kaydet", "raporu kaydet", "kaydet"]):
            steps.append({
                "action": "add_note",
                "tool": "add_note",
                "description": "Elde edilen bulguları yönetici notlarına arşivle"
            })

        if not steps:
            steps.append({
                "action": "get_telemetry",
                "tool": "system_status",
                "description": f"Hedef analizi ve sistem kontrolü: {goal[:50]}"
            })

        return steps[:max_steps]

    def plan_and_execute_goal(self, goal: str, max_steps: int = 5, user_confirmed: bool = False) -> Dict[str, Any]:
        """
        End-to-end 7-Step Autonomous Goal Planner & Executor:
        Decomposes a compound directive into up to 5 verified steps and executes them sequentially.
        """
        plan_steps = self.decompose_goal_into_steps(goal, max_steps=max_steps)
        accumulated_notes: List[str] = []

        def _step_executor(step: Dict[str, Any]) -> Dict[str, Any]:
            tool = step.get("tool", "")
            if tool == "git_diff":
                from core_jarvis.orchestrator import orchestrator
                res = orchestrator.code.get_git_diff()
                out = res.get("output", "Kaydedilmemiş değişiklik yok.")
                accumulated_notes.append(f"[Git Diff]: {out[:300]}")
                return {"success": True, "message": out[:300]}

            if tool == "code_tests":
                from core_jarvis.orchestrator import orchestrator
                res = orchestrator.code.run_tests()
                ok = res.get("success", False)
                msg = "Tüm testler geçti." if ok else f"Test hatası: {res.get('error', '')}"
                accumulated_notes.append(f"[Testler]: {msg}")
                return {"success": ok, "message": msg, "error": res.get("error", "")}

            if tool == "system_status":
                from core_jarvis.vram_guard import vram_guard
                m = vram_guard.get_system_metrics()
                msg = f"RAM %{m.get('ram_used_pct')} dolu ({m.get('ram_available_gb')} GB boş)."
                accumulated_notes.append(f"[Telemetri]: {msg}")
                return {"success": True, "message": msg}

            if tool == "screen_inspect":
                from core_jarvis.tools.vision_tool import vision_tool
                res = vision_tool.analyze_screen(prompt=goal, mode="general")
                msg = res.get("analysis", "Ekran incelendi.")
                accumulated_notes.append(f"[Ekran]: {msg[:250]}")
                return {"success": res.get("success", True), "message": msg}

            if tool == "web_research":
                from core_jarvis.tools.browser_research_tool import browser_research_tool
                res = browser_research_tool.conduct_research_and_archive(topic=step.get("query", goal), auto_note=False)
                msg = res.get("summary_text", "")
                accumulated_notes.append(f"[Web Araştırması]: {msg[:300]}")
                return {"success": True, "message": msg}

            if tool == "daily_briefing":
                from core_jarvis.personal_assistant import personal_assistant
                b = personal_assistant.get_daily_briefing()
                msg = b.get("speak_text", "")
                accumulated_notes.append(f"[Brifing]: {msg}")
                return {"success": True, "message": msg}

            if tool == "add_note":
                from core_jarvis.personal_assistant import personal_assistant
                body = "\n".join(accumulated_notes) if accumulated_notes else goal
                personal_assistant.add_note(title=f"Otonom Görev Raporu: {goal[:35]}", content=body, tags=["autonomous"])
                return {"success": True, "message": "Bulgular yönetici notlarına kaydedildi."}

            return {"success": True, "message": "Adım tamamlandı."}

        return self.run_goal_loop(
            goal=goal,
            plan_steps=plan_steps,
            executor_func=_step_executor,
            user_confirmed=user_confirmed
        )


autonomous_engine = AutonomousEngine()
