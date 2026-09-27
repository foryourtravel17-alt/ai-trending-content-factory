import json
import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = Path("output")
MEDIA_DIR = OUTPUT_DIR / "media"
TMP_DIR = Path("/tmp/bullseye_reel_frames")
WIDTH, HEIGHT = 1080, 1920
FPS = 30
SCENE_SECONDS = 3


def load_font(size, bold=False):
    names = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]
    for p in names:
        if os.path.exists(p):
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()


TITLE = load_font(68, True)
BODY = load_font(46, False)
SMALL = load_font(34, True)
FOOT = load_font(30, False)


def wrap(draw, text, font, max_width):
    words = str(text).split()
    lines, cur = [], ""
    for word in words:
        test = word if not cur else f"{cur} {word}"
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def centered(draw, text, center_y, font, max_width, fill="white", gap=10):
    lines = wrap(draw, text, font, max_width)
    heights = [draw.textbbox((0, 0), x, font=font)[3] for x in lines]
    total = sum(heights) + gap * max(0, len(lines) - 1)
    y = center_y - total / 2
    for line, h in zip(lines, heights):
        box = draw.textbbox((0, 0), line, font=font)
        x = (WIDTH - (box[2] - box[0])) / 2
        draw.text((x, y), line, font=font, fill=fill)
        y += h + gap


def draw_simple_chart(draw, y=1180):
    left, right = 180, 900
    top, bottom = y - 150, y + 150
    draw.line((left, bottom, right, bottom), fill="white", width=3)
    draw.line((left, top, left, bottom), fill="white", width=3)

    pts = [
        (left + 20, bottom - 20),
        (left + 140, bottom - 85),
        (left + 250, bottom - 55),
        (left + 370, bottom - 135),
        (left + 490, bottom - 95),
        (left + 620, bottom - 175),
        (right - 20, bottom - 125),
    ]
    draw.line(pts, fill="white", width=8, joint="curve")
    for x, yy in pts:
        draw.ellipse((x - 7, yy - 7, x + 7, yy + 7), fill="white")


def make_frame(path, title, body, footer, scene_index):
    img = Image.new("RGB", (WIDTH, HEIGHT), (18, 22, 32))
    d = ImageDraw.Draw(img)

    # Instagram-safe layout: keep important content away from top/bottom UI.
    d.text((80, 90), "BULLSEYE THEORY", font=SMALL, fill="white")
    d.rounded_rectangle(
        (60, 180, WIDTH - 60, 1650),
        radius=44,
        fill=(31, 38, 52),
        outline=(105, 115, 135),
        width=3,
    )

    centered(d, title, 470, TITLE, WIDTH - 220)
    centered(d, body, 850, BODY, WIDTH - 220)

    if scene_index % 2 == 1:
        draw_simple_chart(d, 1190)

    d.text((90, 1690), footer, font=FOOT, fill="white")
    d.text((90, 1780), "Educational content only. Not financial advice.",
           font=FOOT, fill="white")

    img.save(path, format="PNG")


def approved_items():
    items = []
    for p in OUTPUT_DIR.glob("content_*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("status") == "approved_for_publishing":
            items.append((p, data))
    return sorted(items, key=lambda x: x[0].stat().st_mtime, reverse=True)


def build(content):
    content_id = content["content_id"]
    topic = content.get("topic", {}).get("title", "Forex Education")
    script = content.get("script", {})
    visual = content.get("visual_plan", {})
    scenes = visual.get("scenes", [])

    cards = [("HOOK", script.get("hook", topic), "Learn • Verify • Manage risk")]
    for i, scene in enumerate(scenes[:4], start=1):
        cards.append((
            scene.get("text", f"Forex concept {i}"),
            scene.get("visual", "Educational forex concept."),
            "Bullseye Theory • Educational content",
        ))
    cards.append((
        "KEY TAKEAWAY",
        script.get("body", topic)[:380],
        "Save this educational guide",
    ))

    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    TMP_DIR.mkdir(parents=True)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    for i, (title, body, footer) in enumerate(cards):
        path = TMP_DIR / f"frame_{i:03d}.png"
        make_frame(path, title, body, footer, i)

    output = MEDIA_DIR / f"{content_id}.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-framerate", "1",
        "-i", str(TMP_DIR / "frame_%03d.png"),
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-vf", "scale=1080:1920,format=yuv420p",
        "-r", str(FPS),
        "-c:v", "libx264",
        "-profile:v", "high",
        "-level", "4.2",
        "-b:v", "4M",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "48000",
        "-shortest",
        "-movflags", "+faststart",
        str(output),
    ]
    # Each still frame becomes SCENE_SECONDS seconds by using concat timing below.
    concat = TMP_DIR / "concat.txt"
    lines = []
    for i in range(len(cards)):
        p = (TMP_DIR / f"frame_{i:03d}.png").resolve()
        lines.append(f"file '{p}'")
        lines.append(f"duration {SCENE_SECONDS}")
    lines.append(f"file '{(TMP_DIR / f'frame_{len(cards)-1:03d}.png').resolve()}'")
    concat.write_text("\n".join(lines) + "\n", encoding="utf-8")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat),
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-vf", "scale=1080:1920,format=yuv420p",
        "-r", str(FPS),
        "-c:v", "libx264", "-profile:v", "high", "-level", "4.2",
        "-b:v", "4M",
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
        "-shortest", "-movflags", "+faststart", str(output)
    ]
    subprocess.run(cmd, check=True)

    # Store a small metadata record used by the publisher.
    meta = {
        "content_id": content_id,
        "video": str(output),
        "caption": content.get("caption", ""),
        "hashtags": content.get("hashtags", []),
        "status": "ready_for_instagram",
    }
    (MEDIA_DIR / f"{content_id}.publish.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Created: {output}")


def main():
    items = approved_items()
    if not items:
        print("No approved_for_publishing content found.")
        return
    path, content = items[0]
    print(f"Using approved content: {path}")
    build(content)


if __name__ == "__main__":
    main()
