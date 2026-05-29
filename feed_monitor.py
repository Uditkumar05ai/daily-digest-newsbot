"""Weekly RSS feed health check — reports broken feeds to Telegram."""

import logging
import os

import feedparser
import requests

from config import RSS_FEEDS
from telegram_sender import send_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; DailyDigestBot/1.0)"}
TIMEOUT = 10


def _check(feed):
    """Return (status, reason) where status is 'healthy' | 'empty' | 'dead'."""
    try:
        r = requests.get(feed["url"], headers=HEADERS, timeout=TIMEOUT)
    except requests.exceptions.SSLError:
        return "dead", "SSL certificate error"
    except requests.exceptions.ConnectionError:
        return "dead", "connection/DNS failure"
    except requests.exceptions.Timeout:
        return "dead", "timed out"
    except Exception as e:
        return "dead", f"request error: {type(e).__name__}"

    if r.status_code >= 400:
        return "dead", f"HTTP {r.status_code}"

    parsed = feedparser.parse(r.content)
    entries = parsed.entries or []
    if parsed.bozo and not entries:
        reason = type(parsed.bozo_exception).__name__ if parsed.bozo_exception else "parse error"
        if "SAXParseException" in reason or "NonXMLContentType" in reason:
            reason = "malformed XML"
        return "dead", reason

    if not entries:
        return "empty", "0 entries"

    return "healthy", f"{len(entries)} entries"


def main():
    missing = [k for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID") if not os.getenv(k)]
    if missing:
        raise SystemExit(f"Missing env vars: {', '.join(missing)}")

    healthy, empty, dead = [], [], []
    for feed in RSS_FEEDS:
        status, reason = _check(feed)
        logger.info("%-28s %s (%s)", feed["name"], status, reason)
        if status == "healthy":
            healthy.append(feed["name"])
        elif status == "empty":
            empty.append(feed["name"])
        else:
            dead.append((feed["name"], reason))

    divider = "━" * 20
    parts = [
        "🔍 FEED HEALTH REPORT",
        divider,
        f"✅ Healthy ({len(healthy)}): " + (", ".join(healthy) if healthy else "none"),
        "",
        f"⚠️ Empty ({len(empty)}): " + (", ".join(empty) if empty else "none"),
        "",
        f"❌ Dead ({len(dead)}):",
    ]
    if dead:
        parts.extend(f"• {name} — {reason}" for name, reason in dead)
    else:
        parts.append("none")
    parts.extend(["", f"Total: {len(RSS_FEEDS)} feeds checked", divider])

    send_message("\n".join(parts))
    logger.info("Feed health report sent (%d healthy, %d empty, %d dead).",
                len(healthy), len(empty), len(dead))


if __name__ == "__main__":
    main()
