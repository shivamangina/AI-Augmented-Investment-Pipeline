from app.models import Candidate, TractionSignal
from app.sourcing.dedupe import dedupe


def test_dedupe_merges_same_domain_across_sources():
    yc_version = Candidate(
        name="Acme",
        slug="acme",
        website="https://acme.io",
        one_liner="Agents for SMBs",
        sources=["yc"],
        source_urls=["https://ycombinator.com/companies/acme"],
        traction_signals=[TractionSignal(type="yc_batch", label="YC batch W25")],
    )
    ph_version = Candidate(
        name="Acme Inc",
        slug="acme-inc",
        website="https://www.acme.io/?ref=ph",  # same domain, different formatting
        sources=["producthunt"],
        source_urls=["https://producthunt.com/posts/acme"],
        traction_signals=[TractionSignal(type="producthunt_votes", label="200 votes")],
    )

    result = dedupe([yc_version, ph_version])

    assert len(result) == 1
    merged = result[0]
    assert set(merged.sources) == {"yc", "producthunt"}
    assert len(merged.traction_signals) == 2
    assert merged.one_liner == "Agents for SMBs"  # kept from the version that had it


def test_dedupe_keeps_distinct_companies_separate():
    a = Candidate(name="Acme", slug="acme", website="https://acme.io", sources=["yc"])
    b = Candidate(name="Zenith", slug="zenith", website="https://zenith.io", sources=["hn"])

    result = dedupe([a, b])

    assert len(result) == 2


def test_dedupe_falls_back_to_slug_when_no_website():
    a = Candidate(name="Acme", slug="acme", website=None, sources=["hn"])
    b = Candidate(name="Acme", slug="acme", website=None, sources=["producthunt"])

    result = dedupe([a, b])

    assert len(result) == 1
    assert set(result[0].sources) == {"hn", "producthunt"}
