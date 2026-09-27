import json
import os
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = Path("output")
MEDIA_DIR = OUTPUT_DIR / "media"
TMP_DIR = MEDIA_DIR / "_frames"
WIDTH, HEIGHT = 1080, 1920
FPS = 24
SCENE_SECONDS = 3


def font(size, bold=False):
    candidates = []
    if bold:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


TITLE_FONT = font(72, bold=True)
BODY_FONT = font(48)
SMALL_FONT = font(36)
FOOTER_FONT = font(30)


def wrap_text(draw, text, fnt, max_width):
    words = str(text).split()
    lines = []
    current = ""
    for word in words:
        test = word if not current else current + " " + word
        if draw.textbbox((0, 0), test, font=fnt)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_centered(draw, text, y, fnt, max_width, spacing=12):
    lines = wrap_text(draw, text, fnt, max_width)
    heights = []
    for line in lines:
        box = draw.textbbox((0, 0), line, font=fnt)
        heights.append(box[3] - box[1])
    total = sum(heights) + spacing * max(0, len(lines) - 1)
    cursor = y - total / 2
    for line, h in zip(lines, heights):
        box = draw.textbbox((0, 0), line, font=fnt)
        x = (WIDTH - (box[2] - box[0])) / 2
        draw.text((x, cursor), line, font=fnt, fill="white")
        cursor += h + spacing


def make_scene(path, title, body, footer):
    img = Image.new("RGB", (WIDTH, HEIGHT), (18, 22, 32))
    draw = ImageDraw.Draw(img)

    # Simple educational-card layout; intentionally no trading signals.
    draw.rounded_rectangle(
        (70, 150, WIDTH - 70, HEIGHT - 170),
        radius=42,
        fill=(31, 38, 52),
        outline=(90, 100, 120),
        width=3,
    )

    draw.text((90, 80), "BULLSEYE THEORY", font=SMALL_FONT, fill="white")

    draw_centered(draw, title, 500, TITLE_FONT, WIDTH - 220)
    draw_centered(draw, body, 980, BODY_FONT, WIDTH - 240)

    draw.line((150, 1430, WIDTH - 150, 1430), fill=(100, 110, 125), width=3)
    draw_centered(draw, footer, 1535, SMALL_FONT, WIDTH - 260)

    disclaimer = "Educational content only. Not financial advice."
    draw_centered(draw, disclaimer, 1745, FOOTER_FONT, WIDTH - 220)

    img.save(path, quality=95)


def get_latest_approved():
    candidates = []
    for path in OUTPUT_DIR.glob("content_*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("status") == "approved_for_publishing":
            candidates.append((path, data))
    return sorted(candidates, key=lambda x: x[0].stat().st_mtime, reverse=True)


def build_reel(content):
    content_id = content["content_id"]
    script = content.get("script", {})
    visual = content.get("visual_plan", {})
    scenes = visual.get("scenes", [])

    title = content.get("topic", {}).get("title", "Forex Education")
    hook = script.get("hook", title)
    body = script.get("body", "")
    caption = content.get("caption", "")

    scene_cards = [
        ("HOOK", hook, "Learn the concept before you trade it."),
    ]

    for scene in scenes[:4]:
        scene_cards.append(
            (
                scene.get("text", "Forex education"),
                scene.get("visual", "Educational forex graphic."),
                "Bullseye Theory • Educational content",
            )
        )

    scene_cards.append(
        (
            "KEY TAKEAWAY",
            body[:420] if body else title,
            "Save for later • Learn • Verify",
        )
    )

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    # Clean only this run's temporary frames.
    for old in TMP_DIR.glob("frame_*.png"):
        old.unlink()

    frames = []
    frame_no = 0
    for title_text, body_text, footer in scene_cards:
        frame_count = FPS * SCENE_SECONDS
        for _ in range(frame_count):
            frame_path = TMP_DIR / f"frame_{frame_no:05d}.png"
            make_scene(frame_path, title_text, body_text, footer)
            frames.append(frame_path)
            frame_no += 1

    output = MEDIA_DIR / f"{content_id}.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", str(TMP_DIR / "frame_%05d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output),
    ]
    subprocess.run(cmd, check=True)

    print(f"Created reel: {output}")
    print(f"Caption available in content JSON: {caption[:120]}")


def main():
    approved = get_latest_approved()
    if not approved:
        print("No approved_for_publishing content found. Nothing to generate.")
        return
    path, content = approved[0]
    print(f"Using approved content: {path}")
    build_reel(content)


if __name__ == "__main__":
    main()
