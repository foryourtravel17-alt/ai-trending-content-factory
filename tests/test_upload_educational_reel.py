import json
import os
import tempfile
import urllib.error
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import upload_educational_reel as MODULE


class UploadEducationalReelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.old_output = MODULE.OUTPUT_DIR
        MODULE.OUTPUT_DIR = self.root / "output"
        (MODULE.OUTPUT_DIR / "media").mkdir(parents=True)
        self.content_id = "draft_upload_test_20261022"
        self.video = MODULE.OUTPUT_DIR / "media" / f"{self.content_id}.mp4"
        self.video.write_bytes(b"test-video-bytes")
        self.metadata = MODULE.OUTPUT_DIR / f"{self.content_id}.json"
        self.metadata.write_text(json.dumps({
            "content_id": self.content_id,
            "status": "draft_only",
            "video": str(self.video),
        }), encoding="utf-8")
        self.env = patch.dict(os.environ, {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "fake-test-key",
        })
        self.env.start()

    def tearDown(self):
        self.env.stop()
        MODULE.OUTPUT_DIR = self.old_output
        self.temp.cleanup()

    def test_upload_records_url_hash_size_and_ffprobe_duration(self):
        with patch.object(MODULE, "probe_duration", return_value=42.29), \
             patch.object(MODULE, "verify_public_video", side_effect=[FileNotFoundError(), None]), \
             patch.object(MODULE, "upload_object") as upload:
            MODULE.upload_latest_draft()
        result = json.loads(self.metadata.read_text(encoding="utf-8"))
        self.assertEqual(result["video_content_id"], self.content_id)
        self.assertEqual(result["video_url"],
                         f"https://example.supabase.co/storage/v1/object/public/REELS/reels/{self.content_id}.mp4")
        self.assertEqual(result["video_size_bytes"], len(b"test-video-bytes"))
        self.assertEqual(result["video_duration_seconds"], 42.29)
        self.assertEqual(len(result["video_sha256"]), 64)
        upload.assert_called_once()

    def test_existing_public_object_is_reused_when_verified(self):
        with patch.object(MODULE, "probe_duration", return_value=42.29), \
             patch.object(MODULE, "verify_public_video", return_value=None), \
             patch.object(MODULE, "upload_object") as upload:
            MODULE.upload_latest_draft()
        upload.assert_not_called()

    def test_mismatched_existing_url_fails_closed(self):
        record = json.loads(self.metadata.read_text(encoding="utf-8"))
        record["video_url"] = "https://evil.invalid/wrong.mp4"
        self.metadata.write_text(json.dumps(record), encoding="utf-8")
        with patch.object(MODULE, "probe_duration", return_value=42.29):
            with self.assertRaises(SystemExit):
                MODULE.upload_latest_draft()

    def test_409_conflict_with_different_existing_object_bytes_fails_closed(self):
        mismatch = RuntimeError("Supabase public object bytes do not match generated MP4 SHA-256/size.")
        conflict = urllib.error.HTTPError(
            "https://example.supabase.co/storage/v1/object/REELS/reels/test.mp4",
            409, "Conflict", {}, None,
        )
        with patch.object(MODULE, "probe_duration", return_value=42.29):
            with patch.object(MODULE, "verify_public_video", side_effect=[FileNotFoundError(), mismatch]) as verify:
                with patch.object(MODULE.urllib.request, "urlopen", side_effect=conflict):
                    with self.assertRaisesRegex(RuntimeError, "do not match"):
                        MODULE.upload_latest_draft()
        self.assertEqual(verify.call_count, 2)


if __name__ == "__main__":
    unittest.main()
