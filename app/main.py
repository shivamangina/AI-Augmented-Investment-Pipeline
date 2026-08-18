"""Thin FastAPI wrapper that serves the memo HTML files the CLI generates.

Run with: uvicorn app.main:app --reload
Then browse: http://localhost:8000/memos/<topic-slug>/memos/index.html
"""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)

OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="AI-Augmented Investment Pipeline",
    description="Serves the memo HTML files produced by `python -m app.cli run`.",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.mount("/memos", StaticFiles(directory=OUTPUTS_DIR, html=True), name="memos")
