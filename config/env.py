"""Canonical environment-variable resolution for both Bullseye pipelines."""
from __future__ import annotations
import os

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

def content_is_approved(content: dict) -> bool:
    if human_approval_required():
        approval = content.get("approval") or {}
        return (approval.get("required") is True and approval.get("status") == "approved"
                and content.get("status") == "approved_for_publishing"
                and bool(approval.get("version")) and bool(approval.get("content_hash")))
    fact = (content.get("fact_check") or {}).get("status")
    safety = (content.get("safety_check") or {}).get("passed") is True
    return fact in {"passed", "verified", "approved"} and safety
