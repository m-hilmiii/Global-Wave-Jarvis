"""
Global-Wawe / Stark-Core - Safe Math Evaluation, Currency & Financial Intelligence Tool
Imported and adapted from OpenJarvis / JARVIS capabilities catalog.
Features:
1. Safe AST-based mathematical evaluation (Zero eval() vulnerability risk).
2. $0.00 Cost Live FX / Currency Rates (USD/TRY, EUR/TRY, GBP/TRY, etc.) with offline cache.
3. E-commerce & Agency Business Margins, KDV (VAT), and Price Calculator (Lussera & Global Wave).
"""

import ast
import math
import operator
import json
import time
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger("Jarvis.Finance")

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
CACHE_DIR = WORKSPACE_ROOT / ".jarvis_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
RATES_CACHE_FILE = CACHE_DIR / "fx_rates_cache.json"

# Allowed binary operators
_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

# Allowed unary operators
_UNARYOPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

# Allowed math functions
_MATH_FUNCS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "pi": math.pi,
    "e": math.e,
    "ceil": math.ceil,
    "floor": math.floor,
}


def _safe_eval_node(node: ast.AST) -> Any:
    """Recursively evaluates an AST node using whitelisted mathematical operations only."""
    if isinstance(node, ast.Expression):
        return _safe_eval_node(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, complex)):
            return node.value
        raise ValueError(f"Desteklenmeyen sabit türü: {type(node.value).__name__}")
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _BINOPS:
            raise ValueError(f"Desteklenmeyen matematiksel operatör: {op_type.__name__}")
        left = _safe_eval_node(node.left)
        right = _safe_eval_node(node.right)
        return _BINOPS[op_type](left, right)
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _UNARYOPS:
            raise ValueError(f"Desteklenmeyen tekli operatör: {op_type.__name__}")
        operand = _safe_eval_node(node.operand)
        return _UNARYOPS[op_type](operand)
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Yalnızca güvenli matematiksel fonksiyonlar çağrılabilir.")
        fname = node.func.id
        if fname not in _MATH_FUNCS:
            raise ValueError(f"Bilinmeyen veya yetkisiz fonksiyon: {fname}")
        func = _MATH_FUNCS[fname]
        args = [_safe_eval_node(a) for a in node.args]
        return func(*args)
    if isinstance(node, ast.Name):
        name = node.id
        if name in _MATH_FUNCS:
            val = _MATH_FUNCS[name]
            if isinstance(val, (int, float)):
                return val
        raise ValueError(f"Bilinmeyen değişken: {name}")
    raise ValueError(f"Desteklenmeyen ifade türü: {type(node).__name__}")


def safe_math_eval(expression: str) -> float:
    """Evaluates a mathematical expression safely via Python AST."""
    expr = expression.replace("^", "**").strip()
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Sözdizimi hatası: {exc}") from exc
    return float(_safe_eval_node(tree.body))


class FinanceTool:
    def __init__(self):
        self._cached_rates: Optional[Dict[str, float]] = None
        self._last_rates_time: float = 0.0

    def evaluate_math(self, expression: str) -> Dict[str, Any]:
        """Safely evaluates a mathematical expression and returns structured result."""
        try:
            val = safe_math_eval(expression)
            # Format nicely if integer
            fmt = f"{int(val):,}" if val.is_integer() else f"{val:,.4f}".rstrip("0").rstrip(".")
            return {
                "success": True,
                "expression": expression,
                "result": val,
                "formatted": fmt,
                "summary": f"Hesaplama Sonucu: `{expression}` = **{fmt}**"
            }
        except ZeroDivisionError:
            return {"success": False, "error": "Sıfıra bölme hatası (ZeroDivisionError)."}
        except Exception as exc:
            return {"success": False, "error": f"Matematiksel ifade çözülemedi: {exc}"}

    def get_live_rates(self) -> Dict[str, Any]:
        """Fetches live FX rates from open.er-api.com with 10-minute cache and resilient fallback."""
        now = time.time()
        # 1. Memory Cache
        if self._cached_rates and (now - self._last_rates_time < 600):
            return {"success": True, "rates": self._cached_rates, "source": "Bellek Önbelleği"}

        # 2. Disk Cache
        if RATES_CACHE_FILE.exists():
            try:
                with open(RATES_CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if now - data.get("timestamp", 0) < 600:
                        self._cached_rates = data.get("rates", {})
                        self._last_rates_time = data.get("timestamp", now)
                        return {"success": True, "rates": self._cached_rates, "source": "Disk Önbelleği"}
            except Exception:
                pass

        # 3. Live HTTP Request
        try:
            import urllib.request
            req = urllib.request.Request(
                "https://open.er-api.com/v6/latest/USD",
                headers={"User-Agent": "Jarvis-Financial-Engine/3.0"}
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                rates = data.get("rates", {})
                if rates:
                    self._cached_rates = rates
                    self._last_rates_time = now
                    try:
                        with open(RATES_CACHE_FILE, "w", encoding="utf-8") as f:
                            json.dump({"rates": rates, "timestamp": now}, f, indent=2)
                    except Exception:
                        pass
                    return {"success": True, "rates": rates, "source": "Live Open FX API"}
        except Exception as exc:
            logger.debug(f"[Finance] Live FX fetch error: {exc}")

        # 4. Resilient Fallback (Standard baseline rates)
        baseline = {
            "USD": 1.0,
            "TRY": 49.80,
            "EUR": 0.89,
            "GBP": 0.75,
            "CAD": 1.39,
            "AUD": 1.54,
            "JPY": 152.0
        }
        return {"success": True, "rates": baseline, "source": "Yerel Güvenli Tahmin Motoru"}

    def convert_currency(
        self,
        amount: float,
        from_curr: str = "USD",
        to_curr: str = "TRY"
    ) -> Dict[str, Any]:
        """Converts currency amount between from_curr and to_curr."""
        f_curr = from_curr.upper().strip()
        t_curr = to_curr.upper().strip()

        rates_data = self.get_live_rates()
        rates = rates_data.get("rates", {})

        if f_curr not in rates or t_curr not in rates:
            return {"success": False, "error": f"Para birimi desteklenmiyor ({f_curr} -> {t_curr})"}

        # Rates are base USD: amount in USD = amount / rates[f_curr]
        in_usd = amount / rates[f_curr]
        result = in_usd * rates[t_curr]
        unit_rate = rates[t_curr] / rates[f_curr]

        symbols = {"TRY": "₺", "USD": "$", "EUR": "€", "GBP": "£"}
        sym_to = symbols.get(t_curr, t_curr)
        sym_from = symbols.get(f_curr, f_curr)

        summary = (
            f"💱 **Döviz Kuru:** 1 {f_curr} = **{unit_rate:,.2f} {t_curr}**\n"
            f"• **Çeviri:** {sym_from}{amount:,.2f} {f_curr} = **{sym_to}{result:,.2f} {t_curr}**\n"
            f"• *Kaynak:* {rates_data.get('source', 'FX Engine')}"
        )

        return {
            "success": True,
            "amount": amount,
            "from_currency": f_curr,
            "to_currency": t_curr,
            "converted_amount": round(result, 2),
            "unit_rate": round(unit_rate, 4),
            "summary": summary,
            "source": rates_data.get("source")
        }

    def calculate_vat_or_margin(
        self,
        amount: float,
        vat_rate: float = 20.0,
        margin_pct: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculates KDV (VAT) and Profit Margin for Lussera e-commerce and Global Wave agency operations.
        """
        vat_amount = amount * (vat_rate / 100.0)
        total_with_vat = amount + vat_amount
        profit_amount = amount * (margin_pct / 100.0) if margin_pct > 0 else 0.0

        summary = (
            f"📊 **Mali & KDV Analizi (Tutar: {amount:,.2f} ₺):**\n\n"
            f"• **KDV Oranı (%{vat_rate}):** {vat_amount:,.2f} ₺\n"
            f"• **KDV Dahil Toplam:** **{total_with_vat:,.2f} ₺**"
        )
        if margin_pct > 0:
            summary += f"\n• **Kâr Marjı (%{margin_pct}):** +{profit_amount:,.2f} ₺ (Hedef: {total_with_vat + profit_amount:,.2f} ₺)"

        return {
            "success": True,
            "base_amount": amount,
            "vat_rate": vat_rate,
            "vat_amount": round(vat_amount, 2),
            "total_with_vat": round(total_with_vat, 2),
            "margin_pct": margin_pct,
            "profit_amount": round(profit_amount, 2),
            "summary": summary
        }


finance_tool = FinanceTool()
