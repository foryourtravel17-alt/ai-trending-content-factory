"""Read-only Meta/Instagram credential diagnostic; never creates or publishes media."""
from __future__ import annotations

import os
import sys
import requests

API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v23.0").strip() or "v23.0"
BASE = f"https://graph.facebook.com/{API_VERSION}"


def first_env(names):
    for name in names:
        if os.getenv(name, "").strip():
            return name, os.getenv(name, "").strip()
    return "", ""


def get(path, token):
    response = requests.get(f"{BASE}/{path.lstrip('/')}", params={"access_token": token}, timeout=25)
    try:
        body = response.json()
    except ValueError:
        raise RuntimeError(f"Meta returned non-JSON HTTP {response.status_code}; values redacted.")
    if not response.ok or isinstance(body, dict) and body.get("error"):
        error = body.get("error", {}) if isinstance(body, dict) else {}
        raise RuntimeError(
            f"Meta GET failed: HTTP {response.status_code}, "
            f"code={error.get('code', 'unknown')}, subcode={error.get('error_subcode', 'unknown')}; values redacted."
        )
    return body


def main():
    token_name, token = first_env(("META_SYSTEM_USER_TOKEN", "INSTAGRAM_ACCESS_TOKEN", "IG_ACCESS_TOKEN"))
    id_name, configured_id = first_env(("IG_USER_ID", "INSTAGRAM_USER_ID"))
    print(f"Token source variable: {token_name or 'MISSING'}")
    print(f"Configured ID source variable: {id_name or 'MISSING'}")
    if not token:
        print("FAIL: no supported Meta token variable is configured.")
        return 1
    if not configured_id:
        print("FAIL: IG_USER_ID and INSTAGRAM_USER_ID are both missing; cannot compare configured ID.")
        return 1
    try:
        configured = get(f"{configured_id}?fields=id,username", token)
        print(f"Configured account lookup: id={configured.get('id', 'MISSING')}, username=@{configured.get('username', 'unknown')}")
        pages = get("me/accounts?fields=id,name,instagram_business_account{id,username}", token)
    except RuntimeError as exc:
        print(f"FAIL: {exc}")
        return 1
    rows = pages.get("data", []) if isinstance(pages, dict) else []
    for page in rows:
        if not isinstance(page, dict):
            continue
        ig = page.get("instagram_business_account") or {}
        print(f"Page: {page.get('name', 'unnamed')} | linked Instagram: @{ig.get('username', 'none')} | linked ID present: {'yes' if ig.get('id') else 'no'}")
    target = [p for p in rows if isinstance(p, dict) and str(p.get("name", "")).strip().casefold() == "bullseye theory"]
    linked = (target[0].get("instagram_business_account") or {}) if len(target) == 1 else {}
    linked_id = str(linked.get("id") or "")
    if len(target) != 1 or not linked_id:
        print("FAIL: expected exactly one Bullseye Theory Page with a linked Instagram professional account.")
        return 1
    if configured_id == linked_id:
        print("MATCH: configured account ID equals the Instagram account linked to the Bullseye Theory Page.")
        print("PASS")
        return 0
    print("MISMATCH: configured account ID does not equal the Instagram account linked to the Bullseye Theory Page.")
    print("FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
