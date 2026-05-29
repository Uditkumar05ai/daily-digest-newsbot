"""Persist a rolling 90-day archive of sent briefs (used by the weekly roundup)."""

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

ARCHIVE_FILE = Path("archive.json")
RETENTION_DAYS = 90


def _load():
    if not ARCHIVE_FILE.exists():
        return {"briefs": []}
    try:
        data = json.loads(ARCHIVE_FILE.read_text(encoding="utf-8"))
        if "briefs" not in data:
            data = {"briefs": []}
        return data
    except Exception as e:
        logger.warning("Could not read %s, starting fresh: %s", ARCHIVE_FILE, e)
        return {"briefs": []}


def _parse_date(value: str):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _prune(briefs):
    cutoff = date.today() - timedelta(days=RETENTION_DAYS)
    kept = []
    for b in briefs:
        d = _parse_date(b.get("date", ""))
        if d is None or d >= cutoff:
            kept.append(b)
    return kept


def save_brief(brief: dict):
    """Append a brief and prune entries older than 90 days."""
    data = _load()
    data["briefs"].append(brief)
    data["briefs"] = _prune(data["briefs"])
    try:
        ARCHIVE_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info("Archived %s %s brief (archive now holds %d briefs).",
                    brief.get("date"), brief.get("slot"), len(data["briefs"]))
    except Exception as e:
        logger.warning("Could not write %s: %s", ARCHIVE_FILE, e)


def load_recent_briefs(days: int = 7):
    """Return briefs from the last ``days`` days, oldest first."""
    cutoff = date.today() - timedelta(days=days)
    recent = []
    for b in _load()["briefs"]:
        d = _parse_date(b.get("date", ""))
        if d and d >= cutoff:
            recent.append(b)
    recent.sort(key=lambda b: (b.get("date", ""), b.get("sent_at", "")))
    return recent
