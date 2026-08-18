import asyncio
import json
import logging
from pathlib import Path

from app.analysis.analyze import analyze_candidate, build_client
from app.config import get_settings
from app.models import Analysis, Candidate
from app.util import slugify

logger = logging.getLogger(__name__)


async def analyze_candidates(candidates: list[Candidate]) -> list[Analysis]:
    """Analyzes every candidate concurrently (bounded by
    settings.analysis_concurrency). A single candidate failing (model refusal,
    API error, bad response) is logged and skipped rather than failing the
    whole batch — one bad company shouldn't block the other 14 memos.
    """
    settings = get_settings()
    client = build_client()
    semaphore = asyncio.Semaphore(settings.analysis_concurrency)

    async def _run(candidate: Candidate) -> Analysis | None:
        async with semaphore:
            try:
                return await analyze_candidate(candidate, client=client)
            except Exception as exc:
                logger.warning(
                    "Analysis failed for %s (%s) — skipping", candidate.name, exc
                )
                return None

    results = await asyncio.gather(*(_run(c) for c in candidates))
    return [r for r in results if r is not None]


def write_analyses(topic: str, analyses: list[Analysis]) -> Path:
    settings = get_settings()
    run_dir = Path(settings.output_dir) / slugify(topic) / "analysis"
    run_dir.mkdir(parents=True, exist_ok=True)
    for analysis in analyses:
        out_path = run_dir / f"{analysis.slug}.json"
        out_path.write_text(json.dumps(analysis.model_dump(), indent=2))
    logger.info("Wrote %d analyses to %s", len(analyses), run_dir)
    return run_dir


def load_analyses(topic: str) -> list[Analysis]:
    settings = get_settings()
    run_dir = Path(settings.output_dir) / slugify(topic) / "analysis"
    analyses = []
    for path in sorted(run_dir.glob("*.json")):
        analyses.append(Analysis.model_validate(json.loads(path.read_text())))
    return analyses
