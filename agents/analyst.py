"""Write a transparent trader-view using an optional OpenAI-compatible LLM."""
from __future__ import annotations

import json
import logging
import os
import requests
from pathlib import Path

log = logging.getLogger(__name__)
DEFAULT_BASE = "https://api.venice.ai/api/v1"
DEFAULT_MODEL = "llama-3.3-70b"

def _voice() -> str:
    path = Path("prompts/voice.txt")
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return "Write concise first-person trading education. Never promise returns or certainty."

def analyze(signal: dict) -> dict:
    base = os.getenv("LLM_BASE", os.getenv("LLM_BASE_URL", DEFAULT_BASE)).strip().rstrip("/")
    key = os.getenv("LLM_API_KEY", "").strip()
    model = os.getenv("LLM_MODEL", DEFAULT_MODEL).strip()
    enabled = os.getenv("LLM_ENABLED", "true" if key else "false").strip().lower() == "true"
    fallback = {
        "view": (
            f"I’m watching {signal['label']} through structure, momentum, and defined risk. "
            f"EMA20 is {'above' if signal['ema20'] > signal['ema50'] else 'below'} EMA50, "
            f"while RSI(14) is {signal['rsi14']:.1f}. My {signal['direction'].lower()} scenario "
            "only stays relevant while the underlying structure holds; the stop is an invalidation level, not a promise."
        ),
        "hook": "Structure first. Risk always.",
        "caveat": "A rule-based screen is not a prediction; price can invalidate this scenario.",
    }
    if not enabled or not key:
        return fallback
    system = _voice().replace("{CHANNEL}", os.getenv("CHANNEL", "Bullseye Theory"))
    system += (
        "\nReturn JSON with keys view, hook, caveat. Use only supplied fields; "
        "do not claim a live news catalyst or guarantee a target."
    )
    payload = {
        "model": model, "temperature": 0.35, "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(signal, ensure_ascii=False)},
        ],
    }
    try:
        response = requests.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload, timeout=40,
        )
        response.raise_for_status()
        result = response.json()["choices"][0]["message"]["content"]
        if isinstance(result, str):
            result = json.loads(result)
        if not isinstance(result, dict) or not result.get("view"):
            raise ValueError("LLM response missing view")
        return {
            "view": str(result["view"]).strip(),
            "hook": str(result.get("hook") or fallback["hook"]).strip(),
            "caveat": str(result.get("caveat") or fallback["caveat"]).strip(),
        }
    except Exception as exc:
        log.warning("LLM analysis failed; using deterministic analyst fallback: %s", exc)
        return fallback
