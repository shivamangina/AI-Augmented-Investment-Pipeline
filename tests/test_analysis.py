from unittest.mock import AsyncMock, MagicMock

import pytest

from app.analysis.analyze import LLMAnalysisOutput, analyze_candidate
from app.models import Candidate, SubScores


def _fake_completion(parsed: LLMAnalysisOutput | None, refusal: str | None = None):
    message = MagicMock(parsed=parsed, refusal=refusal)
    choice = MagicMock(message=message)
    return MagicMock(choices=[choice])


@pytest.mark.asyncio
async def test_analyze_candidate_computes_score_and_call_from_llm_output():
    candidate = Candidate(
        name="InvoiceAgent",
        slug="invoiceagent",
        website="https://invoiceagent.ai",
        source_urls=["https://ycombinator.com/companies/invoiceagent"],
    )
    llm_output = LLMAnalysisOutput(
        team="Unknown — not found in available sources",
        product="Automates SMB invoicing end to end.",
        market="Large fragmented SMB bookkeeping market.",
        risks=["Depends heavily on accounting API integrations staying stable."],
        mind_changers=["Evidence of paying customers", "A technical co-founder"],
        sub_scores=SubScores(team=40, product=90, market=80, risk_adjustment=60),
    )
    client = MagicMock()
    client.chat.completions.parse = AsyncMock(
        return_value=_fake_completion(llm_output)
    )

    result = await analyze_candidate(candidate, client=client)

    # score = 40*.25 + 90*.30 + 80*.25 + 60*.20 = 10 + 27 + 20 + 12 = 69
    assert result.score == 69.0
    assert result.call == "Watch"
    assert result.name == "InvoiceAgent"
    assert result.slug == "invoiceagent"
    assert result.source_urls == candidate.source_urls
    assert result.team == "Unknown — not found in available sources"


@pytest.mark.asyncio
async def test_analyze_candidate_raises_on_refusal():
    candidate = Candidate(name="Acme", slug="acme")
    client = MagicMock()
    client.chat.completions.parse = AsyncMock(
        return_value=_fake_completion(None, refusal="policy violation")
    )

    with pytest.raises(ValueError, match="policy violation"):
        await analyze_candidate(candidate, client=client)
