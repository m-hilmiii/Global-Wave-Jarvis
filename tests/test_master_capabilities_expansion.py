"""
Unit Tests for JARVIS Master Capabilities Expansion & Model Arsenal Audit
Verifies:
1. Model Manager on-disk manifests detection and new specialist roles (Mistral-NeMo, DeepSeek-R1, Coder Q8_0).
2. Protocol Zero (Kill-Switch / Lockdown Engine).
3. System Hygiene & Temp Cleaner (Akıllı Disk & Sistem Hijyen Robotu).
4. PDF Tool Extraction & Document Summarizer.
5. Finance & Safe Math AST Evaluator (FX Rates & KDV/Margin).
6. Brain Fast-Path Reflex Routing for all new intents.
7. Telemetry Router REST API endpoints.
"""

import os
import json
import tempfile
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from core_jarvis.tools.model_manager import model_manager, SPECIALIST_ARSENAL
from core_jarvis.protocol_zero import protocol_zero
from core_jarvis.tools.system_tool import system_tool
from core_jarvis.tools.pdf_tool import pdf_tool
from core_jarvis.tools.finance_tool import finance_tool, safe_math_eval
from core_jarvis.jarvis_brain import jarvis_brain
from web.server import app, LOCAL_SESSION_TOKEN


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-Local-Token": LOCAL_SESSION_TOKEN}


# ==========================================
# 1. Model Manager & Arsenal Tests
# ==========================================
def test_model_manager_expanded_arsenal():
    status = model_manager.get_arsenal_status()
    arsenal = status.get("arsenal", [])
    roles = {a["role"] for a in arsenal}

    assert "primary_brain" in roles
    assert "embedding" in roles
    assert "vision" in roles
    assert "coding" in roles
    assert "reasoning" in roles
    assert "deep_reasoning" in roles
    assert "long_context" in roles

    # Check that DeepSeek-R1 and Mistral-NeMo are recognized
    deep_spec = next(a for a in arsenal if a["role"] == "deep_reasoning")
    assert "deepseek-r1" in deep_spec["recommended_model"]

    nemo_spec = next(a for a in arsenal if a["role"] == "long_context")
    assert "mistral-nemo" in nemo_spec["recommended_model"]


def test_model_manager_generate_with_role():
    res_deep = model_manager.generate_with_role("deep_reasoning", "1+1 nedir?")
    assert res_deep.get("success") is True
    assert "deepseek-r1" in res_deep.get("model", "")

    res_nemo = model_manager.generate_with_role("long_context", "Bu dokümanı analiz et.")
    assert res_nemo.get("success") is True
    assert "mistral-nemo" in res_nemo.get("model", "")


def test_model_manager_disk_manifest_scan():
    manifests = model_manager._scan_disk_manifests()
    # If ran on the host, it should find downloaded Ollama models
    assert isinstance(manifests, list)
    if manifests:
        assert any("qwen" in m or "llama" in m or "bge" in m for m in manifests)


# ==========================================
# 2. Protocol Zero Tests
# ==========================================
def test_protocol_zero_lifecycle():
    # Activate
    act_res = protocol_zero.activate(reason="Test Acil Durum")
    assert act_res["success"] is True
    assert act_res["status"] == "ENGAGED"
    assert protocol_zero.is_active is True

    status = protocol_zero.get_status()
    assert status["active"] is True
    assert status["reason"] == "Test Acil Durum"

    # Deactivate
    deact_res = protocol_zero.deactivate()
    assert deact_res["success"] is True
    assert deact_res["status"] == "RESTORED"
    assert protocol_zero.is_active is False


# ==========================================
# 3. System Hygiene Tests
# ==========================================
def test_system_hygiene_preview_and_clean():
    # Create a temporary scratch file in temp dir
    with tempfile.NamedTemporaryFile(prefix="jarvis_temp_", suffix=".tmp", delete=False) as tmp:
        tmp.write(b"Temporary scratch render data 12345")
        tmp_path = tmp.name

    try:
        # Preview mode
        res_prev = system_tool.clean_system_hygiene(preview_only=True)
        assert res_prev["success"] is True
        assert res_prev["preview_only"] is True
        assert res_prev["deleted_count"] == 0

        # Run mode
        res_clean = system_tool.clean_system_hygiene(preview_only=False)
        assert res_clean["success"] is True
        assert res_clean["preview_only"] is False
    finally:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


# ==========================================
# 4. PDF Tool Tests
# ==========================================
def test_pdf_tool_extraction():
    # Create a valid minimal PDF using pypdf
    import pypdf
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=72, height=72)
    test_pdf = Path(tempfile.gettempdir()) / "jarvis_unit_test.pdf"

    try:
        with open(test_pdf, "wb") as f:
            writer.write(f)

        res = pdf_tool.extract_text(str(test_pdf))
        assert res["success"] is True
        assert res["total_pages"] == 1
        assert "file_name" in res

        sum_res = pdf_tool.summarize_pdf(str(test_pdf))
        assert sum_res["success"] is True
        assert "summary" in sum_res
    finally:
        if test_pdf.exists():
            test_pdf.unlink()


def test_pdf_tool_not_found():
    res = pdf_tool.extract_text("non_existent_file_xyz_123.pdf")
    assert res["success"] is False
    assert "bulunamadı" in res["error"]


# ==========================================
# 5. Finance & Math Calculator Tests
# ==========================================
def test_safe_math_eval():
    assert safe_math_eval("2 + 3 * 4") == 14.0
    assert safe_math_eval("100 / 4") == 25.0
    assert safe_math_eval("2 ^ 8") == 256.0
    assert safe_math_eval("sqrt(144)") == 12.0
    assert safe_math_eval("round(3.14159, 2)") == 3.14

    with pytest.raises(Exception):
        safe_math_eval("__import__('os').system('ls')")


def test_finance_tool_math_and_currency():
    res_math = finance_tool.evaluate_math("1500 * 1.20")
    assert res_math["success"] is True
    assert res_math["result"] == 1800.0

    res_rates = finance_tool.get_live_rates()
    assert res_rates["success"] is True
    assert "rates" in res_rates
    assert "TRY" in res_rates["rates"]

    res_conv = finance_tool.convert_currency(100, from_curr="USD", to_curr="TRY")
    assert res_conv["success"] is True
    assert res_conv["converted_amount"] > 0

    res_vat = finance_tool.calculate_vat_or_margin(1000, vat_rate=20.0, margin_pct=15.0)
    assert res_vat["success"] is True
    assert res_vat["total_with_vat"] == 1200.0
    assert res_vat["profit_amount"] == 150.0


# ==========================================
# 6. Brain Fast-Path Reflex Routing Tests
# ==========================================
def test_brain_fast_path_reflexes():
    # 1. Screen inspect
    r = jarvis_brain.process_message("ekranıma bak hatayı çöz")
    assert r["action_taken"] == "screen_inspect"

    # 2. Protocol Zero
    r = jarvis_brain.process_message("protokol sıfır")
    assert r["action_taken"] == "protocol_zero_engage"

    r = jarvis_brain.process_message("protokol sıfırı kaldır")
    assert r["action_taken"] == "protocol_zero_release"

    # 3. System Hygiene
    r = jarvis_brain.process_message("sistem temizliği yap")
    assert r["action_taken"] == "system_hygiene"

    # 4. Currency
    r = jarvis_brain.process_message("dolar kaç tl")
    assert r["action_taken"] == "live_currency"

    # 5. Math
    r = jarvis_brain.process_message("hesapla 250 * 4")
    assert r["action_taken"] == "calculate_math"

    # 6. DeepSeek
    r = jarvis_brain.process_message("deepseek ile düşün bu soruyu çöz")
    assert r["action_taken"] == "deepseek_reasoning"

    # 7. Mistral NeMo
    r = jarvis_brain.process_message("mistral ile analiz et")
    assert r["action_taken"] == "nemo_analysis"


# ==========================================
# 7. REST API Endpoints Tests
# ==========================================
def test_api_new_endpoints(client, auth_headers):
    # Unauthenticated access should be blocked
    resp_unauth = client.get("/api/jarvis/protocol_zero/status")
    assert resp_unauth.status_code == 401

    # Authenticated access
    resp = client.get("/api/jarvis/protocol_zero/status", headers=auth_headers)
    assert resp.status_code == 200
    assert "protocol_zero" in resp.json()

    resp = client.post("/api/jarvis/protocol_zero/activate", json={"reason": "API Test"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    resp = client.post("/api/jarvis/protocol_zero/deactivate", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    # Hygiene
    resp = client.post("/api/jarvis/system/hygiene", json={"preview_only": True}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    # Finance
    resp = client.get("/api/jarvis/finance/rates", headers=auth_headers)
    assert resp.status_code == 200
    assert "rates" in resp.json()["result"]

    resp = client.post("/api/jarvis/finance/calc", json={"expression": "500 * 2"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["result"]["result"] == 1000.0

    resp = client.post("/api/jarvis/finance/calc", json={"amount": 50, "from_currency": "USD", "to_currency": "TRY"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["result"]["converted_amount"] > 0
