import json
import os
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
    for p in Path("output").glob("content_*.json"):
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
    if today_count >= DAILY_PUBLISH_LIMIT:
        print(f"Daily publishing cap reached: {today_count}/{DAILY_PUBLISH_LIMIT} Instagram Reels in Asia/Kolkata. Nothing to publish.")
        return None, None

    now = datetime.now(timezone.utc)
    candidates = []
    for p in Path("output").glob("content_*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue

        if data.get("status") != "approved_for_publishing":
            continue
        if is_already_published(data):
            print(f"Skipping already-published draft: {p.name}")
            continue

        fact_check_status = str((data.get("fact_check") or {}).get("status", "")).strip().lower()
        if fact_check_status not in {"passed", "verified", "approved"}:
            print(f"Skipping draft requiring fact-check review ({fact_check_status or 'missing status'}): {p.name}")
            continue

        created_at = parse_timestamp(data.get("created_at"))
        if not created_at:
            print(f"Skipping draft with missing/invalid created_at: {p.name}")
            continue
        age = now - created_at
        if age < timedelta(seconds=0) or age > MAX_CONTENT_AGE:
            print(f"Skipping stale/future-dated draft ({age} old): {p.name}")
            continue

        content_id = str(data.get("content_id", ""))
        video_path = Path("output/media") / f"{content_id}.mp4"
        if not video_path.exists():
            print(f"Skipping approved draft without Reel file: {p.name}")
            continue

        candidates.append((created_at.isoformat(), content_id, p, data))

    if not candidates:
        print("No fresh, fact-checked, unpublished approved content is eligible.")
        return None, None

    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    _, _, content_path, approved = candidates[0]
    return content_path, approved


def save_state(content_path, approved):
    content_path.write_text(
        json.dumps(approved, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def publish_instagram_reel_container(ig_user_id, video_url, caption, approved, content_path):
    """Create once, persist the Reel container, and reuse it after an ambiguous failure."""
    publishing = approved.setdefault("publishing", {})
    instagram = publishing.setdefault("instagram", {})
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

    published = request("POST", f"{API}/{ig_user_id}/media_publish", {
        "creation_id": creation_id,
        "access_token": TOKEN,
    })
    media_id = str(published.get("id") or "").strip()
    if not media_id:
        raise RuntimeError(
            "Instagram Reel publish returned no media id; existing container retained."
        )
    return media_id


def main():
    content_path, approved = load_newest_unpublished_approved()
    if not approved:
        print("No unpublished approved content. Nothing to publish.")
        return

    print(f"Selected newest unpublished approved content: {content_path.name}")
    ig_user_id = resolve_instagram_user_id()
    print(f"Using Instagram account ID: {ig_user_id}")

    content_id = approved["content_id"]
    video_path = Path("output/media") / f"{content_id}.mp4"

    supabase_url = os.environ["SUPABASE_URL"].rstrip("/")
    supabase_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    object_path = f"reels/{content_id}.mp4"
    upload_url = (
        f"{supabase_url}/storage/v1/object/REELS/"
        f"{urllib.parse.quote(object_path, safe='/')}"
    )
    print(f"Uploading Reel to Supabase: {object_path}")

    upload_req = urllib.request.Request(
        upload_url,
        data=video_path.read_bytes(),
        method="PUT",
        headers={
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "video/mp4",
            "x-upsert": "true",
        },
    )
    try:
        with urllib.request.urlopen(upload_req, timeout=180) as response:
            response.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"Supabase upload failed HTTP {e.code}: {body}") from e

    video_url = (
        f"{supabase_url}/storage/v1/object/public/REELS/"
        f"{urllib.parse.quote(object_path, safe='/')}"
    )
    print(f"Public Reel URL: {video_url}")

    social = approved.get("social", {}) or {}
    caption = social.get("caption", "")
    hashtags = social.get("hashtags", [])
    if isinstance(hashtags, list):
        caption = (caption + "\n\n" + " ".join(hashtags)).strip()

    media_id = publish_instagram_reel_container(
        ig_user_id, video_url, caption, approved, content_path
    )
    print(f"Instagram Reel published media ID: {media_id}")

    media_id = published.get("id")
    if not media_id:
        raise RuntimeError(f"Instagram publish returned no media id: {published}")

    approved["status"] = "published_to_instagram"
    approved["instagram_media_id"] = media_id
    approved["published_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    publishing = approved.setdefault("publishing", {})
    instagram = publishing.setdefault("instagram", {})
    instagram["status"] = "published_to_instagram"
    instagram["media_id"] = media_id
    save_state(content_path, approved)

    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if telegram_token:
        telegram_state = publishing.setdefault("telegram", {})
        if telegram_state.get("status") == "published":
            print("Telegram already marked as published. Skipping Telegram duplicate.")
        else:
            telegram_caption = (
                caption + "\n\n🎯 Bullseye Theory\nLearn | Trade | Earn"
            ).strip()
            telegram_url = f"https://api.telegram.org/bot{telegram_token}/sendVideo"
            telegram_params = urllib.parse.urlencode({
                "chat_id": TELEGRAM_CHANNEL,
                "video": video_url,
                "caption": telegram_caption[:1024],
            }).encode()
            telegram_req = urllib.request.Request(
                telegram_url,
                data=telegram_params,
                method="POST",
            )
            try:
                with urllib.request.urlopen(telegram_req, timeout=120) as response:
                    telegram_result = json.loads(response.read().decode())
                if not telegram_result.get("ok"):
                    raise RuntimeError(f"Telegram API error: {telegram_result}")
                message_id = telegram_result["result"].get("message_id")
                print(f"Telegram channel post sent: {message_id}")
                telegram_state["status"] = "published"
                telegram_state["message_id"] = message_id
                telegram_state["published_at"] = time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                )
                save_state(content_path, approved)
            except urllib.error.HTTPError as e:
                raise RuntimeError(
                    f"Telegram channel post failed HTTP {e.code}; response redacted to protect bot token."
                ) from None
            except urllib.error.URLError as exc:
                raise RuntimeError(
                    f"Telegram channel request failed ({type(exc).__name__}); bot token redacted."
                ) from None


if __name__ == "__main__":
    main()
