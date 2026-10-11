#!/usr/bin/env python3

"""
Bullseye Theory — AI Trading Content Factory

Creates English educational trading Reel drafts for scheduled daily publishing windows.
The system is designed for chart education, market structure, risk awareness,
trading psychology, and disciplined learning. It does not provide personalized
financial advice, trade signals, or guaranteed-return claims.
"""

import json
import os
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

from config.env import human_approval_required

from free_llm_router import generate_json

BRAND = "Bullseye Theory"
OUTPUT_DIR = Path("output")
MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"
AUTO_PUBLISH_ENABLED = os.getenv("AUTO_PUBLISH_ENABLED", "false").lower() == "true"
HUMAN_APPROVAL = human_approval_required()
TOPIC_HISTORY_PATH = OUTPUT_DIR / "recent_topics.json"
TOPIC_REPEAT_DAYS = 10
CONTENT_BATCH_SIZE = max(1, min(int(os.getenv("CONTENT_BATCH_SIZE", "1")), 3))

PHILOSOPHY = "TRADING IS NOT FOR THOSE WHO DON'T HAVE PATIENCE.  LEARN | TRADE | EARN"

DISCLAIMER = (
    "Educational content only. This is not financial advice. "
    "Trading involves substantial risk, and losses are possible."
)

REFERENCE_DNA_PATH = Path("config/reference_content_dna.json")

def load_reference_dna():
    try:
        return json.loads(REFERENCE_DNA_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "derived_content_pillars": [],
            "format_principles": [],
            "conversion_principles": [],
            "target_mix": {"education": 70, "authority_and_trust": 20, "course_conversion": 10},
        }

REFERENCE_DNA = load_reference_dna()

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
    {
        "title": "What You Actually Learn Inside Bullseye Theory",
        "market": "Multi-Market",
        "category": "Course Preview",
        "hook": "A trading course should teach you a process, not sell you a dream.",
        "body": (
            "Bullseye Theory is built around the foundations that traders need before chasing complexity: "
            "market structure, trend and context, price action, risk management, trading psychology, and disciplined execution. "
            "The goal is to help learners understand why a chart behaves the way it does and build a repeatable learning process. "
            "Trading remains uncertain, and education cannot remove market risk."
        ),
        "visuals": [
            ("THE FOUNDATION", "Reveal a premium course curriculum grid."),
            ("THE FRAMEWORK", "Animate market structure, price action, risk, and psychology modules."),
            ("THE PROCESS", "Show lessons moving from concept to chart application."),
            ("LEARN FIRST", "Finish with the Bullseye Theory website/course CTA and risk disclaimer."),
        ],
        "hashtags": ["#BullseyeTheory", "#TradingEducation", "#ForexEducation", "#TradingCourse", "#TradingPsychology"],
    },
    {
        "title": "Before You Learn Entries, Learn These Four Trading Foundations",
        "market": "Multi-Market",
        "category": "Course Preview",
        "hook": "If you only learn entries, you are learning the smallest part of trading.",
        "body": (
            "Before focusing on entries, build four foundations: market structure, context, risk management, and psychology. "
            "These determine how you interpret a setup, how much exposure you take, and how you behave when the market does not cooperate. "
            "A good education should connect all four instead of teaching an isolated pattern as a shortcut."
        ),
        "visuals": [
            ("01 STRUCTURE", "Mark higher highs, lower lows, and structural shifts."),
            ("02 CONTEXT", "Compare trend, range, and unclear conditions."),
            ("03 RISK", "Show position size and invalidation before a target."),
            ("04 PSYCHOLOGY", "End with discipline and patience, then a soft course CTA."),
        ],
        "hashtags": ["#BullseyeTheory", "#TradingEducation", "#MarketStructure", "#RiskManagement", "#TradingMindset"],
    }
]



# Additional evergreen topics keep the ten-day no-repeat policy feasible at three runs/day.
_ADDITIONAL_TOPIC_SEEDS = [
    ("Why Backtesting Needs Out-of-Sample Validation", "Process", "A strategy that only works on the data you tested may be overfit.", "Separate the data used to develop a trading idea from the data used to evaluate it. Out-of-sample checks can reveal whether a pattern generalizes, though they cannot guarantee future performance."),
    ("The Difference Between Volatility and Direction", "Market Context", "A market can move a lot without giving a clear direction.", "Volatility describes the scale of price movement, not whether the next move will be up or down. Keep directional bias separate from the question of how quickly prices are changing."),
    ("Why Candlestick Patterns Need Context", "Price Action", "A candle pattern without context is only a shape.", "Candlestick formations are observations, not guarantees. Interpret them alongside market structure, timeframe, location, and follow-through rather than treating a single candle as a complete trading thesis."),
    ("How Timeframes Can Tell Different Stories", "Market Structure", "The five-minute chart and daily chart can disagree without either being broken.", "Different timeframes show different parts of market behavior. Define which timeframe provides context and which provides detail before drawing conclusions from conflicting signals."),
    ("What Slippage Means in Fast Markets", "Risk Management", "The price you expect is not always the price you receive.", "Slippage is the difference between an expected execution price and the actual fill. Fast markets, thin liquidity, and order type can affect execution, so plans should account for uncertainty."),
    ("Why Stop Placement Is About Invalidation", "Risk Management", "A stop should relate to the idea becoming invalid, not to hope.", "A risk limit should be connected to the assumptions behind an analysis. No placement method guarantees a small loss in every market condition, especially when gaps or slippage occur."),
    ("How to Recognize Confirmation Bias on a Chart", "Trading Psychology", "If you only notice evidence that supports your idea, pause.", "Confirmation bias makes people favor information that agrees with an existing belief. Deliberately write down what would disprove a thesis and review opposing evidence before deciding how strong the idea is."),
    ("Why a Missed Move Is Not a Trading Failure", "Trading Psychology", "Missing a move can be better than breaking your process.", "A disciplined process cannot capture every market move. Chasing after price has moved can create decisions that were never part of a plan. Review the process, not the emotional urge to catch up."),
    ("What a Trading Drawdown Actually Measures", "Risk Management", "A drawdown describes a decline from a previous equity peak.", "Drawdown helps describe the depth of a decline from a prior peak. It is not a prediction of recovery time, and hypothetical drawdowns should never be confused with a real broker record."),
    ("Why Correlated Markets Can Increase Exposure", "Risk Management", "Different tickers do not always mean different risks.", "Assets can move together during particular regimes. Multiple positions may share exposure to the same underlying driver, so diversification should be assessed by risk behavior rather than by counting symbols."),
    ("The Difference Between a Breakout and Follow-Through", "Price Action", "A level can break once and still fail to establish direction.", "A breakout is an event; follow-through is additional behavior after that event. Neither removes uncertainty. Observe closes, subsequent price action, and the broader structure before describing a move."),
    ("How to Build a Pre-Analysis Checklist", "Process", "A checklist helps you slow down before forming a market view.", "A useful checklist can cover context, structure, volatility, key levels, risk assumptions, and invalidation. It should help identify missing information, not mechanically force a trade idea."),
    ("Why Trading Costs Belong in Every Review", "Risk Management", "Fees and spreads can change the result of a strategy.", "Spreads, commissions, financing, and slippage affect realized outcomes. Backtests that omit trading costs can overstate results, so any evaluation should document assumptions and limitations."),
    ("What Market Regimes Mean for Strategy Evaluation", "Market Context", "A method tested in one market regime may behave differently in another.", "Markets can alternate between trending, ranging, volatile, and quiet conditions. Compare strategy behavior across different regimes and avoid assuming that one historical period represents all future environments."),
    ("Why Journaling the Decision Matters More Than the Screenshot", "Process", "A chart screenshot shows price; a journal explains your reasoning.", "Record the context, assumptions, risk, emotions, and outcome of a decision. A useful journal helps identify repeated process errors instead of merely collecting attractive chart images."),
    ("How to Separate Observation From Interpretation", "Technical Analysis", "Price made a move; your explanation of that move is a separate claim.", "Observation describes what the chart shows. Interpretation explains what it might mean. Keeping those separate helps avoid presenting uncertain narratives as facts and makes analysis easier to review."),
    ("Why One Winning Example Does Not Prove an Edge", "Process", "One successful example is not enough to validate a method.", "A single outcome can occur by chance. Evaluating an approach requires a defined method, a meaningful sample, realistic costs, and attention to selection bias. Past examples do not guarantee future results."),
    ("What to Do When the Market Is Unclear", "Trading Psychology", "Unclear is a valid market assessment.", "A responsible analysis can conclude that the available evidence is mixed. Label uncertainty explicitly, define what information would change the assessment, and avoid forcing a directional narrative."),
    ("Why Risk Limits Need to Be Defined Beforehand", "Risk Management", "Rules written after a loss are harder to follow consistently.", "Predefined risk limits reduce the temptation to change rules under pressure. They cannot eliminate losses, but they create a consistent framework for reviewing decisions and limiting discretionary escalation."),
    ("How to Review a Strategy Without Cherry-Picking", "Process", "Review the full sample, not only the examples that look convincing.", "A balanced review includes losing periods, flat periods, costs, and failed setups. Selecting only favorable examples can create a misleading impression of reliability and should not be used as evidence of guaranteed performance."),
]
for _title, _category, _hook, _body in _ADDITIONAL_TOPIC_SEEDS:
    TOPICS.append({
        "title": _title,
        "market": "Multi-Market",
        "category": _category,
        "hook": _hook,
        "body": _body,
        "visuals": [
            ("OBSERVE", f"Illustrate the core concept: {_title}."),
            ("ADD CONTEXT", "Show market structure and relevant assumptions without live-price claims."),
            ("TEST THE IDEA", "Contrast supporting evidence with a possible failure case."),
            ("DISCIPLINE", "Finish with a practical checklist and an uncertainty reminder."),
        ],
        "hashtags": ["#BullseyeTheory", "#TradingEducation", "#RiskManagement", "#TechnicalAnalysis"],
    })



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
    """Choose topics not used in the previous ten days, persisted across runs."""
    now = datetime.now(timezone.utc)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        history = json.loads(TOPIC_HISTORY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        history = []
    cutoff = now - timedelta(days=TOPIC_REPEAT_DAYS)
    recent = []
    for row in history if isinstance(history, list) else []:
        try:
            used = datetime.fromisoformat(str(row["used_at"]).replace("Z", "+00:00"))
            if used.tzinfo is None:
                used = used.replace(tzinfo=timezone.utc)
            if used >= cutoff:
                recent.append(row)
        except (KeyError, TypeError, ValueError):
            continue
    used_titles = {str(row.get("title", "")) for row in recent}
    offset = int(now.timestamp()) % len(TOPICS)
    ordered = TOPICS[offset:] + TOPICS[:offset]
    available = [topic for topic in ordered if topic["title"] not in used_titles]
    if not available:
        print("No unused topics remain inside the ten-day repeat window.")
        return []
    selected = [dict(topic) for topic in available[:CONTENT_BATCH_SIZE]]
    day_number, slot = now.timetuple().tm_yday, now.hour // 6
    for i, topic in enumerate(selected):
        topic["score"] = round(0.84 + ((day_number + slot + i) % 8) / 100, 2)
        recent.append({"title": topic["title"], "used_at": now.isoformat()})
    TOPIC_HISTORY_PATH.write_text(json.dumps(recent, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8")
    return selected


def research(item):
    return {
        "summary": item["body"],
        "reference_strategy": {
            "source_type": "six_account_reference_dna",
            "pillars": REFERENCE_DNA.get("derived_content_pillars", []),
            "format_principles": REFERENCE_DNA.get("format_principles", []),
            "rule": "Use reference accounts for patterns and topic research only; generate original Bullseye Theory wording, visuals, and analysis.",
        },
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
    # The built-in topic library is evergreen education only: no live prices,
    # news, trade calls, performance claims, or market-outcome predictions.
    # This status means the automated evergreen-content screen passed; it is
    # not a claim that live market data or a specific trade has been verified.
    summary = str(research_data.get("summary", ""))
    blocked_claims = (
        "guaranteed profit", "guaranteed return", "risk-free trade",
        "buy now", "sell now", "100% win rate", "sure shot signal",
    )
    lower_summary = summary.lower()
    flagged = [phrase for phrase in blocked_claims if phrase in lower_summary]
    return {
        "status": "review_required" if flagged else "passed",
        "notes": (
            [f"Automated screen flagged claim: {phrase}" for phrase in flagged]
            if flagged else [
                "Evergreen educational-content screen passed.",
                "No live price/news claims or trade instructions are verified by this screen.",
                "Keep charts labeled illustrative; do not claim guaranteed outcomes or personalized financial advice.",
            ]
        ),
        "source_count": len(sources),
        "verification_scope": "evergreen_educational_screen_only",
    }


def script_generation(item, research_data):
    fallback = {
        "hook": item["hook"],
        "body": item["body"],
        "cta": (
            "Follow Bullseye Theory for practical chart analysis, disciplined trading education, "
            "and realistic market thinking."
        ),
        "tagline": PHILOSOPHY,
        "disclaimer": DISCLAIMER,
    }

    system_prompt = (
        "You write original English educational trading content for Bullseye Theory. "
        "Never give personalized financial advice, direct buy/sell instructions, guaranteed outcomes, "
        "or claims of certainty. Use clear institutional language. Return JSON only with keys: "
        "hook, body, cta, tagline, disclaimer. Keep the educational meaning faithful to the supplied topic."
    )
    user_prompt = json.dumps({
        "topic": item,
        "research": research_data,
        "required_disclaimer": DISCLAIMER,
        "brand_philosophy": PHILOSOPHY,
        "constraints": [
            "Do not invent live market data or sources.",
            "Do not turn an educational example into a trade signal.",
            "Keep hook concise and body practical.",
            "CTA must be educational, not profit-oriented.",
        ],
    }, ensure_ascii=False)

    try:
        generated = generate_json(system_prompt, user_prompt)
    except Exception as exc:
        print(f"Optional LLM unavailable; using deterministic script fallback: {exc}")
        generated = None

    if not isinstance(generated, dict):
        return fallback

    result = {
        "hook": str(generated.get("hook", fallback["hook"])).strip(),
        "body": str(generated.get("body", fallback["body"])).strip(),
        "cta": str(generated.get("cta", fallback["cta"])).strip(),
        "tagline": PHILOSOPHY,
        "disclaimer": DISCLAIMER,
    }
    if not result["hook"] or not result["body"]:
        return fallback
    return result


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


def build_content(item, index, content_id=None, content_role="education"):
    research_data = research(item)
    fact_check_data = fact_check(research_data)
    script = script_generation(item, research_data)
    safety = safety_check(script)
    visuals = visual_plan(item)
    social = caption_and_hashtags(item)

    fact_check_passed = str(fact_check_data.get("status", "")).lower() in {"passed", "verified", "approved"}
    safety_passed = safety.get("passed") is True
    review_blocked = not fact_check_passed
    if not safety_passed:
        status = "safety_review_required"
    elif review_blocked:
        status = "fact_check_review_required"
    elif HUMAN_APPROVAL:
        status = "pending_approval"
    elif AUTO_PUBLISH_ENABLED:
        status = "approved_for_publishing"
    else:
        status = "pending_approval"

    content = {
        "content_id": content_id or f"content_{index}",
        "content_version": 1,
        "created_at": now_utc(),
        "brand": BRAND,
        "language": "English",
        "market": item["market"],
        "audience": "Global",
        "content_category": item["category"],
        "content_role": content_role,
        "content_strategy": {
            "target_mix": REFERENCE_DNA.get("target_mix", {}),
            "conversion_principles": REFERENCE_DNA.get("conversion_principles", []),
        },
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
            "required": HUMAN_APPROVAL or not AUTO_PUBLISH_ENABLED,
            "status": "pending" if (HUMAN_APPROVAL or not AUTO_PUBLISH_ENABLED or review_blocked or not safety_passed) else "approved",
            "mode": "manual" if HUMAN_APPROVAL or not AUTO_PUBLISH_ENABLED else "automatic",
            "version": 1,
        },
    }
    approval_basis = {
        "content_id": content["content_id"], "version": content["content_version"],
        "created_at": content["created_at"], "title": content["topic"]["title"],
        "hook": content["script"]["hook"], "body": content["script"]["body"],
    }
    content["approval"]["content_hash"] = hashlib.sha256(
        json.dumps(approval_basis, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return content


def load_json(filename, default=None):
    """Load a JSON file from OUTPUT_DIR, returning default when it is missing or invalid."""
    path = OUTPUT_DIR / filename
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {} if default is None else default


def create_approval_queue(contents):
    existing = load_json("approval_queue.json", {})
    existing_items = {}
    existing_sent = []

    if isinstance(existing, dict):
        existing_sent = list(existing.get("telegram_sent", []))
        for item in existing.get("items", []):
            if item.get("content_id"):
                existing_items[item["content_id"]] = item

    for content in contents:
        existing_items[content["content_id"]] = {
            "content_id": content["content_id"],
            "content_version": content.get("content_version", 1),
            "content_hash": (content.get("approval") or {}).get("content_hash", ""),
            "topic": content["topic"]["title"],
            "status": content["status"],
            "approval_required": content["approval"].get("required", True),
            "created_at": content["created_at"],
        }

    return {
        "updated_at": now_utc(),
        "items": list(existing_items.values()),
        "telegram_sent": existing_sent,
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
    if not topics:
        save_json("latest_generated.json", {"content_ids": [], "generated_at": now_utc()})
        print("No fresh topic available. No-op run: nothing to publish.")
        return
    contents = []

    run_stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    for index, item in enumerate(topics, start=1):
        content_id = f"content_{run_stamp}_{index}"
        sequence_number = ((datetime.now(timezone.utc).timetuple().tm_yday - 1) * 3) + index
        if sequence_number % 10 == 0:
            content_role = "course_conversion"
        elif sequence_number % 5 == 0:
            content_role = "authority_and_trust"
        else:
            content_role = "education"
        print(f"Generating {content_id}: {item['title']} [{content_role}]")
        content = build_content(item, index, content_id, content_role)
        contents.append(content)
        save_json(f"{content_id}.json", content)
        print(f"Saved: {content_id}.json")

    save_json("approval_queue.json", create_approval_queue(contents))
    save_json("latest_generated.json", {
        "content_ids": [item["content_id"] for item in contents],
        "generated_at": now_utc(),
    })

    print("---------------------------------------------")
    print(f"Generated: {len(contents)} English educational Reel drafts")
    print(f"Content batch size: {CONTENT_BATCH_SIZE}")
    print("Approval queue created.")
    print("---------------------------------------------")


if __name__ == "__main__":
    main()
