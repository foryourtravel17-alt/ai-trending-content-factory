"""Alert only when the market-content workflow has no recent successful run."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def request_json(url: str, token: str) -> dict:
    req = Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise RuntimeError(f"GitHub Actions status query failed ({type(exc).__name__}).") from None


def send_alert(token: str, chat_id: str, message: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urlencode({"chat_id": chat_id, "text": message}).encode()
    req = Request(url, data=data, method="POST")
    try:
        with urlopen(req, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise RuntimeError(f"Telegram stall alert failed ({type(exc).__name__}); credentials redacted.") from None
    if not payload.get("ok"):
        raise RuntimeError("Telegram rejected the market stall alert; response redacted.")


def main() -> int:
    github_token = os.getenv("GITHUB_TOKEN", "").strip()
    repository = os.getenv("GITHUB_REPOSITORY", "").strip()
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not all((github_token, repository, tg_token, chat_id)):
        print("Stall check requires GITHUB_TOKEN, GITHUB_REPOSITORY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID.")
        return 2

    query = urlencode({"branch": "main", "per_page": 20})
    url = f"https://api.github.com/repos/{repository}/actions/workflows/market_content.yml/runs?{query}"
    payload = request_json(url, github_token)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=8)
    recent_success = None
    for run in payload.get("workflow_runs", []):
        if run.get("status") != "completed" or run.get("conclusion") != "success":
            continue
        try:
            completed = datetime.fromisoformat(run["updated_at"].replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError):
            continue
        if completed >= cutoff:
            recent_success = run
            break

    if recent_success:
        print(f"Market workflow healthy: successful run {recent_success.get('id')} at {recent_success.get('updated_at')}. No alert sent.")
        return 0

    latest = payload.get("workflow_runs", [{}])[0] if payload.get("workflow_runs") else {}
    latest_url = latest.get("html_url", f"https://github.com/{repository}/actions/workflows/market_content.yml")
    latest_state = f"{latest.get('status', 'no run')} / {latest.get('conclusion', 'no conclusion')}"
    message = (
        "⚠️ Bullseye Theory market-content stall alert\n\n"
        "No successful Autonomous Market Content Factory run was recorded in the last 8 hours "
        "during the weekday monitoring window.\n"
        f"Latest run: {latest_state}\n"
        f"Open Actions: {latest_url}\n\n"
        "Check Yahoo Finance availability, GitHub Actions status, image hosting, and publishing secrets."
    )
    send_alert(tg_token, chat_id, message)
    print("Stall alert sent because no successful market workflow run was found in the last 8 hours.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
