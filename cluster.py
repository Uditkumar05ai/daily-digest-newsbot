"""Group near-identical stories across sources before summarising.

The same event often arrives from BBC, Reuters, Al Jazeera, and a Google News
query at once. Sending all four to the LLM wastes the token budget and dilutes
attention. Clustering merges them into one representative item annotated with
how many outlets carried it — which doubles as an importance signal (a story
covered by six sources is probably the day's big one).
"""

import logging
import re
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

# Common words that carry no topical signal when comparing headlines.
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for", "with",
    "at", "by", "from", "as", "is", "are", "was", "were", "be", "been", "it",
    "its", "this", "that", "these", "those", "after", "over", "amid", "into",
    "new", "says", "say", "said", "will", "has", "have", "had", "not", "no",
    "up", "out", "how", "why", "what", "who", "when", "where", "his", "her",
    "their", "they", "you", "your", "our", "we", "he", "she", "than", "more",
    "report", "reports", "news", "latest", "update", "updates",
}

# Two headlines are treated as the same story at/above this similarity.
SIMILARITY_THRESHOLD = 0.5


def _tokens(title: str):
    words = re.findall(r"[a-z0-9]+", (title or "").lower())
    return {w for w in words if len(w) > 2 and w not in STOPWORDS}


def _similarity(a: str, b: str) -> float:
    """Blend Jaccard token overlap with difflib ratio.

    Jaccard catches different outlets phrasing the same event with shared
    keywords; difflib catches lightly-reworded near-duplicates.
    """
    ta, tb = _tokens(a), _tokens(b)
    jaccard = (len(ta & tb) / len(ta | tb)) if (ta and tb) else 0.0
    ratio = SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()
    return max(jaccard, ratio)


def cluster_articles(articles, threshold: float = SIMILARITY_THRESHOLD):
    """Merge same-event articles (within a category) into representatives.

    Each returned dict is a copy of the richest article in its cluster, plus:
      - ``source_count``: how many articles fell into the cluster
      - ``sources``: sorted unique source names

    Result is sorted so the most-corroborated stories come first.
    """
    clusters = []  # list of lists of articles
    for art in articles:
        placed = False
        for members in clusters:
            head = members[0]
            if head["category"] == art["category"] and _similarity(head["title"], art["title"]) >= threshold:
                members.append(art)
                placed = True
                break
        if not placed:
            clusters.append([art])

    merged = []
    for members in clusters:
        rep = dict(max(members, key=lambda a: len(a.get("summary", ""))))
        rep["source_count"] = len(members)
        rep["sources"] = sorted({m["source"] for m in members})
        merged.append(rep)

    merged.sort(key=lambda a: a["source_count"], reverse=True)
    logger.info(
        "Clustered %d articles into %d stories (%d multi-source).",
        len(articles), len(merged), sum(1 for m in merged if m["source_count"] > 1),
    )
    return merged
