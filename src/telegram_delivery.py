"""Conservative Telegram delivery helpers for approval-message sends."""
from __future__ import annotations

import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Callable


class TelegramDeliveryRejected(RuntimeError):
    """Telegram returned an explicit API rejection; no message was accepted."""


class TelegramDeliveryUnknown(RuntimeError):
    """A send may have reached Telegram; never resend automatically."""


def _safe_description(raw: bytes, token: str) -> str:
    try:
        payload = json.loads(raw.decode("utf-8", errors="replace"))
        description = " ".join(str(payload.get("description") or "").split())
    except (ValueError, TypeError, AttributeError):
        description = ""
    if token:
        description = description.replace(token, "[REDACTED]")
    return description[:180]


def api_request(
    method: str,
    params: dict,
    *,
    base_url: str,
    timeout: int = 30,
) -> dict:
    """Call Telegram and classify all transport failures as ambiguous delivery."""
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/{method}",
        data=urllib.parse.urlencode(params).encode("utf-8"),
        method="POST",
    )
    token = base_url.rsplit("/bot", 1)[-1]
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        description = _safe_description(raw, token)
        suffix = f": {description}" if description else ""
        if exc.code >= 500:
            raise TelegramDeliveryUnknown(
                f"Telegram {method} returned HTTP {exc.code}; automatic resend is blocked."
            ) from None
        raise TelegramDeliveryRejected(
            f"Telegram {method} rejected with HTTP {exc.code}{suffix}."
        ) from None
    except (TimeoutError, socket.timeout, urllib.error.URLError, OSError) as exc:
        raise TelegramDeliveryUnknown(
            f"Telegram {method} transport outcome is unknown ({type(exc).__name__}); automatic resend is blocked."
        ) from None

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise TelegramDeliveryUnknown(
            f"Telegram {method} response could not be verified; automatic resend is blocked."
        ) from None
    if not isinstance(payload, dict):
        raise TelegramDeliveryUnknown(
            f"Telegram {method} response shape could not be verified; automatic resend is blocked."
        )
    if payload.get("ok") is not True or not isinstance(payload.get("result"), dict):
        description = _safe_description(raw, token)
        suffix = f": {description}" if description else ""
        raise TelegramDeliveryRejected(f"Telegram {method} API rejected the request{suffix}.")
    return payload["result"]


def send_once(
    record: dict,
    send: Callable[[], dict],
    persist: Callable[[], None],
) -> dict | None:
    """Persist a sending marker before the request and an unknown marker on timeout.

    Returns the Telegram result when a send completes. Returns None when a prior
    sent/sending/unknown state requires manual reconciliation instead of a resend.
    """
    publishing = record.setdefault("publishing", {})
    if not isinstance(publishing, dict):
        raise ValueError("publishing state must be an object")
    dm = publishing.setdefault("telegram_dm", {})
    if not isinstance(dm, dict):
        raise ValueError("telegram_dm state must be an object")
    status = str(dm.get("status", "")).strip().lower()
    if status in {"sent", "sending", "unknown"}:
        return None

    dm.clear()
    dm.update({
        "status": "sending",
        "started_at": datetime.now(timezone.utc).isoformat(),
    })
    persist()

    try:
        result = send()
    except TelegramDeliveryUnknown as exc:
        dm.update({"status": "unknown", "error_type": type(exc).__name__})
        persist()
        raise
    except TelegramDeliveryRejected as exc:
        dm.update({"status": "failed", "error_type": type(exc).__name__})
        persist()
        raise

    message_id = result.get("message_id") if isinstance(result, dict) else None
    if message_id is None:
        dm.update({"status": "unknown", "error_type": "MissingMessageId"})
        persist()
        raise TelegramDeliveryUnknown(
            "Telegram send response did not contain a message_id; automatic resend is blocked."
        )

    dm.update({
        "status": "sent",
        "message_id": message_id,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    })
    persist()
    return {"message_id": message_id}
