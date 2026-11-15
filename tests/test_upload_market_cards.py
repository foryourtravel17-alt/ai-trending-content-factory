import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import upload_market_cards as MODULE


class UploadMarketCardsTests(unittest.TestCase):
    def test_uploads_market_png_to_public_reels_bucket_and_records_verified_url(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "output"
            output.mkdir()
            image = output / "nifty-card.png"
            payload = b"fake-png-market-card"
            image.write_bytes(payload)
            state_path = root / "state.json"
            state = {
                "signals": {
                    "nifty-20261115-long": {
                        "status": "generated",
                        "signal": {"signal_id": "nifty-20261115-long"},
                        "card_path": str(image),
                    },
                    "education-item": {
                        "content_type": "educational_reel",
                        "status": "pending_approval",
                    },
                },
                "runs": [],
            }
            state_path.write_text(json.dumps(state), encoding="utf-8")
            calls = []

            class Response:
                status = 200
                def __init__(self, body=b""):
                    self.body = body
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    return False
                def read(self, size=-1):
                    if size == -1:
                        return self.body
                    body, self.body = self.body[:size], self.body[size:]
                    return body

            def fake_urlopen(request, timeout=0):
                calls.append(request)
                if request.method == "PUT":
                    return Response()
                return Response(payload)

            with patch.dict("os.environ", {
                "SUPABASE_URL": "https://example.supabase.co",
                "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
            }), patch.object(MODULE.urllib.request, "urlopen", side_effect=fake_urlopen):
                MODULE.upload_market_cards(state_path=state_path, output_dir=output)

            saved = json.loads(state_path.read_text(encoding="utf-8"))
            record = saved["signals"]["nifty-20261115-long"]
            expected = "https://example.supabase.co/storage/v1/object/public/REELS/market-cards/nifty-20261115-long.png"
            self.assertEqual(record["image_url"], expected)
            self.assertEqual(record["image_sha256"], hashlib.sha256(payload).hexdigest())
            self.assertEqual(record["image_size_bytes"], len(payload))
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[0].method, "PUT")
            self.assertEqual(calls[1].method, "GET")
            self.assertNotIn("image_url", saved["signals"]["education-item"])

    def test_rejects_card_paths_outside_output_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "output"
            output.mkdir()
            outside = root / "private.png"
            outside.write_bytes(b"not a market card")
            state_path = root / "state.json"
            state_path.write_text(json.dumps({
                "signals": {
                    "bad-id": {
                        "status": "generated",
                        "signal": {"signal_id": "bad-id"},
                        "card_path": str(outside),
                    }
                }
            }), encoding="utf-8")
            with patch.dict("os.environ", {
                "SUPABASE_URL": "https://example.supabase.co",
                "SUPABASE_SERVICE_ROLE_KEY": "test-key",
            }):
                with self.assertRaisesRegex(RuntimeError, "inside output"):
                    MODULE.upload_market_cards(state_path=state_path, output_dir=output)

    def test_requires_existing_supabase_credentials_without_printing_them(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "output"
            output.mkdir()
            state_path = root / "state.json"
            state_path.write_text(json.dumps({"signals": {}}), encoding="utf-8")
            with patch.dict("os.environ", {}, clear=True):
                with self.assertRaisesRegex(RuntimeError, "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY"):
                    MODULE.upload_market_cards(state_path=state_path, output_dir=output)


if __name__ == "__main__":
    unittest.main()
