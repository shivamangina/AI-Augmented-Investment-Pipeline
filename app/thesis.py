"""Single source of truth for the investment thesis and scoring rubric.

Both the analysis prompt (app/analysis/prompts.py) and the memo template
(app/recommendation/memo_template.md.j2) pull from here, so the thesis is
stated once and applied consistently everywhere it's used.
"""

THESIS_NAME = "AI Agents & Infrastructure for SMBs"

THESIS_STATEMENT = """\
We back startups building AI agents (or the infrastructure underneath them) that \
automate a specific, recurring, painful back-office or operational workflow for \
small-and-medium businesses (SMBs) — e.g. bookkeeping, scheduling, customer support, \
compliance paperwork, inventory/ordering, or marketing ops. We are not investing in \
consumer AI, enterprise-only AI (long sales cycles, custom deployments), or general \
foundation-model plays.

Why now: reliable tool-use and function-calling in frontier LLMs (the post-2023 \
jump in agentic capability) makes it newly viable to automate messy, multi-step \
SMB workflows that previously required a human doing repetitive digital work. SMBs \
are underserved by expensive enterprise software and can't afford dedicated \
headcount for these tasks — that gap is the opportunity.

What we require to take a company seriously:
- A concrete, named workflow being automated (not "AI for productivity")
- Genuine agentic behavior — multi-step, tool-using, closing the loop on a task —
  not a chat wrapper around a single prompt
- A path to self-serve or low-touch SMB distribution (SMBs can't sustain 6-month
  enterprise sales cycles)
- Some real differentiation beyond prompting a frontier model: proprietary data,
  workflow/integration depth, or agent reliability engineering
"""

# Weights must sum to 1.0 — this is what makes the final score a computed,
# auditable formula instead of one opaque model guess.
SCORE_WEIGHTS = {
    "team": 0.25,
    "product": 0.30,
    "market": 0.25,
    "risk_adjustment": 0.20,
}

RUBRIC = {
    "team": (
        "Do the founders have the technical depth to build a *reliable* agent "
        "(not just prompt one), or domain expertise in the specific SMB vertical "
        "being targeted? Prior relevant exits/experience are a plus, not a "
        "requirement. Score low if team info is unavailable — don't assume "
        "competence absent evidence."
    ),
    "product": (
        "Does the product solve one concrete, recurring, painful SMB workflow? "
        "Is the automation genuinely agentic (multi-step, tool-using, closes the "
        "loop) versus a thin wrapper around a single LLM call? Is there any "
        "evidence of real usage (launch traction, retention signal, GitHub "
        "activity)? This is the highest-weighted dimension — it's the core bet."
    ),
    "market": (
        "Is the SMB segment being targeted reachable and large enough to matter? "
        "How crowded is the competitive landscape (including the risk that an "
        "incumbent SMB software vendor ships this as a feature)? Is there a "
        "credible why-now argument tied to recent LLM capability jumps?"
    ),
    "risk_adjustment": (
        "Inverse of red flags: foundation-model dependency risk (thin wrapper an "
        "OpenAI/Anthropic feature could replicate), incumbent replication risk, "
        "reliability/trust risk (SMBs have no ops team to catch a costly agent "
        "mistake), and unclear defensibility. Score 100 = few/no red flags, "
        "0 = existential red flags."
    ),
}

CALL_THRESHOLDS = {
    "take_a_meeting": 75,  # score >= this -> "Take a meeting"
    "watch": 55,  # score >= this (and < take_a_meeting) -> "Watch"
    # below "watch" -> "Pass"
}


def compute_score(sub_scores: dict[str, float]) -> float:
    """Weighted sum of the four sub-scores. Each sub-score must be 0-100."""
    return round(
        sum(sub_scores[dim] * weight for dim, weight in SCORE_WEIGHTS.items()), 1
    )


def call_from_score(score: float) -> str:
    if score >= CALL_THRESHOLDS["take_a_meeting"]:
        return "Take a meeting"
    if score >= CALL_THRESHOLDS["watch"]:
        return "Watch"
    return "Pass"
