import unittest
from unittest.mock import patch
from types import SimpleNamespace
from pathlib import Path

from agents import publisher


class MarketCardPublicUrlTests(unittest.TestCase):
    def test_verified_supabase_url_is_used_without_github_fallback(self):
        url = "https://example.supabase.co/storage/v1/object/public/REELS/market-cards/card.png"
        with patch.object(publisher.requests, "head", return_value=SimpleNamespace(status_code=200)) as head:
            result = publisher._accessible_image_url(Path("output/card.png"), url)
        self.assertEqual(result, url)
        head.assert_called_once_with(url, allow_redirects=True, timeout=12)

    def test_unreachable_supabase_url_blocks_instead_of_falling_back_to_github(self):
        url = "https://example.supabase.co/storage/v1/object/public/REELS/market-cards/card.png"
        with patch.object(publisher.requests, "head", return_value=SimpleNamespace(status_code=404)):
            with self.assertRaisesRegex(RuntimeError, "private-repository fallback"):
                publisher._accessible_image_url(Path("output/card.png"), url)


if __name__ == "__main__":
    unittest.main()
