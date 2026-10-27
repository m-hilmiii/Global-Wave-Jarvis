"""
JARVIS Hardware Telemetry, System Control & Infrastructure Router
Handles CPU/RAM/GPU telemetry, safe PowerShell commands, and AI model routing.
"""

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from typing import Optional

from core_jarvis.tools.system_tool import system_tool
from core_jarvis.vram_guard import vram_guard
from core_jarvis.proactive_daemon import proactive_watchdog
from core_jarvis.tools.infra_tool import infra_tool
from core_jarvis.logger import get_logger
from web.schemas import PowerShellRequest, ModelRouteRequest

logger = get_logger("Jarvis.Router.Telemetry")
router = APIRouter(prefix="/api/jarvis", tags=["Telemetry & System"])


async def _safe_json(request: Request) -> dict:
    try:
        data = await request.json()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


@router.get("/system/telemetry")
async def api_jarvis_system_telemetry():
    """Returns real-time CPU, RAM, Disk, GPU, and top process telemetry."""
    data = await run_in_threadpool(system_tool.get_hardware_telemetry)
    return {"status": "success", "telemetry": data}


@router.get("/telemetry")
async def api_jarvis_telemetry():
    """Returns VRAM Guard system metrics."""
    return {"status": "success", "metrics": vram_guard.get_system_metrics()}


@router.post("/system/powershell")
async def api_jarvis_system_powershell(payload: PowerShellRequest):
    """Executes a whitelisted PowerShell command with safety guardrails."""
    cmd = payload.command.strip()
    if not cmd:
        return JSONResponse({"status": "error", "message": "Komut boş olamaz."}, status_code=status.HTTP_400_BAD_REQUEST)

    res = await run_in_threadpool(system_tool.run_safe_powershell, cmd, payload.confirmed)
    return {"status": "success" if res.get("success") else "error", "result": res}


@router.post("/system/backup")
async def api_jarvis_system_backup(request: Request):
    """Creates a snapshot backup of a file."""
    payload = await _safe_json(request)
    file_path = payload.get("file_path", "").strip()
    note = payload.get("note", "api_backup").strip()
    if not file_path:
        return JSONResponse({"status": "error", "message": "file_path gereklidir."}, status_code=status.HTTP_400_BAD_REQUEST)

    res = await run_in_threadpool(system_tool.create_snapshot, file_path, note)
    return {"status": "success" if res.get("success") else "error", "result": res}


@router.get("/system/diagnose")
async def api_jarvis_system_diagnose():
    """Diagnoses system hardware bottlenecks (VRAM, thermal, CPU limits)."""
    res = await run_in_threadpool(system_tool.diagnose_system_bottlenecks)
    return {"status": "success", "diagnosis": res}


@router.post("/files/organize")
async def api_jarvis_files_organize(request: Request):
    """Organizes downloads or project folders into categorized directories."""
    payload = await request.json() if request.headers.get("content-length") else {}
    preview_only = bool(payload.get("preview_only", True))
    res = await run_in_threadpool(system_tool.organize_downloads_folder, preview_only=preview_only)
    return {"status": "success", "result": res}


@router.get("/watchdog/alerts")
async def api_jarvis_watchdog_alerts():
    """Retrieves recent proactive watchdog anomaly alerts."""
    res = await run_in_threadpool(proactive_watchdog.get_recent_alerts, 10)
    return {"status": "success", "alerts": res}


@router.get("/infra/models")
async def api_jarvis_infra_models():
    """Lists local Ollama models installed on the system."""
    res = await run_in_threadpool(infra_tool.get_ollama_models)
    return {"status": "success", "models": res}


@router.post("/infra/route")
async def api_jarvis_infra_route(payload: ModelRouteRequest):
    """Dynamically activates or switches target AI model on RX 9060 XT."""
    target = payload.task_type or payload.model or "general"
    res = await run_in_threadpool(infra_tool.route_model_for_task, target)
    return {"status": "success", "routing": res}


@router.get("/infra/docker")
async def api_jarvis_infra_docker():
    """Reports Docker daemon and container status."""
    res = await run_in_threadpool(infra_tool.check_docker_status)
    return {"status": "success", "docker": res}


# ---------------------------------------------------------------------------
# Network WOL & Security Audit
# ---------------------------------------------------------------------------
from core_jarvis.tools.wol_tool import wol_tool
from core_jarvis.permission_guard import permission_guard

@router.get("/wol/identity")
async def api_jarvis_wol_identity():
    """Returns local host Wake-on-LAN identifiers (MAC, subnet, IP)."""
    identity = await run_in_threadpool(wol_tool.get_host_wol_identity)
    return {"status": "success", "wol_identity": identity}


@router.post("/wol/wake")
async def api_jarvis_wol_wake(request: Request):
    """Sends a magic packet to wake up a remote workstation with strict validation and Level 3 confirmation."""
    data = await _safe_json(request)
    mac = data.get("mac_address", "").strip()
    broadcast_ip = data.get("broadcast_ip", "255.255.255.255").strip()
    raw_port = data.get("port", 9)
    try:
        port = int(raw_port)
        if not (1 <= port <= 65535):
            raise ValueError()
    except Exception:
        return JSONResponse({"status": "error", "message": "Geçersiz port numarası (1-65535 aralığında olmalıdır)."}, status_code=status.HTTP_400_BAD_REQUEST)

    if not mac:
        return JSONResponse({"status": "error", "message": "Hedef MAC adresi zorunludur."}, status_code=status.HTTP_400_BAD_REQUEST)

    try:
        from core_jarvis.tools.wol_tool import WOLTool
        WOLTool.clean_mac(mac)
    except ValueError as ve:
        return JSONResponse({"status": "error", "message": f"Geçersiz MAC adresi: {ve}"}, status_code=status.HTTP_400_BAD_REQUEST)

    confirmed = bool(data.get("confirmed", False))
    eval_res = permission_guard.evaluate_action("wol_dispatch", confirmed_by_user=confirmed)
    if not eval_res["allowed"]:
        return JSONResponse({
            "status": "error",
            "message": eval_res["reason"],
            "requires_confirmation": True
        }, status_code=status.HTTP_403_FORBIDDEN)

    res = await run_in_threadpool(wol_tool.send_magic_packet, mac, broadcast_ip=broadcast_ip, port=port)
    return {"status": "success" if res.get("success") else "error", "result": res}


@router.get("/security/audit")
async def api_jarvis_security_audit():
    """Returns the persistent security guardrail audit trail."""
    return {
        "status": "success",
        "audit_trail": permission_guard.get_audit_trail(limit=50)
    }


@router.get("/protocol_zero/status")
async def api_jarvis_protocol_zero_status():
    """Returns the current Protocol Zero (emergency lockdown) status."""
    from core_jarvis.protocol_zero import protocol_zero
    return {"status": "success", "protocol_zero": protocol_zero.get_status()}


@router.post("/protocol_zero/activate")
async def api_jarvis_protocol_zero_activate(request: Request):
    """Engages Protocol Zero emergency lockdown immediately."""
    from core_jarvis.protocol_zero import protocol_zero
    data = await _safe_json(request)
    reason = data.get("reason", "Web HUD üzerinden acil durum kilidi tetiklendi.")
    res = await run_in_threadpool(protocol_zero.activate, reason=reason)
    return {"status": "success", "result": res}


@router.post("/protocol_zero/deactivate")
async def api_jarvis_protocol_zero_deactivate():
    """Releases Protocol Zero and restores nominal system status."""
    from core_jarvis.protocol_zero import protocol_zero
    res = await run_in_threadpool(protocol_zero.deactivate)
    return {"status": "success", "result": res}


@router.post("/system/hygiene")
async def api_jarvis_system_hygiene(request: Request):
    """Scans or cleans temporary render files, caches and orphaned locks."""
    data = await _safe_json(request)
    preview_only = bool(data.get("preview_only", True))
    res = await run_in_threadpool(system_tool.clean_system_hygiene, preview_only=preview_only)
    return {"status": "success", "result": res}


@router.get("/finance/rates")
async def api_jarvis_finance_rates():
    """Returns live and cached foreign exchange rates."""
    from core_jarvis.tools.finance_tool import finance_tool
    res = await run_in_threadpool(finance_tool.get_live_rates)
    return {"status": "success", "result": res}


@router.post("/finance/calc")
async def api_jarvis_finance_calc(request: Request):
    """Safely evaluates a mathematical expression or currency conversion."""
    from core_jarvis.tools.finance_tool import finance_tool
    data = await _safe_json(request)
    if "expression" in data:
        res = await run_in_threadpool(finance_tool.evaluate_math, data["expression"])
        return {"status": "success" if res.get("success") else "error", "result": res}
    elif "amount" in data:
        amount = float(data.get("amount", 1.0))
        from_curr = data.get("from_currency", "USD")
        to_curr = data.get("to_currency", "TRY")
        res = await run_in_threadpool(finance_tool.convert_currency, amount, from_curr, to_curr)
        return {"status": "success" if res.get("success") else "error", "result": res}
    return JSONResponse({"status": "error", "message": "Geçersiz istek parametresi."}, status_code=status.HTTP_400_BAD_REQUEST)


@router.post("/pdf/extract")
async def api_jarvis_pdf_extract(request: Request):
    """Extracts text and metadata from a local PDF document."""
    from core_jarvis.tools.pdf_tool import pdf_tool
    data = await _safe_json(request)
    file_path = data.get("file_path", "")
    if not file_path:
        return JSONResponse({"status": "error", "message": "file_path zorunludur."}, status_code=status.HTTP_400_BAD_REQUEST)
    res = await run_in_threadpool(pdf_tool.extract_text, file_path)
    return {"status": "success" if res.get("success") else "error", "result": res}
