"""Read-only Meta/Instagram credential diagnostic; never creates or publishes media."""
from __future__ import annotations

import os
import sys
import requests

API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v23.0").strip() or "v23.0"
BASE = f"https://graph.facebook.com/{API_VERSION}"


def first_env(names):
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return name, value
    return "", ""


def get(path, token):
    response = requests.get(f"{BASE}/{path.lstrip('/')}", params={"access_token": token}, timeout=25)
    try:
        body = response.json()
    except ValueError:
        raise RuntimeError(f"Meta GET failed: HTTP {response.status_code}, code=unknown, subcode=unknown; non-JSON response, values redacted.")
    if not response.ok or isinstance(body, dict) and body.get("error"):
        error = body.get("error", {}) if isinstance(body, dict) else {}
        raise RuntimeError(
            f"Meta GET failed: HTTP {response.status_code}, "
            f"code={error.get('code', 'unknown')}, subcode={error.get('error_subcode', 'unknown')}; values redacted."
        )
    return body


def main():
    token_names = ("META_SYSTEM_USER_TOKEN", "INSTAGRAM_ACCESS_TOKEN", "IG_ACCESS_TOKEN")
    id_names = ("IG_USER_ID", "INSTAGRAM_USER_ID")
    token_name, token = first_env(token_names)
    id_name, configured_id = first_env(id_names)
    for name in token_names + id_names:
        print(f"ENV {name}: {'SET' if os.getenv(name, '').strip() else 'EMPTY'}")
    print(f"Token source variable: {token_name or 'MISSING'}")
    print(f"Configured ID source variable: {id_name or 'MISSING'}")
    if not token:
        print("FAIL: no supported Meta token variable is configured.")
        return 1

    # Resolve the source of truth first. A stale configured ID must never block this.
    try:
        pages = get("me/accounts?fields=id,name,tasks,instagram_business_account{id,username}", token)
    except RuntimeError as exc:
        print(f"FAIL: Page-link resolution failed: {exc}")
        return 1

    rows = pages.get("data", []) if isinstance(pages, dict) else []
    for page in rows:
        if not isinstance(page, dict):
            continue
        ig = page.get("instagram_business_account") or {}
        print(f"Page: {page.get('name', 'unnamed')} | linked Instagram: @{ig.get('username', 'none')} | linked ID present: {'yes' if ig.get('id') else 'no'}")
        tasks = page.get("tasks")
        if isinstance(tasks, list):
            print(f"Page tasks for {page.get('name', 'unnamed')}: {', '.join(str(task) for task in tasks) or 'none returned'}")

    target = [
        p for p in rows
        if isinstance(p, dict)
        and str(p.get("name", "")).strip().casefold() == "bullseye theory"
        and isinstance(p.get("instagram_business_account"), dict)
        and str(p["instagram_business_account"].get("id", "")).strip()
    ]
    if len(target) != 1:
        print("FAIL: expected exactly one Bullseye Theory Page with a linked Instagram professional account.")
        return 1

    linked = target[0]["instagram_business_account"]
    linked_id = str(linked.get("id") or "").strip()
    linked_username = str(linked.get("username") or "unknown").strip()
    print(f"Correct linked Instagram account: id={linked_id}, username=@{linked_username}")
    print(f"CORRECT IG_USER_ID = {linked_id}")

    # Scope inspection is read-only. Some System User token types do not expose
    # /me/permissions; in that case report the limitation rather than guessing.
    missing_required_scopes = None
    try:
        permission_body = get("me/permissions", token)
        permission_rows = permission_body.get("data", []) if isinstance(permission_body, dict) else []
        granted = {
            str(item.get("permission", "")).strip()
            for item in permission_rows
            if isinstance(item, dict) and str(item.get("status", "")).lower() == "granted"
        }
        if permission_rows:
            required_scopes = {"pages_show_list", "pages_read_engagement", "instagram_basic", "instagram_content_publish"}
            for scope in sorted(required_scopes):
                print(f"Meta permission {scope}: {'GRANTED' if scope in granted else 'NOT GRANTED'}")
            missing_required_scopes = required_scopes - granted
        else:
            print("WARNING: Meta returned no permission rows; publishing scope could not be verified.")
    except RuntimeError as exc:
        import re
        match = re.search(r"code=([^,]+), subcode=([^;]+)", str(exc))
        code, subcode = match.groups() if match else ("unknown", "unknown")
        print(f"WARNING: Permission-scope lookup unavailable (code={code}, subcode={subcode}); confirm Instagram content-publishing access in Meta settings.")

    configured_lookup_ok = False
    if configured_id:
        try:
            configured = get(f"{configured_id}?fields=id,username", token)
            print(f"Configured account lookup: id={configured.get('id', 'MISSING')}, username=@{configured.get('username', 'unknown')}")
            configured_lookup_ok = str(configured.get("id") or "") == linked_id
        except RuntimeError as exc:
            import re
            match = re.search(r"code=([^,]+), subcode=([^;]+)", str(exc))
            code, subcode = match.groups() if match else ("unknown", "unknown")
            print(f"Configured ID lookup failed (code={code}, subcode={subcode})")
    else:
        print("Configured ID lookup skipped: both ID variables are EMPTY.")

    if configured_id == linked_id and configured_lookup_ok:
        print("MATCH: configured account ID equals the Instagram account linked to the Bullseye Theory Page.")
        if missing_required_scopes:
            print("BLOCKED: required Instagram publishing permissions are missing: " + ", ".join(sorted(missing_required_scopes)))
            print("Grant the missing permissions to the Meta app/System User, then refresh the credential.")
            print("FAIL")
            return 1
        if missing_required_scopes is None:
            print("WARNING: account ID matches, but required publishing permissions could not be verified.")
            print("PASS: account-link check only; publishing readiness remains unverified.")
            return 0
        print("PASS: account ID matches and required publishing permissions are granted.")
        return 0

    print("MISMATCH: configured account ID is missing, invalid, or differs from the linked Instagram account.")
    print(f"SET IG_USER_ID to this value: {linked_id}")
    print("FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
