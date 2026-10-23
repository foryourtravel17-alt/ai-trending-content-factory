"""Idempotent Telegram and Instagram publishing for generated signal cards."""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from urllib.parse import quote

import requests

log = logging.getLogger(__name__)
API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v23.0")
TELEGRAM_CHANNEL = os.getenv("TELEGRAM_CHANNEL", "@bullseye_theory")


def _first_configured_env(names: tuple[str, ...]) -> tuple[str, str]:
    """Return a configured value and its variable name without logging the value."""
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value, name
    return "", ""


def _safe_meta_label(value: object) -> str:
    """Keep Meta error identifiers useful while excluding arbitrary response text."""
    raw = str(value) if value is not None else "unknown"
    safe = "".join(char for char in raw if char.isalnum() or char in "._-")
    return safe[:64] or "unknown"


def public_image_url(image_path: Path) -> str:
    gh_user = os.getenv("GH_USER", "").strip()
    gh_repo = os.getenv("GH_REPO", "").strip()
    custom_base = os.getenv("IMAGE_BASE_URL", "").strip().rstrip("/")
    if custom_base:
        return f"{custom_base}/{quote(image_path.name)}"
    if gh_user and gh_repo:
        return f"https://{gh_user}.github.io/{gh_repo}/output/{quote(image_path.name)}"
    repository = os.getenv("GITHUB_REPOSITORY", "").strip()
    if repository:
        owner, separator, repo = repository.partition("/")
        if separator:
            return f"https://{owner}.github.io/{repo}/output/{quote(image_path.name)}"
        return f"https://raw.githubusercontent.com/{repository}/main/output/{quote(image_path.name)}"
    raise RuntimeError("Set GITHUB_REPOSITORY, GH_USER/GH_REPO, or IMAGE_BASE_URL to create a public image URL.")


def _accessible_image_url(image_path: Path) -> str:
    """Prefer GitHub Pages; fall back to raw GitHub if Pages is not deployed yet."""
    gh_user = os.getenv("GH_USER", "").strip()
    gh_repo = os.getenv("GH_REPO", "").strip()
    custom_base = os.getenv("IMAGE_BASE_URL", "").strip().rstrip("/")
    candidates = []
    if custom_base:
        candidates.append(f"{custom_base}/{quote(image_path.name)}")
    if gh_user and gh_repo:
        candidates.append(f"https://{gh_user}.github.io/{gh_repo}/output/{quote(image_path.name)}")
    repository = os.getenv("GITHUB_REPOSITORY", "").strip()
    if repository:
        owner, separator, repo = repository.partition("/")
        if separator:
            pages_candidate = f"https://{owner}.github.io/{repo}/output/{quote(image_path.name)}"
            if pages_candidate not in candidates:
                candidates.append(pages_candidate)
        raw_candidate = f"https://raw.githubusercontent.com/{repository}/main/output/{quote(image_path.name)}"
        if raw_candidate not in candidates:
            candidates.append(raw_candidate)
    if not candidates:
        raise RuntimeError("Set GH_USER and GH_REPO, or IMAGE_BASE_URL, to create a public image URL.")
    for candidate in candidates:
        try:
            response = requests.head(candidate, allow_redirects=True, timeout=12)
            if response.status_code == 200:
                log.info("Public image URL verified: %s", candidate)
                return candidate
            log.warning("Image URL not ready (%s): %s", response.status_code, candidate)
        except requests.RequestException as exc:
            log.warning("Could not verify image URL (%s).", type(exc).__name__)
    raise RuntimeError("Generated card is not publicly reachable. Enable GitHub Pages or check the raw GitHub URL.")


def _telegram(method: str, data: dict, files: dict | None = None) -> dict:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured.")
    try:
        response = requests.post(f"https://api.telegram.org/bot{token}/{method}", data=data, files=files, timeout=45)
    except requests.RequestException as exc:
        raise RuntimeError(f"Telegram {method} request failed ({type(exc).__name__}); bot token redacted.") from None
    if not response.ok:
        raise RuntimeError(f"Telegram {method} failed with HTTP {response.status_code}; response redacted.")
    try:
        body = response.json()
    except ValueError:
        raise RuntimeError(f"Telegram {method} returned invalid JSON; response redacted.") from None
    if not body.get("ok"):
        raise RuntimeError(f"Telegram {method} failed: {body.get('description', 'unknown error')}")
    return body["result"]


def _meta_request(method: str, url: str, **kwargs):
    """Call Meta without leaking tokens; preserve safe error identifiers for diagnosis."""
    try:
        response = requests.request(method, url, **kwargs)
    except requests.RequestException as exc:
        raise RuntimeError(f"Meta API request failed ({type(exc).__name__}); credentials redacted.") from None
    try:
        body = response.json()
    except ValueError:
        if not response.ok:
            raise RuntimeError(f"Meta API HTTP {response.status_code}; non-JSON error response (credentials redacted).") from None
        raise RuntimeError("Meta API returned invalid JSON; credentials redacted.") from None
    if not response.ok:
        error = body.get("error") if isinstance(body, dict) else {}
        error = error if isinstance(error, dict) else {}
        code = _safe_meta_label(error.get("code"))
        subcode = _safe_meta_label(error.get("error_subcode"))
        error_type = _safe_meta_label(error.get("type"))
        # Meta's user-facing message can contain identifiers or request details; don't log it.
        raise RuntimeError(
            f"Meta API HTTP {response.status_code}; code={code}, subcode={subcode}, "
            f"type={error_type}; message redacted, credentials protected."
        )
    return body


def _resolve_linked_instagram_user_id(token: str) -> tuple[str, str]:
    """Resolve the Instagram account linked to the Bullseye Theory Page.

    The account ID secret can become stale when Meta assets are re-linked. Resolve
    from the System User's assigned Page instead of publishing to an arbitrary ID.
    """
    result = _meta_request(
        "GET", f"https://graph.facebook.com/{API_VERSION}/me/accounts",
        params={
            "fields": "id,name,access_token,instagram_business_account{id,username}",
            "access_token": token,
        }, timeout=30,
    )
    pages = result.get("data") if isinstance(result, dict) else []
    eligible = [
        page for page in (pages or [])
        if isinstance(page, dict)
        and str(page.get("name", "")).strip().casefold() == "bullseye theory"
        and isinstance(page.get("instagram_business_account"), dict)
        and str(page["instagram_business_account"].get("id", "")).strip()
    ]
    if len(eligible) != 1:
        raise RuntimeError(
            "Instagram account resolution failed: expected exactly one assigned Page named "
            "'Bullseye Theory' with a linked Instagram professional account."
        )
    page = eligible[0]
    account = page["instagram_business_account"]
    page_token = str(page.get("access_token") or "").strip()
    account_id = str(account.get("id") or "").strip()
    if not page_token or not account_id:
        raise RuntimeError("Bullseye Theory Page did not provide a Page token and linked Instagram account ID.")
    return account_id, page_token


def _instagram_publish(
    image_url: str,
    caption: str,
    publish_state: dict | None = None,
) -> str:
    """Publish an Instagram image, reusing a persisted container on retries.

    The creation ID is stored before media_publish is attempted. If Meta accepts
    a publish request but the response is lost or fails, a retry must not create
    a fresh container and risk duplicating the post.
    """
    state = publish_state if isinstance(publish_state, dict) else {}
    token, token_source = _first_configured_env(
        ("META_SYSTEM_USER_TOKEN", "INSTAGRAM_ACCESS_TOKEN", "IG_ACCESS_TOKEN")
    )
    configured_user_id, user_id_source = _first_configured_env(
        ("IG_USER_ID", "INSTAGRAM_USER_ID")
    )
    log.info(
        "Instagram credential source: token=%s; account ID resolved from linked Page",
        token_source or "none",
    )
    if not token:
        raise RuntimeError("Instagram publishing token is not configured.")
    user_id, page_token = _resolve_linked_instagram_user_id(token)
    if configured_user_id and configured_user_id != user_id:
        log.warning(
            "Configured Instagram account ID secret is stale; using the account linked to the exact Bullseye Theory Page. "
            "The configured value is not logged."
        )

    api = f"https://graph.facebook.com/{API_VERSION}/{user_id}"
    creation_id = str(state.get("creation_id") or "").strip()
    if not creation_id:
        container = _meta_request("POST", f"{api}/media", data={
            "image_url": image_url, "caption": caption[:2200], "access_token": page_token,
        }, timeout=60)
        creation_id = str(container.get("id") or "").strip()
        if not creation_id:
            raise RuntimeError("Instagram media container response had no id.")
        # Persist the ID in the record before any publish request can fail.
        state["creation_id"] = creation_id
        log.info("Created Instagram media container and retained its ID for safe retries.")
    else:
        log.info("Reusing retained Instagram media container for retry; no new container will be created.")

    finished = False
    for attempt in range(6):
        status = _meta_request(
            "GET", f"https://graph.facebook.com/{API_VERSION}/{creation_id}",
            params={"fields": "status_code", "access_token": page_token}, timeout=30,
        )
        code = status.get("status_code")
        if code in {"ERROR", "EXPIRED"}:
            raise RuntimeError(
                f"Instagram image container entered {code} status; "
                "container retained for manual reconciliation."
            )
        if code in (None, "FINISHED"):
            finished = True
            break
        if attempt < 5:
            time.sleep(5)
    if not finished:
        raise RuntimeError(
            "Instagram image container did not reach FINISHED status after six checks; "
            "container retained for safe retry."
        )

    published = _meta_request("POST", f"{api}/media_publish", data={
        "creation_id": creation_id, "access_token": page_token,
    }, timeout=60)
    media_id = published.get("id")
    if not media_id:
        raise RuntimeError(
            "Instagram publish response had no media id; the existing container is retained."
        )
    return str(media_id)

def publish(signal: dict, copy: dict, card_path: Path, record: dict, dry_run: bool = False) -> dict:
    """Publish one signal; each platform is isolated and successful posts are never repeated."""
    record.setdefault("publishing", {})
    platforms = record["publishing"]
    if dry_run:
        log.info("DRY_RUN: not posting %s to Telegram or Instagram.", signal["signal_id"])
        record["status"] = "generated"
        record["last_run_mode"] = "dry_run"
        return record

    human_approval = os.getenv("HUMAN_APPROVAL", "false").strip().lower() == "true"
    approval_status = str(record.get("approval_status", "")).strip().lower()
    if approval_status == "rejected":
        record["status"] = "rejected"
        log.info("Rejected record %s is blocked from public publishing.", signal["signal_id"])
        return record

    # A pending record needs a DM; an explicitly approved record must continue
    # through public publishing even though this poller retains HUMAN_APPROVAL=true.
    awaiting_decision = human_approval and approval_status != "approved"
    image_url = record.get("image_url")
    telegram_caption = copy["telegram_html"][:1000]
    if awaiting_decision:
        if platforms.get("telegram_dm", {}).get("status") != "sent":
            chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
            if not chat_id:
                raise RuntimeError("HUMAN_APPROVAL=true requires TELEGRAM_CHAT_ID for draft delivery.")
            keyboard = {"inline_keyboard": [[
                {"text": "✅ APPROVE & PUBLISH", "callback_data": f"market_approve:{signal['signal_id']}"},
                {"text": "❌ REJECT", "callback_data": f"market_reject:{signal['signal_id']}"},
            ]]}
            with card_path.open("rb") as photo:
                result = _telegram("sendPhoto", {
                    "chat_id": chat_id,
                    "caption": ("📝 DRAFT — choose approve or reject\n\n" + telegram_caption)[:1024],
                    "parse_mode": "HTML",
                    "reply_markup": json.dumps(keyboard, separators=(",", ":")),
                }, files={"photo": photo})
            platforms["telegram_dm"] = {"status": "sent", "message_id": result.get("message_id")}
            log.info("Draft sent to Telegram DM for %s; waiting for button approval.", signal["signal_id"])
        record["status"] = "pending_approval"
        return record

    errors = []
    instagram_only_retry = os.getenv("MARKET_RETRY_INSTAGRAM_ONLY", "false").strip().lower() == "true"
    if instagram_only_retry:
        if platforms.get("telegram", {}).get("status") != "published":
            raise RuntimeError("Instagram-only retry blocked: Telegram is not already marked published.")
        log.info("Instagram-only retry enabled; Telegram publishing is deliberately skipped.")
    elif platforms.get("telegram", {}).get("status") != "published":
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        if token:
            try:
                with card_path.open("rb") as photo:
                    result = _telegram("sendPhoto", {
                        "chat_id": TELEGRAM_CHANNEL,
                        "caption": telegram_caption, "parse_mode": "HTML",
                    }, files={"photo": photo})
                platforms["telegram"] = {"status": "published", "message_id": result.get("message_id")}
                log.info("Telegram published %s (message %s).", signal["signal_id"], result.get("message_id"))
            except Exception as exc:
                platforms["telegram"] = {"status": "failed", "error": str(exc)[:300]}
                errors.append(f"Telegram: {exc}")
                log.error("Telegram publish failed for %s; still attempting Instagram: %s", signal["signal_id"], exc)
        else:
            message = "TELEGRAM_BOT_TOKEN is not configured."
            platforms["telegram"] = {"status": "failed", "error": message}
            errors.append(f"Telegram: {message}")
            log.error("Telegram publishing cannot run because its bot token is missing.")
    if platforms.get("instagram", {}).get("status") != "published":
        token, token_source = _first_configured_env(
            ("META_SYSTEM_USER_TOKEN", "INSTAGRAM_ACCESS_TOKEN", "IG_ACCESS_TOKEN")
        )
        user_id, user_id_source = _first_configured_env(
            ("IG_USER_ID", "INSTAGRAM_USER_ID")
        )
        log.info(
            "Instagram credential source: token=%s; account ID will be resolved from linked Page",
            token_source or "none",
        )
        instagram_state = platforms.setdefault("instagram", {})
        if token:
            try:
                image_url = _accessible_image_url(card_path)
                media_id = _instagram_publish(
                    image_url, copy["instagram_caption"], instagram_state
                )
                instagram_state.update({"status": "published", "media_id": media_id})
                instagram_state.pop("error", None)
                log.info("Instagram published %s (media %s).", signal["signal_id"], media_id)
            except Exception as exc:
                # Keep creation_id: ambiguous publish errors must retry the same container.
                instagram_state["status"] = "failed"
                instagram_state["error"] = str(exc)[:300]
                errors.append(f"Instagram: {exc}")
                log.error("Instagram publish failed for %s: %s", signal["signal_id"], exc)
        else:
            message = f"Instagram publishing token missing (source={token_source or 'none'})."
            instagram_state["status"] = "failed"
            instagram_state["error"] = message
            errors.append(f"Instagram: {message}")
            log.error("%s", message)
    statuses = [platforms.get(k, {}).get("status") for k in ("telegram", "instagram")]
    if all(status == "published" for status in statuses):
        record["status"] = "published"
    elif "published" in statuses:
        record["status"] = "partial"
    elif errors:
        record["status"] = "publish_failed"
    else:
        record["status"] = "generated"
    record["image_url"] = image_url
    if errors:
        raise RuntimeError("One or more publishing platforms failed: " + " | ".join(errors))
    return record
