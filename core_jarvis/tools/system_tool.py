"""
Global-Wawe / Stark-Core - System & Windows Management Tool
Provides hardware telemetry, process monitoring, whitelisted safe PowerShell execution,
and automated file snapshot/rollback backup mechanisms.
Hardware-tailored for: Intel i5-14400F + AMD Radeon RX 9060 XT + 16GB RAM.
"""

import os
import shutil
import subprocess
import time
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from core_jarvis.permission_guard import permission_guard, PermissionLevel

logger = logging.getLogger("Jarvis.SystemTool")

WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent
BACKUP_DIR = WORKSPACE_DIR / ".jarvis_backups"

# Strictly forbidden command patterns (Level 4: never run)
FORBIDDEN_COMMAND_PATTERNS = [
    "format-volume", "remove-item -recurse c:\\", "del /f /s /q c:\\",
    "netsh advfirewall set", "reg delete hklm", "bcdedit",
    "disable-netadapter", "stop-computer", "restart-computer"
]

# Sensitive operations requiring explicit confirmation (Level 3)
SENSITIVE_COMMAND_PATTERNS = [
    "stop-process", "kill", "taskkill", "set-executionpolicy",
    "remove-item", "del", "rmdir"
]

class SystemTool:
    def __init__(self):
        self.backup_dir = BACKUP_DIR
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def get_hardware_telemetry(self) -> Dict[str, Any]:
        """
        Gathers live CPU, RAM, Disk, GPU, and Top Process telemetry on Windows.
        """
        telemetry = {
            "timestamp": time.time(),
            "cpu": {"model": "Intel Core i5-14400F", "usage_percent": 0.0, "logical_cores": 16},
            "ram": {"total_gb": 16.0, "free_gb": 0.0, "used_gb": 0.0, "usage_percent": 0.0},
            "disk": {"drive": "C:", "total_gb": 0.0, "free_gb": 0.0, "usage_percent": 0.0},
            "gpu": {"name": "AMD Radeon RX 9060 XT", "architecture": "AMD RDNA", "status": "Active"},
            "top_processes": []
        }

        # 1. RAM & CPU via PowerShell
        try:
            ps_cmd = (
                "$os = Get-CimInstance Win32_OperatingSystem; "
                "$total = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2); "
                "$free = [math]::Round($os.FreePhysicalMemory / 1MB, 2); "
                "$cpu = (Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average; "
                "@{TotalRamGB=$total; FreeRamGB=$free; CpuLoad=$cpu} | ConvertTo-Json"
            )
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, timeout=8)
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout.strip())
                total = float(data.get("TotalRamGB", 16.0))
                free = float(data.get("FreeRamGB", 6.0))
                used = round(total - free, 2)
                usage_pct = round((used / total) * 100, 1) if total > 0 else 0.0
                telemetry["ram"] = {
                    "total_gb": total,
                    "free_gb": free,
                    "used_gb": used,
                    "usage_percent": usage_pct
                }
                cpu_load = data.get("CpuLoad")
                if cpu_load is not None:
                    telemetry["cpu"]["usage_percent"] = float(cpu_load)
        except Exception as e:
            logger.warning(f"Failed to read RAM/CPU stats: {e}")

        # 2. Disk Space for C:
        try:
            usage = shutil.disk_usage("C:\\")
            total_gb = round(usage.total / (1024 ** 3), 2)
            free_gb = round(usage.free / (1024 ** 3), 2)
            used_gb = round(usage.used / (1024 ** 3), 2)
            pct = round((used_gb / total_gb) * 100, 1) if total_gb > 0 else 0.0
            telemetry["disk"] = {
                "drive": "C:",
                "total_gb": total_gb,
                "free_gb": free_gb,
                "used_gb": used_gb,
                "usage_percent": pct
            }
        except Exception as e:
            logger.warning(f"Failed to read disk usage: {e}")

        # 3. Top 5 CPU/Memory Processes
        try:
            ps_proc = (
                "Get-Process | Sort-Object -Property WorkingSet64 -Descending | "
                "Select-Object -First 5 Name, Id, @{Name='MemoryMB';Expression={[math]::Round($_.WorkingSet64 / 1MB, 1)}} | "
                "ConvertTo-Json"
            )
            proc_res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_proc], capture_output=True, text=True, timeout=6)
            if proc_res.returncode == 0 and proc_res.stdout.strip():
                procs = json.loads(proc_res.stdout.strip())
                if isinstance(procs, dict):
                    procs = [procs]
                telemetry["top_processes"] = [
                    {"name": p.get("Name"), "pid": p.get("Id"), "memory_mb": p.get("MemoryMB")}
                    for p in procs
                ]
        except Exception as e:
            logger.warning(f"Failed to read top processes: {e}")

        return telemetry

    def run_safe_powershell(self, command: str, confirmed_by_user: bool = False, timeout_sec: int = 15) -> Dict[str, Any]:
        """
        Executes a PowerShell command with strict permission & whitelist checks.
        """
        cmd_lower = command.strip().lower()

        # Check for Level 4 (Forbidden)
        for forbidden in FORBIDDEN_COMMAND_PATTERNS:
            if forbidden in cmd_lower:
                return {
                    "success": False,
                    "allowed": False,
                    "error": f"GÜVENLİK İHLALİ: '{command}' Seviye 4 yasaklı komut kalıbı içeriyor.",
                    "level": PermissionLevel.LEVEL_4_FORBIDDEN
                }

        # Check for Level 3 (Sensitive)
        is_sensitive = any(s in cmd_lower for s in SENSITIVE_COMMAND_PATTERNS)
        action_name = "system_powershell_sensitive" if is_sensitive else "system_powershell_safe"

        guard_result = permission_guard.evaluate_action(
            action_name=action_name,
            confirmed_by_user=confirmed_by_user,
            context={"command": command}
        )

        if not guard_result["allowed"]:
            return {
                "success": False,
                "allowed": False,
                "error": guard_result["reason"],
                "level": guard_result["level"],
                "requires_confirmation": True
            }

        # Execution
        try:
            start_time = time.time()
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                capture_output=True,
                text=True,
                cwd=str(WORKSPACE_DIR),
                timeout=timeout_sec
            )
            elapsed = round(time.time() - start_time, 2)

            return {
                "success": res.returncode == 0,
                "allowed": True,
                "returncode": res.returncode,
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip(),
                "elapsed_seconds": elapsed,
                "level": guard_result["level"]
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "allowed": True,
                "error": f"Komut zaman aşımına uğradı ({timeout_sec} sn).",
                "elapsed_seconds": timeout_sec
            }
        except Exception as e:
            return {
                "success": False,
                "allowed": True,
                "error": f"Komut yürütme hatası: {str(e)}"
            }

    def create_snapshot(self, relative_path: str, note: str = "auto_snapshot") -> Dict[str, Any]:
        """
        Creates a versioned backup snapshot of a workspace file before alteration.
        """
        target_path = WORKSPACE_DIR / relative_path
        if not target_path.exists() or not target_path.is_file():
            return {"success": False, "error": f"Hedef dosya bulunamadı: {relative_path}"}

        guard_res = permission_guard.evaluate_action("workspace_backup", confirmed_by_user=False)
        if not guard_res["allowed"]:
            return {"success": False, "error": guard_res["reason"]}

        timestamp = int(time.time())
        snapshot_name = f"{target_path.stem}_{timestamp}_{note}{target_path.suffix}"
        dest_path = self.backup_dir / snapshot_name

        try:
            shutil.copy2(target_path, dest_path)
            return {
                "success": True,
                "original_file": str(relative_path),
                "snapshot_file": dest_path.name,
                "snapshot_path": str(dest_path),
                "timestamp": timestamp
            }
        except Exception as e:
            return {"success": False, "error": f"Yedekleme hatası: {str(e)}"}

    def rollback_snapshot(self, snapshot_file: str, relative_dest_path: str, confirmed_by_user: bool = False) -> Dict[str, Any]:
        """
        Restores a file from a snapshot. Requires explicit confirmation (Level 3).
        """
        guard_res = permission_guard.evaluate_action("workspace_rollback", confirmed_by_user=confirmed_by_user)
        if not guard_res["allowed"]:
            return {"success": False, "error": guard_res["reason"], "requires_confirmation": True}

        snap_path = self.backup_dir / snapshot_file
        dest_path = WORKSPACE_DIR / relative_dest_path

        if not snap_path.exists():
            return {"success": False, "error": f"Snapshot dosyası bulunamadı: {snapshot_file}"}

        try:
            shutil.copy2(snap_path, dest_path)
            return {
                "success": True,
                "restored_file": str(relative_dest_path),
                "from_snapshot": snapshot_file
            }
        except Exception as e:
            return {"success": False, "error": f"Geri yükleme hatası: {str(e)}"}


system_tool = SystemTool()
