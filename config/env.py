"""Canonical environment-variable resolution for both Bullseye pipelines."""
from __future__ import annotations
import os
import hashlib
import json
from datetime import datetime, timezone, timedelta

def first_nonempty(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return default

def instagram_user_id() -> str:
    return first_nonempty("IG_USER_ID", "INSTAGRAM_USER_ID")

def instagram_access_token() -> str:
    return first_nonempty("IG_ACCESS_TOKEN", "META_SYSTEM_USER_TOKEN", "INSTAGRAM_ACCESS_TOKEN")

def human_approval_required() -> bool:
    """Fail closed: unset or ambiguous values require human approval."""
    value = os.getenv("HUMAN_APPROVAL", "").strip().lower()
    return value not in {"false", "0", "no", "off"}

def approval_hash(content: dict) -> str:
    basis = {
        "content_id": content.get("content_id"),
        "version": content.get("content_version", 1),
        "created_at": content.get("created_at"),
        "title": (content.get("topic") or {}).get("title"),
        "hook": (content.get("script") or {}).get("hook"),
        "body": (content.get("script") or {}).get("body"),
    }
    return hashlib.sha256(json.dumps(basis, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()



def is_content_fresh(created_at: str, max_age_hours: int = 24, now: datetime | None = None) -> bool:
    try:
        created = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        age = current.astimezone(timezone.utc) - created.astimezone(timezone.utc)
        return timedelta(0) <= age <= timedelta(hours=max_age_hours)
    except (TypeError, ValueError):
        return False


def content_is_approved(content: dict) -> bool:
    fact = (content.get("fact_check") or {}).get("status")
    safety = (content.get("safety_check") or {}).get("passed") is True
    if content.get("status") != "approved_for_publishing":
        return False
    if fact not in {"passed", "verified", "approved"} or not safety:
        return False
    if human_approval_required():
        approval = content.get("approval") or {}
        try:
            version_matches = int(approval.get("version", 0)) == int(content.get("content_version", 1))
        except (TypeError, ValueError):
            version_matches = False
        return (
            approval.get("required") is True
            and approval.get("status") == "approved"
            and content.get("status") == "approved_for_publishing"
            and version_matches
            and approval.get("content_hash") == approval_hash(content)
        )
    return True
