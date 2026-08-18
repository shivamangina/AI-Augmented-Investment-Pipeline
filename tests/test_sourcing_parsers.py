import json
from pathlib import Path

from app.sourcing.hn import _parse_show_hn_title
from app.sourcing.yc import _keywords, _relevance
from app.util import normalize_domain, slugify

FIXTURES = Path(__file__).parent / "fixtures"


def load_yc_fixture():
    return json.loads((FIXTURES / "yc_sample.json").read_text())


def test_keywords_strips_stopwords_and_short_tokens():
    kws = _keywords("AI agents for SMBs")
    assert "agents" in kws
    assert "smbs" in kws
    assert "for" not in kws  # stopword
    assert "ai" not in kws  # len <= 2, dropped


def test_relevance_ranks_on_topic_company_higher():
    companies = load_yc_fixture()
    keywords = _keywords("AI agents for SMBs bookkeeping")

    scores = {c["name"]: _relevance(c, keywords) for c in companies}

    assert scores["InvoiceAgent"] > scores["SpaceRobotics"]
    assert scores["SpaceRobotics"] == 0


def test_parse_show_hn_title_with_en_dash():
    name, one_liner = _parse_show_hn_title(
        "Show HN: Plandex – open source AI coding agent"
    )
    assert name == "Plandex"
    assert one_liner == "open source AI coding agent"


def test_parse_show_hn_title_with_hyphen():
    name, one_liner = _parse_show_hn_title("Show HN: Acme - agents for SMBs")
    assert name == "Acme"
    assert one_liner == "agents for SMBs"


def test_parse_show_hn_title_no_separator():
    name, one_liner = _parse_show_hn_title("Show HN: JustATitle")
    assert name == "JustATitle"
    assert one_liner == ""


def test_normalize_domain_strips_scheme_www_and_query():
    assert normalize_domain("https://www.acme.io/?ref=yc") == "acme.io"
    assert normalize_domain("http://acme.io/pricing") == "acme.io"
    assert normalize_domain("acme.io") == "acme.io"
    assert normalize_domain(None) is None


def test_slugify():
    assert slugify("Acme, Inc.") == "acme-inc"
    assert slugify("  Multi   Space  ") == "multi-space"
