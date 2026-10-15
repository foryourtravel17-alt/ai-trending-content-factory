"""Render six review-only PNGs using the production Reel frame renderer."""
from pathlib import Path

from src.reel_generator import make_frame

OUT = Path("output/archetype_samples")
SAMPLES = [
    ("hook", "Structure beats prediction", "THE HOOK"),
    ("chartproof", "A break is valid only after the close", "CHART PROOF"),
    ("wrongright", "Wrong: chase the candle. Right: wait for structure.", "WRONG / RIGHT"),
    ("list", "Three checks before a breakout", "THE CHECKLIST"),
    ("myth", "A high win rate does not guarantee profit", "MYTH CHECK"),
    ("cta", "Build a repeatable process, not a prediction habit", "NEXT STEP"),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for archetype, hook, label in SAMPLES:
        path = OUT / f"{archetype}.png"
        make_frame(
            path=path,
            topic="Trading education",
            category="Education",
            title=label,
            body=hook,
            scene_index=0,
            scene_visual="Illustrative chart only",
            archetype=archetype,
        )
        print(f"Rendered: {path}")


if __name__ == "__main__":
    main()
