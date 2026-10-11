"""Idempotent Telegram and Instagram publishing for generated signal cards."""
from __future__ import annotations

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
    # IMAGE containers normally become available quickly; poll briefly for status if exposed.
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
        record["status"] = "dry_run"
        return record

    human_approval = os.getenv("HUMAN_APPROVAL", "false").strip().lower() == "true"
    image_url = public_image_url(card_path)
    # Telegram HTML caption has a 1024-character limit for media captions.
    telegram_caption = copy["telegram_html"][:1000]
    if human_approval:
        if platforms.get("telegram_dm", {}).get("status") != "sent":
            chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
            if not chat_id:
                raise RuntimeError("HUMAN_APPROVAL=true requires TELEGRAM_CHAT_ID for draft delivery.")
            result = _telegram("sendPhoto", {
                "chat_id": chat_id, "photo": image_url,
                "caption": ("📝 DRAFT — approval mode is ON\n\n" + telegram_caption)[:1024],
                "parse_mode": "HTML",
            })
            platforms["telegram_dm"] = {"status": "sent", "message_id": result.get("message_id")}
            log.info("Draft sent to Telegram DM for %s; public publishing withheld.", signal["signal_id"])
        record["status"] = "pending_approval"
        return record

    # A successful platform is never sent again if another platform fails.
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
        if os.getenv("IG_ACCESS_TOKEN", os.getenv("META_SYSTEM_USER_TOKEN", "")).strip() and os.getenv("IG_USER_ID", os.getenv("INSTAGRAM_USER_ID", "")).strip():
            media_id = _instagram_publish(image_url, copy["instagram_caption"])
            platforms["instagram"] = {"status": "published", "media_id": media_id}
            log.info("Instagram published %s (media %s).", signal["signal_id"], media_id)
        else:
            log.warning("Instagram skipped: IG_ACCESS_TOKEN/IG_USER_ID are not configured.")
    statuses = [v.get("status") for k, v in platforms.items() if k in {"telegram", "instagram"}]
    record["status"] = "published" if "published" in statuses else "generated"
    record["image_url"] = image_url
    return record
