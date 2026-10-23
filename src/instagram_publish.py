import hashlib
import json
import os
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

API_VERSION = os.environ.get("META_GRAPH_API_VERSION", "v23.0")
SYSTEM_USER_TOKEN = os.environ.get("META_SYSTEM_USER_TOKEN", "").strip()
TOKEN = SYSTEM_USER_TOKEN
CONFIGURED_INSTAGRAM_USER_ID = os.environ.get("INSTAGRAM_USER_ID", "").strip()

API = f"https://graph.facebook.com/{API_VERSION}"
TELEGRAM_CHANNEL = "@bullseye_theory"


def request(method, url, params):
    encoded = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=encoded if method == "POST" else None, method=method)
    if method == "GET":
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        if e.code == 400 and '"code":190' in body:
            raise RuntimeError(
                "META_ACCESS_TOKEN_INVALID: Meta rejected the current System User credential "
                "(OAuth error 190). No Reel was published. Check META_SYSTEM_USER_TOKEN "
                "and the Bullseye Theory Page/Instagram asset assignment."
            ) from None
        raise RuntimeError(f"Meta API HTTP {e.code}; response redacted to protect credentials.") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Meta API request failed ({type(exc).__name__}); credentials redacted.") from None


def resolve_instagram_user_id():
    global TOKEN
    if not SYSTEM_USER_TOKEN:
        raise RuntimeError(
            "META_SYSTEM_USER_TOKEN_NOT_CONFIGURED: Add META_SYSTEM_USER_TOKEN to GitHub Actions."
        )

    pages = request("GET", f"{API}/me/accounts", {
        "fields": "id,name,access_token,tasks,instagram_business_account{id,username}",
        "access_token": SYSTEM_USER_TOKEN,
    })
    rows = pages.get("data") or []
    eligible = [p for p in rows if (p.get("instagram_business_account") or {}).get("id")]
    eligible.sort(
        key=lambda p: 0
        if str(p.get("name", "")).strip().lower() == "bullseye theory"
        else 1
    )
    selected = eligible[0] if eligible else None
    if not selected:
        raise RuntimeError(
            "META_PAGE_NOT_ASSIGNED: Meta System User has no assigned Page with a linked Instagram professional account."
        )

    page_id = str(selected.get("id") or "")
    page_name = str(selected.get("name") or "")
    page_token = str(selected.get("access_token") or "")
    ig = selected.get("instagram_business_account") or {}
    ig_id = str(ig.get("id") or "")
    username = str(ig.get("username") or "")

    if not page_token or not ig_id:
        raise RuntimeError(
            f"META_INSTAGRAM_ACCOUNT_NOT_READY: Page '{page_name}' ({page_id}) "
            "did not return its Page token and linked Instagram account."
        )

    TOKEN = page_token
    print(
        f"Resolved Instagram account: @{username} ({ig_id}) via Page "
        f"'{page_name}' ({page_id}) using Meta System User token"
    )
    return ig_id


def is_already_published(data):
    instagram = data.get("publishing", {}).get("instagram", {}) or {}
    return (
        data.get("status") == "published_to_instagram"
        or instagram.get("status") == "published_to_instagram"
        or bool(data.get("instagram_media_id"))
        or bool(instagram.get("media_id"))
    )


MAX_CONTENT_AGE = timedelta(hours=24)
DAILY_PUBLISH_LIMIT = 3
LOCAL_TZ = ZoneInfo("Asia/Kolkata")
OUTPUT_DIR = Path("output")


def content_record_paths():
    """Return legacy and daily-educational metadata without duplicate paths."""
    paths = set()
    for pattern in ("content_*.json", "draft_*.json"):
        paths.update(OUTPUT_DIR.glob(pattern))
    return sorted(paths, key=lambda path: path.name)


def parse_timestamp(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def published_today_count():
    today_local = datetime.now(LOCAL_TZ).date()
    count = 0
    for p in content_record_paths():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not is_already_published(data):
            continue
        published_at = parse_timestamp(data.get("published_at") or data.get("publishing", {}).get("instagram", {}).get("published_at"))
        if published_at and published_at.astimezone(LOCAL_TZ).date() == today_local:
            count += 1
    return count


def load_newest_unpublished_approved():
    today_count = published_today_count()
    now = datetime.now(timezone.utc)
    candidates = []
    for p in content_record_paths():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue

        content_id = str(data.get("content_id", "")).strip()
        if not content_id or p.stem != content_id:
            print(f"Skipping content ID / filename mismatch: {p.name}")
            continue
        status = str(data.get("status", "")).strip()
        if status not in {"approved_for_publishing", "published_to_instagram"}:
            continue

        instagram_done = is_already_published(data)
        publishing = data.get("publishing", {}) if isinstance(data.get("publishing"), dict) else {}
        telegram_state = publishing.get("telegram", {}) if isinstance(publishing.get("telegram"), dict) else {}
        telegram_status = str(telegram_state.get("status", "")).strip().lower()
        if instagram_done:
            if telegram_status == "published":
                print(f"Skipping fully published Reel: {p.name}")
                continue
            if telegram_status in {"sending", "unknown"}:
                print(f"Skipping Reel with ambiguous Telegram outcome; manual reconciliation required: {p.name}")
                continue
            if telegram_status != "failed":
                print(f"Skipping Instagram-published Reel without a safe Telegram retry state: {p.name}")
                continue

        fact_check_status = str((data.get("fact_check") or {}).get("status", "")).strip().lower()
        approval = data.get("approval", {}) if isinstance(data.get("approval"), dict) else {}
        safety_check = data.get("safety_check", {}) if isinstance(data.get("safety_check"), dict) else {}
        automated_review_ok = (
            approval.get("mode") == "automated_policy"
            and approval.get("required") is False
            and bool(approval.get("automated_review_at"))
            and safety_check.get("passed") is True
        )
        human_fact_check_ok = fact_check_status in {"passed", "verified", "approved"}
        automated_fact_check_ok = fact_check_status in {"automated_passed", "passed"} and automated_review_ok
        if not (human_fact_check_ok or automated_fact_check_ok):
            print(f"Skipping draft without an accepted fact/safety check ({fact_check_status or 'missing status'}): {p.name}")
            continue

        if approval.get("status") != "approved":
            print(f"Skipping draft without a persisted publishing decision: {p.name}")
            continue

        created_at = parse_timestamp(data.get("created_at"))
        if not created_at:
            print(f"Skipping draft with missing/invalid created_at: {p.name}")
            continue
        age = now - created_at
        if not instagram_done and (age < timedelta(seconds=0) or age > MAX_CONTENT_AGE):
            print(f"Skipping stale/future-dated draft ({age} old): {p.name}")
            continue

        video_url = str(data.get("video_url", "")).strip()
        video_path = OUTPUT_DIR / "media" / f"{content_id}.mp4"
        if video_url:
            if data.get("video_content_id") != content_id or not video_url.endswith(f"/{content_id}.mp4"):
                print(f"Skipping draft with mismatched video URL/content ID: {p.name}")
                continue
        elif not video_path.is_file():
            print(f"Skipping approved draft without verified public video URL or local Reel file: {p.name}")
            continue

        priority = 0 if instagram_done else 1
        candidates.append((priority, created_at, content_id, p, data))

    if not candidates:
        if today_count >= DAILY_PUBLISH_LIMIT:
            print(f"Daily publishing cap reached: {today_count}/{DAILY_PUBLISH_LIMIT} Instagram Reels in Asia/Kolkata. Nothing to publish.")
        else:
            print("No fresh, fact-checked, unpublished approved content is eligible.")
        return None, None

    candidates.sort(key=lambda item: (item[0], -item[1].timestamp(), item[2]))
    priority, _, content_id, content_path, approved = candidates[0]
    if priority != 0 and today_count >= DAILY_PUBLISH_LIMIT:
        print(f"Daily publishing cap reached: {today_count}/{DAILY_PUBLISH_LIMIT} Instagram Reels in Asia/Kolkata. Nothing to publish.")
        return None, None
    return content_path, approved


def save_state(content_path, approved):
    content_path.write_text(
        json.dumps(approved, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


class InstagramPublishUnknown(RuntimeError):
    """Instagram publish outcome is ambiguous; automatic re-publish is blocked."""


def publish_instagram_reel_container(ig_user_id, video_url, caption, approved, content_path):
    """Create once and fail closed when Instagram's final publish outcome is ambiguous."""
    publishing = approved.setdefault("publishing", {})
    instagram = publishing.setdefault("instagram", {})
    if instagram.get("status") in {"publish_attempt_started", "publish_outcome_unknown"}:
        raise InstagramPublishUnknown(
            "Instagram media_publish outcome is unresolved; automatic re-publish is blocked to prevent duplicates."
        )
    creation_id = str(instagram.get("creation_id") or "").strip()

    if not creation_id:
        container = request("POST", f"{API}/{ig_user_id}/media", {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": "true",
            "access_token": TOKEN,
        })
        creation_id = str(container.get("id") or "").strip()
        if not creation_id:
            raise RuntimeError("Instagram Reel container response had no id.")
        instagram["creation_id"] = creation_id
        instagram["status"] = "container_created"
        instagram["container_created_at"] = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
        )
        # Persist the container before polling or asking Instagram to publish it.
        save_state(content_path, approved)
        print("Created and persisted Instagram Reel container ID (ID redacted).")
    else:
        print("Reusing persisted Instagram Reel container; no new container will be created.")

    for attempt in range(20):
        status = request("GET", f"{API}/{creation_id}", {
            "fields": "status_code,status",
            "access_token": TOKEN,
        })
        print(f"Upload status: {status}")
        if status.get("status_code") == "FINISHED":
            break
        if status.get("status_code") in {"ERROR", "EXPIRED"}:
            raise RuntimeError(
                f"Instagram Reel container entered {status.get('status_code')} status; "
                "container ID retained for manual reconciliation."
            )
        time.sleep(15)
    else:
        raise RuntimeError(
            "Instagram Reel container did not finish in the expected time; "
            "container ID retained for safe retry."
        )

    # Persist a one-way attempt marker before the network call. If the runner or
    # response fails, a later run must reconcile manually rather than POST again.
    instagram["status"] = "publish_attempt_started"
    instagram["publish_attempt_started_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    save_state(content_path, approved)
    try:
        published = request("POST", f"{API}/{ig_user_id}/media_publish", {
            "creation_id": creation_id,
            "access_token": TOKEN,
        })
    except Exception as exc:
        instagram["status"] = "publish_outcome_unknown"
        instagram["publish_error_type"] = type(exc).__name__
        save_state(content_path, approved)
        raise InstagramPublishUnknown(
            "Instagram media_publish outcome is ambiguous; automatic re-publish is blocked to prevent duplicates."
        ) from None
    media_id = str(published.get("id") or "").strip()
    if not media_id:
        instagram["status"] = "publish_outcome_unknown"
        instagram["publish_error_type"] = "MissingMediaId"
        save_state(content_path, approved)
        raise InstagramPublishUnknown(
            "Instagram Reel publish returned no media ID; automatic re-publish is blocked for reconciliation."
        )
    instagram["status"] = "published_to_instagram"
    instagram["media_id"] = media_id
    instagram["published_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    instagram.pop("publish_error_type", None)
    save_state(content_path, approved)
    return media_id


class TelegramPublishRejected(RuntimeError):
    """Telegram returned an explicit rejection; a deliberate retry is safe."""


class TelegramPublishUnknown(RuntimeError):
    """Telegram outcome is ambiguous; do not automatically send a duplicate."""


def sha256_and_size(path: Path):
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
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
    if not content_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for ch in content_id):
        raise RuntimeError("Missing or unsafe content_id for public video URL.")
    supabase_url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    if not supabase_url:
        raise RuntimeError("SUPABASE_URL is required to verify the approved Reel's public video URL.")
    return (
        f"{supabase_url}/storage/v1/object/public/REELS/reels/"
        f"{urllib.parse.quote(content_id, safe='')}.mp4"
    )


def verify_public_video_url(video_url: str, approved: dict) -> str:
    """Download the exact Supabase object and verify ID, size, SHA-256, and ffprobe duration."""
    content_id = str(approved.get("content_id", "")).strip()
    expected_url = expected_public_video_url(content_id)
    if video_url != expected_url or approved.get("video_content_id") != content_id:
        raise RuntimeError("Public video URL/content_id mismatch; publishing blocked.")
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
    request_obj = urllib.request.Request(video_url, method="GET")
    try:
        with urllib.request.urlopen(request_obj, timeout=180) as response:
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
        raise RuntimeError(f"Supabase public video URL returned HTTP {exc.code}; publishing blocked.") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not retrieve approved Reel from Supabase ({type(exc).__name__}); publishing blocked.") from None

    try:
        actual_sha = digest.hexdigest()
        if actual_size != expected_size or actual_sha != expected_sha:
            raise RuntimeError("Supabase video byte size/SHA-256 differs from the approved metadata; publishing blocked.")
        actual_duration = probe_duration(Path(temp_name))
        if abs(actual_duration - expected_duration) > 0.75:
            raise RuntimeError(
                f"Supabase video duration mismatch (expected {expected_duration:.2f}s, got {actual_duration:.2f}s); publishing blocked."
            )
    finally:
        if temp_name:
            try:
                Path(temp_name).unlink(missing_ok=True)
            except OSError:
                pass
    print(f"Verified exact public MP4 for {content_id}: {actual_size} bytes, {actual_duration:.2f}s, SHA-256 matched.")
    return video_url


def _upload_local_video_to_supabase(video_path: Path, approved: dict) -> str:
    """Fallback for older approved records that do not already have a public video URL."""
    supabase_url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not supabase_url or not supabase_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for Reel media upload.")
    content_id = str(approved.get("content_id", "")).strip()
    digest, size = sha256_and_size(video_path)
    duration = probe_duration(video_path)
    object_path = f"reels/{content_id}.mp4"
    upload_url = f"{supabase_url}/storage/v1/object/REELS/{urllib.parse.quote(object_path, safe='/')}"
    video_url = expected_public_video_url(content_id)
    request_obj = urllib.request.Request(
        upload_url, data=video_path.read_bytes(), method="PUT",
        headers={
            "Authorization": f"Bearer {supabase_key}", "apikey": supabase_key,
            "Content-Type": "video/mp4", "x-upsert": "false",
        },
    )
    try:
        with urllib.request.urlopen(request_obj, timeout=180) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        if exc.code != 409:
            raise RuntimeError(f"Supabase upload failed HTTP {exc.code}; response redacted.") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Supabase upload failed ({type(exc).__name__}); credentials redacted.") from None
    approved.update({
        "video_url": video_url, "video_content_id": content_id,
        "video_sha256": digest, "video_size_bytes": size, "video_duration_seconds": duration,
    })
    verify_public_video_url(video_url, approved)
    return video_url


def _send_telegram_video(token: str, video_url: str, caption: str) -> int:
    endpoint = f"https://api.telegram.org/bot{token}/sendVideo"
    payload = urllib.parse.urlencode({
        "chat_id": TELEGRAM_CHANNEL, "video": video_url, "caption": caption[:1024],
    }).encode()
    req = urllib.request.Request(endpoint, data=payload, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raise TelegramPublishRejected(f"Telegram channel sendVideo failed HTTP {exc.code}; response redacted.") from None
    except urllib.error.URLError as exc:
        raise TelegramPublishUnknown(
            f"Telegram channel sendVideo outcome is unknown ({type(exc).__name__}); automatic retry is blocked to avoid duplicates."
        ) from None
    if not result.get("ok"):
        raise TelegramPublishRejected("Telegram channel rejected sendVideo; response redacted.")
    message_id = (result.get("result") or {}).get("message_id")
    if not message_id:
        raise TelegramPublishUnknown("Telegram sendVideo returned no message ID; automatic retry is blocked.")
    return int(message_id)


def publish_content_record(content_path: Path, approved: dict, ig_user_id: str | None = None) -> dict:
    """Publish an eligible educational Reel with retry-safe Instagram and Telegram state."""
    content_id = str(approved.get("content_id", "")).strip()
    if not content_id or content_path.stem != content_id:
        raise RuntimeError("Publishing metadata filename/content_id mismatch.")
    if approved.get("status") not in {"approved_for_publishing", "published_to_instagram"}:
        raise RuntimeError("Publishing blocked: the Reel does not have an approved publishing status.")
    approval = approved.get("approval", {}) if isinstance(approved.get("approval"), dict) else {}
    fact_check = approved.get("fact_check", {}) if isinstance(approved.get("fact_check"), dict) else {}
    automated_mode = approval.get("mode") == "automated_policy"
    safety_check = approved.get("safety_check", {}) if isinstance(approved.get("safety_check"), dict) else {}
    automated_gate_ok = (
        automated_mode
        and approval.get("required") is False
        and bool(approval.get("automated_review_at"))
        and fact_check.get("status") in {"automated_passed", "passed"}
        and safety_check.get("passed") is True
    )
    human_gate_ok = (
        approval.get("status") == "approved"
        and fact_check.get("status") in {"approved", "passed", "verified"}
        and bool(approval.get("reviewed_at"))
        and bool(approval.get("reviewed_by"))
    )
    if approval.get("status") != "approved" or not (automated_gate_ok or human_gate_ok):
        raise RuntimeError("Publishing blocked: neither the automated safety policy nor the legacy human-review gate passed.")

    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not telegram_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required because approved Reels must also post to @bullseye_theory.")
    video_url = str(approved.get("video_url", "")).strip()
    if video_url:
        video_url = verify_public_video_url(video_url, approved)
    else:
        video_path = OUTPUT_DIR / "media" / f"{content_id}.mp4"
        if not video_path.is_file() or video_path.stat().st_size <= 0:
            raise RuntimeError("Approved Reel has no valid local MP4 or public Supabase video URL.")
        video_url = _upload_local_video_to_supabase(video_path, approved)
        save_state(content_path, approved)

    social = approved.get("social", {}) if isinstance(approved.get("social"), dict) else {}
    caption = str(social.get("caption", approved.get("caption", "")))
    hashtags = social.get("hashtags", approved.get("hashtags", []))
    if isinstance(hashtags, list):
        caption = (caption + "\n\n" + " ".join(str(tag) for tag in hashtags)).strip()

    publishing = approved.setdefault("publishing", {})
    instagram = publishing.setdefault("instagram", {})
    instagram_error = None

    # Keep the two destinations independent: a Meta/Instagram failure must not
    # prevent the public Telegram channel from receiving this educational Reel.
    if not is_already_published(approved):
        try:
            if not ig_user_id:
                ig_user_id = resolve_instagram_user_id()
            media_id = publish_instagram_reel_container(ig_user_id, video_url, caption, approved, content_path)
            approved["status"] = "published_to_instagram"
            approved["instagram_media_id"] = media_id
            approved["published_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            instagram["status"] = "published_to_instagram"
            instagram["media_id"] = media_id
            instagram["published_at"] = approved["published_at"]
            save_state(content_path, approved)
            print(f"Instagram Reel published; media ID saved for {content_id}.")
        except Exception as exc:
            instagram_error = exc
            # Preserve ambiguous publish markers. They must never be reset to a
            # retryable state because that could create duplicate Instagram posts.
            if instagram.get("status") not in {"publish_attempt_started", "publish_outcome_unknown"}:
                instagram["status"] = "failed"
                instagram["error_type"] = type(exc).__name__
            save_state(content_path, approved)
            print(f"Instagram publish failed for {content_id} ({type(exc).__name__}); continuing to Telegram.")
    else:
        print(f"Instagram already published for {content_id}; skipping duplicate Instagram publish.")

    telegram = publishing.setdefault("telegram", {})
    tg_status = str(telegram.get("status", "")).lower()
    telegram_error = None
    if tg_status == "published":
        print(f"Telegram channel already published for {content_id}; skipping duplicate channel post.")
    elif tg_status in {"sending", "unknown"}:
        telegram_error = TelegramPublishUnknown(
            f"Telegram channel outcome for {content_id} is ambiguous; automatic resend blocked to prevent duplicates."
        )
    else:
        telegram["status"] = "sending"
        telegram["attempt_started_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        save_state(content_path, approved)
        telegram_caption = (caption + "\n\n🎯 Bullseye Theory\nLearn | Trade | Earn").strip()
        try:
            message_id = _send_telegram_video(telegram_token, video_url, telegram_caption)
        except TelegramPublishRejected as exc:
            telegram["status"] = "failed"
            telegram["error"] = str(exc)[:300]
            save_state(content_path, approved)
            telegram_error = exc
        except TelegramPublishUnknown as exc:
            telegram["status"] = "unknown"
            telegram["error"] = str(exc)[:300]
            save_state(content_path, approved)
            telegram_error = exc
        else:
            telegram["status"] = "published"
            telegram["message_id"] = message_id
            telegram["published_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            telegram.pop("error", None)
            save_state(content_path, approved)
            print(f"Telegram channel post recorded for {content_id}; message ID saved.")

    # Surface publishing failure to GitHub Actions after recording both channel
    # outcomes, so the watchdog still alerts while successful delivery is retained.
    if telegram_error is not None and instagram_error is not None:
        raise RuntimeError(
            f"Instagram and Telegram publishing failed for {content_id} "
            f"(Instagram={type(instagram_error).__name__}, Telegram={type(telegram_error).__name__}); "
            "both outcomes were recorded."
        ) from telegram_error
    if telegram_error is not None:
        raise telegram_error
    if instagram_error is not None:
        raise RuntimeError(
            f"Instagram publishing failed for {content_id} ({type(instagram_error).__name__}); "
            "Telegram was attempted and its result was recorded."
        ) from instagram_error
    return approved


def publish_approved_educational_reel(record: dict) -> dict:
    """PUBLISH_ONLY adapter for the shared data/state.json market approval machine."""
    content_id = str(record.get("content_id", "")).strip()
    if record.get("content_type") != "educational_reel":
        raise RuntimeError("Expected educational_reel content_type.")
    if record.get("approval_status") != "approved":
        raise RuntimeError("Publishing blocked: shared state lacks an approved publish policy decision.")
    approval_mode = str(record.get("approval_mode", "")).strip()
    automated_mode = approval_mode == "automated_policy"
    fact_check = record.get("fact_check", {}) if isinstance(record.get("fact_check"), dict) else {}
    if automated_mode:
        if fact_check.get("status") != "automated_passed" or not record.get("automated_review_at"):
            raise RuntimeError("Publishing blocked: shared-state automated safety decision is incomplete.")
    elif (
        fact_check.get("status") != "approved"
        or not record.get("reviewed_at")
        or not record.get("reviewed_by")
    ):
        raise RuntimeError("Publishing blocked: shared-state legacy human review is incomplete.")
    metadata_path = OUTPUT_DIR / f"{content_id}.json"
    metadata = load_json(metadata_path, None)
    if not isinstance(metadata, dict) or metadata.get("content_id") != content_id:
        raise RuntimeError("Publishing blocked: matching Reel metadata file is missing or mismatched.")
    approval = metadata.get("approval", {}) if isinstance(metadata.get("approval"), dict) else {}
    metadata_fact = metadata.get("fact_check", {}) if isinstance(metadata.get("fact_check"), dict) else {}
    if approval.get("status") != "approved":
        raise RuntimeError("Publishing blocked: metadata approval/policy status does not match shared state.")
    if automated_mode:
        metadata_safety = metadata.get("safety_check", {}) if isinstance(metadata.get("safety_check"), dict) else {}
        if (
            approval.get("mode") != "automated_policy"
            or approval.get("required") is not False
            or metadata_fact.get("status") != "automated_passed"
            or metadata_safety.get("passed") is not True
            or not approval.get("automated_review_at")
        ):
            raise RuntimeError("Publishing blocked: metadata automated safety decision does not match shared state.")
    elif metadata_fact.get("status") != "approved":
        raise RuntimeError("Publishing blocked: metadata human fact-check does not match shared state.")
    created_at = parse_timestamp(metadata.get("created_at"))
    already_ig = is_already_published(metadata)
    if not created_at:
        raise RuntimeError("Publishing blocked: metadata created_at is missing or invalid.")
    if not already_ig and (datetime.now(timezone.utc) - created_at > MAX_CONTENT_AGE):
        print(f"Skipping stale approved educational Reel ({content_id}); exceeds 24-hour publishing window.")
        record["status"] = "expired"
        record["expired_at"] = datetime.now(timezone.utc).isoformat()
        return record

    try:
        publish_content_record(metadata_path, metadata)
    finally:
        record["publishing"] = metadata.get("publishing", {})
        record["instagram_media_id"] = metadata.get("instagram_media_id") or record.get("instagram_media_id")
        record["published_at"] = metadata.get("published_at") or record.get("published_at")
        ig_state = (record.get("publishing", {}).get("instagram", {}) or {}).get("status")
        tg_state = (record.get("publishing", {}).get("telegram", {}) or {}).get("status")
        if ig_state in {"published", "published_to_instagram"} and tg_state == "published":
            record["status"] = "published"
        elif ig_state in {"published", "published_to_instagram"}:
            record["status"] = "partial"
        elif record.get("approval_status") == "approved":
            record["status"] = "publish_failed"
    return record


def main():
    content_path, approved = load_newest_unpublished_approved()
    if not approved:
        print("No unpublished approved content. Nothing to publish.")
        return
    print(f"Selected approved Reel: {content_path.name}")
    publish_content_record(content_path, approved)


if __name__ == "__main__":
    main()
