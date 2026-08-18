import logging

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.analysis.prompts import SYSTEM_PROMPT, build_user_prompt
from app.config import get_settings
from app.models import Analysis, Candidate, SubScores
from app.thesis import call_from_score, compute_score

logger = logging.getLogger(__name__)


class LLMAnalysisOutput(BaseModel):
    """Shape the model must fill in via structured outputs. Deliberately
    excludes fields we already know from the Candidate (name, website,
    source_urls) or compute ourselves (score, call) — the model should only
    produce what it's actually being asked to judge."""

    team: str
    product: str
    market: str
    risks: list[str]
    mind_changers: list[str]
    sub_scores: SubScores


def build_client() -> AsyncOpenAI:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to .env (see .env.example)."
        )
    return AsyncOpenAI(api_key=settings.openai_api_key)


async def analyze_candidate(
    candidate: Candidate, client: AsyncOpenAI
) -> Analysis:
    settings = get_settings()

    completion = await client.chat.completions.parse(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(candidate)},
        ],
        response_format=LLMAnalysisOutput,
        temperature=0.2,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        refusal = completion.choices[0].message.refusal
        raise ValueError(
            f"Model produced no structured output for {candidate.name}: {refusal}"
        )

    score = compute_score(parsed.sub_scores.model_dump())
    call = call_from_score(score)

    return Analysis(
        name=candidate.name,
        slug=candidate.slug,
        website=candidate.website,
        team=parsed.team,
        product=parsed.product,
        market=parsed.market,
        risks=parsed.risks,
        mind_changers=parsed.mind_changers,
        sub_scores=parsed.sub_scores,
        score=score,
        call=call,
        source_urls=candidate.source_urls,
    )
