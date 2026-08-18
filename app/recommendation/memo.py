import logging
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import get_settings
from app.models import Analysis
from app.thesis import SCORE_WEIGHTS, THESIS_NAME
from app.util import slugify

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent
_STATIC_DIR = _TEMPLATE_DIR / "static"
_env = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIR),
    autoescape=select_autoescape(),  # on for .html — this renders LLM text, must be escaped
    trim_blocks=True,
    lstrip_blocks=True,
)
_MEMO_TEMPLATE = _env.get_template("memo_template.html")
_INDEX_TEMPLATE = _env.get_template("index_template.html")

_DIMENSION_LABELS = {
    "team": "Team",
    "product": "Product",
    "market": "Market",
    "risk_adjustment": "Risk adjustment",
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
            f"{_DIMENSION_LABELS[strongest].lower()} ({scores[strongest]}/100) — "
            f"clears the bar for a conversation."
        )
    if analysis.call == "Watch":
        return (
            f"Scores {analysis.score}/100 — "
            f"{_DIMENSION_LABELS[strongest].lower()} looks promising "
            f"({scores[strongest]}/100) but "
            f"{_DIMENSION_LABELS[weakest].lower()} is the open question "
            f"({scores[weakest]}/100). Worth revisiting if that changes."
        )
    return (
        f"Scores {analysis.score}/100 — {_DIMENSION_LABELS[weakest].lower()} "
        f"({scores[weakest]}/100) is the main blocker and doesn't currently "
        f"clear the bar."
    )


def _call_class(call: str) -> str:
    return slugify(call)


def _breakdown_rows(analysis: Analysis) -> list[dict]:
    scores = analysis.sub_scores.model_dump()
    rows = []
    for dim, label in _DIMENSION_LABELS.items():
        score = scores[dim]
        weight = SCORE_WEIGHTS[dim]
        rows.append(
            {
                "label": label,
                "score": score,
                "weight_pct": round(weight * 100),
                "contribution": round(score * weight, 1),
            }
        )
    return rows


def render_memo(analysis: Analysis) -> str:
    return _MEMO_TEMPLATE.render(
        analysis=analysis,
        weights=SCORE_WEIGHTS,
        thesis_name=THESIS_NAME,
        call_rationale=_call_rationale(analysis),
        call_class=_call_class(analysis.call),
        breakdown=_breakdown_rows(analysis),
    )


def _snippet(text: str, length: int = 110) -> str:
    text = " ".join(text.split())
    return text if len(text) <= length else text[: length - 1].rstrip() + "…"


def render_index(analyses: list[Analysis]) -> str:
    ranked = sorted(analyses, key=lambda a: a.score, reverse=True)
    rows = [
        {
            "score": a.score,
            "call": a.call,
            "call_class": _call_class(a.call),
            "slug": a.slug,
            "name": a.name,
            "snapshot": _snippet(a.product),
        }
        for a in ranked
    ]
    return _INDEX_TEMPLATE.render(thesis_name=THESIS_NAME, rows=rows)


def write_memos(topic: str, analyses: list[Analysis]) -> Path:
    settings = get_settings()
    memos_dir = Path(settings.output_dir) / slugify(topic) / "memos"
    memos_dir.mkdir(parents=True, exist_ok=True)

    shutil.copyfile(_STATIC_DIR / "memo.css", memos_dir / "style.css")

    for analysis in analyses:
        (memos_dir / f"{analysis.slug}.html").write_text(render_memo(analysis))

    (memos_dir / "index.html").write_text(render_index(analyses))
    logger.info("Wrote %d memos to %s", len(analyses), memos_dir)
    return memos_dir
