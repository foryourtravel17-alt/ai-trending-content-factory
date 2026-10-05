"""Optional OpenAI-compatible LLM router for Bullseye Theory.

This is intentionally disabled by default. It uses a provider/model supplied through
environment variables so no API key or provider is hard-coded. If the configured
provider fails, callers can fall back to the deterministic local topic/script path.

Environment:
  LLM_ENABLED=true|false
  LLM_API_KEY=...
  LLM_BASE_URL=https://api.groq.com/openai/v1
  LLM_MODEL=openai/gpt-oss-120b
  LLM_TIMEOUT_SECONDS=45
"""

import json
import os
import urllib.error
import urllib.request


DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "openai/gpt-oss-120b"


def enabled():
    return os.getenv("LLM_ENABLED", "false").strip().lower() == "true"


def generate_json(system_prompt, user_prompt):
    if not enabled():
        return None

    api_key = os.getenv("LLM_API_KEY", "").strip()
    base_url = os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/")
    model = os.getenv("LLM_MODEL", DEFAULT_MODEL).strip()
    timeout = max(10, int(os.getenv("LLM_TIMEOUT_SECONDS", "45")))

    if not api_key:
        raise RuntimeError("LLM_API_KEY is required when LLM_ENABLED=true.")

    payload = {
        "model": model,
        "temperature": 0.35,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:1000]
        raise RuntimeError(f"LLM provider HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"LLM provider unavailable: {exc}") from exc

    try:
        content = body["choices"][0]["message"]["content"]
        result = json.loads(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("LLM provider returned invalid JSON content.") from exc

    if not isinstance(result, dict):
        raise RuntimeError("LLM provider JSON response must be an object.")

    return result
