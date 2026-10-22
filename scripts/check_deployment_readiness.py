#!/usr/bin/env python3
"""Read-only deployment readiness checks; never publishes or mutates remote state."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

TIMEOUT = 15
CHANNEL = "@bullseye_theory"
GRAPH_VERSION = os.getenv("META_GRAPH_API_VERSION", "v23.0").strip() or "v23.0"
SAFE_ID = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"


@dataclass
class Report:
    failures: int = 0
    warnings: int = 0
    checks: int = 0

    def emit(self, level: str, name: str, reason: str) -> None:
        self.checks += 1
        if level == "FAIL":
            self.failures += 1
        elif level == "WARN":
            self.warnings += 1
        print(f"{level} | {name} | {reason}")

    def passed(self, name: str, reason: str) -> None:
        self.emit("PASS", name, reason)

    def failed(self, name: str, reason: str) -> None:
        self.emit("FAIL", name, reason)

    def warned(self, name: str, reason: str) -> None:
        self.emit("WARN", name, reason)

    def exit_code(self) -> int:
        print(f"SUMMARY | checks={self.checks} failures={self.failures} warnings={self.warnings}")
        return 1 if self.failures else 0


def request_bytes(url: str, method: str = "GET", headers: dict | None = None,
                  body: bytes | None = None) -> tuple[int | None, bytes, str | None]:
    """Return response details without including URLs, headers, or remote bodies in errors."""
    req = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            return response.status, response.read(), None
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read()
        except Exception:
            raw = b""
        return exc.code, raw, None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return None, b"", type(exc).__name__


def json_request(url: str, method: str = "GET", headers: dict | None = None,
                 payload: dict | None = None) -> tuple[int | None, dict | list | None, str | None]:
    merged = {"Accept": "application/json", **(headers or {})}
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        merged["Content-Type"] = "application/json"
    status, raw, error = request_bytes(url, method, merged, body)
    if error:
        return status, None, error
    try:
        parsed = json.loads(raw.decode("utf-8")) if raw else None
    except (UnicodeDecodeError, json.JSONDecodeError):
        parsed = None
    return status, parsed, None


def env_present(name: str) -> bool:
    return bool(os.environ.get(name, "").strip())


def telegram_api(token: str, method: str, payload: dict | None = None) -> tuple[bool, dict | None, str]:
    # The token appears only in the request URL; never print it or raw exception text.
    url = f"https://api.telegram.org/bot{token}/{method}"
    status, parsed, error = json_request(url, "POST" if payload is not None else "GET",
                                        payload=payload)
    if error:
        return False, None, f"network error ({error})"
    if status != 200 or not isinstance(parsed, dict) or not parsed.get("ok"):
        return False, None, f"Telegram API returned HTTP {status if status is not None else 'no response'}"
    result = parsed.get("result")
    return True, result if isinstance(result, dict) else None, "OK"


def supabase_headers(key: str) -> dict:
    return {"Authorization": f"Bearer {key}", "apikey": key}


def storage_objects(supabase_url: str, key: str) -> tuple[list, str | None, int | None]:
    url = f"{supabase_url.rstrip('/')}/storage/v1/object/list/REELS"
    status, parsed, error = json_request(
        url, "POST", supabase_headers(key),
        {"prefix": "reels", "limit": 100, "offset": 0,
         "sortBy": {"column": "created_at", "order": "desc"}},
    )
    if error:
        return [], error, status
    if status != 200 or not isinstance(parsed, list):
        return [], "storage object listing failed", status
    return parsed, None, status


def mp4_object_path(objects: list) -> str | None:
    names = []
    for item in objects:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip().lstrip("/")
        if not name.lower().endswith(".mp4"):
            continue
        path = name if name.startswith("reels/") else f"reels/{name}"
        if all(part not in {"", ".", ".."} for part in path.split("/")):
            names.append(path)
    return sorted(set(names), reverse=True)[0] if names else None


def committed_card_paths(repository: str, token: str) -> tuple[list[str], str | None]:
    if "/" not in repository:
        return [], "GITHUB_REPOSITORY is unavailable or malformed"
    owner, repo = repository.split("/", 1)
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1"
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    status, parsed, error = json_request(url, headers=headers)
    if error:
        return [], f"GitHub API network error ({error})"
    if status != 200 or not isinstance(parsed, dict):
        return [], f"GitHub repository tree API returned HTTP {status if status is not None else 'no response'}"
    tree = parsed.get("tree") or []
    paths = [
        str(item.get("path"))
        for item in tree
        if isinstance(item, dict)
        and str(item.get("path") or "").startswith("output/")
        and str(item.get("path") or "").lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
    ]
    cards = [path for path in paths if path.lower().endswith("_card.png")]
    return sorted(cards or paths, reverse=True), None


def image_url_for_card(card_path: str) -> tuple[str | None, str]:
    filename = card_path.rsplit("/", 1)[-1]
    image_base = os.environ.get("IMAGE_BASE_URL", "").strip().rstrip("/")
    gh_user = os.environ.get("GH_USER", "").strip()
    gh_repo = os.environ.get("GH_REPO", "").strip()
    if image_base:
        if not image_base.startswith(("https://", "http://")):
            return None, "IMAGE_BASE_URL must start with https:// or http://"
        return f"{image_base}/{urllib.parse.quote(filename)}", "IMAGE_BASE_URL"
    if gh_user and gh_repo:
        if any(char not in SAFE_ID for char in gh_user + gh_repo):
            return None, "GH_USER/GH_REPO contains unsupported characters"
        return f"https://{gh_user}.github.io/{gh_repo}/output/{urllib.parse.quote(filename)}", "GitHub Pages"
    return None, "set IMAGE_BASE_URL or both GH_USER and GH_REPO"


def run_checks() -> int:
    report = Report()
    required = (
        "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
        "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "META_SYSTEM_USER_TOKEN",
    )
    for name in required:
        if env_present(name):
            report.passed(f"env:{name}", "configured; value intentionally hidden")
        else:
            report.failed(f"env:{name}", "missing repository secret or variable")
    if env_present("TELEGRAM_APPROVER_USER_IDS"):
        report.passed("env:TELEGRAM_APPROVER_USER_IDS", "configured; value intentionally hidden")
    else:
        report.warned("env:TELEGRAM_APPROVER_USER_IDS", "unset; private owner chat fallback works, group approvals require an explicit allowlist")

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if token:
        ok, me, reason = telegram_api(token, "getMe")
        if ok and me and me.get("id"):
            bot_id = str(me["id"])
            report.passed("Telegram bot identity", "getMe succeeded")
            chat_ok, chat, chat_reason = telegram_api(token, "getChat", {"chat_id": CHANNEL})
            if chat_ok and chat and str(chat.get("type", "")) == "channel":
                report.passed("Telegram channel access", f"getChat {CHANNEL} succeeded")
                member_ok, member, member_reason = telegram_api(
                    token, "getChatMember", {"chat_id": CHANNEL, "user_id": bot_id}
                )
                if member_ok and member:
                    status = str(member.get("status", ""))
                    can_post = member.get("can_post_messages")
                    if status == "creator" or (status == "administrator" and can_post is True):
                        report.passed("Telegram channel permissions", "bot is owner/admin with post permission")
                    else:
                        report.failed("Telegram channel permissions", "bot must be administrator with can_post_messages=true")
                else:
                    report.failed("Telegram channel permissions", member_reason)
            else:
                report.failed("Telegram channel access", chat_reason)
        else:
            report.failed("Telegram bot API", reason)

    supabase_url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if supabase_url and supabase_key:
        status, bucket, error = json_request(
            f"{supabase_url}/storage/v1/bucket/REELS",
            headers=supabase_headers(supabase_key),
        )
        if error:
            report.failed("Supabase REELS bucket", f"network error ({error})")
        elif status == 200 and isinstance(bucket, dict) and str(bucket.get("id") or bucket.get("name") or "").upper() == "REELS":
            report.passed("Supabase REELS bucket", "bucket exists")
            if bucket.get("public") is True:
                report.passed("Supabase public bucket", "REELS is marked public")
            else:
                report.failed("Supabase public bucket", "REELS bucket is not marked public")
            objects, list_error, list_status = storage_objects(supabase_url, supabase_key)
            if list_error:
                report.failed("Supabase REELS listing", f"{list_error}; HTTP {list_status}")
            else:
                path = mp4_object_path(objects)
                if path:
                    public_url = f"{supabase_url}/storage/v1/object/public/REELS/{urllib.parse.quote(path, safe='/')}"
                    probe_status, _, probe_error = request_bytes(public_url, "HEAD")
                    if probe_error:
                        report.failed("Supabase public MP4 URL", f"network error ({probe_error})")
                    elif probe_status == 200:
                        report.passed("Supabase public MP4 URL", "an existing reels/*.mp4 object returns HTTP 200")
                    else:
                        report.failed("Supabase public MP4 URL", f"an existing reels/*.mp4 object returned HTTP {probe_status}")
                else:
                    sentinel = f"{supabase_url}/storage/v1/object/public/REELS/reels/__deployment_readiness_probe_not_found__.mp4"
                    probe_status, _, probe_error = request_bytes(sentinel, "HEAD")
                    if probe_error:
                        report.failed("Supabase public MP4 URL", f"network error ({probe_error})")
                    elif probe_status == 404 and bucket.get("public") is True:
                        report.passed("Supabase public MP4 URL", "public object route responds as expected (HTTP 404 for a non-existent probe)")
                        report.warned("Supabase sample MP4", "no existing reels/*.mp4 object was available to verify real file bytes")
                    else:
                        report.failed("Supabase public MP4 URL", f"non-existent probe returned HTTP {probe_status}; expected HTTP 404")
        else:
            report.failed("Supabase REELS bucket", f"bucket lookup returned HTTP {status if status is not None else 'no response'}")

    meta_token = os.environ.get("META_SYSTEM_USER_TOKEN", "").strip()
    if meta_token:
        url = f"https://graph.facebook.com/{GRAPH_VERSION}/me/accounts"
        fields = "id,name,tasks,instagram_business_account{id,username}"
        url += "?" + urllib.parse.urlencode({"fields": fields, "access_token": meta_token})
        status, parsed, error = json_request(url)
        if error:
            report.failed("Meta linked Instagram", f"network error ({error})")
        elif status == 200 and isinstance(parsed, dict) and isinstance(parsed.get("data"), list):
            pages = parsed["data"]
            links = []
            for page in pages:
                if not isinstance(page, dict):
                    continue
                ig = page.get("instagram_business_account")
                if isinstance(ig, dict) and ig.get("id"):
                    links.append((str(page.get("name") or ""), str(ig.get("username") or ""), str(ig.get("id"))))
            match = next((item for item in links if item[1].lower() == "bullseye_theory"), None)
            if match:
                report.passed("Meta linked Instagram", f"@{match[1]} is linked to Page '{match[0]}' (account ID present)")
            elif links:
                report.failed("Meta linked Instagram", f"token sees {len(links)} linked professional account(s), but @bullseye_theory was not found")
            else:
                report.failed("Meta linked Instagram", "no linked Instagram professional account was returned; check Page assignment and token permissions")
        else:
            report.failed("Meta linked Instagram", f"Graph API returned HTTP {status if status is not None else 'no response'}; token/permissions may be invalid")

    image_base = os.environ.get("IMAGE_BASE_URL", "").strip()
    gh_user = os.environ.get("GH_USER", "").strip()
    gh_repo = os.environ.get("GH_REPO", "").strip()
    if image_base or (gh_user and gh_repo):
        report.passed("Image URL configuration", "IMAGE_BASE_URL or GH_USER/GH_REPO is configured")
    else:
        report.failed("Image URL configuration", "set IMAGE_BASE_URL or both GH_USER and GH_REPO")
    repository = os.environ.get("GITHUB_REPOSITORY", "").strip() or (
        f"{gh_user}/{gh_repo}" if gh_user and gh_repo else ""
    )
    if repository:
        paths, tree_error = committed_card_paths(repository, os.environ.get("GITHUB_TOKEN", "").strip())
        if tree_error:
            report.failed("Committed card lookup", tree_error)
        elif not paths:
            report.failed("Committed card lookup", "no committed image card found under output/")
        else:
            url, source = image_url_for_card(paths[0])
            if not url:
                report.failed("Committed card URL", source)
            else:
                probe_status, _, probe_error = request_bytes(url, "HEAD")
                if probe_error:
                    report.failed("Committed card URL", f"network error ({probe_error})")
                elif probe_status == 200:
                    report.passed("Committed card URL", f"{source} card URL returns HTTP 200 ({paths[0]})")
                else:
                    report.failed("Committed card URL", f"{source} card URL returned HTTP {probe_status} ({paths[0]})")
    else:
        report.failed("Committed card lookup", "GITHUB_REPOSITORY is unavailable and GH_USER/GH_REPO were not both set")

    return report.exit_code()


if __name__ == "__main__":
    raise SystemExit(run_checks())
