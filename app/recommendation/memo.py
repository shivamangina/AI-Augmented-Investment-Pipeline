import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import get_settings
from app.models import Analysis
from app.thesis import SCORE_WEIGHTS, THESIS_NAME
from app.util import slugify

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent
_env = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIR),
    autoescape=select_autoescape(disabled_extensions=(".j2",)),
    trim_blocks=True,
    lstrip_blocks=True,
)
_TEMPLATE = _env.get_template("memo_template.md.j2")

_DIMENSION_LABELS = {
    "team": "team",
    "product": "product",
    "market": "market",
    "risk_adjustment": "risk profile",
}


def _call_rationale(analysis: Analysis) -> str:
    """A short, deterministic sentence explaining the call, built from the
    computed sub-scores rather than another LLM call — keeps the memo's
    headline claim traceable to the same numbers shown in the breakdown
    table just below it."""
    scores = analysis.sub_scores.model_dump()
    strongest = max(scores, key=scores.get)
    weakest = min(scores, key=scores.get)

    if analysis.call == "Take a meeting":
        return (
            f"Scores {analysis.score}/100 against the thesis, driven by a strong "
            f"{_DIMENSION_LABELS[strongest]} ({scores[strongest]}/100) — clears "
            f"the bar for a conversation."
        )
    if analysis.call == "Watch":
        return (
            f"Scores {analysis.score}/100 — {_DIMENSION_LABELS[strongest]} looks "
            f"promising ({scores[strongest]}/100) but "
            f"{_DIMENSION_LABELS[weakest]} is the open question "
            f"({scores[weakest]}/100). Worth revisiting if that changes."
        )
    return (
        f"Scores {analysis.score}/100 — {_DIMENSION_LABELS[weakest]} "
        f"({scores[weakest]}/100) is the main blocker and doesn't currently "
        f"clear the bar."
    )


def render_memo(analysis: Analysis) -> str:
    return _TEMPLATE.render(
        analysis=analysis,
        weights=SCORE_WEIGHTS,
        thesis_name=THESIS_NAME,
        call_rationale=_call_rationale(analysis),
    )


def _snippet(text: str, length: int = 90) -> str:
    text = " ".join(text.split())
    return text if len(text) <= length else text[: length - 1].rstrip() + "…"


def render_index(analyses: list[Analysis]) -> str:
    ranked = sorted(analyses, key=lambda a: a.score, reverse=True)
    lines = [
        f"# {THESIS_NAME} — Memo Index",
        "",
        f"{len(ranked)} companies analyzed.",
        "",
        "| Score | Call | Company | Snapshot | Memo |",
        "|---|---|---|---|---|",
    ]
    for a in ranked:
        lines.append(
            f"| {a.score} | {a.call} | {a.name} | {_snippet(a.product)} "
            f"| [{a.slug}.md](./{a.slug}.md) |"
        )
    return "\n".join(lines) + "\n"


def write_memos(topic: str, analyses: list[Analysis]) -> Path:
    settings = get_settings()
    memos_dir = Path(settings.output_dir) / slugify(topic) / "memos"
    memos_dir.mkdir(parents=True, exist_ok=True)

    for analysis in analyses:
        (memos_dir / f"{analysis.slug}.md").write_text(render_memo(analysis))

    (memos_dir / "index.md").write_text(render_index(analyses))
    logger.info("Wrote %d memos to %s", len(analyses), memos_dir)
    return memos_dir
