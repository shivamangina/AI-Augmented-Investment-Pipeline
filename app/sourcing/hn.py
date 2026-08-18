"""Hacker News sourcing via the official Algolia HN Search API (free, no auth).

Used two ways:
- discovery: Show HN posts matching the topic (supplementary — Show HN skews
  toward hobby/OSS projects, so YC remains the primary discovery source)
- enrichment: for every candidate (regardless of origin), search HN by name to
  pull points/comments as a traction/freshness signal
"""

import logging

import httpx

from app.models import Candidate, TractionSignal
from app.util import normalize_domain, slugify

logger = logging.getLogger(__name__)

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"


def _parse_show_hn_title(title: str) -> tuple[str, str]:
    body = title.split(":", 1)[-1].strip()
    for sep in (" – ", " — ", " - "):
        if sep in body:
            name, one_liner = body.split(sep, 1)
            return name.strip(), one_liner.strip()
    return body.strip(), ""


async def fetch_show_hn_candidates(topic: str, limit: int = 10) -> list[Candidate]:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                HN_SEARCH_URL,
                params={"query": topic, "tags": "show_hn", "hitsPerPage": limit * 3},
                timeout=15,
            )
            resp.raise_for_status()
            hits = resp.json().get("hits", [])
    except httpx.HTTPError as exc:
        logger.warning("HN Show HN discovery failed (%s) — continuing without it", exc)
        return []

    candidates = []
    for hit in hits:
        url = hit.get("url")
        if not url:
            continue  # no external link means no product page to point to
        name, one_liner = _parse_show_hn_title(hit.get("title", ""))
        if not name:
            continue
        hn_url = f"https://news.ycombinator.com/item?id={hit['objectID']}"
        candidates.append(
            Candidate(
                name=name,
                slug=slugify(name),
                website=url,
                one_liner=one_liner,
                sources=["hn"],
                source_urls=[hn_url, url],
                traction_signals=[
                    TractionSignal(
                        type="hn_show_hn",
                        label=(
                            f"Show HN: {hit.get('points', 0)} points, "
                            f"{hit.get('num_comments', 0)} comments"
                        ),
                        url=hn_url,
                        date=hit.get("created_at"),
                    )
                ],
            )
        )
        if len(candidates) >= limit:
            break
    return candidates


async def enrich_traction(
    client: httpx.AsyncClient, candidate: Candidate
) -> list[TractionSignal]:
    try:
        resp = await client.get(
            HN_SEARCH_URL,
            params={"query": candidate.name, "tags": "story", "hitsPerPage": 5},
            timeout=15,
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
    except httpx.HTTPError as exc:
        logger.warning("HN enrichment failed for %s (%s)", candidate.name, exc)
        return []

    name_lower = candidate.name.lower()
    domain = normalize_domain(candidate.website)
    signals = []
    for hit in hits:
        title = (hit.get("title") or "").lower()
        hit_domain = normalize_domain(hit.get("url"))
        # require the name in the title or a matching domain, otherwise
        # Algolia's fuzzy match pulls in unrelated posts
        if name_lower not in title and (not domain or hit_domain != domain):
            continue
        hn_url = f"https://news.ycombinator.com/item?id={hit['objectID']}"
        signals.append(
            TractionSignal(
                type="hn_mention",
                label=(
                    f'HN: "{hit.get("title")}" — {hit.get("points", 0)} points, '
                    f"{hit.get('num_comments', 0)} comments"
                ),
                url=hn_url,
                date=hit.get("created_at"),
            )
        )
    return signals
