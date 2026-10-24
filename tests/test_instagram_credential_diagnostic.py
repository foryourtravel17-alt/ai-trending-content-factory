"""Regression tests for read-only Instagram credential diagnosis."""
import contextlib
import io
import unittest
from unittest.mock import patch

from scripts import diagnose_instagram_credential as diagnostic


class InstagramCredentialDiagnosticTests(unittest.TestCase):
    def test_bad_configured_id_does_not_block_page_resolution_and_prints_correct_id(self):
        calls = []

        def fake_get(url, params=None, timeout=None):
            path = url.split('/v23.0/', 1)[-1]
            calls.append(path)
            if path.startswith("me/accounts?"):
                class Response:
                    ok = True
                    status_code = 200
                    def json(self):
                        return {"data": [{
                            "id": "page-1",
                            "name": "Bullseye Theory",
                            "instagram_business_account": {
                                "id": "correct-ig-123",
                                "username": "bullseye_theory",
                            },
                        }]}
                return Response()
            class Response:
                ok = False
                status_code = 400
                def json(self):
                    return {"error": {"code": 100, "error_subcode": 33}}
            return Response()

        output = io.StringIO()
        with patch.dict("os.environ", {
            "META_SYSTEM_USER_TOKEN": "test-token",
            "IG_USER_ID": "",
            "INSTAGRAM_USER_ID": "stale-id",
            "INSTAGRAM_ACCESS_TOKEN": "",
            "IG_ACCESS_TOKEN": "",
        }, clear=False), patch.object(diagnostic.requests, "get", side_effect=fake_get):
            with contextlib.redirect_stdout(output):
                result = diagnostic.main()

        text = output.getvalue()
        self.assertEqual(result, 1)
        self.assertGreaterEqual(len(calls), 2)
        self.assertTrue(calls[0].startswith("me/accounts?"), calls)
        self.assertIn("Configured ID lookup failed (code=100, subcode=33)", text)
        self.assertIn("CORRECT IG_USER_ID = correct-ig-123", text)
        self.assertIn("SET IG_USER_ID to this value: correct-ig-123", text)
        self.assertIn("ENV IG_USER_ID: EMPTY", text)
        self.assertIn("WARNING: Permission-scope lookup unavailable", text)


    def test_missing_required_publish_scope_blocks_readiness(self):
        responses = {
            "me/accounts?fields=id,name,tasks,instagram_business_account{id,username}": {
                "data": [{
                    "id": "page-1",
                    "name": "Bullseye Theory",
                    "tasks": ["CREATE_CONTENT"],
                    "instagram_business_account": {"id": "correct-ig-123", "username": "bullseye_theory"},
                }]
            },
            "me/permissions": {"data": [
                {"permission": "pages_show_list", "status": "granted"},
                {"permission": "instagram_basic", "status": "granted"},
                {"permission": "instagram_content_publish", "status": "granted"},
            ]},
            "correct-ig-123?fields=id,username": {"id": "correct-ig-123", "username": "bullseye_theory"},
        }

        def fake_get(path, token):
            return responses[path]

        output = io.StringIO()
        with patch.dict("os.environ", {
            "META_SYSTEM_USER_TOKEN": "test-token",
            "IG_USER_ID": "correct-ig-123",
            "INSTAGRAM_USER_ID": "",
            "INSTAGRAM_ACCESS_TOKEN": "",
            "IG_ACCESS_TOKEN": "",
        }, clear=False), patch.object(diagnostic, "get", side_effect=fake_get):
            with contextlib.redirect_stdout(output):
                result = diagnostic.main()

        self.assertEqual(result, 1)
        self.assertIn("Meta permission pages_read_engagement: NOT GRANTED", output.getvalue())
        self.assertIn("BLOCKED: required Instagram publishing permissions are missing: pages_read_engagement", output.getvalue())


if __name__ == "__main__":
    unittest.main()
