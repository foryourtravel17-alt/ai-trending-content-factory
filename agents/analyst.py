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
    if signal.get("region") == "INDIA":
        fallback = {
            "view": (
                f"Main {signal['label']} par {signal['direction'].lower()} scenario dekh raha hoon. "
                f"EMA20 EMA50 ke {'upar' if signal['ema20'] > signal['ema50'] else 'neeche'} hai; "
                f"RSI(14) {signal['rsi14']:.1f} hai. Structure hold nahi hua toh setup invalid ho sakta hai."
            ),
            "hook": "Structure first. Risk always.",
            "caveat": "Setup fail ho sakta hai; levels guarantee nahi hain. Yeh education hai, financial advice nahi.",
        }
    else:
        fallback = {
            "view": (
                f"I’m watching {signal['label']} through structure, momentum, and defined risk. "
                f"EMA20 is {'above' if signal['ema20'] > signal['ema50'] else 'below'} EMA50, "
                f"while RSI(14) is {signal['rsi14']:.1f}. The scenario is invalid if structure fails."
            ),
            "hook": "Structure first. Risk always.",
            "caveat": "This rule-based screen is not a prediction; price can invalidate the scenario.",
        }
    if not enabled or not key:
        return fallback
    system = _voice().replace("{CHANNEL}", os.getenv("CHANNEL", "Bullseye Theory"))
    system += (
        "\nReturn JSON with keys view, hook, caveat. Use only supplied fields; "
        "do not claim a live news catalyst or guarantee a target. "
        "For signal.language='Hinglish', write view and caveat in natural Roman-script Hinglish "
        "mixed with common English trading terms. For English, write natural English. "
        "The hook must be a short simple English line understood by both Indian and global audiences."
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
            "view": str(result["view"]).strip()[:260],
            "hook": str(result.get("hook") or fallback["hook"]).strip()[:100],
            "caveat": str(result.get("caveat") or fallback["caveat"]).strip()[:130],
        }
    except Exception as exc:
        log.warning("LLM analysis failed; using deterministic analyst fallback (%s).", type(exc).__name__)
        return fallback
