"""Orchestrates the three stages. This is the one function both the CLI
(app/cli.py) and the FastAPI app (app/main.py) call — neither interface
contains pipeline logic of its own.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from app.analysis.run import analyze_candidates, load_analyses, write_analyses
from app.models import Analysis, Candidate
from app.recommendation.memo import write_memos
from app.sourcing.run import load_candidates, source_candidates, write_candidates

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    topic: str
    candidates: list[Candidate]
    analyses: list[Analysis]
    memos_dir: Path


async def run_pipeline(
    topic: str,
    limit: int = 15,
    skip_sourcing: bool = False,
    skip_analysis: bool = False,
) -> PipelineResult:
    """Runs sourcing -> analysis -> recommendation for `topic`, writing each
    stage's output to outputs/<topic-slug>/ before the next stage starts.

    `skip_sourcing` / `skip_analysis` replay a later stage from the
    already-committed JSON for that topic instead of re-hitting external
    APIs — useful for re-generating memos after a template tweak, or for a
    reviewer re-running just the last stage without needing API keys for the
    earlier ones (analysis still needs OPENAI_API_KEY; recommendation needs
    neither).
    """
    if skip_sourcing:
        logger.info("Skipping sourcing — loading existing candidates for %r", topic)
        candidates = load_candidates(topic)
    else:
        candidates = await source_candidates(topic, limit=limit)
        write_candidates(topic, candidates)

    if not candidates:
        logger.warning("No candidates to analyze for topic %r", topic)
        return PipelineResult(topic, [], [], Path())

    if skip_analysis:
        logger.info("Skipping analysis — loading existing analyses for %r", topic)
        analyses = load_analyses(topic)
    else:
        analyses = await analyze_candidates(candidates)
        write_analyses(topic, analyses)

    memos_dir = write_memos(topic, analyses)

    return PipelineResult(topic, candidates, analyses, memos_dir)
