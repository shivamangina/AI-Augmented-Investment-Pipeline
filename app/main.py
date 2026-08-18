"""Thin FastAPI wrapper around the same pipeline the CLI uses. No frontend —
Swagger UI at /docs is the surface area (per the assignment's explicit
"no React frontend" scope constraint).

Run with: uvicorn app.main:app --reload
"""

import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.pipeline import run_pipeline

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)

app = FastAPI(
    title="AI-Augmented Investment Pipeline",
    description="Sourcing -> Analysis -> Recommendation for VC deal triage.",
)


class RunRequest(BaseModel):
    topic: str
    limit: int = 15
    skip_sourcing: bool = False
    skip_analysis: bool = False


class MemoSummary(BaseModel):
    name: str
    slug: str
    score: float
    call: str


class RunResponse(BaseModel):
    topic: str
    candidate_count: int
    memos: list[MemoSummary]
    memos_dir: str


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/pipeline/run", response_model=RunResponse)
async def run(req: RunRequest) -> RunResponse:
    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="topic must not be empty")

    result = await run_pipeline(
        topic=req.topic,
        limit=req.limit,
        skip_sourcing=req.skip_sourcing,
        skip_analysis=req.skip_analysis,
    )

    ranked = sorted(result.analyses, key=lambda a: a.score, reverse=True)
    return RunResponse(
        topic=result.topic,
        candidate_count=len(result.candidates),
        memos=[
            MemoSummary(name=a.name, slug=a.slug, score=a.score, call=a.call)
            for a in ranked
        ],
        memos_dir=str(result.memos_dir),
    )
