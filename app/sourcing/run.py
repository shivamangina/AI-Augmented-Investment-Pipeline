import asyncio
import json
import logging
from pathlib import Path

import httpx

from app.config import get_settings
from app.models import Candidate
from app.sourcing import hn, producthunt, yc
from app.sourcing.dedupe import dedupe
from app.util import slugify

logger = logging.getLogger(__name__)


async def source_candidates(topic: str, limit: int = 15) -> list[Candidate]:
    """Runs all configured sources concurrently, dedupes, enriches every
    candidate with HN traction signals, and returns the top `limit` ranked by
    how many sources corroborate them and how much traction signal they have.
    """
    yc_candidates, hn_candidates, ph_candidates = await asyncio.gather(
        yc.fetch_candidates(topic, limit=limit),
        hn.fetch_show_hn_candidates(topic, limit=limit),
        producthunt.fetch_candidates(topic, limit=limit),
    )

    all_candidates = dedupe(yc_candidates + hn_candidates + ph_candidates)
    if not all_candidates:
        logger.warning("No candidates found for topic %r from any source", topic)
        return []

    # Cap the enrichment pool before doing per-candidate HN lookups, so a large
    # dedup'd pool doesn't turn into an unbounded number of HN API calls.
    all_candidates.sort(key=lambda c: len(c.sources), reverse=True)
    pool = all_candidates[: max(limit * 2, 30)]

    semaphore = asyncio.Semaphore(8)

    async def _enrich(client: httpx.AsyncClient, candidate: Candidate) -> None:
        async with semaphore:
            signals = await hn.enrich_traction(client, candidate)
        candidate.traction_signals = candidate.traction_signals + signals

    async with httpx.AsyncClient() as client:
        await asyncio.gather(*(_enrich(client, c) for c in pool))

    pool.sort(key=lambda c: (len(c.sources), len(c.traction_signals)), reverse=True)
    return pool[:limit]


def write_candidates(topic: str, candidates: list[Candidate]) -> Path:
    settings = get_settings()
    run_dir = Path(settings.output_dir) / slugify(topic)
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "candidates.json"
    out_path.write_text(json.dumps([c.model_dump() for c in candidates], indent=2))
    logger.info("Wrote %d candidates to %s", len(candidates), out_path)
    return out_path


def load_candidates(topic: str) -> list[Candidate]:
    settings = get_settings()
    path = Path(settings.output_dir) / slugify(topic) / "candidates.json"
    data = json.loads(path.read_text())
    return [Candidate.model_validate(item) for item in data]
