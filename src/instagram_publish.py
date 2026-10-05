import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error
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
                "META_ACCESS_TOKEN_INVALID: Meta rejected INSTAGRAM_ACCESS_TOKEN "
                "(OAuth error 190). The token is expired, revoked, or invalid. "
                "No Reel was published; refresh/re-authorize the Meta token and "
                "replace the GitHub secret INSTAGRAM_ACCESS_TOKEN."
            ) from e
        raise RuntimeError(f"Meta API HTTP {e.code}: {body}") from e


def resolve_instagram_user_id():
    global TOKEN
    if not SYSTEM_USER_TOKEN:
        raise RuntimeError("META_SYSTEM_USER_TOKEN_NOT_CONFIGURED: Add the Meta System User token to GitHub Actions.")

    if SYSTEM_USER_TOKEN:
        pages = request("GET", f"{API}/me/accounts", {
            "fields": "id,name,access_token,tasks,instagram_business_account{id,username}",
            "access_token": SYSTEM_USER_TOKEN,
        })
        rows = pages.get("data") or []
        eligible = [p for p in rows if (p.get("instagram_business_account") or {}).get("id")]
        eligible.sort(key=lambda p: 0 if str(p.get("name", "")).strip().lower() == "bullseye theory" else 1)
        selected = eligible[0] if eligible else None
        if not selected:
            raise RuntimeError("META_PAGE_NOT_ASSIGNED: Meta System User has no assigned Page with a linked Instagram professional account.")
        page_id = str(selected.get("id") or "")
        page_name = str(selected.get("name") or "")
        page_token = str(selected.get("access_token") or "")
        ig = selected.get("instagram_business_account") or {}
        ig_id = str(ig.get("id") or "")
        username = str(ig.get("username") or "")
        if not page_token or not ig_id:
            raise RuntimeError(f"META_INSTAGRAM_ACCOUNT_NOT_READY: Page '{page_name}' ({page_id}) did not return its Page token and linked Instagram account.")
        TOKEN = page_token
        print(f"Resolved Instagram account: @{username} ({ig_id}) via Page '{page_name}' ({page_id}) using Meta System User token")
        return ig_id

    raise RuntimeError("META_SYSTEM_USER_ONLY: Legacy Instagram token publishing is disabled; use META_SYSTEM_USER_TOKEN.")\n
