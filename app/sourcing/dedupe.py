"""Merge candidates found by multiple sources into one record per company,
so a startup found on both YC and Product Hunt shows up once with combined
signals rather than as two separate memo candidates."""

from app.models import Candidate
from app.util import normalize_domain


def dedupe(candidates: list[Candidate]) -> list[Candidate]:
    merged: dict[str, Candidate] = {}
    order: list[str] = []

    for c in candidates:
        key = normalize_domain(c.website) or c.slug
        if key not in merged:
            merged[key] = c.model_copy(deep=True)
            order.append(key)
            continue

        existing = merged[key]
        existing.sources = list(dict.fromkeys(existing.sources + c.sources))
        existing.source_urls = list(
            dict.fromkeys(existing.source_urls + c.source_urls)
        )
        existing.traction_signals = existing.traction_signals + c.traction_signals
        existing.tags = list(dict.fromkeys(existing.tags + c.tags))
        existing.founders = list(dict.fromkeys(existing.founders + c.founders))
        if len(c.description) > len(existing.description):
            existing.description = c.description
        if not existing.one_liner and c.one_liner:
            existing.one_liner = c.one_liner
        if not existing.team_signal and c.team_signal:
            existing.team_signal = c.team_signal
        if not existing.website and c.website:
            existing.website = c.website

    return [merged[k] for k in order]
