import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
bank = json.loads((ROOT / "content_bank.json").read_text(encoding="utf-8"))["posts"]

today = datetime.now().astimezone()
day_index = today.timetuple().tm_yday - 1

# Rotate through the bank so every day has a fresh combination without
# requiring a paid AI API. The dashboard can later hand these prompts to
# an authorized image/video provider.
selected = [bank[(day_index + i) % len(bank)] for i in range(3)]

queue = {
    "generated_at": today.isoformat(),
    "mode": "free-first",
    "status": "ready_for_asset_generation",
    "manual_required": [
        "Connect an authorized AI image/video provider when generation credits/API access are available.",
        "Connect Meta/Instagram publishing permissions before automated posting."
    ],
    "posts": [
        {
            "slot": i + 1,
            **item,
            "approval": "pending",
            "publishing": "not_connected"
        }
        for i, item in enumerate(selected)
    ]
}

(ROOT / "content_queue.json").write_text(
    json.dumps(queue, indent=2, ensure_ascii=False),
    encoding="utf-8"
)
print(f"Generated {len(selected)} Ritu posts for {today.date()}")
