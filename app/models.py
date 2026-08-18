from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

Call = Literal["Pass", "Watch", "Take a meeting"]


class TractionSignal(BaseModel):
    """A single freshness/traction data point, always tied to a source URL."""

    type: str  # e.g. "yc_batch", "hn_points", "hn_show_hn", "producthunt_votes"
    label: str  # human-readable, e.g. "142 points on Show HN (2025-06-01)"
    url: str | None = None
    date: str | None = None


class Candidate(BaseModel):
    """Output of the sourcing stage: one startup with everything found about it."""

    name: str
    slug: str
    website: str | None = None
    one_liner: str = ""
    description: str = ""
    founders: list[str] = Field(default_factory=list)
    team_signal: str = ""  # e.g. "Team size 5" or founder bios if findable
    tags: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)  # ["yc", "hn", "producthunt"]
    source_urls: list[str] = Field(default_factory=list)
    traction_signals: list[TractionSignal] = Field(default_factory=list)


class SubScores(BaseModel):
    """Dimension scores (0-100) the final score is computed from. See app/thesis.py
    for the weights — keeping this separate from `score` is what makes the final
    number auditable instead of one opaque model guess."""

    team: float
    product: float
    market: float
    risk_adjustment: float  # higher = lower risk


class Analysis(BaseModel):
    """Output of the analysis stage: structured writeup + computed score."""

    name: str
    slug: str
    website: str | None = None

    team: str
    product: str
    market: str
    risks: list[str]
    mind_changers: list[str]  # 2-3 things that would change the call

    sub_scores: SubScores
    score: float
    call: Call

    source_urls: list[str] = Field(default_factory=list)
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
