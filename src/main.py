#!/usr/bin/env python3

"""
Bullseye Theory — AI Trading Content Factory

Educational content automation only.
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
    "Trading and investing involve risk, and losses are possible."
)


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def clean_text(value):
    if value is None:
        return ""
    return str(value).strip()


def save_json(filename, data):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
    return path


def trend_discovery():
    topics = [
        {
            "topic": "What is a Support Level in Trading?",
            "score": 0.90,
        },
        {
            "topic": "3 Common Mistakes Beginner Traders Make",
            "score": 0.88,
        },
    ]
    return topics


def research(topic):
    """
    Educational research content.
    This does not claim live verification.
    Sources must be checked before public publishing.
    """

    topic_lower = topic.lower()

    if "support level" in topic_lower:
        return {
            "summary": (
                "A support level is a price area where buying interest "
                "may be strong enough to slow or stop a decline. "
                "Support is not a guaranteed floor, and price can move "
                "below the area."
            ),
            "key_points": [
                "Support is better understood as a price area rather than an exact guaranteed price.",
                "Traders often identify support from previous price areas where buying interest appeared.",
                "A support area can fail and price can move below it.",
                "Technical analysis helps interpret market data but does not guarantee future price movement."
            ],
            "sources": [
                {
                    "name": "Fidelity — Support and Resistance",
                    "url": ""
                },
                {
                    "name": "Fidelity — What Is Technical Analysis?",
                    "url": ""
                }
            ]
        }

    if "mistakes" in topic_lower or "beginner traders" in topic_lower:
        return {
            "summary": (
                "Beginner traders can face avoidable problems when they "
                "trade without a defined plan, misunderstand risk, or "
                "treat market predictions as guarantees."
            ),
            "key_points": [
                "Trading without a defined plan can make decisions inconsistent.",
                "Risk management is important because individual trades can result in losses.",
                "Past price movement does not guarantee future results.",
                "A trading idea should be treated as a possibility rather than a guaranteed outcome.",
                "Educational content should remain separate from personalized financial advice."
            ],
            "sources": [
                {
                    "name": "Fidelity — Trading and Investing Education",
                    "url": ""
                }
            ]
        }

    return {
        "summary": (
            f"Beginner educational explanation of {topic}. "
            "Topic-specific claims should be verified against "
            "reliable sources before public publishing."
        ),
        "key_points": [
            "Explain the concept in simple beginner-friendly language.",
            "Separate facts from predictions.",
            "Do not present market outcomes as guaranteed.",
            "Verify important claims before publication."
        ],
        "sources": []
    }


def fact_check(research_data):
    sources = research_data.get("sources", [])

    if sources:
        status = "review_required"
        notes = [
            "Educational claims should be checked against the listed sources.",
            "Do not publish unverified claims as confirmed facts.",
            "Do not describe market outcomes as guaranteed."
        ]
    else:
        status = "review_required"
        notes = [
            "No source list is available for this topic.",
            "Verify important claims before public publishing."
        ]

    return {
        "status": status,
        "notes": notes,
        "source_count": len(sources)
    }


def script_generation(topic, research_data):
    points = research_data.get("key_points", [])

    if "support level" in topic.lower():
        hook = (
            "Support level kya hota hai? "
            "Chalo ise simple example se samajhte hain."
        )
        body = (
            "Support ek price area hota hai jahan past mein buying interest "
            "dekhne ko mila ho sakta hai. Important point ye hai ki support "
            "exact floor nahi hota. Price support ke neeche bhi ja sakta hai. "
            "Isliye support ko prediction ya guarantee nahi samajhna chahiye."
        )
        cta = (
            "Agar aap trading basics simple language mein seekhna chahte ho, "
            "follow for more educational content."
        )

    elif "mistakes" in topic.lower():
        hook = (
            "Beginner traders ki 3 common mistakes — "
            "kya aap bhi inmein se koi kar rahe ho?"
        )
        body = (
            "First, bina plan ke trade karna. Second, risk ko ignore karna. "
            "Third, past price movement ko future guarantee samajhna. "
            "Trading mein uncertainty hoti hai, isliye educational concepts "
            "ko guaranteed outcomes ki tarah present nahi karna chahiye."
        )
        cta = (
            "Aise beginner-friendly trading concepts ke liye "
            "follow for more educational content."
        )

    else:
        hook = f"{topic} — let's understand it in simple terms."
        body = " ".join(points)
        cta = "Follow for more beginner-friendly educational trading content."

    return {
        "hook": hook,
        "body": body,
        "cta": cta,
        "disclaimer": DISCLAIMER
    }


def safety_check(script):
    full_text = " ".join([
        clean_text(script.get("hook")),
        clean_text(script.get("body")),
        clean_text(script.get("cta"))
    ]).lower()

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
        "double your money"
    ]

    found = [
        phrase for phrase in blocked_phrases
        if phrase in full_text
    ]

    return {
        "passed": len(found) == 0,
        "blocked_phrases": found,
        "notes": (
            "Content passed basic safety screening."
            if not found
            else "Potentially risky promotional language detected."
        )
    }


def visual_plan(topic):
    if "support level" in topic.lower():
        return {
            "format": "short_video",
            "scenes": [
                {
                    "scene": 1,
                    "visual": "Simple price chart showing a horizontal support area.",
                    "text": "Support = price area"
                },
                {
                    "scene": 2,
                    "visual": "Price touches the support area and moves upward.",
                    "text": "Buying interest may appear"
                },
                {
                    "scene": 3,
                    "visual": "Price breaks below the support area.",
                    "text": "Support can fail"
                },
                {
                    "scene": 4,
                    "visual": "Educational disclaimer on screen.",
                    "text": "Not financial advice"
                }
            ]
        }

    return {
        "format": "short_video",
        "scenes": [
            {
                "scene": 1,
                "visual": "Clean beginner-friendly trading graphic.",
                "text": topic
            },
            {
                "scene": 2,
                "visual": "Simple educational chart or diagram.",
                "text": "Understand the concept"
            },
            {
                "scene": 3,
                "visual": "Risk reminder graphic.",
                "text": "Markets involve risk"
            },
            {
                "scene": 4,
                "visual": "Educational disclaimer.",
                "text": "Not financial advice"
            }
        ]
    }


def caption_and_hashtags(topic, research_data):
    if "support level" in topic.lower():
        caption = (
            "Support level ko simple language mein samjho: "
            "ye ek price area ho sakta hai jahan buying interest "
            "historically appear hua ho. "
            "Lekin support guaranteed floor nahi hota.\n\n"
            f"{DISCLAIMER}"
        )
        hashtags = [
            "#TradingEducation",
            "#TechnicalAnalysis",
            "#SupportAndResistance",
            "#TradingBasics",
            "#StockMarketEducation",
            "#BeginnerTrading"
        ]

    elif "mistakes" in topic.lower():
        caption = (
            "Beginner traders ke liye 3 important lessons: "
            "plan, risk awareness aur realistic expectations.\n\n"
            f"{DISCLAIMER}"
        )
        hashtags = [
            "#TradingEducation",
            "#TradingBasics",
            "#BeginnerTrader",
            "#RiskManagement",
            "#StockMarketEducation"
        ]

    else:
        caption = (
            f"{topic}\n\n"
            "Simple educational explanation for beginners.\n\n"
            f"{DISCLAIMER}"
        )
        hashtags = [
            "#TradingEducation",
            "#TradingBasics",
            "#StockMarketEducation"
        ]

    return {
        "caption": caption,
        "hashtags": hashtags
    }


def build_content(item, index):
    topic = item["topic"]

    research_data = research(topic)
    fact_check_data = fact_check(research_data)
    script = script_generation(topic, research_data)
    safety = safety_check(script)
    visuals = visual_plan(topic)
    social = caption_and_hashtags(topic, research_data)

    status = "pending_approval" if safety["passed"] else "safety_review_required"

    return {
        "content_id": f"content_{index}",
        "created_at": now_utc(),
        "brand": BRAND,
        "status": status,
        "topic": {
            "title": topic,
            "source": "controlled_educational_topic",
            "score": item.get("score", 0)
        },
        "research": research_data,
        "fact_check": fact_check_data,
        "script": script,
        "safety_check": safety,
        "visual_plan": visuals,
        "social": social,
        "publishing": {
            "instagram": {"status": "not_published"},
            "telegram": {"status": "not_published"}
        },
        "approval": {
            "required": True,
            "status": "pending"
        }
    }


def create_approval_queue(contents):
    queue = []

    for content in contents:
        queue.append({
            "content_id": content["content_id"],
            "topic": content["topic"]["title"],
            "status": content["status"],
            "approval_required": True,
            "created_at": content["created_at"]
        })

    return {
        "updated_at": now_utc(),
        "items": queue
    }


def main():
    print("======================================")
    print("Bullseye Theory Content Factory")
    print("======================================")
    print(f"Mock mode: {MOCK_MODE}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    topics = trend_discovery()
    contents = []

    for index, item in enumerate(topics, start=1):
        print(f"Generating content {index}: {item['topic']}")

        content = build_content(item, index)
        contents.append(content)

        filename = f"content_{index}.json"
        save_json(filename, content)
        print(f"Saved: {filename}")

    approval_queue = create_approval_queue(contents)
    save_json("approval_queue.json", approval_queue)

    print("--------------------------------------")
    print("Pipeline completed successfully.")
    print(f"Generated: {len(contents)} content items")
    print("Approval queue created.")
    print("--------------------------------------")


if __name__ == "__main__":
    main()
