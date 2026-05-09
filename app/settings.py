"""Runtime settings and project paths."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=False)


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    catalog_path: Path = PROJECT_ROOT / os.getenv("CATALOG_PATH", "data/processed/catalog.json")
    catalog_coverage_path: Path = PROJECT_ROOT / os.getenv(
        "CATALOG_COVERAGE_PATH", "data/processed/catalog_coverage.json"
    )
    trace_fixtures_dir: Path = PROJECT_ROOT / os.getenv("TRACE_FIXTURES_DIR", "data/traces/public")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "")
    llm_model: str = os.getenv("LLM_MODEL", "")
    llm_enable_intent_extraction: bool = env_bool("LLM_ENABLE_INTENT_EXTRACTION", True)
    llm_enable_reranking: bool = env_bool("LLM_ENABLE_RERANKING", True)


settings = Settings()
