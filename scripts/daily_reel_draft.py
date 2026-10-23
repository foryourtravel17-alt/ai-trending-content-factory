#!/usr/bin/env python3
"""Create one fresh, draft-only Bullseye educational Reel seed.

No paid APIs, scraping of private content, live quotes, or publishing.
Topics rotate deterministically by UTC date; copy is original evergreen education.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("output")
SLOTS = ("morning", "afternoon", "evening")

TOPICS = [
    {
        "slug": "market-structure",
        "title": "Market Structure: Higher Highs, Lower Lows, and Real Direction",
        "hook": "Before you call a market bullish, check what its swing points are actually doing.",
        "body": "A sequence of higher highs and higher lows can describe upward structure. Lower highs and lower lows can describe downward structure. One swing alone does not define the whole market, and structure can change. Mark the swings, zoom out for context, and wait for confirmation instead of forcing a label.",
        "visuals": ["MARK EACH SWING", "TRACE THE SEQUENCE", "ZOOM OUT FOR CONTEXT", "WAIT FOR CONFIRMATION"],
        "chart": "trend",
    },
    {
        "slug": "support-resistance",
        "title": "Support and Resistance Are Zones, Not Magic Lines",
        "hook": "If you expect price to respect one perfect line every time, rethink the chart.",
        "body": "Markets often react around areas rather than one exact price. Repeated reactions can help you mark a zone, but the zone is not a guaranteed floor or ceiling. Watch how price behaves when it returns, consider the higher timeframe, and decide what would invalidate your idea.",
        "visuals": ["MARK THE ZONE", "COMPARE REACTIONS", "CHECK HIGHER-TIMEFRAME CONTEXT", "DEFINE INVALIDATION"],
        "chart": "range",
    },
    {
        "slug": "risk-per-trade",
        "title": "Position Sizing Starts With Risk, Not the Lot Button",
        "hook": "Your lot size should not be the first decision you make.",
        "body": "Position sizing connects the distance to your invalidation point with the amount you can afford to risk. A larger position can magnify losses just as it can magnify gains. Understand the instrument, account currency, contract rules, and possible slippage before calculating size. If those inputs are unclear, do not guess.",
        "visuals": ["DEFINE RISK FIRST", "KNOW INVALIDATION", "CALCULATE SIZE", "NEVER GUESS INPUTS"],
        "chart": "risk",
    },
    {
        "slug": "overtrading",
        "title": "Overtrading Can Turn Small Decisions Into Big Problems",
        "hook": "More trades do not automatically mean more progress.",
        "body": "Repeated entries can come from boredom, frustration, or trying to recover a loss. A written plan can define when a setup is valid and when to stop for the day. Track whether each trade followed your rules rather than judging yourself only by the result. Sometimes the disciplined decision is to do nothing.",
        "visuals": ["NOTICE THE TRIGGER", "FOLLOW A WRITTEN PLAN", "TRACK PROCESS", "DO NOTHING WHEN NEEDED"],
        "chart": "range",
    },
    {
        "slug": "false-breakouts",
        "title": "False Breakouts: Read the Reaction, Not Just the Wick",
        "hook": "A candle poking beyond a level does not prove a breakout will hold.",
        "body": "Price can move beyond a visible level and then return to the prior range. Traders often call this a false breakout, but the label is clearer after observing the reaction. Look at the close, follow-through, surrounding structure, and your invalidation criteria. No single candle can guarantee continuation.",
        "visuals": ["LEVEL BREAKS", "CHECK THE CLOSE", "LOOK FOR FOLLOW-THROUGH", "PLAN INVALIDATION"],
        "chart": "break",
    },
    {
        "slug": "risk-reward",
        "title": "Risk-to-Reward Is a Planning Tool, Not a Win-Rate Promise",
        "hook": "A two-to-one reward-to-risk ratio does not guarantee a profitable strategy.",
        "body": "Reward-to-risk compares a planned potential gain with a planned potential loss. It does not tell you how often a setup wins, and real fills can differ because of costs or slippage. Evaluate a method over a meaningful sample, include expenses, and avoid treating one ratio as proof of an edge.",
        "visuals": ["COMPARE PLANNED OUTCOMES", "INCLUDE COSTS", "TRACK A SAMPLE", "RATIO ≠ EDGE"],
        "chart": "risk",
    },
    {
        "slug": "trading-journal",
        "title": "A Trading Journal Helps You Review Decisions, Not Predict Price",
        "hook": "Your journal is more useful when it records the decision—not just the profit.",
        "body": "Record the setup, the reason for entry, the invalidation point, the risk, and whether you followed your rules. Review a group of trades to look for repeated process errors. A small sample can be misleading, and a journal cannot remove uncertainty, but it can make your learning more structured.",
        "visuals": ["RECORD THE PLAN", "NOTE THE RISK", "REVIEW THE PROCESS", "LEARN FROM A SAMPLE"],
        "chart": "trend",
    },
    {
        "slug": "moving-averages",
        "title": "EMA Crosses Are Clues, Not Automatic Buy or Sell Signals",
        "hook": "EMA 20 crossed EMA 50. Does that automatically mean buy? No.",
        "body": "The 20-period exponential moving average reacts faster to recent prices than the 50-period EMA. A cross may help describe momentum, but both averages use past prices and lag. Sideways markets can produce repeated whipsaws. Check broader structure and risk before interpreting the chart.",
        "visuals": ["CROSS ≠ GUARANTEE", "COMPARE EMA 20 AND 50", "WATCH FOR WHIPSAWS", "CONTEXT BEFORE CONCLUSION"],
        "chart": "trend",
    },
]

SLOT_CRON_UTC = {"morning": (4, 47), "afternoon": (8, 47), "evening": (12, 47)}


def resolve_slot(now: datetime, requested: str | None = None) -> str:
    """Use the explicit scheduled slot; auto falls back to the most recent UTC cron window."""
    requested = (requested or "auto").strip().lower()
    if requested in SLOTS:
        return requested
    if requested != "auto":
        raise ValueError("SLOT_INPUT must be auto, morning, afternoon, or evening.")
    current_minute = now.hour * 60 + now.minute
    scheduled_minutes = {
        slot: hour * 60 + minute
        for slot, (hour, minute) in SLOT_CRON_UTC.items()
    }
    # Treat each cron time as the start of its slot window. Delayed starts
    # remain assigned to the most recent slot instead of drifting forward.
    elapsed_slots = [slot for slot in SLOTS if scheduled_minutes[slot] <= current_minute]
    if elapsed_slots:
        return max(elapsed_slots, key=lambda slot: scheduled_minutes[slot])
    return min(SLOTS, key=lambda slot: scheduled_minutes[slot])


def existing_draft_for_slot(out_dir: Path, utc_date: str, slot_name: str) -> Path | None:
    """Return a persisted draft for this UTC date/slot, preventing rerun duplicates."""
    for path in out_dir.glob("draft_*.json"):
        if path.name == "draft_seed.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        slot = data.get("schedule_slot")
        if (
            isinstance(slot, dict)
            and slot.get("utc_date") == utc_date
            and slot.get("name") == slot_name
            and str(data.get("content_id", "")).strip() == path.stem
        ):
            return path
    return None


def write_github_output(skip: bool, slot_name: str) -> None:
    """Expose only control metadata to subsequent workflow steps."""
    target = os.getenv("GITHUB_OUTPUT", "").strip()
    if not target:
        return
    with open(target, "a", encoding="utf-8") as handle:
        handle.write(f"skip={str(skip).lower()}\n")
        handle.write(f"slot={slot_name}\n")


def build_draft(now: datetime, slot_name: str) -> dict:
    """Build one original, evergreen draft for a particular daily slot."""
    if slot_name not in SLOTS:
        raise ValueError(f"Unsupported content slot: {slot_name}")
    slot_index = SLOTS.index(slot_name)
    # Each daily slot advances the evergreen-topic rotation so three daily drafts
    # cover different topics. The day number and slot also make this repeatable.
    topic_index = (now.date().toordinal() * len(SLOTS) + slot_index) % len(TOPICS)
    topic = TOPICS[topic_index]
    slug = topic["slug"]
    content_id = f"draft_{slug}_{slot_name}_{now.strftime('%Y%m%d_%H%M%S')}"
    scenes = [
        {"scene": i + 1, "text": label, "visual": visual}
        for i, (label, visual) in enumerate(zip(topic["visuals"], [
            "Premium institutional terminal; illustrative chart only.",
            "Animate one concept label with clean chart annotation.",
            "Show an illustrative counterexample or context panel.",
            "Finish with a concise risk-aware takeaway.",
        ]))
    ]
    return {
        "content_id": content_id,
        "created_at": now.isoformat(),
        "schedule_slot": {
            "name": slot_name,
            "utc_date": now.date().isoformat(),
            "index": slot_index,
        },
        "brand": "Bullseye Theory",
        "language": "English",
        "market": "Education",
        "audience": "Beginner to intermediate traders",
        "content_category": "Trading Education",
        "content_role": "education",
        "status": "draft_only",
        "topic": {"title": topic["title"], "source": "curated evergreen topic rotation", "score": 1.0},
        "research": {
            "summary": topic["body"],
            "sources": [
                {"name": "CME Group education", "url": "https://www.cmegroup.com/education.html", "type": "general_education_reference"},
                {"name": "Investor.gov", "url": "https://www.investor.gov/introduction-investing", "type": "general_investing_education"}
            ],
            "verification_scope": "evergreen concept draft; source links are general references, not claim-level citations; no live market data"
        },
        "fact_check": {
            "status": "needs_human_review",
            "notes": ["Evergreen educational copy; verify wording and any source claims before approval."],
            "source_count": 2,
            "verification_scope": "automated safety screen only; not independent fact verification"
        },
        "safety_check": {"passed": True, "blocked_phrases": [], "notes": "Draft only; no personalized advice, guaranteed outcomes, live price, or trade signal."},
        "script": {
            "hook": topic["hook"],
            "body": topic["body"],
            "cta": "Follow Bullseye Theory for practical chart breakdowns. Save this Reel and review the checklist before your next chart analysis.",
            "tagline": "FILTER THE NOISE. READ THE STRUCTURE. HIT THE BULLSEYE.",
            "disclaimer": "Educational content only—not financial advice. Illustrative chart, not a live signal. Trading involves risk."
        },
        "visual_plan": {
            "format": "short_video",
            "style": "Premium institutional trading terminal; deep obsidian navy, restrained metallic gold and neon lime; clear mobile-safe typography; illustrative chart only.",
            "chart_style": topic["chart"],
            "scenes": scenes
        },
        "social": {
            "caption": topic["hook"] + "\n\n" + topic["body"] + "\n\nEducational content only; not financial advice.",
            "hashtags": ["#BullseyeTheory", "#TradingEducation", "#TechnicalAnalysis", "#RiskManagement"]
        },
        "approval": {"required": True, "status": "draft_only", "mode": "human_review"},
        "reel_generated": False
    }


def main() -> int:
    now = datetime.now(timezone.utc)
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        slot_name = resolve_slot(now, os.getenv("SLOT_INPUT", os.getenv("CONTENT_SLOT", "auto")))
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    existing = existing_draft_for_slot(OUT, now.date().isoformat(), slot_name)
    if existing is not None:
        print(
            f"NO-OP: an educational Reel draft already exists for "
            f"{now.date().isoformat()} / {slot_name}: {existing.name}"
        )
        write_github_output(skip=True, slot_name=slot_name)
        return 0

    content = build_draft(now, slot_name)
    path = OUT / "draft_seed.json"
    path.write_text(json.dumps(content, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_github_output(skip=False, slot_name=slot_name)
    print(
        f"Prepared {slot_name} educational draft: {content['content_id']} | "
        f"{content['topic']['title']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
