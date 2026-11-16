import unittest
from unittest.mock import patch

from scripts import check_deployment_readiness as doctor


class DeploymentReadinessDoctorTests(unittest.TestCase):
    def test_report_exit_code_fails_only_when_a_check_fails(self):
        report = doctor.Report()
        report.passed("one", "ok")
        report.warned("optional", "not configured")
        self.assertEqual(report.exit_code(), 0)
        report.failed("required", "missing")
        self.assertEqual(report.exit_code(), 1)

    def test_telegram_api_only_exposes_safe_result(self):
        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "test"}, clear=True), patch.object(
            doctor.urllib.request, "urlopen"
        ) as urlopen:
            class Response:
                def __enter__(self): return self
                def __exit__(self, *args): return False
                def read(self): return b'{"ok":true,"result":{"id":123}}'
            urlopen.return_value = Response()
            result = doctor.api("test", "getMe")
        self.assertEqual(result["id"], 123)

    def test_readiness_checks_only_telegram_and_supabase(self):
        env = {
            "TELEGRAM_BOT_TOKEN": "bot",
            "TELEGRAM_CHAT_ID": "123",
            "TELEGRAM_APPROVER_USER_IDS": "123",
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "service-key",
        }
        calls = []
        def fake_api(token, method, payload=None):
            calls.append(method)
            if method == "getMe":
                return {"id": 777}
            if method == "getChat":
                return {"type": "channel"} if payload["chat_id"] == "@bullseye_theory" else {"type": "private"}
            return {"status": "administrator", "can_post_messages": True}
        def fake_json(url, method="GET", headers=None, payload=None):
            if url.endswith("/bucket/REELS"):
                return 200, {"id": "REELS", "public": True}
            return 200, [{"name": "example.mp4"}]
        report = doctor.run_checks
        with patch.dict("os.environ", env, clear=True), patch.object(doctor, "api", side_effect=fake_api), patch.object(doctor, "request_json", side_effect=fake_json), patch("builtins.print"):
            code = report()
        self.assertEqual(code, 0)
        self.assertEqual(calls, ["getMe", "getChat", "getChatMember", "getChat"])

    def test_request_json_sets_json_content_type_for_storage_list_payload(self):
        captured = {}
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return b'[]'
        def fake_urlopen(request, timeout):
            captured["headers"] = dict(request.header_items())
            captured["data"] = request.data
            return Response()
        with patch.object(doctor.urllib.request, "urlopen", side_effect=fake_urlopen):
            status, result = doctor.request_json(
                "https://example.supabase.co/storage/v1/object/list/REELS",
                method="POST",
                headers={"Authorization": "Bearer test", "apikey": "test"},
                payload={"prefix": "reels", "limit": 20, "offset": 0},
            )
        self.assertEqual(status, 200)
        self.assertEqual(result, [])
        self.assertEqual(captured["headers"].get("Content-type"), "application/json")
        self.assertEqual(captured["data"], b'{"prefix": "reels", "limit": 20, "offset": 0}')

if __name__ == "__main__":
    unittest.main()
