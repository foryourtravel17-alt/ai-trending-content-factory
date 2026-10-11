"""Create a branded square market-analysis card using Pillow."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

NAVY = (7, 17, 31)
PANEL = (14, 29, 48)
LIME = (184, 255, 92)
GOLD = (217, 183, 110)
WHITE = (238, 244, 250)
MUTED = (157, 174, 193)
RED = (255, 100, 124)

def _font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()

def render_card(signal: dict, output_dir: str = "output") -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{signal['slug']}_card.png"
    im = Image.new("RGB", (1080, 1080), NAVY)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((36, 36, 1044, 1044), radius=34, outline=(42, 62, 82), width=3)
    d.text((76, 70), "BULLSEYE THEORY", font=_font(32, True), fill=GOLD)
    d.text((76, 116), "FILTER THE NOISE. READ THE STRUCTURE.", font=_font(19), fill=MUTED)
    d.line((76, 160, 1004, 160), fill=(42, 62, 82), width=2)
    d.text((76, 190), signal["symbol"], font=_font(42, True), fill=WHITE)
    d.text((76, 246), signal["label"], font=_font(24), fill=MUTED)
    color = LIME if signal["direction"] == "LONG" else RED
    d.rounded_rectangle((76, 300, 1004, 392), radius=18, fill=PANEL, outline=color, width=3)
    d.text((112, 321), signal["direction"], font=_font(44, True), fill=color)
    d.text((770, 333), "RULE-BASED SCENARIO", font=_font(16, True), fill=MUTED)
    def money(value):
        return f"{value:,.4f}" if abs(value) < 10 else f"{value:,.2f}"
    rows = [
        ("ENTRY", signal["entry"], WHITE),
        ("STOP LOSS", signal["stop_loss"], RED),
        ("TARGET 1", signal["tp1"], LIME),
        ("TARGET 2", signal["tp2"], LIME),
        ("TARGET 3", signal["tp3"], LIME),
    ]
    y = 432
    for label, value, col in rows:
        d.rounded_rectangle((76, y, 1004, y + 74), radius=13, fill=PANEL)
        d.text((105, y + 19), label, font=_font(22, True), fill=MUTED)
        text = money(float(value))
        box = d.textbbox((0, 0), text, font=_font(29, True))
        d.text((972 - (box[2] - box[0]), y + 15), text, font=_font(29, True), fill=col)
        y += 86
    d.line((76, 886, 1004, 886), fill=(42, 62, 82), width=2)
    d.text((76, 907), f"RSI 14: {signal['rsi14']:.1f}  |  R:R to TP2: {signal['rr_tp2']:.2f}", font=_font(20), fill=WHITE)
    d.text((76, 948), "Educational only · Market conditions can change", font=_font(19), fill=MUTED)
    d.text((76, 995), "@bullseye_theory  •  LEARN | TRADE | EARN", font=_font(22, True), fill=GOLD)
    im.save(path, format="PNG", optimize=True)
    return path
