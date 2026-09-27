#!/usr/bin/env python3

"""
Bullseye Theory — AI Trading Content Factory

Educational forex content automation only.
No trading, brokerage, order execution, or investment recommendations.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

BRAND = "Bullseye Theory"
OUTPUT_DIR = Path("output")
MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"

DISCLAIMER = (
    "Educational content only. This is not financial advice. "
    "Forex trading involves substantial risk, and losses are possible."
)


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def save_json(filename, data):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def trend_discovery():
    return [
        {
            "topic": "What Is a Support Level in Forex Trading?",
            "score": 0.90,
        },
        {
            "topic": "3 Common Mistakes Beginner Forex Traders Make",
            "score": 0.88,
        },
    ]


def research(topic):
    topic_lower = topic.lower()

    if "support level" in topic_lower:
        return {
            "summary": (
                "A support level is a price area where buying interest "
                "may be strong enough to slow or temporarily stop a decline. "
                "Support is not a guaranteed floor, and price can move below it."
            ),
            "key_points": [
                "Support is a price area, not an exact guaranteed price.",
                "Traders may identify support from previous areas where buying interest appeared.",
                "A support area can fail and price can move below it.",
                "Technical analysis does not guarantee future forex price movements.",
            ],
            "sources": [
                {
                    "name": "Fidelity — Support and Resistance",
                    "url": "https://www.fidelity.com/learning-center/trading-investing/technical-analysis/support-and-resistance",
                },
                {
                    "name": "Fidelity — What Is Technical Analysis?",
                    "url": "https://www.fidelity.com/learning-center/trading-investing/technical-analysis/what-is-technical-analysis",
                },
            ],
        }

    if "mistakes" in topic_lower:
        return {
            "summary": (
                "Beginner forex traders can face avoidable problems when "
                "they trade without a defined plan, misunderstand risk, "
                "or treat market predictions as guarantees."
            ),
            "key_points": [
                "Trading without a defined plan can make decisions inconsistent.",
                "Risk management matters because individual forex trades can result in losses.",
                "Past price movement does not guarantee future results.",
                "A trading idea is a possibility, not a guaranteed outcome.",
                "Educational content should not be presented as personalized financial advice.",
            ],
            "sources": [
                {
                    "name": "Fidelity — Trading and Investing Education",
                    "url": "",
                }
            ],
        }

    return {
        "summary": f"Beginner educational explanation of {topic}.",
        "key_points": [
            "Explain the concept in clear beginner-friendly English.",
            "Separate facts from predictions.",
            "Never present market outcomes as guaranteed.",
            "Verify important claims before public publishing.",
        ],
        "sources": [],
    }


def fact_check(research_data):
    sources = research_data.get("sources", [])
    return {
        "status": "review_required",
        "notes": [
            "Educational claims should be checked against the listed sources.",
            "Do not publish unverified claims as confirmed facts.",
            "Do not describe market outcomes as guaranteed.",
        ],
        "source_count": len(sources),
    }


def script_generation(topic, research_data):
    if "support level" in topic.lower():
        hook = "What is a support level in forex trading? Here is the simple explanation."
        body = (
            "A support level is a price area where buying interest may appear "
            "after a decline. Think of it as an area where price has previously "
            "found demand. But support is not a guaranteed floor. Price can break "
            "below it, so it should never be treated as a prediction or guarantee."
        )
        cta = "Follow Bullseye Theory for more beginner-friendly forex education."

    elif "mistakes" in topic.lower():
        hook = "3 common mistakes beginner forex traders should understand."
        body = (
            "First, trading without a clear plan. Second, ignoring risk management. "
            "Third, assuming past price movement guarantees the future. Forex markets "
            "are uncertain, so educational concepts should never be presented as "
            "guaranteed outcomes."
        )
        cta = "Follow Bullseye Theory for more practical forex education."

    else:
        hook = f"{topic} — explained in simple English."
        body = " ".join(research_data.get("key_points", []))
        cta = "Follow Bullseye Theory for more forex education."

    return {
        "hook": hook,
        "body": body,
        "cta": cta,
        "disclaimer": DISCLAIMER,
    }


def safety_check(script):
    text = " ".join(
        [
            script.get("hook", ""),
            script.get("body", ""),
            script.get("cta", ""),
        ]
    ).lower()

    blocked_phrases = [
        "guaranteed profit",
        "guaranteed return",
        "sure shot",
        "100% profit",
        "risk free",
        "risk-free",
        "buy now",
        "sell now",
        "all in",
        "double your money",
    ]

    found = [phrase for phrase in blocked_phrases if phrase in text]

    return {
        "passed": not found,
        "blocked_phrases": found,
        "notes": (
            "Content passed basic safety screening."
            if not found
            else "Potentially risky promotional language detected."
        ),
    }


def visual_plan(topic):
    if "support level" in topic.lower():
        return {
            "format": "short_video",
            "scenes": [
                {
                    "scene": 1,
                    "visual": "Clean forex price chart showing a horizontal support area.",
                    "text": "Support = price area",
                },
                {
                    "scene": 2,
                    "visual": "Currency-pair price approaches the support area.",
                    "text": "Buying interest may appear",
                },
                {
                    "scene": 3,
                    "visual": "Price breaks below the support area.",
                    "text": "Support can fail",
                },
                {
                    "scene": 4,
                    "visual": "Clean educational disclaimer screen.",
                    "text": "Not financial advice",
                },
            ],
        }

    return {
        "format": "short_video",
        "scenes": [
            {
                "scene": 1,
                "visual": "Clean beginner-friendly forex graphic.",
                "text": topic,
            },
            {
                "scene": 2,
                "visual": "Simple currency-pair chart or diagram.",
                "text": "Understand the concept",
            },
            {
                "scene": 3,
                "visual": "Risk-management reminder graphic.",
                "text": "Forex involves risk",
            },
            {
                "scene": 4,
                "visual": "Educational disclaimer.",
                "text": "Not financial advice",
            },
        ],
    }


def caption_and_hashtags(topic):
    if "support level" in topic.lower():
        caption = (
            "What is a support level in forex trading?\n\n"
            "A support level is a price area where buying interest may have "
            "appeared historically. It is not a guaranteed floor, and price "
            "can break below the area.\n\n"
            f"{DISCLAIMER}"
        )
        hashtags = [
            "#ForexTrading",
            "#ForexEducation",
            "#TechnicalAnalysis",
            "#SupportAndResistance",
            "#TradingEducation",
            "#BeginnerForex",
        ]

    elif "mistakes" in topic.lower():
        caption = (
            "3 common mistakes beginner forex traders should understand:\n"
            "1. Trading without a clear plan.\n"
            "2. Ignoring risk management.\n"
            "3. Treating past price movement as a guarantee.\n\n"
            f"{DISCLAIMER}"
        )
        hashtags = [
            "#ForexTrading",
            "#ForexEducation",
            "#BeginnerTrader",
            "#RiskManagement",
            "#TradingBasics",
            "#TradingEducation",
        ]

    else:
        caption = f"{topic}\n\nSimple educational forex content.\n\n{DISCLAIMER}"
        hashtags = [
            "#ForexTrading",
            "#ForexEducation",
            "#TradingEducation",
        ]

    return {"caption": caption, "hashtags": hashtags}


def build_content(item, index):
    topic = item["topic"]
    research_data = research(topic)
    fact_check_data = fact_check(research_data)
    script = script_generation(topic, research_data)
    safety = safety_check(script)
    visuals = visual_plan(topic)
    social = caption_and_hashtags(topic)

    status = "pending_approval" if safety["passed"] else "safety_review_required"

    return {
        "content_id": f"content_{index}",
        "created_at": now_utc(),
        "brand": BRAND,
        "language": "English",
        "market": "Forex",
        "audience": "Global",
        "status": status,
        "topic": {
            "title": topic,
            "source": "controlled_educational_topic",
            "score": item.get("score", 0),
        },
        "research": research_data,
        "fact_check": fact_check_data,
        "script": script,
        "safety_check": safety,
        "visual_plan": visuals,
        "social": social,
        "publishing": {
            "instagram": {"status": "not_published"},
            "telegram": {"status": "not_published"},
        },
        "approval": {
            "required": True,
            "status": "pending",
        },
    }


def create_approval_queue(contents):
    return {
        "updated_at": now_utc(),
        "items": [
            {
                "content_id": content["content_id"],
                "topic": content["topic"]["title"],
                "status": content["status"],
                "approval_required": True,
                "created_at": content["created_at"],
            }
            for content in contents
        ],
    }


def main():
    print("======================================")
    print("Bullseye Theory Forex Content Factory")
    print("======================================")
    print(f"Mock mode: {MOCK_MODE}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    topics = trend_discovery()
    contents = []

    for index, item in enumerate(topics, start=1):
        print(f"Generating content {index}: {item['topic']}")
        content = build_content(item, index)
        contents.append(content)
        save_json(f"content_{index}.json", content)
        print(f"Saved: content_{index}.json")

    save_json("approval_queue.json", create_approval_queue(contents))

    print("--------------------------------------")
    print(f"Generated: {len(contents)} English forex content items")
    print("Approval queue created.")
    print("--------------------------------------")


if __name__ == "__main__":
    main()
