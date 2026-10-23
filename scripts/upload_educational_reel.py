#!/usr/bin/env python3
"""Upload the exact rendered educational Reel to Supabase and verify public bytes."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUTPUT_DIR = Path("output")
BUCKET = "REELS"


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def save_json(path, data):
    path = Path(path)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)


def probe_duration(path: Path) -> float:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            check=True, capture_output=True, text=True, timeout=30,
        )
        duration = float(result.stdout.strip())
    except Exception as exc:
        raise RuntimeError(f"ffprobe could not validate the generated Reel ({type(exc).__name__}).") from None
    if duration <= 0:
        raise RuntimeError("ffprobe reported a non-positive Reel duration.")
    return duration


def sha256_and_size(path: Path):
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def expected_public_url(supabase_url: str, content_id: str) -> str:
    return (
        f"{supabase_url.rstrip('/')}/storage/v1/object/public/{BUCKET}/reels/"
        f"{urllib.parse.quote(content_id, safe='')}.mp4"
    )


def verify_public_video(url: str, sha256: str, size_bytes: int, duration_seconds: float):
    digest = hashlib.sha256()
    actual_size = 0
    temp_path = None
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=180) as response:
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp:
                temp_path = Path(temp.name)
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    digest.update(chunk)
                    actual_size += len(chunk)
                    temp.write(chunk)
    except urllib.error.HTTPError as exc:
        # Supabase Storage can return structured JSON for configuration and path
        # errors. Include only its short message/code (never request headers or URLs)
        # so the next failed run identifies the real cause without leaking secrets.
        try:
            payload = json.loads(exc.read().decode("utf-8", errors="replace"))
            detail = str(payload.get("message") or payload.get("error") or payload.get("statusCode") or "")
        except Exception:
            detail = ""
        detail = " ".join(detail.split())[:180]
        if exc.code == 404 or (exc.code == 400 and any(
            marker in detail.lower() for marker in ("object not found", "resource not found", "not found")
        )):
            raise FileNotFoundError("Supabase public object not found yet.") from None
        suffix = f" ({detail})" if detail else ""
        raise RuntimeError(f"Supabase public video verification returned HTTP {exc.code}{suffix}.") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not verify Supabase public video ({type(exc).__name__}).") from None

    try:
        if actual_size != size_bytes or digest.hexdigest() != sha256:
            raise RuntimeError("Supabase public object bytes do not match generated MP4 SHA-256/size.")
        actual_duration = probe_duration(temp_path)
        if abs(actual_duration - duration_seconds) > 0.75:
            raise RuntimeError(
                f"Supabase public object duration mismatch (expected {duration_seconds:.2f}s, got {actual_duration:.2f}s)."
            )
    finally:
        if temp_path:
            temp_path.unlink(missing_ok=True)


def upload_object(upload_url: str, api_key: str, video_path: Path):
    request_obj = urllib.request.Request(
        upload_url,
        data=video_path.read_bytes(),
        method="PUT",
        headers={
            "Authorization": f"Bearer {api_key}",
            "apikey": api_key,
            "Content-Type": "video/mp4",
            "x-upsert": "false",
        },
    )
    try:
        with urllib.request.urlopen(request_obj, timeout=180) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 409:
            return
        try:
            payload = json.loads(exc.read().decode("utf-8", errors="replace"))
            detail = str(payload.get("message") or payload.get("error") or payload.get("statusCode") or "")
        except Exception:
            detail = ""
        detail = " ".join(detail.split())[:180]
        suffix = f" ({detail})" if detail else ""
        raise RuntimeError(f"Supabase MP4 upload failed HTTP {exc.code}{suffix}; credentials redacted.") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Supabase MP4 upload failed ({type(exc).__name__}); credentials redacted.") from None


def upload_latest_draft():
    supabase_url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    api_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not supabase_url or not api_key:
        raise SystemExit("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for durable MP4 handoff.")

    candidates = []
    for path in OUTPUT_DIR.glob("draft_*.json"):
        if path.name == "draft_seed.json":
            continue
        record = load_json(path)
        if isinstance(record, dict) and record.get("content_id") == path.stem:
            candidates.append((path, record))
    if not candidates:
        raise SystemExit("No matching output/draft_<content_id>.json metadata found.")
    metadata_path, record = max(candidates, key=lambda item: item[0].stat().st_mtime)
    content_id = str(record.get("content_id", "")).strip()
    if not content_id or metadata_path.stem != content_id:
        raise SystemExit("Draft metadata content_id/filename mismatch.")
    if record.get("status") in {"approved_for_publishing", "published_to_instagram", "published", "rejected"}:
        raise SystemExit("Refusing to replace media for an already decided/published draft.")

    video_path = Path(str(record.get("video") or (OUTPUT_DIR / "media" / f"{content_id}.mp4")))
    if not video_path.is_file() or video_path.stat().st_size <= 0:
        video_path = OUTPUT_DIR / "media" / f"{content_id}.mp4"
    if not video_path.is_file() or video_path.stat().st_size <= 0:
        raise SystemExit(f"Matching non-empty MP4 missing for {content_id}.")

    sha256, size_bytes = sha256_and_size(video_path)
    duration_seconds = probe_duration(video_path)
    public_url = expected_public_url(supabase_url, content_id)
    existing_url = str(record.get("video_url", "")).strip()
    if existing_url and existing_url != public_url:
        raise SystemExit("Existing video_url does not match this content_id's Supabase object path.")

    object_path = f"reels/{content_id}.mp4"
    upload_url = f"{supabase_url}/storage/v1/object/{BUCKET}/{urllib.parse.quote(object_path, safe='/')}"
    try:
        verify_public_video(public_url, sha256, size_bytes, duration_seconds)
        print(f"Reusing byte-identical Supabase object for {content_id}.")
    except FileNotFoundError:
        upload_object(upload_url, api_key, video_path)
        verify_public_video(public_url, sha256, size_bytes, duration_seconds)
        print(f"Uploaded and verified exact MP4 object for {content_id}.")

    record.update({
        "video_url": public_url,
        "video_content_id": content_id,
        "video_sha256": sha256,
        "video_size_bytes": size_bytes,
        "video_duration_seconds": duration_seconds,
        "video_uploaded_at": datetime.now(timezone.utc).isoformat(),
    })
    save_json(metadata_path, record)
    print(f"Saved verified public video URL and integrity metadata for {content_id}; no public post was made.")


if __name__ == "__main__":
    upload_latest_draft()
