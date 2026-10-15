import hashlib
import json
import math
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
FRAME_SECONDS = 5
MIN_SCENE_SECONDS = 2.25

NAVY = (8, 14, 27)
PANEL = (14, 22, 38)
GOLD = (211, 175, 88)
LIME = (181, 255, 74)
WHITE = (245, 247, 250)
MUTED = (163, 173, 191)
GRID = (34, 49, 70)
RED = (224, 102, 100)


def load_font(size, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
        if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


TITLE = load_font(64, True)
BODY = load_font(42, False)
SMALL = load_font(28, True)
TINY = load_font(22, False)
BIG = load_font(88, True)


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


def centered(draw, text, center_y, font, max_width, fill=WHITE, gap=12):
    lines = wrap(draw, text, font, max_width)
    heights = [draw.textbbox((0, 0), x, font=font)[3] for x in lines]
    total = sum(heights) + gap * max(0, len(lines) - 1)
    y = center_y - total / 2
    for line, h in zip(lines, heights):
        box = draw.textbbox((0, 0), line, font=font)
        x = (WIDTH - (box[2] - box[0])) / 2
        draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0))
        draw.text((x, y), line, font=font, fill=fill)
        y += h + gap


def gradient_background():
    img = Image.new("RGB", (WIDTH, HEIGHT), NAVY)
    px = img.load()
    for y in range(HEIGHT):
        t = y / max(1, HEIGHT - 1)
        r = int(7 + 9 * t)
        g = int(13 + 10 * t)
        b = int(26 + 18 * t)
        for x in range(WIDTH):
            glow = int(
                5
                * max(0, 1 - abs(x - 770) / 420)
                * max(0, 1 - abs(y - 430) / 780)
            )
            px[x, y] = (
                min(255, r + glow),
                min(255, g + glow),
                min(255, b + glow),
            )
    return img


def draw_bullseye(draw, cx=914, cy=125):
    for radius, width, fill in [
        (52, 4, GOLD),
        (37, 3, WHITE),
        (22, 5, LIME),
    ]:
        draw.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            outline=fill,
            width=width,
        )
    draw.ellipse((cx - 5, cy - 5, cx + 5, cy + 5), fill=LIME)


def draw_grid(draw, box):
    left, top, right, bottom = box
    for x in range(left, right + 1, 72):
        draw.line((x, top, x, bottom), fill=GRID, width=1)
    for y in range(top, bottom + 1, 72):
        draw.line((left, y, right, y), fill=GRID, width=1)


def draw_skyline(draw):
    base = 1690
    buildings = [
        (0, 140, 116),
        (140, 235, 210),
        (235, 330, 150),
        (330, 405, 245),
        (405, 505, 175),
        (505, 615, 285),
        (615, 700, 210),
        (700, 790, 330),
        (790, 905, 195),
        (905, 1080, 255),
    ]
    for left, right, height in buildings:
        top = base - height
        draw.rectangle((left, top, right, base), fill=(10, 17, 29))
        for wx in range(left + 14, right - 8, 24):
            for wy in range(top + 18, base - 18, 36):
                draw.rectangle(
                    (wx, wy, wx + 7, wy + 10),
                    fill=(88, 77, 43),
                )
    draw.polygon([(715, 1360), (748, 1110), (781, 1360)], fill=(12, 19, 31))
    draw.line((748, 1110, 748, 1015), fill=GOLD, width=4)


def draw_ticker(draw, topic, category):
    draw.rounded_rectangle(
        (60, 180, WIDTH - 60, 250),
        radius=20,
        fill=(15, 24, 41),
        outline=GRID,
        width=2,
    )
    left = f"BTX  •  {category.upper()}"
    right = "USD  EUR  GBP  JPY   |   ILLUSTRATIVE"
    draw.text((86, 197), left, font=TINY, fill=GOLD)
    bbox = draw.textbbox((0, 0), right, font=TINY)
    draw.text(
        (WIDTH - 88 - (bbox[2] - bbox[0]), 197),
        right,
        font=TINY,
        fill=MUTED,
    )
    draw.text((80, 270), "BULLSEYE THEORY", font=SMALL, fill=WHITE)
    topic_line = topic.upper()
    lines = wrap(draw, topic_line, TINY, 680)
    y = 306
    for line in lines[:2]:
        draw.text((80, y), line, font=TINY, fill=MUTED)
        y += 28


def draw_chart(draw, area, style="trend"):
    left, top, right, bottom = area
    draw.rounded_rectangle(
        area, radius=28, fill=(10, 18, 31), outline=GRID, width=2
    )
    draw_grid(draw, (left + 22, top + 22, right - 22, bottom - 22))

    n = 14
    step = (right - left - 84) / n
    base = bottom - 46
    trend = [0, 22, 10, 48, 30, 64, 40, 82, 68, 106, 96, 128, 110, 150]

    if style == "range":
        trend = [42, 70, 25, 65, 35, 75, 30, 68, 28, 72, 34, 64, 40, 58]
        zone_y = top + int((bottom - top) * 0.46)
        draw.rectangle(
            (left + 34, zone_y, right - 34, zone_y + 90),
            outline=GOLD,
            width=2,
        )
        draw.text((left + 48, zone_y + 20), "RANGE", font=TINY, fill=GOLD)
    elif style == "break":
        trend = [22, 35, 30, 48, 46, 62, 55, 74, 70, 86, 82, 95, 155, 48]
        bx = left + 44 + 12 * step
        draw.line((bx, top + 36, bx, bottom - 30), fill=LIME, width=4)
        draw.polygon([(bx, top + 42), (bx - 12, top + 64), (bx + 12, top + 64)], fill=LIME)
    elif style == "risk":
        trend = [10, 18, 15, 26, 40, 34, 48, 45, 60, 54, 72, 66, 82, 76]
        risk_y = bottom - 170
        draw.line((left + 34, risk_y, right - 34, risk_y), fill=GOLD, width=3)
        draw.text((left + 48, risk_y - 34), "EXPOSURE", font=TINY, fill=GOLD)
    elif style == "sweep":
        trend = [25, 50, 32, 64, 44, 80, 42, 28, 55, 92, 76, 112, 94, 132]
        sweep_y = top + int((bottom - top) * 0.55)
        draw.line((left + 30, sweep_y, right - 30, sweep_y), fill=GOLD, width=3)
        draw.text((left + 42, sweep_y - 32), "LIQUIDITY SWEEP", font=TINY, fill=GOLD)
    elif style == "choch":
        trend = [28, 52, 34, 68, 50, 85, 62, 38, 58, 95, 78, 122, 106, 145]
        choch_x = left + 44 + 9 * step
        draw.line((left + 28, top + 180, right - 28, top + 180), fill=GOLD, width=3)
        draw.line((choch_x, top + 70, choch_x, bottom - 35), fill=LIME, width=3)
        draw.text((left + 42, top + 190), "CHOCH", font=TINY, fill=GOLD)
    elif style == "retest":
        trend = [24, 44, 36, 64, 55, 82, 70, 102, 88, 72, 96, 118, 105, 138]
        retest_y = top + int((bottom - top) * 0.42)
        draw.line((left + 30, retest_y, right - 30, retest_y), fill=LIME, width=3)
        draw.text((left + 42, retest_y - 32), "RETEST ZONE", font=TINY, fill=LIME)
    elif style == "break":
        trend = [22, 35, 30, 48, 46, 62, 55, 74, 70, 86, 82, 95, 155, 48]

    for i in range(n):
        x = left + 44 + i * step
        close = base - trend[i] * 1.55
        open_ = close + (13 if i % 3 == 0 else -11)
        high = max(open_, close) - 24
        low = min(open_, close) + 28

        body_top = min(open_, close)
        body_bottom = max(open_, close)
        up = close < open_
        fill = LIME if not up else RED
        draw.line((x, high, x, low), fill=MUTED, width=3)
        draw.rounded_rectangle(
            (x - 9, body_top, x + 9, body_bottom),
            radius=4,
            fill=fill,
            outline=fill,
        )

    draw.text(
        (left + 30, top + 24),
        "ILLUSTRATIVE / NOT A SIGNAL",
        font=TINY,
        fill=MUTED,
    )


def add_emphasis_panel(draw, label, text):
    draw.rounded_rectangle(
        (70, 570, WIDTH - 70, 1210),
        radius=40,
        fill=PANEL,
        outline=GRID,
        width=2,
    )
    draw.text((105, 620), label.upper(), font=SMALL, fill=GOLD)
    centered(draw, text, 860, BODY, WIDTH - 260)


def load_archetypes():
    try:
        return json.loads(Path("config/card_archetypes.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"archetypes": {}}


def choose_archetype(content_id, previous=None):
    """Stable hash-based archetype selection with an optional repeat guard."""
    archetypes = load_archetypes().get("archetypes", {})
    names = sorted(archetypes)
    if not names:
        return "hook"
    digest = hashlib.sha256(str(content_id).encode("utf-8")).hexdigest()
    index = int(digest[:12], 16) % len(names)
    chosen = names[index]
    if previous == chosen and len(names) > 1:
        chosen = names[(index + 1) % len(names)]
    return chosen


def make_frame(path, topic, category, title, body, scene_index, scene_visual, archetype=None):
    img = gradient_background()
    d = ImageDraw.Draw(img)

    draw_bullseye(d)
    draw_ticker(d, topic, category)
    draw_skyline(d)

    if scene_index == 0:
        archetype_data = load_archetypes().get("archetypes", {}).get(archetype or "hook", {})
        accent_hex = archetype_data.get("accent", "#D3AF58").lstrip("#")
        accent = tuple(int(accent_hex[i:i + 2], 16) for i in (0, 2, 4))
        zone = archetype_data.get("zones", {}).get("hook", {"x": 70, "y": 570, "w": 940, "h": 620})
        x, y, w, h = zone["x"], zone["y"], zone["w"], zone["h"]
        d.rounded_rectangle((x, y, x + w, y + h), radius=40, fill=PANEL, outline=accent, width=2)
        label = archetype_data.get("label", (archetype or "hook").replace("_", " ").upper())
        d.text((x + 38, y + 42), label.upper(), font=SMALL, fill=accent)
        font_size = int(archetype_data.get("font_sizes", {}).get("hook", 64))
        hook_font = load_font(font_size, True)
        centered(d, body or title, y + h * 0.52, hook_font, max(220, w - 110), fill=WHITE)
        draw_chart(d, (105, 1260, 975, 1570), archetype_data.get("chart_style", "trend"))
    elif scene_index in (1, 2, 3, 4):
        d.text((85, 570), f"SCENE {scene_index}", font=SMALL, fill=GOLD)
        add_emphasis_panel(d, title, body)
        style = "trend"
        lower = f"{title} {body} {scene_visual}".lower()
        if "range" in lower:
            style = "range"
        elif "break" in lower or "false" in lower or "invalid" in lower:
            style = "break"
        elif "risk" in lower or "position" in lower or "leverage" in lower:
            style = "risk"
        draw_chart(d, (105, 1260, 975, 1570), style)
    elif scene_index == 5:
        d.text((85, 575), "KEY TAKEAWAY", font=SMALL, fill=GOLD)
        centered(d, body, 895, BODY, WIDTH - 250)
        draw_chart(d, (105, 1260, 975, 1570), "trend")
    elif scene_index == 6:
        d.rounded_rectangle(
            (70, 570, WIDTH - 70, 1180),
            radius=40,
            fill=PANEL,
            outline=GOLD,
            width=2,
        )
        centered(d, body or "LEARN | TRADE | GROW", 875, BIG, WIDTH - 220, fill=WHITE)
        draw_chart(d, (105, 1260, 975, 1570), "range")
    else:
        d.rounded_rectangle(
            (70, 570, WIDTH - 70, 1200),
            radius=40,
            fill=PANEL,
            outline=GOLD,
            width=2,
        )
        d.text(
            (108, 625),
            "EDUCATIONAL NOTICE",
            font=SMALL,
            fill=GOLD,
        )
        short_notice = " ".join(str(body or "").split()[:8]) or "Education only. Not financial advice. Trading involves risk."
        centered(d, short_notice, 875, BODY, WIDTH - 250, fill=WHITE)
        draw_chart(d, (105, 1260, 975, 1570), "risk")

    d.text((80, 1645), "BULLSEYE THEORY", font=SMALL, fill=WHITE)
    d.text((80, 1683), "LEARN  |  TRADE  |  GROW", font=TINY, fill=MUTED)

    img.save(path, format="PNG")


def approved_items():
    items = []
    for path in OUTPUT_DIR.glob("content_*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if (
            data.get("status") == "approved_for_publishing"
            and not data.get("reel_generated", False)
            and not (MEDIA_DIR / f"{data.get('content_id', '')}.mp4").exists()
        ):
            items.append((path, data))
    return sorted(items, key=lambda item: item[0].stat().st_mtime)


def run(cmd, check=True):
    print("$", " ".join(str(x) for x in cmd))
    return subprocess.run(cmd, check=check)


def ffprobe_duration(path):
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def make_voice_segment(text, base_path):
    mp3 = base_path.with_suffix(".mp3")
    wav = base_path.with_suffix(".wav")

    edge_ok = False
    try:
        run([
            "edge-tts",
            "--voice", "en-US-GuyNeural",
            "--rate=-5%",
            "--pitch=-2Hz",
            "--text", text,
            "--write-media", str(mp3),
        ])
        edge_ok = mp3.exists() and mp3.stat().st_size > 0
    except Exception as exc:
        print(f"edge-tts unavailable: {exc}")

    if edge_ok:
        run([
            "ffmpeg", "-y", "-i", str(mp3),
            "-ac", "1", "-ar", "48000",
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=7",
            str(wav),
        ])
        return wav

    local = base_path.with_suffix(".local.wav")
    run([
        "espeak-ng",
        "-v", "en-us+m3",
        "-s", "150",
        "-p", "35",
        "-a", "165",
        "-w", str(local),
        text,
    ])
    run([
        "ffmpeg", "-y", "-i", str(local),
        "-ac", "1", "-ar", "48000",
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=7",
        str(wav),
    ])
    return wav


def make_voiceover(script):
    segments = [
        ("hook", script.get("hook", "")),
        ("body", script.get("body", "")),
        ("cta", script.get("cta", "")),
        ("disclaimer", script.get("disclaimer", "")),
    ]
    paths = []
    for name, text in segments:
        if not str(text).strip():
            continue
        out = TMP_DIR / f"voice_{name}"
        paths.append(make_voice_segment(str(text), out))

    concat = TMP_DIR / "voice_concat.txt"
    concat.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in paths) + "\n",
        encoding="utf-8",
    )
    voice = TMP_DIR / "voiceover.wav"
    run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat),
        "-c:a", "pcm_s16le",
        "-ar", "48000", "-ac", "1",
        str(voice),
    ])
    return voice, segments


def make_music():
    music = TMP_DIR / "music.wav"
    duration = 60
    run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=frequency=82:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency=123:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency=164:duration={duration}",
        "-filter_complex",
        "[0:a]volume=0.055,lowpass=f=700[a0];"
        "[1:a]volume=0.032,lowpass=f=1000[a1];"
        "[2:a]volume=0.018,lowpass=f=1400[a2];"
        "[a0][a1][a2]amix=inputs=3:duration=longest,"
        "aecho=0.8:0.6:80|140:0.18|0.10,"
        "alimiter=limit=0.35,"
        "afade=t=in:st=0:d=2,"
        "afade=t=out:st=55:d=5,"
        "volume=0.65[m]",
        "-map", "[m]",
        "-ar", "48000", "-ac", "2",
        str(music),
    ])
    return music


def subtitle_chunks(text, max_words=8):
    words = str(text).split()
    return [" ".join(words[i:i + max_words]) for i in range(0, len(words), max_words)]


def ass_time(seconds):
    seconds = max(0, float(seconds))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 0
        s += 1
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def make_ass(script, voice_durations):
    events = []
    timeline = 0.0
    colors = {
        "hook": "&H003BFFF6",
        "body": "&H00FFFFFF",
        "cta": "&H003BFFF6",
        "disclaimer": "&H00D8B358",
    }

    active_segments = [
        x for x in [
            ("hook", script.get("hook", "")),
            ("body", script.get("body", "")),
            ("cta", script.get("cta", "")),
            ("disclaimer", script.get("disclaimer", "")),
        ] if str(x[1]).strip()
    ]

    for (name, text), duration in zip(active_segments, voice_durations):
        chunks = subtitle_chunks(text, 8)
        piece = duration / max(1, len(chunks))
        for idx, chunk in enumerate(chunks):
            start = timeline + idx * piece
            end = timeline + (idx + 1) * piece
            events.append(
                f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Default,"
                f"{{\\c{colors.get(name, '&H00FFFFFF')}}}{chunk}"
            )
        timeline += duration

    ass = TMP_DIR / "captions.ass"
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,43,&H00FFFFFF,&H00FFFFFF,&H90000000,&H90000000,1,0,0,0,100,100,0,0,0,3,2,1,2,80,80,250,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ass.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return ass


def build(content):
    content_id = content["content_id"]
    topic = content.get("topic", {}).get("title", "Trading Education")
    category = content.get("content_category", "Trading Education")
    script = content.get("script", {})
    visual = content.get("visual_plan", {})
    scenes = visual.get("scenes", [])

    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    TMP_DIR.mkdir(parents=True)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    frame_specs = []
    archetype = choose_archetype(content_id)
    frame_specs.append(("THE HOOK", script.get("hook", topic), 0, ""))
    for i, scene in enumerate(scenes[:4], start=1):
        frame_specs.append((
            scene.get("text", f"Market concept {i}"),
            scene.get("visual", "Educational trading concept."),
            i,
            scene.get("visual", ""),
        ))
    frame_specs.append(("KEY TAKEAWAY", script.get("body", topic), 5, ""))
    frame_specs.append(("BULLSEYE THEORY", script.get("tagline", "LEARN | TRADE | GROW"), 6, ""))
    frame_specs.append(("EDUCATIONAL NOTICE", script.get("disclaimer", ""), 7, ""))

    for i, (title, body, index, visual_text) in enumerate(frame_specs):
        path = TMP_DIR / f"frame_{i:03d}.png"
        make_frame(path, topic, category, title, body, index, visual_text, archetype=archetype)

    voice, segments = make_voiceover(script)
    voice_durations = []
    for name, text in segments:
        if str(text).strip():
            voice_path = TMP_DIR / f"voice_{name}.wav"
            voice_durations.append(ffprobe_duration(voice_path))

    captions = make_ass(script, voice_durations)
    music = make_music()
    voice_duration = ffprobe_duration(voice)

    concat = TMP_DIR / "frames.txt"
    # Fit the complete storyboard to the narration so the takeaway,
    # philosophy, and disclaimer are not silently cut off.
    scene_seconds = max(MIN_SCENE_SECONDS, voice_duration / len(frame_specs))
    lines = []
    for i in range(len(frame_specs)):
        path = (TMP_DIR / f"frame_{i:03d}.png").resolve()
        lines.append(f"file '{path}'")
        lines.append(f"duration {scene_seconds:.3f}")
    lines.append(
        f"file '{(TMP_DIR / f'frame_{len(frame_specs)-1:03d}.png').resolve()}'"
    )
    concat.write_text("\n".join(lines) + "\n", encoding="utf-8")

    output = MEDIA_DIR / f"{content_id}.mp4"
    filter_complex = (
        "[1:a]volume=1.0[voice];"
        "[2:a]volume=0.08[music];"
        "[voice][music]amix=inputs=2:duration=shortest:dropout_transition=2,"
        "loudnorm=I=-14:TP=-1.5:LRA=7[aout]"
    )

    run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat),
        "-i", str(voice),
        "-i", str(music),
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[aout]",
        "-vf", f"scale={WIDTH}:{HEIGHT},format=yuv420p,ass={captions}",
        "-r", str(FPS),
        "-t", f"{voice_duration:.3f}",
        "-c:v", "libx264",
        "-profile:v", "high",
        "-level", "4.2",
        "-preset", "medium",
        "-crf", "19",
        "-c:a", "aac",
        "-b:a", "160k",
        "-ar", "48000",
        "-movflags", "+faststart",
        str(output),
    ])

    social = content.get("social", {}) or {}
    meta = {
        "content_id": content_id,
        "video": str(output),
        "caption": social.get("caption", ""),
        "hashtags": social.get("hashtags", []),
        "status": "ready_for_instagram",
        "audio": {
            "voice": "professional male English neural voice with local fallback",
            "background_music": "procedural cinematic low-volume bed",
            "voice_duration_seconds": round(voice_duration, 2),
        },
        "visual_style": content.get("visual_plan", {}).get("style", ""),
    }
    (MEDIA_DIR / f"{content_id}.publish.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    content["reel_generated"] = True
    content["reel_generated_at"] = (
        __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    )
    publishing = content.setdefault("publishing", {})
    instagram = publishing.setdefault("instagram", {})
    instagram["status"] = "ready_for_publish"
    content["publishing"]["reel_file"] = str(output)
    content_path = OUTPUT_DIR / f"{content_id}.json"
    content_path.write_text(
        json.dumps(content, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Created premium Reel: {output}")
    print(f"Voiceover duration: {voice_duration:.2f}s")
    print(f"Storyboard scene duration: {scene_seconds:.2f}s across {len(frame_specs)} scenes")
    print(f"Marked {content_id} as reel_generated to prevent duplicate generation.")


def main():
    items = approved_items()
    if not items:
        print("No ungenerated approved_for_publishing content found.")
        return
    path, content = items[0]
    print(f"Using approved content: {path}")
    build(content)


if __name__ == "__main__":
    main()
