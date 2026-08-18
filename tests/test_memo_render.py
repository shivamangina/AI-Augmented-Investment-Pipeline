from app.models import Analysis, SubScores
from app.recommendation.memo import render_index, render_memo


def _make_analysis(name="InvoiceAgent", score_overrides=None) -> Analysis:
    sub_scores = SubScores(team=40, product=90, market=80, risk_adjustment=60)
    if score_overrides:
        sub_scores = sub_scores.model_copy(update=score_overrides)
    return Analysis(
        name=name,
        slug="invoiceagent",
        website="https://invoiceagent.ai",
        team="Unknown — not found in available sources.",
        product="Automates SMB invoicing end to end using an autonomous agent.",
        market="Large, fragmented SMB bookkeeping market with few AI-native entrants.",
        risks=["Depends on third-party accounting API access staying stable."],
        mind_changers=["Evidence of paying customers", "A technical co-founder"],
        sub_scores=sub_scores,
        score=69.0,
        call="Watch",
        source_urls=["https://ycombinator.com/companies/invoiceagent"],
        generated_at="2026-08-17T12:00:00+00:00",
    )


def test_render_memo_includes_key_sections():
    memo = render_memo(_make_analysis())

    assert "<title>InvoiceAgent — Watch</title>" in memo
    assert '<span class="badge watch">Watch</span>' in memo
    assert "69.0/100" in memo
    assert "Automates SMB invoicing end to end" in memo
    assert "Depends on third-party accounting API access" in memo
    assert "Evidence of paying customers" in memo
    assert 'href="https://ycombinator.com/companies/invoiceagent"' in memo
    # score breakdown reflects the actual sub-scores, not just the total
    assert '<td class="num">40.0</td>' in memo  # team
    assert '<td class="num">90.0</td>' in memo  # product


def test_render_memo_escapes_llm_text():
    analysis = _make_analysis()
    analysis = analysis.model_copy(
        update={"team": "Founders came from <script>alert(1)</script> Acme."}
    )
    memo = render_memo(analysis)

    assert "<script>alert(1)</script>" not in memo
    assert "&lt;script&gt;" in memo


def test_render_memo_claims_trace_to_source_urls():
    analysis = _make_analysis()
    memo = render_memo(analysis)

    for url in analysis.source_urls:
        assert f'href="{url}"' in memo


def test_render_index_sorts_by_score_descending():
    high = _make_analysis(name="HighScorer", score_overrides={"product": 100})
    high = high.model_copy(update={"score": 95.0, "call": "Take a meeting"})
    low = _make_analysis(name="LowScorer")
    low = low.model_copy(update={"score": 20.0, "call": "Pass", "slug": "lowscorer"})

    index = render_index([low, high])

    assert index.index("HighScorer") < index.index("LowScorer")
    assert '<span class="badge take-a-meeting">Take a meeting</span>' in index
    assert 'href="highscorer.html"' in index or 'href="invoiceagent.html"' in index
