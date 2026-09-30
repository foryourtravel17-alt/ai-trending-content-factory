import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

API_VERSION = os.environ.get("META_GRAPH_API_VERSION", "v23.0")
IG_USER_ID = os.environ["INSTAGRAM_USER_ID"]
TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]

API = f"https://graph.facebook.com/{API_VERSION}"
PAGE_ID = "1327622920435805"
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
        raise RuntimeError(f"Meta API HTTP {e.code}: {body}") from e


def resolve_instagram_user_id():
    # Resolve the connected Instagram Professional account from the Bullseye Theory Page.
    # The Page ID is stable and the same Page query was verified in Graph API Explorer.
    page = request("GET", f"{API}/{PAGE_ID}", {
        "fields": "id,name,instagram_business_account{id,username}",
        "access_token": TOKEN,
    })
    ig = (page.get("instagram_business_account") or {})
    resolved_id = ig.get("id")
    if not resolved_id:
        raise RuntimeError(f"Meta token has no connected Instagram account: {page}")
    print(f"Resolved Instagram account: @{ig.get('username', '')} ({resolved_id})")
    return resolved_id


def main():
    content_path = Path("output/content_2.json")
    approved = None
    approved_candidates = []
    for p in Path("output").glob("content_*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("status") == "approved_for_publishing":
            approved_candidates.append((p, data))

    # Pick the newest approved draft so the generated MP4 and the content JSON
    # stay aligned when two Reels are approved in the same day.
    if approved_candidates:
        approved_candidates.sort(key=lambda item: item[0].stat().st_mtime, reverse=True)
        content_path, approved = approved_candidates[0]

    if not approved:
        print("No approved content. Nothing to publish.")
        return

    # Duplicate-publish guard: never create a second Instagram container
    # for content that is already marked as published.
    instagram_state = approved.get("publishing", {}).get("instagram", {})
    if (
        approved.get("status") == "published_to_instagram"
        or instagram_state.get("status") == "published_to_instagram"
        or approved.get("instagram_media_id")
        or instagram_state.get("media_id")
    ):
        print(f"{content_path.name} is already marked as published. Nothing to publish.")
        return

    ig_user_id = resolve_instagram_user_id()

    content_id = approved["content_id"]
    video_path = Path("output/media") / f"{content_id}.mp4"
    if not video_path.exists():
        raise RuntimeError(f"Approved Reel file not found: {video_path}")

    # Upload the Reel to the public Supabase REELS bucket first.
    # Meta needs a publicly reachable video URL; the GitHub repository is private.
    supabase_url = os.environ["SUPABASE_URL"].rstrip("/")
    supabase_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    object_path = f"reels/{content_id}.mp4"
    upload_url = (
        f"{supabase_url}/storage/v1/object/REELS/"
        f"{urllib.parse.quote(object_path, safe='/')}"
    )
    print(f"Uploading Reel to Supabase: {object_path}")
    upload_data = video_path.read_bytes()
    upload_req = urllib.request.Request(
        upload_url,
        data=upload_data,
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
        raise RuntimeError(
            f"Supabase upload failed HTTP {e.code}: {body}"
        ) from e

    video_url = (
        f"{supabase_url}/storage/v1/object/public/REELS/"
        f"{urllib.parse.quote(object_path, safe='/')}"
    )
    print(f"Public Reel URL: {video_url}")

    # Live content schema stores social metadata under approved["social"].
    social = approved.get("social", {}) or {}
    caption = social.get("caption", "")
    hashtags = social.get("hashtags", [])
    if isinstance(hashtags, list):
        caption = (caption + "\n\n" + " ".join(hashtags)).strip()

    print(f"Creating Instagram Reel container for {content_path.name}")
    container = request("POST", f"{API}/{ig_user_id}/media", {
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

    published = request("POST", f"{API}/{ig_user_id}/media_publish", {
        "creation_id": creation_id,
        "access_token": TOKEN,
    })
    print(f"Instagram published media: {published}")

    media_id = published.get("id")

    # Mirror the successfully published Reel to the public Bullseye Theory
    # Telegram channel. The bot is already an administrator with Post Messages.
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if telegram_token:
        telegram_caption = (caption + "\n\n🎯 Bullseye Theory\nLearn | Trade | Earn").strip()
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
            print(f"Telegram channel post sent: {telegram_result['result'].get('message_id')}")
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            raise RuntimeError(f"Telegram channel post failed HTTP {e.code}: {body}") from e
    approved["status"] = "published_to_instagram"
    approved["instagram_media_id"] = media_id

    publishing = approved.setdefault("publishing", {})
    instagram = publishing.setdefault("instagram", {})
    instagram["status"] = "published_to_instagram"
    instagram["media_id"] = media_id

    approved["published_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    content_path.write_text(
        json.dumps(approved, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
