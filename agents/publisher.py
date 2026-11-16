"""Approval-gated Telegram-only publishing for Bullseye Theory market cards."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import requests

log = logging.getLogger(__name__)
TELEGRAM_CHANNEL = os.getenv("TELEGRAM_CHANNEL", "@bullseye_theory").strip() or "@bullseye_theory"


class TelegramDeliveryRejected(RuntimeError):
    """Telegram explicitly rejected delivery; an intentional retry may be safe."""


class TelegramDeliveryUnknown(RuntimeError):
    """Telegram delivery result is ambiguous; automatic resend is blocked."""


def _telegram(method: str, data: dict, files: dict | None = None) -> dict:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured.")
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/{method}",
            data=data, files=files, timeout=60,
        )
    except requests.RequestException as exc:
        raise TelegramDeliveryUnknown(
            f"Telegram {method} outcome is unknown ({type(exc).__name__}); automatic resend is blocked."
        ) from None
    if not response.ok:
        raise TelegramDeliveryRejected(
            f"Telegram {method} rejected with HTTP {response.status_code}; response redacted."
        )
    try:
        body = response.json()
    except ValueError:
        raise TelegramDeliveryUnknown(
            f"Telegram {method} returned invalid JSON; automatic resend is blocked."
        ) from None
    if not body.get("ok") or not isinstance(body.get("result"), dict):
        raise TelegramDeliveryRejected(f"Telegram {method} failed; response redacted.")
    return body["result"]


def publish(signal: dict, copy: dict, card_path: Path, record: dict, dry_run: bool = False) -> dict:
    """Send a card for private owner approval, then publish only after approval."""
    platforms = record.setdefault("publishing", {})
    if dry_run:
        log.info("DRY_RUN: not sending %s to Telegram.", signal["signal_id"])
        record["status"] = "generated"
        record["last_run_mode"] = "dry_run"
        return record

    approval_status = str(record.get("approval_status", "")).strip().lower()
    if approval_status == "rejected":
        record["status"] = "rejected"
        log.info("Rejected record %s is blocked from Telegram publishing.", signal["signal_id"])
        return record

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required for Telegram-only publishing.")
    caption = str(copy.get("telegram_html", ""))[:1000]

    # Every market card requires an explicit Telegram owner decision.
    if approval_status != "approved":
        dm_state = platforms.setdefault("telegram_dm", {})
        dm_status = str(dm_state.get("status", "")).lower()
        if dm_status == "sent":
            record["status"] = "pending_approval"
            return record
        if dm_status in {"sending", "unknown"}:
            raise TelegramDeliveryUnknown("Telegram approval request outcome is ambiguous; duplicate DM blocked.")
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        if not chat_id:
            raise RuntimeError("TELEGRAM_CHAT_ID is required for private market-card approval.")
        signal_id = str(signal.get("signal_id", "")).strip()
        keyboard = {"inline_keyboard": [[
            {"text": "✅ APPROVE & PUBLISH", "callback_data": f"market_approve:{signal_id}"},
            {"text": "❌ REJECT", "callback_data": f"market_reject:{signal_id}"},
        ]]}
        dm_state["status"] = "sending"
        try:
            with Path(card_path).open("rb") as photo:
                result = _telegram("sendPhoto", {
                    "chat_id": chat_id,
                    "caption": ("📝 DRAFT — review and choose approve or reject\n\n" + caption)[:1024],
                    "parse_mode": "HTML",
                    "reply_markup": json.dumps(keyboard, separators=(",", ":")),
                }, files={"photo": photo})
        except TelegramDeliveryUnknown:
            dm_state["status"] = "unknown"
            raise
        except TelegramDeliveryRejected as exc:
            dm_state.update({"status": "failed", "error_type": type(exc).__name__})
            raise
        dm_state.update({"status": "sent", "message_id": result.get("message_id")})
        record["status"] = "pending_approval"
        log.info("Market draft %s sent to private Telegram for explicit owner approval.", signal_id)
        return record

    channel_state = platforms.setdefault("telegram", {})
    channel_status = str(channel_state.get("status", "")).lower()
    if channel_status == "published":
        record["status"] = "published"
        log.info("Telegram already published %s; duplicate skipped.", signal["signal_id"])
        return record
    if channel_status in {"sending", "unknown"}:
        raise TelegramDeliveryUnknown("Telegram channel outcome is ambiguous; automatic resend is blocked.")

    channel_state["status"] = "sending"
    try:
        with Path(card_path).open("rb") as photo:
            result = _telegram("sendPhoto", {
                "chat_id": TELEGRAM_CHANNEL,
                "caption": caption,
                "parse_mode": "HTML",
            }, files={"photo": photo})
    except TelegramDeliveryUnknown as exc:
        channel_state.update({"status": "unknown", "error_type": type(exc).__name__})
        record["status"] = "publish_failed"
        raise
    except TelegramDeliveryRejected as exc:
        channel_state.update({"status": "failed", "error_type": type(exc).__name__})
        record["status"] = "publish_failed"
        raise
    channel_state.update({
        "status": "published",
        "message_id": result.get("message_id"),
    })
    record["status"] = "published"
    record["published_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    log.info("Telegram channel published %s (message %s).", signal["signal_id"], result.get("message_id"))
    return record
