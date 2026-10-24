"""Offline MP4 smoke test: exercise real ffmpeg output and the production ffprobe reader.

This intentionally does not call the scheduled publishing workflow, network TTS,
Supabase, Telegram, or Instagram. It creates a tiny local fixture only.
"""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from src.reel_generator import ffprobe_duration


@unittest.skipUnless(
    shutil.which("ffmpeg") and shutil.which("ffprobe"),
    "ffmpeg and ffprobe are required for the offline MP4 smoke test",
)
class Mp4RenderSmokeTests(unittest.TestCase):
    def test_real_mp4_is_nonempty_and_duration_is_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "smoke.mp4"
            subprocess.run(
                [
                    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", "color=c=navy:s=180x320:r=12:d=1",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                    "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-movflags", "+faststart", str(video),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertTrue(video.is_file())
            self.assertGreater(video.stat().st_size, 0)
            duration = ffprobe_duration(video)
            self.assertGreaterEqual(duration, 0.8)
            self.assertLessEqual(duration, 1.2)


if __name__ == "__main__":
    unittest.main()
