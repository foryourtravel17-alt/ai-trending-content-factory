#!/usr/bin/env python3
"""Read-only diagnostic for the configured Telegram Premium destination.

This script uses getMe, getChat, and getChatMember only. It never sends a
Telegram message and never prints the bot token or configured chat ID.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

API_BASE = "https://api.telegram.org"
_SIGNED_INTEGER = re.compile(r"^-?\d+$")
_CHANNEL_STYLE = re.compile(r"^-100\d+$")


def describe_chat_id(chat_id: str) -> str:
    """Describe the configured chat ID's shape without printing its value."""
    problems = []
    if not _SIGNED_INTEGER.fullmatch(chat_id):
        problems.append("not_a_plain_signed_integer")
    if any(ord(char) > 127 for char in chat_id):
        problems.append("contains_non_ascii_char")
    if any(char in chat_id for char in ('"', "'")):
        problems.append("contains_quote")
    if any(char.isspace() for char in chat_id):
        problems.append("contains_inner_space")
    return (
        f"length={len(chat_id)} "
        f"leading_minus={chat_id.startswith('-')} "
        f"channel_or_supergroup_style={bool(_CHANNEL_STYLE.fullmatch(chat_id))} "
        f"problems={','.join(problems) if problems else 'none'}"
    )


def telegram_api(token: str, method: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    """Call a read-only Telegram Bot API method without exposing credentials."""
    url = f"{API_BASE}/bot{token}/{method}"
    body = urllib.parse.urlencode(params or {}).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8", errors="replace")).get("description", "HTTP error")
        except Exception:
            detail = "HTTP error"
        raise RuntimeError(f"Telegram {method} request failed (HTTP {exc.code}): {detail}") from None
    except urllib.error.URLError:
        raise RuntimeError(f"Telegram {method} request failed due to a network error") from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise RuntimeError(f"Telegram {method} returned an unreadable response") from None

    if not payload.get("ok"):
        detail = str(payload.get("description", "unspecified Telegram API error"))
        raise RuntimeError(f"Telegram {method} request failed: {detail}")
    return payload


def check_destination(token: str, chat_id: str) -> int:
    print("READ-ONLY TELEGRAM DESTINATION CHECK — no messages will be sent.")

    # Resolve and display bot identity first, even if the private destination lookup fails.
    try:
        me = telegram_api(token, "getMe")["result"]
        bot_id = int(me["id"])
        bot_username = me.get("username") or "(username not returned)"
    except (RuntimeError, KeyError, TypeError, ValueError) as exc:
        print(f"CHECK FAILED: bot token identity could not be verified: {exc}", file=sys.stderr)
        return 1

    printable_bot = f"@{bot_username}" if bot_username != "(username not returned)" else bot_username
    print(f"Bot token identifies: {printable_bot}")
    print(f"Configured chat ID fingerprint: {describe_chat_id(chat_id)}")

    try:
        chat = telegram_api(token, "getChat", {"chat_id": chat_id})["result"]
    except (RuntimeError, KeyError, TypeError, ValueError) as exc:
        print("CHECK FAILED: Telegram could not find the configured destination for this bot.", file=sys.stderr)
        print(f"Details: {exc}", file=sys.stderr)
        print("Most likely causes, in order:", file=sys.stderr)
        print(
            "  1. This exact bot is not a member/admin of the intended private Premium destination.",
            file=sys.stderr,
        )
        print(
            "  2. The configured ID is malformed (see the fingerprint), is a stale value from another secret scope, "
            "or points to a different destination.",
            file=sys.stderr,
        )
        print("No message was sent.", file=sys.stderr)
        return 1

    try:
        member = telegram_api(
            token,
            "getChatMember",
            {"chat_id": chat_id, "user_id": str(bot_id)},
        )["result"]
    except (RuntimeError, KeyError, TypeError, ValueError) as exc:
        print(f"CHECK FAILED: destination was found, but bot membership could not be verified: {exc}", file=sys.stderr)
        return 1

    chat_type = str(chat.get("type", "unknown"))
    status = str(member.get("status", "unknown"))
    if chat_type == "channel":
        can_publish = status == "creator" or (
            status == "administrator" and member.get("can_post_messages") is True
        )
        permission_detail = (
            "owner/creator" if status == "creator"
            else str(member.get("can_post_messages", "not reported"))
        )
    elif chat_type in {"group", "supergroup"}:
        if status in {"creator", "administrator"}:
            can_publish = True
            permission_detail = "administrator/creator"
        elif status == "restricted":
            can_publish = member.get("can_send_messages") is True
            permission_detail = str(member.get("can_send_messages", "not reported"))
        elif status == "member":
            permissions = chat.get("permissions") or {}
            can_publish = permissions.get("can_send_messages") is True
            permission_detail = str(permissions.get("can_send_messages", "not reported"))
        else:
            can_publish = False
            permission_detail = "bot is not an active member"
    else:
        can_publish = False
        permission_detail = "unsupported chat type"

    result = {
        "bot_username": printable_bot,
        "destination_title": chat.get("title") or chat.get("username") or "(no title returned)",
        "destination_type": chat_type,
        "bot_membership_status": status,
        "posting_permission": permission_detail,
        "ready_to_post": bool(can_publish),
        "messages_sent": 0,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not can_publish:
        print(
            "CHECK FAILED: the bot's membership or posting permission could not be confirmed. "
            "Do not enable scheduled publishing yet.",
            file=sys.stderr,
        )
        return 1
    print("CHECK PASSED: Telegram confirms the bot can post to this destination.")
    print("Confirm the destination title above is the intended private Premium destination before enabling auto-publishing.")
    return 0


def main() -> int:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("PREMIUM_TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print(
            "CHECK FAILED: TELEGRAM_BOT_TOKEN and PREMIUM_TELEGRAM_CHAT_ID must be configured. "
            "Secret values are never printed.",
            file=sys.stderr,
        )
        return 2
    return check_destination(token, chat_id)


if __name__ == "__main__":
    raise SystemExit(main())
