import logging
import re

from groq import Groq

from cluster import cluster_articles
from config import GROQ_API_KEY, GROQ_MODEL, SYSTEM_PROMPT
from dedup import add_headlines

logger = logging.getLogger(__name__)

# Story headlines in the digest are wrapped in **bold**.
_HEADLINE_RE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)


def _extract_headlines(digest: str):
    """Pull every **bolded** story headline out of the digest body."""
    headlines = []
    for match in _HEADLINE_RE.findall(digest):
        text = match.strip()
        # Drop any leading rating emoji (🔴/🟡/🔵) if it slipped inside the bold.
        text = text.lstrip("🔴🟡🔵 ").strip()
        if text:
            headlines.append(text)
    return headlines

CATEGORY_LABELS = {
    "geopolitics": "GEOPOLITICS",
    "ai": "AI & TECH",
    "ai_releases": "AI RELEASES",
    "india_business": "INDIA BUSINESS",
    "business": "INDIA BUSINESS",
    "india_news": "INDIA NEWS",
    "science": "SCIENCE & SPACE",
}


def _format_articles(articles):
    # Merge same-event stories across sources first; this frees token budget
    # and orders each category by how many outlets corroborated a story.
    clustered = cluster_articles(articles)

    grouped = {}
    for a in clustered:
        grouped.setdefault(a["category"], []).append(a)

    lines = []
    for cat, items in grouped.items():
        label = CATEGORY_LABELS.get(cat, cat.upper())
        lines.append(f"### Category: {label}")
        # Clustering removed duplicates, so we can afford a slightly higher cap.
        for a in items[:10]:
            count = a.get("source_count", 1)
            sources = ", ".join(a.get("sources", [a["source"]]))
            if count > 1:
                lines.append(f"- Source: {sources} (reported by {count} sources)")
            else:
                lines.append(f"- Source: {sources}")
            lines.append(f"  Title: {a['title']}")
            if a.get("summary"):
                lines.append(f"  Summary: {a['summary'][:220]}")
            if a.get("url"):
                lines.append(f"  URL: {a['url']}")
        lines.append("")
    return "\n".join(lines)


def summarize(articles):
    if not articles:
        return None

    client = Groq(api_key=GROQ_API_KEY)
    user_content = _format_articles(articles)

    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.4,
        max_tokens=2000,
    )
    digest = resp.choices[0].message.content.strip()

    # Record headlines so the next brief can skip these stories.
    add_headlines(_extract_headlines(digest))

    return digest
