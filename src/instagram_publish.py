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


def main():
    content_path = Path("output/content_2.json")
    approved = None
    for p in sorted(Path("output").glob("content_*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("status") == "approved_for_publishing":
            approved = data
            content_path = p
            break

    if not approved:
        print("No approved content. Nothing to publish.")
        return

    repo = os.environ["GITHUB_REPOSITORY"]
    video_url = f"https://raw.githubusercontent.com/{repo}/main/output/media/{approved["content_id"]}.mp4"
    print(f"Public Reel URL: {video_url}")

    caption = approved.get("caption", "")
    hashtags = approved.get("hashtags", [])
    if isinstance(hashtags, list):
        caption = (caption + "\n\n" + " ".join(hashtags)).strip()

    print(f"Creating Instagram Reel container for {content_path.name}")
    container = request("POST", f"{API}/{IG_USER_ID}/media", {
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

    published = request("POST", f"{API}/{IG_USER_ID}/media_publish", {
        "creation_id": creation_id,
        "access_token": TOKEN,
    })
    print(f"Instagram published media: {published}")

    approved["status"] = "published_to_instagram"
    approved["instagram_media_id"] = published.get("id")
    content_path.write_text(json.dumps(approved, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
