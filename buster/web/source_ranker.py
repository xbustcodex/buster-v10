from urllib.parse import urlparse

TRUST_HINTS = {
    ".gov": 0.25,
    ".edu": 0.2,
    "docs.": 0.15,
    "github.com": 0.15,
    "wikipedia.org": 0.05,
}

def rank_source(url: str, snippet: str = "") -> float:
    host = urlparse(url).netloc.lower()
    score = 0.5
    for hint, boost in TRUST_HINTS.items():
        if hint in host:
            score += boost
    if snippet and len(snippet) > 80:
        score += 0.1
    return min(score, 1.0)
