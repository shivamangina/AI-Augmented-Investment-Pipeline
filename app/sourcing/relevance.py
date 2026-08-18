"""Shared client-side relevance ranking for sources with no server-side
full-text search (YC, Product Hunt). Both just pull a page of results and
need to rank them against the topic query themselves.

Plain substring keyword counting undersells specific multi-word business
terms relative to generic ones. Concretely: "AI agents for SMBs" tokenizes
to keywords ["agents", "smbs"] — but almost no startup description literally
contains the word "smbs"; they say "small business" or "SME". Without
synonym expansion, ranking collapses to "how often does this company
mention 'agents'", which surfaces generic agent-infra/dev-tool startups
regardless of who their customer is. `_SYNONYMS` fixes the common VC-thesis
abbreviations; per-keyword scoring caps repeat counts so one generic word
mentioned many times can't drown out a specific phrase mentioned once.
"""

import re

_STOPWORDS = {
    "a",
    "an",
    "the",
    "for",
    "of",
    "and",
    "to",
    "in",
    "on",
    "with",
    "startups",
    "startup",
    "companies",
    "company",
}

_SYNONYMS = {
    "smb": ["small business", "small businesses", "small and medium", "sme", "smes"],
    "smbs": ["small business", "small businesses", "small and medium", "sme", "smes"],
    "sme": ["small business", "small businesses", "small and medium", "sme", "smes"],
    "smes": ["small business", "small businesses", "small and medium", "sme", "smes"],
    "b2b": ["b2b", "business-to-business", "enterprise", "businesses"],
    "b2c": ["b2c", "consumer", "consumers"],
}


def expand_keywords(topic: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", topic.lower())
    keywords: list[str] = []
    for w in words:
        if w in _STOPWORDS or len(w) <= 2:
            continue
        keywords.append(w)
        keywords.extend(_SYNONYMS.get(w, []))
    return keywords


def score_relevance(haystack: str, keywords: list[str]) -> int:
    """Each keyword contributes at most 2x its word count, so a two-word
    phrase match ("small business") outweighs a one-word generic term
    ("agents") even if the generic term appears more often."""
    haystack = haystack.lower()
    score = 0
    for kw in keywords:
        hits = min(haystack.count(kw), 2)
        score += hits * len(kw.split())
    return score
