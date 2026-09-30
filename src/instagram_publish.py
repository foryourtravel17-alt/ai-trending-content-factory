import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

API_VERSION = os.environ.get("META_GRAPH_API_VERSION", "v23.0")
TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
INSTAGRAM_USER_ID = os.environ["INSTAGRAM_USER_ID"]

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
                "META_ACCESS_TOKEN_INVALID: Meta rejected INSTAGRAM_ACCESS_TOKEN "
                "(OAuth error 190). The token is expired, revoked, or invalid. "
                "No Reel was published; refresh/re-authorize the Meta token and "
                "replace the GitHub secret INSTAGRAM_ACCESS_TOKEN."
            ) from e
        raise RuntimeError(f"Meta API HTTP {e.code}: {body}") from e


def is_already_published(data):
    instagram = data.get("publishing", {}).get("instagram", {}) or {}
    return (
        data.get("status") == "published_to_instagram"
        or instagram.get("status") == "published_to_instagram"
        or bool(data.get("instagram_media_id"))
        or bool(instagram.get("media_id"))
    )


def load_newest_unpublished_approved():
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

        content_id = str(data.get("content_id", ""))
        video_path = Path("output/media") / f"{content_id}.mp4"
        if not video_path.exists():
            print(f"Skipping approved draft without Reel file: {p.name}")
            continue

        created_at = str(data.get("created_at", ""))
        candidates.append((created_at, content_id, p, data))

    if not candidates:
        return None, None

    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    _, _, content_path, approved = candidates[0]
    return content_path, approved


def save_state(content_path, approved):
    content_path.write_text(
        json.dumps(approved, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main():
    content_path, approved = load_newest_unpublished_approved()
    if not approved:
        print("No unpublished approved content. Nothing to publish.")
        return

    print(f"Selected newest unpublished approved content: {content_path.name}")
    print(f"Using configured Instagram account ID: {INSTAGRAM_USER_ID}")

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

    print(f"Creating Instagram Reel container for {content_path.name}")
    container = request("POST", f"{API}/{INSTAGRAM_USER_ID}/media", {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true",
        "access_token": TOKEN,
    })
    creation_id = container["id"]
    print(f"Instagram container: {creation_id}")

    for attempt in range(20):
        status = request("GET", f"{API}/{creation_id}", {
            "fields": "status_code,status",
            "access_token": TOKEN,
        })
        print(f"Upload status: {status}")
        if status.get("status_code") == "FINISHED":
            break
        if status.get("status_code") in {"ERROR", "EXPIRED"}:
            raise RuntimeError(f"Instagram container failed: {status}")
        time.sleep(15)
    else:
        raise RuntimeError("Instagram container did not finish in the expected time.")

    published = request("POST", f"{API}/{INSTAGRAM_USER_ID}/media_publish", {
        "creation_id": creation_id,
        "access_token": TOKEN,
    })
    print(f"Instagram published media: {published}")

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
                body = e.read().decode(errors="replace")
                raise RuntimeError(
                    f"Telegram channel post failed HTTP {e.code}: {body}"
                ) from e


if __name__ == "__main__":
    main()
