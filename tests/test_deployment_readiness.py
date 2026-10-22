import os
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

    def test_storage_mp4_path_handles_nested_and_flat_listing_names(self):
        self.assertEqual(doctor.mp4_object_path([{"name": "reels/abc.mp4"}]), "reels/abc.mp4")
        self.assertEqual(doctor.mp4_object_path([{"name": "abc.mp4"}]), "reels/abc.mp4")
        self.assertIsNone(doctor.mp4_object_path([{"name": "directory"}]))

    def test_image_url_uses_configured_base_and_does_not_show_credentials(self):
        with patch.dict(os.environ, {"IMAGE_BASE_URL": "https://example.test/output"}, clear=True):
            url, source = doctor.image_url_for_card("output/test_card.png")
        self.assertEqual(url, "https://example.test/output/test_card.png")
        self.assertEqual(source, "IMAGE_BASE_URL")

    def test_image_url_uses_pages_when_configured(self):
        with patch.dict(os.environ, {"GH_USER": "owner", "GH_REPO": "repo"}, clear=True):
            url, source = doctor.image_url_for_card("output/test_card.png")
        self.assertEqual(url, "https://owner.github.io/repo/output/test_card.png")
        self.assertEqual(source, "GitHub Pages")

    def test_github_image_base_rejects_non_http_scheme(self):
        with patch.dict(os.environ, {"IMAGE_BASE_URL": "file:///tmp", "GH_USER": "", "GH_REPO": ""}, clear=True):
            url, reason = doctor.image_url_for_card("output/test_card.png")
        self.assertIsNone(url)
        self.assertIn("https://", reason)

    def test_http_helper_redacts_exception_text(self):
        token = "do-not-log-this-token"
        with patch.object(doctor.urllib.request, "urlopen", side_effect=doctor.urllib.error.URLError(token)):
            status, body, error = doctor.request_bytes("https://example.test")
        self.assertIsNone(status)
        self.assertEqual(body, b"")
        self.assertEqual(error, "URLError")
        self.assertNotIn(token, error)


if __name__ == "__main__":
    unittest.main()
