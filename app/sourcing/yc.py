"""YC company directory sourcing.

Uses YC's public companies API (https://api.ycombinator.com/v0.1/companies),
the same endpoint ycombinator.com/companies calls client-side. It has no
free-text search param, so we pull full batches and rank client-side by
keyword overlap with the topic query.
"""

import logging
import re

import httpx

from app.models import Candidate, TractionSignal
from app.util import slugify

logger = logging.getLogger(__name__)

YC_API_URL = "https://api.ycombinator.com/v0.1/companies"

# Recent batches to search across when a single batch doesn't have enough
# topic-relevant matches. Newest first so freshness is naturally favored.
DEFAULT_BATCHES = ["W25", "S24", "W24"]

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


def _keywords(topic: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", topic.lower())
    return [w for w in words if w not in _STOPWORDS and len(w) > 2]


def _relevance(company: dict, keywords: list[str]) -> int:
    haystack = " ".join(
        [
            company.get("oneLiner") or "",
            company.get("longDescription") or "",
            " ".join(company.get("tags") or []),
            " ".join(company.get("industries") or []),
        ]
    ).lower()
    return sum(haystack.count(kw) for kw in keywords)


async def _fetch_batch(client: httpx.AsyncClient, batch: str) -> list[dict]:
    companies: list[dict] = []
    page = 1
    while True:
        resp = await client.get(
            YC_API_URL, params={"batch": batch, "page": page}, timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
        companies.extend(data.get("companies", []))
        if not data.get("nextPage"):
            break
        page += 1
    return companies


async def fetch_candidates(
    topic: str,
    limit: int = 15,
    batches: list[str] | None = None,
) -> list[Candidate]:
    """Fetch YC companies across `batches`, rank by relevance to `topic`,
    return the top `limit` as Candidates. Returns [] (with a logged warning)
    on any network/API failure rather than raising, so one flaky source
    doesn't take down the whole sourcing stage.
    """
    batches = batches or DEFAULT_BATCHES
    keywords = _keywords(topic)

    all_companies: list[dict] = []
    try:
        async with httpx.AsyncClient() as client:
            for batch in batches:
                all_companies.extend(await _fetch_batch(client, batch))
    except httpx.HTTPError as exc:
        logger.warning("YC sourcing failed (%s) — continuing without YC data", exc)
        return []

    scored = [(c, _relevance(c, keywords)) for c in all_companies]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    top = [c for c, score in scored if score > 0][:limit]

    # If keyword filtering was too narrow to fill the batch, backfill with the
    # most recent companies (still on-topic in spirit: same batch/vertical feed)
    # rather than returning fewer candidates than requested.
    if len(top) < limit:
        seen_ids = {c["id"] for c in top}
        for c, _ in scored:
            if len(top) >= limit:
                break
            if c["id"] not in seen_ids:
                top.append(c)
                seen_ids.add(c["id"])

    candidates = []
    for c in top:
        yc_url = c.get("url") or f"https://www.ycombinator.com/companies/{c['slug']}"
        candidates.append(
            Candidate(
                name=c["name"],
                slug=slugify(c["name"]),
                website=c.get("website"),
                one_liner=c.get("oneLiner", ""),
                description=c.get("longDescription", ""),
                team_signal=f"Team size {c['teamSize']}" if c.get("teamSize") else "",
                tags=list({*(c.get("tags") or []), *(c.get("industries") or [])}),
                sources=["yc"],
                source_urls=[yc_url],
                traction_signals=[
                    TractionSignal(
                        type="yc_batch",
                        label=f"YC batch {c.get('batch')}",
                        url=yc_url,
                        date=None,
                    )
                ],
            )
        )
    return candidates
