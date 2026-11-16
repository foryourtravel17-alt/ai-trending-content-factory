#!/usr/bin/env python3
"""Telegram-only publisher for human-approved Bullseye Theory educational Reels."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

TELEGRAM_CHANNEL = os.getenv("TELEGRAM_CHANNEL", "@bullseye_theory").strip() or "@bullseye_theory"
MAX_CONTENT_AGE = timedelta(hours=48)
DAILY_PUBLISH_LIMIT = 3
LOCAL_TZ = ZoneInfo("Asia/Kolkata")
OUTPUT_DIR = Path("output")


class TelegramPublishRejected(RuntimeError):
    """Telegram explicitly rejected the request; a deliberate retry can be considered."""


class TelegramPublishUnknown(RuntimeError):
    """Delivery outcome is ambiguous; do not resend automatically."""


def load_json(path: Path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return default


def save_state(content_path: Path, approved: dict) -> None:
    path = Path(content_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(approved, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)


def parse_timestamp(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def content_record_paths():
    paths = set()
    for pattern in ("content_*.json", "draft_*.json"):
        paths.update(OUTPUT_DIR.glob(pattern))
    return sorted(paths, key=lambda path: path.name)


def telegram_published(record: dict) -> bool:
    publishing = record.get("publishing", {}) if isinstance(record.get("publishing"), dict) else {}
    telegram = publishing.get("telegram", {}) if isinstance(publishing.get("telegram"), dict) else {}
    return str(telegram.get("status", "")).lower() == "published"


def published_today_count() -> int:
    today_local = datetime.now(LOCAL_TZ).date()
    count = 0
    for path in content_record_paths():
        data = load_json(path, {})
        if not isinstance(data, dict) or not telegram_published(data):
            continue
        telegram = (data.get("publishing") or {}).get("telegram") or {}
        published_at = parse_timestamp(telegram.get("published_at") or data.get("published_at"))
        if published_at and published_at.astimezone(LOCAL_TZ).date() == today_local:
            count += 1
    return count


def load_newest_unpublished_approved():
    today_count = published_today_count()
    now = datetime.now(timezone.utc)
    candidates = []
    for path in content_record_paths():
        data = load_json(path, None)
        if not isinstance(data, dict):
            continue
        content_id = str(data.get("content_id", "")).strip()
        if not content_id or path.stem != content_id:
            print(f"Skipping content ID / filename mismatch: {path.name}")
            continue
        if data.get("status") not in {"approved_for_publishing", "published_to_instagram", "publish_failed", "partial"}:
            continue
        publishing = data.get("publishing", {}) if isinstance(data.get("publishing"), dict) else {}
        telegram = publishing.get("telegram", {}) if isinstance(publishing.get("telegram"), dict) else {}
        telegram_status = str(telegram.get("status", "")).strip().lower()
        if telegram_status == "published":
            continue
        if telegram_status in {"sending", "unknown"}:
            print(f"Skipping ambiguous Telegram delivery; manual reconciliation required: {path.name}")
            continue

        approval = data.get("approval", {}) if isinstance(data.get("approval"), dict) else {}
        fact = data.get("fact_check", {}) if isinstance(data.get("fact_check"), dict) else {}
        if not (
            approval.get("required") is True
            and approval.get("status") == "approved"
            and approval.get("mode") == "human_review"
            and approval.get("reviewed_at")
            and approval.get("reviewed_by")
            and fact.get("status") == "approved"
        ):
            print(f"Skipping Reel without explicit Telegram owner approval: {path.name}")
            continue

        created_at = parse_timestamp(data.get("created_at"))
        if not created_at:
            print(f"Skipping Reel with missing/invalid created_at: {path.name}")
            continue
        age = now - created_at
        if age < timedelta(0) or age > MAX_CONTENT_AGE:
            print(f"Skipping stale/future-dated Reel ({age} old): {path.name}")
            continue

        video_url = str(data.get("video_url", "")).strip()
        video_path = OUTPUT_DIR / "media" / f"{content_id}.mp4"
        if video_url:
            if data.get("video_content_id") != content_id or not video_url.endswith(f"/{content_id}.mp4"):
                print(f"Skipping Reel with mismatched public video URL/content ID: {path.name}")
                continue
        elif not video_path.is_file():
            print(f"Skipping approved Reel without a verified public video URL or local MP4: {path.name}")
            continue
        candidates.append((created_at, content_id, path, data))

    if not candidates:
        if today_count >= DAILY_PUBLISH_LIMIT:
            print(f"Daily Telegram Reel cap reached: {today_count}/{DAILY_PUBLISH_LIMIT} in Asia/Kolkata.")
        else:
            print("No fresh, human-approved, unpublished educational Reel is eligible.")
        return None, None
    candidates.sort(key=lambda item: (-item[0].timestamp(), item[1]))
    if today_count >= DAILY_PUBLISH_LIMIT:
        print(f"Daily Telegram Reel cap reached: {today_count}/{DAILY_PUBLISH_LIMIT} in Asia/Kolkata.")
        return None, None
    _, _, path, data = candidates[0]
    return path, data


def sha256_and_size(path: Path):
    digest = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def probe_duration(path: Path) -> float:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, check=True, timeout=30,
        )
        duration = float(result.stdout.strip())
    except Exception as exc:
        raise RuntimeError(f"Could not validate Reel duration with ffprobe ({type(exc).__name__}).") from None
    if duration <= 0:
        raise RuntimeError("ffprobe reported a non-positive Reel duration.")
    return duration


def expected_public_video_url(content_id: str) -> str:
    safe = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
    if not content_id or any(char not in safe for char in content_id):
        raise RuntimeError("Missing or unsafe content_id for public Reel URL.")
    base = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    if not base:
        raise RuntimeError("SUPABASE_URL is required for the approved Telegram Reel media URL.")
    return f"{base}/storage/v1/object/public/REELS/reels/{urllib.parse.quote(content_id, safe='')}.mp4"


def verify_public_video_url(video_url: str, approved: dict) -> str:
    content_id = str(approved.get("content_id", "")).strip()
    if video_url != expected_public_video_url(content_id) or approved.get("video_content_id") != content_id:
        raise RuntimeError("Public Reel URL/content_id mismatch; Telegram publishing blocked.")
    expected_sha = str(approved.get("video_sha256", "")).strip().lower()
    try:
        expected_size = int(approved.get("video_size_bytes", 0))
        expected_duration = float(approved.get("video_duration_seconds", 0))
    except (TypeError, ValueError):
        raise RuntimeError("Approved Reel is missing valid size/duration metadata.") from None
    if len(expected_sha) != 64 or expected_size <= 0 or expected_duration <= 0:
        raise RuntimeError("Approved Reel is missing required SHA-256, byte size, or duration metadata.")

    temp_name = None
    digest = hashlib.sha256()
    actual_size = 0
    try:
        with urllib.request.urlopen(urllib.request.Request(video_url, method="GET"), timeout=180) as response:
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp:
                temp_name = temp.name
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    digest.update(chunk)
                    actual_size += len(chunk)
                    temp.write(chunk)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Supabase public Reel URL returned HTTP {exc.code}; Telegram publish blocked.") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not retrieve approved Reel ({type(exc).__name__}); Telegram publish blocked.") from None

    try:
        if actual_size != expected_size or digest.hexdigest() != expected_sha:
            raise RuntimeError("Public Reel bytes do not match approved SHA-256/size; Telegram publish blocked.")
        actual_duration = probe_duration(Path(temp_name))
        if abs(actual_duration - expected_duration) > 0.75:
            raise RuntimeError("Public Reel duration does not match approved media metadata; Telegram publish blocked.")
    finally:
        if temp_name:
            Path(temp_name).unlink(missing_ok=True)
    print(f"Verified exact public Reel for {content_id}: {actual_size} bytes; SHA-256 and duration matched.")
    return video_url


def _upload_local_video_to_supabase(video_path: Path, approved: dict) -> str:
    base = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not base or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for durable Telegram Reel media.")
    content_id = str(approved.get("content_id", "")).strip()
    digest, size = sha256_and_size(video_path)
    duration = probe_duration(video_path)
    object_path = f"reels/{content_id}.mp4"
    upload_url = f"{base}/storage/v1/object/REELS/{urllib.parse.quote(object_path, safe='/')}"
    request_obj = urllib.request.Request(
        upload_url, data=Path(video_path).read_bytes(), method="PUT",
        headers={"Authorization": f"Bearer {key}", "apikey": key,
                 "Content-Type": "video/mp4", "x-upsert": "false"},
    )
    try:
        with urllib.request.urlopen(request_obj, timeout=180) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        if exc.code != 409:
            raise RuntimeError(f"Supabase Reel upload failed HTTP {exc.code}; response redacted.") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Supabase Reel upload failed ({type(exc).__name__}); credentials redacted.") from None
    url = expected_public_video_url(content_id)
    approved.update({
        "video_url": url, "video_content_id": content_id,
        "video_sha256": digest, "video_size_bytes": size, "video_duration_seconds": duration,
    })
    verify_public_video_url(url, approved)
    return url


def _send_telegram_video(token: str, video_url: str, caption: str) -> int:
    endpoint = f"https://api.telegram.org/bot{token}/sendVideo"
    payload = urllib.parse.urlencode({
        "chat_id": TELEGRAM_CHANNEL, "video": video_url, "caption": caption[:1024],
    }).encode()
    request_obj = urllib.request.Request(endpoint, data=payload, method="POST")
    try:
        with urllib.request.urlopen(request_obj, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise TelegramPublishRejected(f"Telegram sendVideo rejected with HTTP {exc.code}; response redacted.") from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise TelegramPublishUnknown(f"Telegram sendVideo outcome unknown ({type(exc).__name__}); automatic resend blocked.") from None
    if not isinstance(result, dict) or not result.get("ok"):
        raise TelegramPublishRejected("Telegram rejected sendVideo; response redacted.")
    message_id = (result.get("result") or {}).get("message_id")
    if not message_id:
        raise TelegramPublishUnknown("Telegram returned no message ID; automatic resend blocked.")
    return int(message_id)


def publish_content_record(content_path: Path, approved: dict) -> dict:
    content_id = str(approved.get("content_id", "")).strip()
    if not content_id or Path(content_path).stem != content_id:
        raise RuntimeError("Publishing metadata filename/content_id mismatch.")
    approval = approved.get("approval", {}) if isinstance(approved.get("approval"), dict) else {}
    fact = approved.get("fact_check", {}) if isinstance(approved.get("fact_check"), dict) else {}
    if not (
        approved.get("status") in {"approved_for_publishing", "publish_failed", "published_to_instagram", "partial"}
        and approval.get("required") is True
        and approval.get("status") == "approved"
        and approval.get("mode") == "human_review"
        and approval.get("reviewed_at")
        and approval.get("reviewed_by")
        and fact.get("status") == "approved"
    ):
        raise RuntimeError("Telegram publishing blocked: explicit owner approval and fact-check are required.")

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required for approved Telegram Reels.")
    video_url = str(approved.get("video_url", "")).strip()
    if video_url:
        video_url = verify_public_video_url(video_url, approved)
    else:
        video_path = OUTPUT_DIR / "media" / f"{content_id}.mp4"
        if not video_path.is_file() or video_path.stat().st_size <= 0:
            raise RuntimeError("Approved Reel has no valid local MP4 or verified public video URL.")
        video_url = _upload_local_video_to_supabase(video_path, approved)
        save_state(content_path, approved)

    social = approved.get("social", {}) if isinstance(approved.get("social"), dict) else {}
    caption = str(social.get("caption", approved.get("caption", "")))
    hashtags = social.get("hashtags", approved.get("hashtags", []))
    if isinstance(hashtags, list):
        caption = (caption + "\n\n" + " ".join(str(tag) for tag in hashtags)).strip()
    caption = (caption + "\n\n🎯 Bullseye Theory\nLearn | Trade | Grow").strip()

    publishing = approved.setdefault("publishing", {})
    telegram = publishing.setdefault("telegram", {})
    telegram_status = str(telegram.get("status", "")).lower()
    if telegram_status == "published":
        print(f"Telegram channel already published for {content_id}; duplicate skipped.")
        approved["status"] = "published"
        return approved
    if telegram_status in {"sending", "unknown"}:
        raise TelegramPublishUnknown(f"Telegram outcome for {content_id} is ambiguous; automatic resend blocked.")

    telegram["status"] = "sending"
    telegram["attempt_started_at"] = datetime.now(timezone.utc).isoformat()
    save_state(content_path, approved)
    try:
        message_id = _send_telegram_video(token, video_url, caption)
    except TelegramPublishUnknown as exc:
        telegram.update({"status": "unknown", "error_type": type(exc).__name__})
        save_state(content_path, approved)
        raise
    except TelegramPublishRejected as exc:
        telegram.update({"status": "failed", "error_type": type(exc).__name__})
        save_state(content_path, approved)
        raise
    telegram.update({
        "status": "published",
        "message_id": message_id,
        "published_at": datetime.now(timezone.utc).isoformat(),
    })
    telegram.pop("error_type", None)
    approved["published_at"] = telegram["published_at"]
    approved["status"] = "published"
    save_state(content_path, approved)
    print(f"Telegram channel post recorded for {content_id}; message ID saved.")
    return approved


def publish_approved_educational_reel(record: dict) -> dict:
    content_id = str(record.get("content_id", "")).strip()
    if not content_id or record.get("content_type") != "educational_reel":
        raise RuntimeError("Expected a valid educational Reel record.")
    if record.get("approval_status") != "approved":
        raise RuntimeError("Telegram publishing blocked: shared state has no approved owner decision.")
    if record.get("human_approval_required") is not True:
        raise RuntimeError("Telegram publishing blocked: only owner-approved Reels are eligible.")
    if record.get("fact_check", {}).get("status") != "approved":
        raise RuntimeError("Telegram publishing blocked: owner fact-check status is not approved.")
    metadata_path = OUTPUT_DIR / f"{content_id}.json"
    metadata = load_json(metadata_path, None)
    if not isinstance(metadata, dict) or metadata.get("content_id") != content_id:
        raise RuntimeError("Matching Reel metadata is missing or mismatched.")
    created_at = parse_timestamp(metadata.get("created_at"))
    if not created_at:
        raise RuntimeError("Approved Reel created_at is missing or invalid.")
    if datetime.now(timezone.utc) - created_at > MAX_CONTENT_AGE and not telegram_published(metadata):
        record["status"] = "expired"
        record["expired_at"] = datetime.now(timezone.utc).isoformat()
        return record
    try:
        publish_content_record(metadata_path, metadata)
    finally:
        record["publishing"] = metadata.get("publishing", {})
        record["published_at"] = metadata.get("published_at") or record.get("published_at")
        if telegram_published(metadata):
            record["status"] = "published"
        elif record.get("approval_status") == "approved":
            record["status"] = "publish_failed"
    return record


def main():
    content_path, approved = load_newest_unpublished_approved()
    if not approved:
        print("No unpublished owner-approved Reel. Nothing to publish.")
        return
    publish_content_record(content_path, approved)


if __name__ == "__main__":
    main()
