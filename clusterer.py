"""Cluster near-identical stories so one event doesn't waste multiple slots.

Articles whose titles are >= 60% similar (difflib) and share a category are
grouped. From each cluster we keep the article from the highest-priority
source and tag it with ``cluster_size`` / ``source_count`` so the summarizer
can treat heavily-covered stories as more important.
"""

import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.6

# Highest priority first. Sources not listed fall to the bottom.
SOURCE_PRIORITY = [
    "South China Morning Post",
    "Reuters World",
    "BBC News",
    "Al Jazeera",
    "TechCrunch AI",
    "The Verge AI",
    "Inc42",
    "YourStory",
]


def _priority(source: str) -> int:
    """Lower number = higher priority. Google News and unknowns rank last."""
    for i, name in enumerate(SOURCE_PRIORITY):
        if source == name:
            return i
    # Group all Google News queries together just above truly-unknown sources.
    if source.startswith("Google News"):
        return len(SOURCE_PRIORITY) + 1
    return len(SOURCE_PRIORITY)


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()


def cluster_articles(articles, threshold: float = SIMILARITY_THRESHOLD):
    """Return a de-duplicated list with ``cluster_size``/``source_count`` set."""
    clusters = []  # list of lists of articles
    for art in articles:
        placed = False
        for members in clusters:
            head = members[0]
            if head["category"] == art["category"] and _similar(head["title"], art["title"]) >= threshold:
                members.append(art)
                placed = True
                break
        if not placed:
            clusters.append([art])

    kept = []
    for members in clusters:
        rep = dict(min(members, key=lambda a: _priority(a["source"])))
        rep["cluster_size"] = len(members)
        rep["source_count"] = len(members)
        rep["sources"] = sorted({m["source"] for m in members})
        kept.append(rep)

    multi = sum(1 for k in kept if k["cluster_size"] > 1)
    logger.info(
        "Clustered %d articles into %d stories (%d multi-source).",
        len(articles), len(kept), multi,
    )
    return kept
