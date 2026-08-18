import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    producthunt_api_token: str | None = os.getenv("PRODUCTHUNT_API_TOKEN") or None
    output_dir: str = os.getenv("OUTPUT_DIR", "outputs")
    analysis_concurrency: int = int(os.getenv("ANALYSIS_CONCURRENCY", "5"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
