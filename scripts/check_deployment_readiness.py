#!/usr/bin/env python3
"""Read-only readiness checks for the Telegram-only Bullseye content pipeline."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT = 15
CHANNEL = os.getenv("TELEGRAM_CHANNEL", "@bullseye_theory").strip() or "@bullseye_theory"


class Report:
    def __init__(self):
        self.failures = 0
        self.warnings = 0
        self.checks = 0

    def emit(self, level: str, name: str, reason: str):
        self.checks += 1
        if level == "FAIL":
            self.failures += 1
        elif level == "WARN":
            self.warnings += 1
        print(f"{level} | {name} | {reason}")

    def passed(self, name: str, reason: str):
        self.emit("PASS", name, reason)

    def failed(self, name: str, reason: str):
        self.emit("FAIL", name, reason)

    def warned(self, name: str, reason: str):
        self.emit("WARN", name, reason)

    def exit_code(self) -> int:
        print(f"SUMMARY | checks={self.checks} failures={self.failures} warnings={self.warnings}")
        return 1 if self.failures else 0


def api(token: str, method: str, payload: dict | None = None):
    query = urllib.parse.urlencode(payload or {})
    url = f"https://api.telegram.org/bot{token}/{method}"
    if query and method in {"getChat", "getChatMember", "getMe"}:
        url += "?" + query
    request_obj = urllib.request.Request(url, method="GET" if method.startswith("get") else "POST",
                                         data=None if method.startswith("get") else query.encode())
    try:
        with urllib.request.urlopen(request_obj, timeout=TIMEOUT) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Telegram API returned HTTP {exc.code}; response redacted.") from None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise RuntimeError(f"Telegram API request failed ({type(exc).__name__}); values redacted.") from None
    if not isinstance(result, dict) or not result.get("ok"):
        raise RuntimeError("Telegram API returned an unsuccessful response; details redacted.")
    return result.get("result")


def request_json(url: str, method: str = "GET", headers: dict | None = None,
                 payload: dict | None = None):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request_headers = dict(headers or {})
    if payload is not None:
        request_headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            raw = response.read()
            return response.status, json.loads(raw.decode("utf-8")) if raw else None
    except urllib.error.HTTPError as exc:
        return exc.code, None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise RuntimeError(f"Service request failed ({type(exc).__name__}); details redacted.") from None


def run_checks() -> int:
    report = Report()
    required = ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
                "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")
    for name in required:
        if os.environ.get(name, "").strip():
            report.passed(f"env:{name}", "configured; value hidden")
        else:
            report.failed(f"env:{name}", "missing GitHub Actions secret")
    if os.environ.get("TELEGRAM_APPROVER_USER_IDS", "").strip():
        report.passed("env:TELEGRAM_APPROVER_USER_IDS", "configured; value hidden")
    else:
        report.warned("env:TELEGRAM_APPROVER_USER_IDS", "unset; private owner chat fallback is used")

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if token:
        try:
            me = api(token, "getMe") or {}
            bot_id = str(me.get("id") or "")
            if not bot_id:
                raise RuntimeError("Telegram bot identity was not returned.")
            report.passed("Telegram bot identity", "getMe succeeded")
            chat = api(token, "getChat", {"chat_id": CHANNEL}) or {}
            if str(chat.get("type", "")) != "channel":
                raise RuntimeError("Configured Telegram destination is not a channel.")
            report.passed("Telegram channel access", f"getChat {CHANNEL} succeeded")
            member = api(token, "getChatMember", {"chat_id": CHANNEL, "user_id": bot_id}) or {}
            status = str(member.get("status", ""))
            if status == "creator" or (status == "administrator" and member.get("can_post_messages") is True):
                report.passed("Telegram channel permissions", "bot can post")
            else:
                report.failed("Telegram channel permissions", "bot must be channel administrator with post permission")
            owner_chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
            owner = api(token, "getChat", {"chat_id": owner_chat}) or {}
            if owner:
                report.passed("Private approval chat", "configured owner chat is reachable")
            else:
                report.failed("Private approval chat", "configured owner chat is not reachable")
        except RuntimeError as exc:
            report.failed("Telegram readiness", str(exc))

    base = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if base and key:
        headers = {"Authorization": f"Bearer {key}", "apikey": key}
        status, bucket = request_json(f"{base}/storage/v1/bucket/REELS", headers=headers)
        if status == 200 and isinstance(bucket, dict):
            report.passed("Supabase REELS bucket", "bucket exists")
            if bucket.get("public") is True:
                report.passed("Supabase public media", "REELS is public-read for Telegram video fetch")
            else:
                report.failed("Supabase public media", "REELS must be public-read for Telegram video URL fetch")
            list_status, objects = request_json(
                f"{base}/storage/v1/object/list/REELS", method="POST", headers=headers,
                payload={"prefix": "reels", "limit": 20, "offset": 0,
                         "sortBy": {"column": "created_at", "order": "desc"}},
            )
            if list_status == 200 and isinstance(objects, list):
                if any(str(item.get("name", "")).lower().endswith(".mp4") for item in objects if isinstance(item, dict)):
                    report.passed("Supabase Reel media", "existing MP4 object found")
                else:
                    report.warned("Supabase Reel media", "no MP4 object found yet; next Reel run will create one")
            else:
                report.failed("Supabase Reel media", f"Storage listing returned HTTP {list_status}")
        else:
            report.failed("Supabase REELS bucket", f"bucket lookup returned HTTP {status}")

    return report.exit_code()


if __name__ == "__main__":
    raise SystemExit(run_checks())
