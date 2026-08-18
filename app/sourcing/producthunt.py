"""Product Hunt sourcing via the v2 GraphQL API.

Requires a free developer token (PRODUCTHUNT_API_TOKEN) — see .env.example
for how to get one. The v2 API has no free-text search over posts, so — same
approach as app/sourcing/yc.py — we pull a page of recent/top posts and rank
client-side by keyword overlap with the topic.

If no token is configured this returns [] with a logged warning rather than
raising, so the pipeline still runs end-to-end on YC + HN alone.
"""

import logging

import httpx

from app.config import get_settings
from app.models import Candidate, TractionSignal
from app.sourcing.relevance import expand_keywords, score_relevance
from app.util import slugify

logger = logging.getLogger(__name__)

PH_GRAPHQL_URL = "https://api.producthunt.com/v2/api/graphql"

_QUERY = """
query TopPosts($first: Int!) {
  posts(first: $first, order: VOTES) {
    edges {
      node {
        name
        tagline
        description
        website
        url
        votesCount
        commentsCount
        createdAt
        topics(first: 5) {
          edges { node { name } }
        }
      }
    }
  }
}
"""


async def fetch_candidates(topic: str, limit: int = 10) -> list[Candidate]:
    settings = get_settings()
    if not settings.producthunt_api_token:
        logger.warning(
            "PRODUCTHUNT_API_TOKEN not set — skipping Product Hunt sourcing "
            "(pipeline continues on remaining sources)"
        )
        return []

    keywords = expand_keywords(topic)

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                PH_GRAPHQL_URL,
                json={"query": _QUERY, "variables": {"first": 50}},
                headers={
                    "Authorization": f"Bearer {settings.producthunt_api_token}"
                },
                timeout=15,
            )
            resp.raise_for_status()
            payload = resp.json()
    except httpx.HTTPError as exc:
        logger.warning(
            "Product Hunt sourcing failed (%s) — continuing without it", exc
        )
        return []

    if payload.get("errors"):
        logger.warning(
            "Product Hunt API error: %s — continuing without it", payload["errors"]
        )
        return []

    edges = payload.get("data", {}).get("posts", {}).get("edges", [])
    scored = []
    for edge in edges:
        node = edge["node"]
        topics = [t["node"]["name"] for t in node.get("topics", {}).get("edges", [])]
        haystack = " ".join(
            [
                node.get("name") or "",
                node.get("tagline") or "",
                node.get("description") or "",
                " ".join(topics),
            ]
        )
        score = score_relevance(haystack, keywords)
        if score > 0:
            scored.append((node, topics, score))

    scored.sort(key=lambda triple: triple[2], reverse=True)

    candidates = []
    for node, topics, _ in scored[:limit]:
        candidates.append(
            Candidate(
                name=node["name"],
                slug=slugify(node["name"]),
                website=node.get("website") or node.get("url"),
                one_liner=node.get("tagline", ""),
                description=node.get("description", ""),
                tags=topics,
                sources=["producthunt"],
                source_urls=[node["url"]],
                traction_signals=[
                    TractionSignal(
                        type="producthunt_votes",
                        label=(
                            f"{node.get('votesCount', 0)} PH upvotes, "
                            f"{node.get('commentsCount', 0)} comments"
                        ),
                        url=node["url"],
                        date=node.get("createdAt"),
                    )
                ],
            )
        )
    return candidates
