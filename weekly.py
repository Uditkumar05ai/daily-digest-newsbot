"""Weekly 'Week in Review' roundup, generated from the brief archive."""

import logging
import os
from datetime import datetime, timedelta

import pytz
from groq import Groq

from archiver import load_recent_briefs
from config import GROQ_API_KEY, GROQ_MODEL, IST_TIMEZONE
from telegram_sender import send_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

IST = pytz.timezone(IST_TIMEZONE)

SYSTEM_PROMPT = (
    "You are a sharp weekly news analyst. Given the headlines and themes from the past 7 days of "
    "news briefs, produce a Week in Review. Structure:\n"
    "- One paragraph 'Week in One Line' — the single most important development of the week in 2 sentences max\n"
    "- Top 3 stories of the week — each with a 3 line summary (WHAT, SO WHAT, WHAT'S NEXT) using the same "
    "strict format rules as daily briefs. No banned phrases. Specific facts only.\n"
    "- One paragraph 'What to watch next week' — 2-3 specific things that will develop in the coming week "
    "based on this week's stories. Name specific countries, companies, or people.\n"
    "- Category breakdown: which categories dominated this week (e.g. 'Heavy week for AI, quiet week for India Business')\n"
    "Do not repeat information. Be brutally concise.\n\n"
    "Wrap each of the Top 3 headlines in **bold** and prefix it with its category in square brackets, "
    "e.g. '1. [GEOPOLITICS] **Headline**'. Label the three lines WHAT:, SO WHAT:, NEXT:."
)


def _build_input(briefs):
    lines = []
    themes = [b.get("theme", "") for b in briefs if b.get("theme")]
    if themes:
        lines.append("Daily themes this week:")
        lines.extend(f"- {t}" for t in themes)
        lines.append("")

    lines.append("Headlines by category this week:")
    by_cat = {}
    for b in briefs:
        for s in b.get("stories", []):
            by_cat.setdefault(s.get("category", "GENERAL"), []).append(s.get("headline", ""))
    for cat, heads in by_cat.items():
        lines.append(f"### {cat} ({len(heads)} stories)")
        lines.extend(f"- {h}" for h in heads if h)
        lines.append("")
    return "\n".join(lines)


def _week_range_label(now):
    start = now - timedelta(days=6)
    if start.month == now.month:
        return f"{start.strftime('%b %d')}–{now.strftime('%d, %Y')}"
    return f"{start.strftime('%b %d')}–{now.strftime('%b %d, %Y')}"


def main():
    missing = [k for k in ("GROQ_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID") if not os.getenv(k)]
    if missing:
        raise SystemExit(f"Missing env vars: {', '.join(missing)}")

    briefs = load_recent_briefs(days=7)
    if not briefs:
        logger.info("No briefs in the last 7 days. Skipping weekly roundup.")
        return

    total_stories = sum(len(b.get("stories", [])) for b in briefs)
    logger.info("Building weekly roundup from %d briefs (%d stories).", len(briefs), total_stories)

    client = Groq(api_key=GROQ_API_KEY)
    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_input(briefs)},
        ],
        temperature=0.4,
        max_tokens=2000,
    )
    body = resp.choices[0].message.content.strip()

    now = datetime.now(IST)
    divider = "━" * 20
    message = (
        f"📅 **WEEK IN REVIEW** — {_week_range_label(now)}\n"
        f"{divider}\n\n"
        f"{body}\n"
        f"{divider}"
    )
    send_message(message)
    logger.info("Weekly roundup sent.")


if __name__ == "__main__":
    main()
