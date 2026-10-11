"""Idempotent Telegram and Instagram publishing for generated signal cards."""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from urllib.parse import quote

import requests

log = logging.getLogger(__name__)
API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v23.0")
TELEGRAM_CHANNEL = os.getenv("TELEGRAM_CHANNEL", "@bullseye_theory")


def public_image_url(image_path: Path) -> str:
    gh_user = os.getenv("GH_USER", "").strip()
    gh_repo = os.getenv("GH_REPO", "").strip()
    custom_base = os.getenv("IMAGE_BASE_URL", "").strip().rstrip("/")
    if custom_base:
        return f"{custom_base}/{quote(image_path.name)}"
    if gh_user and gh_repo:
        return f"https://{gh_user}.github.io/{gh_repo}/output/{quote(image_path.name)}"
    repository = os.getenv("GITHUB_REPOSITORY", "").strip()
    if repository:
        return f"https://raw.githubusercontent.com/{repository}/main/output/{quote(image_path.name)}"
    raise RuntimeError("Set GH_USER and GH_REPO, or IMAGE_BASE_URL, to create a public image URL.")


def _accessible_image_url(image_path: Path) -> str:
    """Prefer GitHub Pages; fall back to raw GitHub if Pages is not deployed yet."""
    gh_user = os.getenv("GH_USER", "").strip()
    gh_repo = os.getenv("GH_REPO", "").strip()
    custom_base = os.getenv("IMAGE_BASE_URL", "").strip().rstrip("/")
    candidates = []
    if custom_base:
        candidates.append(f"{custom_base}/{quote(image_path.name)}")
    if gh_user and gh_repo:
        candidates.append(f"https://{gh_user}.github.io/{gh_repo}/output/{quote(image_path.name)}")
    repository = os.getenv("GITHUB_REPOSITORY", "").strip()
    if repository:
        candidates.append(f"https://raw.githubusercontent.com/{repository}/main/output/{quote(image_path.name)}")
    if not candidates:
        raise RuntimeError("Set GH_USER and GH_REPO, or IMAGE_BASE_URL, to create a public image URL.")
    for candidate in candidates:
        try:
            response = requests.head(candidate, allow_redirects=True, timeout=12)
            if response.status_code == 200:
                log.info("Public image URL verified: %s", candidate)
                return candidate
            log.warning("Image URL not ready (%s): %s", response.status_code, candidate)
        except requests.RequestException as exc:
            log.warning("Could not verify image URL %s: %s", candidate, exc)
    raise RuntimeError("Generated card is not publicly reachable. Enable GitHub Pages or check the raw GitHub URL.")


def _telegram(method: str, data: dict) -> dict:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured.")
    response = requests.post(f"https://api.telegram.org/bot{token}/{method}", data=data, timeout=45)
    response.raise_for_status()
    body = response.json()
    if not body.get("ok"):
        raise RuntimeError(f"Telegram {method} failed: {body.get('description', 'unknown error')}")
    return body["result"]


def _instagram_publish(image_url: str, caption: str) -> str:
    token = os.getenv("IG_ACCESS_TOKEN", os.getenv("META_SYSTEM_USER_TOKEN", "")).strip()
    user_id = os.getenv("IG_USER_ID", os.getenv("INSTAGRAM_USER_ID", "")).strip()
    if not token or not user_id:
        raise RuntimeError("Instagram credentials missing (IG_ACCESS_TOKEN and IG_USER_ID).")
    api = f"https://graph.facebook.com/{API_VERSION}/{user_id}"
    response = requests.post(f"{api}/media", data={
        "image_url": image_url, "caption": caption[:2200], "access_token": token,
    }, timeout=60)
    response.raise_for_status()
    creation_id = response.json().get("id")
    if not creation_id:
        raise RuntimeError(f"Instagram media container response had no id: {response.text[:400]}")
    for _ in range(6):
        status = requests.get(f"https://graph.facebook.com/{API_VERSION}/{creation_id}", params={
            "fields": "status_code", "access_token": token,
        }, timeout=30)
        if status.ok:
            code = status.json().get("status_code")
            if code == "ERROR":
                raise RuntimeError("Instagram image container entered ERROR status.")
            if code in (None, "FINISHED"):
                break
        time.sleep(5)
    response = requests.post(f"{api}/media_publish", data={
        "creation_id": creation_id, "access_token": token,
    }, timeout=60)
    response.raise_for_status()
    media_id = response.json().get("id")
    if not media_id:
        raise RuntimeError(f"Instagram publish response had no media id: {response.text[:400]}")
    return str(media_id)


def publish(signal: dict, copy: dict, card_path: Path, record: dict, dry_run: bool = False) -> dict:
    """Publish one signal; persist each platform result into record before returning."""
    record.setdefault("publishing", {})
    platforms = record["publishing"]
    if dry_run:
        log.info("DRY_RUN: not posting %s to Telegram or Instagram.", signal["signal_id"])
        record["status"] = "generated"
        record["last_run_mode"] = "dry_run"
        return record

    human_approval = os.getenv("HUMAN_APPROVAL", "false").strip().lower() == "true"
    image_url = _accessible_image_url(card_path)
    telegram_caption = copy["telegram_html"][:1000]
    if human_approval:
        if platforms.get("telegram_dm", {}).get("status") != "sent":
            chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
            if not chat_id:
                raise RuntimeError("HUMAN_APPROVAL=true requires TELEGRAM_CHAT_ID for draft delivery.")
            keyboard = {"inline_keyboard": [[
                {"text": "✅ APPROVE & PUBLISH", "callback_data": f"market_approve:{signal['signal_id']}"},
                {"text": "❌ REJECT", "callback_data": f"market_reject:{signal['signal_id']}"},
            ]]}
            result = _telegram("sendPhoto", {
                "chat_id": chat_id, "photo": image_url,
                "caption": ("📝 DRAFT — choose approve or reject\n\n" + telegram_caption)[:1024],
                "parse_mode": "HTML",
                "reply_markup": json.dumps(keyboard, separators=(",", ":")),
            })
            platforms["telegram_dm"] = {"status": "sent", "message_id": result.get("message_id")}
            log.info("Draft sent to Telegram DM for %s; waiting for button approval.", signal["signal_id"])
        record["status"] = "pending_approval"
        record["image_url"] = image_url
        return record

    if platforms.get("telegram", {}).get("status") != "published":
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        if token:
            result = _telegram("sendPhoto", {
                "chat_id": TELEGRAM_CHANNEL, "photo": image_url,
                "caption": telegram_caption,
                "parse_mode": "HTML",
            })
            platforms["telegram"] = {"status": "published", "message_id": result.get("message_id")}
            log.info("Telegram published %s (message %s).", signal["signal_id"], result.get("message_id"))
        else:
            log.warning("Telegram skipped: TELEGRAM_BOT_TOKEN is not configured.")
    if platforms.get("instagram", {}).get("status") != "published":
        token = os.getenv("IG_ACCESS_TOKEN", os.getenv("META_SYSTEM_USER_TOKEN", "")).strip()
        user_id = os.getenv("IG_USER_ID", os.getenv("INSTAGRAM_USER_ID", "")).strip()
        if token and user_id:
            media_id = _instagram_publish(image_url, copy["instagram_caption"])
            platforms["instagram"] = {"status": "published", "media_id": media_id}
            log.info("Instagram published %s (media %s).", signal["signal_id"], media_id)
        else:
            log.warning("Instagram skipped: IG_ACCESS_TOKEN/IG_USER_ID are not configured.")
    statuses = [platforms.get(k, {}).get("status") for k in ("telegram", "instagram")]
    if all(status == "published" for status in statuses):
        record["status"] = "published"
    elif "published" in statuses:
        record["status"] = "partial"
    else:
        record["status"] = "generated"
    record["image_url"] = image_url
    return record
