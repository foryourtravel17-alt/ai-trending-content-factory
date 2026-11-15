#!/usr/bin/env python3
"""Upload generated market-card PNGs to the existing public Supabase REELS bucket.

The repository can remain private: only the deliberately public social-media assets
are exposed through Supabase Storage. Every uploaded object is fetched back and
SHA-256/size checked before its URL is written to market state.
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BUCKET = "REELS"
SAFE_ID = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")


def _sha256_and_size(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _public_url(base_url: str, object_path: str) -> str:
    encoded = urllib.parse.quote(object_path, safe="/")
    return f"{base_url.rstrip('/')}/storage/v1/object/public/{BUCKET}/{encoded}"


def _verify_public_object(url: str, expected_hash: str, expected_size: int) -> None:
    digest = hashlib.sha256()
    actual_size = 0
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                actual_size += len(chunk)
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Supabase market-card public URL could not be verified ({type(exc).__name__}); credentials redacted."
        ) from None
    if actual_size != expected_size or digest.hexdigest() != expected_hash:
        raise RuntimeError("Supabase market-card public bytes failed SHA-256/size verification.")


def _upload(path: Path, url: str, api_key: str) -> None:
    request = urllib.request.Request(
        url,
        data=path.read_bytes(),
        method="PUT",
        headers={
            "Authorization": f"Bearer {api_key}",
            "apikey": api_key,
            "Content-Type": "image/png",
            "x-upsert": "false",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 409:
            # Deterministic object path already exists; the GET/hash check below
            # decides whether it is safe to reuse.
            return
        raise RuntimeError(
            f"Supabase market-card upload failed with HTTP {exc.code}; credentials redacted."
        ) from None
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Supabase market-card upload failed ({type(exc).__name__}); credentials redacted."
        ) from None


def upload_market_cards(
    state_path: Path = Path("data/state.json"),
    output_dir: Path = Path("output"),
) -> int:
    base_url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    api_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not base_url or not api_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for public market-card hosting.")

    try:
        state = json.loads(Path(state_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not read market state ({type(exc).__name__}).") from None
    if not isinstance(state, dict) or not isinstance(state.get("signals"), dict):
        raise RuntimeError("data/state.json has an unsupported signals format.")

    root = Path(output_dir).resolve()
    uploaded = 0
    for record_id, record in state["signals"].items():
        if not isinstance(record, dict) or record.get("content_type") == "educational_reel":
            continue
        if record.get("status") != "generated" or not isinstance(record.get("signal"), dict):
            continue
        signal_id = str(record["signal"].get("signal_id") or record_id).strip()
        if not signal_id or any(char not in SAFE_ID for char in signal_id):
            raise RuntimeError(f"Market signal has an unsafe ID: {record_id!r}.")
        card_path = Path(str(record.get("card_path") or "")).resolve()
        try:
            card_path.relative_to(root)
        except ValueError:
            raise RuntimeError(f"Market card path must stay inside output: {record_id}.") from None
        if card_path.suffix.lower() != ".png" or not card_path.is_file() or card_path.stat().st_size <= 0:
            raise RuntimeError(f"Generated market PNG is missing or empty: {record_id}.")
        sha256, size_bytes = _sha256_and_size(card_path)
        object_path = f"market-cards/{signal_id}.png"
        public_url = _public_url(base_url, object_path)
        upload_url = f"{base_url}/storage/v1/object/{BUCKET}/{urllib.parse.quote(object_path, safe='/')}"
        _upload(card_path, upload_url, api_key)
        _verify_public_object(public_url, sha256, size_bytes)
        record.update({
            "image_url": public_url,
            "image_sha256": sha256,
            "image_size_bytes": size_bytes,
            "image_storage": "supabase_public_reels",
        })
        uploaded += 1

    temp = Path(state_path).with_suffix(Path(state_path).suffix + ".tmp")
    temp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(state_path)
    print(f"Uploaded and verified {uploaded} market card(s) in Supabase public storage; no post was published.")
    return uploaded


if __name__ == "__main__":
    upload_market_cards()
