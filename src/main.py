#!/usr/bin/env python3

"""
Bullseye Theory — AI Trading Content Factory

Creates two English educational trading Reels per daily run.
The system is designed for chart education, market structure, risk awareness,
trading psychology, and disciplined learning. It does not provide personalized
financial advice, trade signals, or guaranteed-return claims.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

BRAND = "Bullseye Theory"
OUTPUT_DIR = Path("output")
MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"
AUTO_PUBLISH_ENABLED = os.getenv("AUTO_PUBLISH_ENABLED", "false").lower() == "true"

PHILOSOPHY = "TRADING IS NOT FOR THOSE WHO DON'T HAVE PATIENCE.  LEARN | TRADE | EARN"

DISCLAIMER = (
    "Educational content only. This is not financial advice. "
    "Trading involves substantial risk, and losses are possible."
)

# Evergreen expert-style educational topics. The daily run selects two topics
# deterministically so the page gets variety without inventing live market data.
TOPICS = [
    {
        "title": "Why Support and Resistance Are Zones, Not Magic Lines",
        "market": "Forex",
        "category": "Technical Analysis",
        "hook": "If you draw one perfect support line and expect price to respect it, stop for a second.",
        "body": (
            "Markets often react around price areas, not a single exact number. "
            "Look for repeated reactions, failed breaks, and context from the higher timeframe. "
            "A zone can help organize your analysis, but it is never a guaranteed floor or ceiling. "
            "The real skill is reading what price does when it reaches the area."
        ),
        "visuals": [
            ("ILLUSTRATIVE CHART", "Show a shaded support zone with three historical reactions."),
            ("READ THE REACTION", "Highlight rejection, compression, and a failed break."),
            ("CONTEXT MATTERS", "Zoom out to a higher timeframe before drawing conclusions."),
            ("NO GUARANTEE", "Show price moving through the zone to reinforce uncertainty."),
        ],
        "hashtags": ["#ForexTrading", "#TechnicalAnalysis", "#PriceAction", "#TradingEducation", "#BullseyeTheory"],
    },
    {
        "title": "Market Structure: Higher Highs, Lower Lows, and Real Direction",
        "market": "Forex",
        "category": "Market Structure",
        "hook": "Before you call a market bullish or bearish, learn to read its structure.",
        "body": (
            "A simple starting point is to track swing highs and swing lows. "
            "A sequence of higher highs and higher lows can show upward structure, while lower highs "
            "and lower lows can show downward structure. But structure can change. "
            "Do not force a trend label onto every chart; wait for price to confirm what it is actually doing."
        ),
        "visuals": [
            ("SWING POINTS", "Mark clean swing highs and swing lows on an illustrative chart."),
            ("STRUCTURE", "Connect higher highs and higher lows with subtle guide lines."),
            ("SHIFT", "Show one break that changes the sequence."),
            ("STAY PATIENT", "End with a chart waiting for confirmation instead of a trade signal."),
        ],
        "hashtags": ["#ForexTrading", "#MarketStructure", "#PriceAction", "#TradingEducation", "#BullseyeTheory"],
    },
    {
        "title": "Why Leverage Can Magnify Losses as Fast as Gains",
        "market": "Forex",
        "category": "Risk Management",
        "hook": "Leverage can make a small account look powerful. That is exactly why you need respect for risk.",
        "body": (
            "Leverage increases the size of a position relative to your capital, which can amplify both "
            "gains and losses. More buying power does not create more trading skill. "
            "A larger position can make an ordinary market move have a much larger effect on your account. "
            "Understanding exposure and position size comes before trying to trade bigger."
        ),
        "visuals": [
            ("EXPOSURE", "Compare small and large notional exposure on an illustrative dashboard."),
            ("SAME MOVE", "Show the same price movement affecting two different position sizes."),
            ("LOSS CAN SCALE", "Visualize how larger exposure increases the dollar impact."),
            ("CONTROL THE SIZE", "Finish with a position-sizing checklist, not a profit promise."),
        ],
        "hashtags": ["#ForexTrading", "#RiskManagement", "#Leverage", "#TradingEducation", "#BullseyeTheory"],
    },
    {
        "title": "The Difference Between a Setup and a Guarantee",
        "market": "Forex",
        "category": "Trading Psychology",
        "hook": "A trading setup is a hypothesis, not a promise.",
        "body": (
            "Even a clean chart pattern can fail. Professional-style analysis starts with a clear idea, "
            "defines what would invalidate that idea, and accepts that the market can do something else. "
            "This mindset keeps you focused on process instead of pretending to know the future. "
            "The goal is not certainty. The goal is disciplined decision-making under uncertainty."
        ),
        "visuals": [
            ("THE SETUP", "Show a clean illustrative pattern with a highlighted area of interest."),
            ("INVALIDATION", "Mark the exact point where the original idea stops making sense."),
            ("TWO PATHS", "Animate both continuation and failure scenarios."),
            ("PROCESS OVER PREDICTION", "Replace a certainty icon with a process checklist."),
        ],
        "hashtags": ["#TradingPsychology", "#ForexEducation", "#PriceAction", "#TradingMindset", "#BullseyeTheory"],
    },
    {
        "title": "Why Overtrading Can Destroy Good Decision-Making",
        "market": "Forex",
        "category": "Trading Psychology",
        "hook": "More trades do not automatically mean more opportunity.",
        "body": (
            "Overtrading can happen when boredom, frustration, or the need to recover a loss starts "
            "driving decisions. A disciplined trader can spend more time waiting than clicking. "
            "Build a checklist, define what qualifies as a setup, and learn to do nothing when the chart "
            "does not meet your conditions. Patience is part of the strategy."
        ),
        "visuals": [
            ("NOISE", "Fill an illustrative terminal with low-quality signals and alerts."),
            ("CHECKLIST", "Filter the noise through a simple setup checklist."),
            ("WAIT", "Show an empty chart area with a patience timer."),
            ("DISCIPLINE", "End on a clean rule: no setup, no trade."),
        ],
        "hashtags": ["#TradingPsychology", "#ForexTrading", "#Discipline", "#TradingEducation", "#BullseyeTheory"],
    },
    {
        "title": "Risk-to-Reward: What It Actually Tells You",
        "market": "Forex",
        "category": "Risk Management",
        "hook": "Risk-to-reward is useful, but it does not predict whether a trade will win.",
        "body": (
            "Risk-to-reward compares a planned loss with a planned target. "
            "It can help traders think in terms of potential payoff versus exposure, but it says nothing "
            "about whether price will reach the target. A high ratio does not rescue a weak setup. "
            "Use it as one part of a broader risk framework, not as a shortcut to confidence."
        ),
        "visuals": [
            ("DEFINE RISK", "Mark a hypothetical entry, invalidation, and target on an illustrative chart."),
            ("COMPARE", "Show the distance from risk to reward with clean measurement lines."),
            ("RATIO ≠ WIN RATE", "Cross out a fake certainty icon and label the ratio correctly."),
            ("USE CONTEXT", "Pair the ratio with structure and risk limits."),
        ],
        "hashtags": ["#RiskManagement", "#ForexTrading", "#TradingEducation", "#PriceAction", "#BullseyeTheory"],
    },
    {
        "title": "False Breakouts: Read the Reaction, Not Just the Wick",
        "market": "Forex",
        "category": "Price Action",
        "hook": "A breakout is not confirmed just because price poked through a level.",
        "body": (
            "A false breakout can occur when price moves beyond a level and then returns back inside the area. "
            "Instead of reacting to one candle, study the close, follow-through, and what happens next. "
            "A single wick is information, not proof. Waiting for confirmation can reduce impulsive decisions, "
            "while still leaving room for the market to surprise you."
        ),
        "visuals": [
            ("THE BREAK", "Animate price briefly moving beyond a resistance zone."),
            ("THE REJECTION", "Highlight the close back inside the zone."),
            ("FOLLOW-THROUGH", "Show why the next candles matter more than one wick."),
            ("CONFIRMATION", "Finish with a patient observation window."),
        ],
        "hashtags": ["#PriceAction", "#ForexTrading", "#TechnicalAnalysis", "#TradingEducation", "#BullseyeTheory"],
    },
    {
        "title": "Trend or Range? Stop Using the Same Playbook Everywhere",
        "market": "Forex",
        "category": "Market Context",
        "hook": "One of the fastest ways to misread a chart is to treat every market like a trend.",
        "body": (
            "Trending markets often create directional swings, while ranging markets rotate between boundaries. "
            "The same entry idea can behave very differently in those two environments. "
            "Start by asking what the market is doing before choosing your framework. "
            "Context first, setup second. Do not force a trend simply because you want one."
        ),
        "visuals": [
            ("TREND", "Show clean directional swings and a rising structure."),
            ("RANGE", "Transition to price rotating between two boundaries."),
            ("COMPARE", "Place the two environments side by side."),
            ("CONTEXT FIRST", "Highlight the question: trend, range, or unclear?"),
        ],
        "hashtags": ["#ForexTrading", "#MarketStructure", "#PriceAction", "#TradingEducation", "#BullseyeTheory"],
    },
    {
        "title": "Big Capital Does Not Fix Bad Risk Management",
        "market": "Multi-Market",
        "category": "Risk Management",
        "hook": "More money in an account does not make a bad risk process safer.",
        "body": (
            "Large capital can create large exposure, and careless position sizing can turn an ordinary market move "
            "into a large loss. The amount of money involved is not the same thing as the quality of the decision. "
            "Strong processes start with defined risk, realistic expectations, and the ability to walk away from "
            "a market that does not fit the plan."
        ),
        "visuals": [
            ("CAPITAL ≠ SKILL", "Show a large account number beside a warning about exposure."),
            ("POSITION SIZE", "Animate exposure increasing while the market move stays identical."),
            ("RISK LIMITS", "Display a simple pre-trade risk checklist."),
            ("STAY HUMBLE", "End with process, not profit screenshots."),
        ],
        "hashtags": ["#RiskManagement", "#TradingPsychology", "#ForexTrading", "#TradingEducation", "#BullseyeTheory"],
    },
    {
        "title": "Patience Is a Trading Skill, Not Dead Time",
        "market": "Multi-Market",
        "category": "Trading Psychology",
        "hook": "Sometimes the best trading decision is to wait.",
        "body": (
            "Patience means allowing the market to reach the conditions you have defined instead of inventing "
            "a trade because you feel pressure to act. Waiting can feel boring, especially after a loss or a missed move. "
            "But discipline is built when you follow the process even when nothing exciting is happening. "
            "Learn to value observation as much as execution."
        ),
        "visuals": [
            ("WAIT", "Show a chart moving without a valid setup."),
            ("NO CHASE", "Animate price moving away while the trader stays on the plan."),
            ("READY", "Show the checklist becoming valid later."),
            ("PATIENT PROCESS", "Finish with the Bullseye Theory philosophy."),
        ],
        "hashtags": ["#TradingPsychology", "#TradingDiscipline", "#ForexEducation", "#TradingMindset", "#BullseyeTheory"],
    },
    {
        "title": "Why a Trading Journal Can Improve Your Learning Loop",
        "market": "Multi-Market",
        "category": "Process",
        "hook": "Your chart may forget your mistakes. Your journal should not.",
        "body": (
            "A useful trading journal records the setup, the reason for the decision, the risk, the outcome, "
            "and what you would change next time. The point is not to collect screenshots. "
            "The point is to identify repeated behavior. A journal turns random experiences into a feedback loop "
            "that can help you study your own process."
        ),
        "visuals": [
            ("RECORD", "Show a clean journal template beside a chart."),
            ("REVIEW", "Highlight the decision, risk, and outcome fields."),
            ("FIND PATTERNS", "Group repeated mistakes into a simple dashboard."),
            ("IMPROVE", "End with one process change for the next session."),
        ],
        "hashtags": ["#TradingJournal", "#TradingPsychology", "#TradingEducation", "#ForexTrading", "#BullseyeTheory"],
    },
    {
        "title": "News Volatility Can Change the Trading Environment",
        "market": "Forex",
        "category": "Market Context",
        "hook": "The chart can change character when major economic news hits.",
        "body": (
            "High-impact economic releases can coincide with rapid price movement, wider spreads, and sudden changes "
            "in liquidity conditions. That does not tell you which direction price will move. "
            "It tells you the environment may be different from a quiet session. "
            "Knowing the calendar and adjusting your risk process is part of responsible market preparation."
        ),
        "visuals": [
            ("ECONOMIC CALENDAR", "Show an illustrative high-impact event on a calendar."),
            ("VOLATILITY", "Animate candle ranges expanding around the event."),
            ("UNCERTAINTY", "Show movement in both directions without a prediction."),
            ("PREPARE", "End on a calendar-and-risk checklist."),
        ],
        "hashtags": ["#ForexTrading", "#EconomicCalendar", "#RiskManagement", "#TradingEducation", "#BullseyeTheory"],
    },
    {
        "title": "Position Sizing Starts With Risk, Not With the Lot Button",
        "market": "Forex",
        "category": "Risk Management",
        "hook": "Do not choose position size first and ask about risk later.",
        "body": (
            "Position sizing begins with how much risk your plan allows, not with the biggest lot size you can click. "
            "The same stop distance can create very different account impact at different position sizes. "
            "Learning the relationship between capital, stop distance, and exposure is a core trading skill. "
            "Bigger size is not the same thing as a better trade."
        ),
        "visuals": [
            ("START WITH RISK", "Show a risk budget before a position-size control."),
            ("STOP DISTANCE", "Illustrate how changing stop distance changes exposure."),
            ("SIZE THE POSITION", "Show smaller and larger notional sizes against the same move."),
            ("DISCIPLINE", "Finish with a clean sizing checklist."),
        ],
        "hashtags": ["#RiskManagement", "#PositionSizing", "#ForexTrading", "#TradingEducation", "#BullseyeTheory"],
    },
    {
        "title": "Liquidity: Why Price Can Move Fast Around Key Areas",
        "market": "Forex",
        "category": "Market Microstructure",
        "hook": "Sometimes price moves fast because the liquidity around it changes.",
        "body": (
            "Liquidity describes how easily buying and selling can happen without a large price impact. "
            "When liquidity is thinner or many orders interact around the same area, price can move quickly and "
            "slippage can become more relevant. Treat liquidity as a market condition to understand, not as a magic "
            "signal that tells you what happens next."
        ),
        "visuals": [
            ("LIQUIDITY", "Show a stylized depth-of-market concept."),
            ("KEY AREA", "Highlight clustered activity around a price zone."),
            ("FAST MOVE", "Animate a sharp illustrative candle sequence."),
            ("NO MAGIC SIGNAL", "Separate market condition from directional prediction."),
        ],
        "hashtags": ["#ForexTrading", "#Liquidity", "#MarketMicrostructure", "#TradingEducation", "#BullseyeTheory"],
    },
]


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
    # Two topics per daily run. The rotation is deterministic and avoids
    # pretending that we have live market-news data when no live feed is configured.
    day_number = datetime.now(timezone.utc).timetuple().tm_yday
    start = (day_number * 2) % len(TOPICS)
    selected = [TOPICS[start], TOPICS[(start + 1) % len(TOPICS)]]
    return [
        {
            **topic,
            "score": round(0.84 + ((day_number + i) % 8) / 100, 2),
        }
        for i, topic in enumerate(selected)
    ]


def research(item):
    return {
        "summary": item["body"],
        "key_points": [
            item["body"],
            "Educational analysis should distinguish a scenario from a guarantee.",
            "Risk management and process discipline remain central to responsible trading education.",
        ],
        "sources": [
            {
                "name": "Bullseye Theory educational framework",
                "url": "",
                "type": "internal_educational_reference",
            }
        ],
    }


def fact_check(research_data):
    sources = research_data.get("sources", [])
    return {
        "status": "review_required",
        "notes": [
            "Review the educational claims and chart interpretation before approval.",
            "Do not publish unverified claims as confirmed facts.",
            "Do not describe market outcomes, profits, or losses as guaranteed.",
            "Do not turn educational analysis into personalized financial advice or direct trade instructions.",
        ],
        "source_count": len(sources),
    }


def script_generation(item, research_data):
    return {
        "hook": item["hook"],
        "body": item["body"],
        "cta": (
            "Follow Bullseye Theory for practical chart analysis, disciplined trading education, "
            "and realistic market thinking."
        ),
        "tagline": PHILOSOPHY,
        "disclaimer": DISCLAIMER,
    }


def safety_check(script):
    text = " ".join(
        [
            script.get("hook", ""),
            script.get("body", ""),
            script.get("cta", ""),
            script.get("tagline", ""),
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
        "easy money",
        "get rich",
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


def visual_plan(item):
    return {
        "format": "short_video",
        "style": (
            "Premium institutional forex aesthetic: dark obsidian trading terminal, "
            "Dubai-inspired luxury skyline silhouettes, metallic gold accents, restrained neon lime signals, "
            "USD/currency motifs, realistic illustrative candlestick charts, cinematic motion, and clean typography. "
            "Charts are illustrative and never presented as live signals."
        ),
        "scenes": [
            {
                "scene": i + 1,
                "visual": visual,
                "text": text,
            }
            for i, (text, visual) in enumerate(item["visuals"])
        ],
    }


def caption_and_hashtags(item):
    caption = (
        f"{item['title']}\n\n"
        f"{item['body']}\n\n"
        f"{PHILOSOPHY}\n\n"
        f"{DISCLAIMER}"
    )
    return {
        "caption": caption,
        "hashtags": item["hashtags"],
    }


def build_content(item, index):
    research_data = research(item)
    fact_check_data = fact_check(research_data)
    script = script_generation(item, research_data)
    safety = safety_check(script)
    visuals = visual_plan(item)
    social = caption_and_hashtags(item)

    status = "approved_for_publishing" if (AUTO_PUBLISH_ENABLED and safety["passed"]) else ("pending_approval" if safety["passed"] else "safety_review_required")

    return {
        "content_id": f"content_{index}",
        "created_at": now_utc(),
        "brand": BRAND,
        "language": "English",
        "market": item["market"],
        "audience": "Global",
        "content_category": item["category"],
        "status": status,
        "topic": {
            "title": item["title"],
            "source": "daily_rotating_educational_topic",
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
            "required": not AUTO_PUBLISH_ENABLED,
            "status": "approved" if (AUTO_PUBLISH_ENABLED and safety["passed"]) else "pending",
            "mode": "automatic" if AUTO_PUBLISH_ENABLED else "manual",
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
                "approval_required": content["approval"].get("required", True),
                "created_at": content["created_at"],
            }
            for content in contents
        ],
    }


def main():
    print("=============================================")
    print("Bullseye Theory — AI Trading Content Factory")
    print("=============================================")
    print(f"Mock mode: {MOCK_MODE}")
    print(f"Automatic publishing mode: {AUTO_PUBLISH_ENABLED}")
    print(f"Daily philosophy: {PHILOSOPHY}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    topics = trend_discovery()
    contents = []

    for index, item in enumerate(topics, start=1):
        print(f"Generating content {index}: {item['title']}")
        content = build_content(item, index)
        contents.append(content)
        save_json(f"content_{index}.json", content)
        print(f"Saved: content_{index}.json")

    save_json("approval_queue.json", create_approval_queue(contents))

    print("---------------------------------------------")
    print(f"Generated: {len(contents)} English educational Reel drafts")
    print("Approval queue created.")
    print("---------------------------------------------")


if __name__ == "__main__":
    main()
