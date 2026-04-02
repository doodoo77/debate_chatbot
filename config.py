from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Optional

try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_organization: Optional[str]
    tavily_api_key: Optional[str]
    redis_url: str
    model_easy: str
    model_hard: str
    planner_model: str
    verifier_model: str
    embedding_model: str
    cache_similarity_threshold: float
    early_stop_similarity_threshold: float
    max_verification_loops: int
    summary_token_threshold: int
    topic: str


DEFAULT_TOPIC = "알고리즘의 추천이 우리의 삶을 풍요롭게 해줄까?"


def _read_secret(name: str, default: Optional[Any] = None) -> Optional[Any]:
    if os.getenv(name) is not None:
        return os.getenv(name)

    if st is not None:
        try:
            if name in st.secrets:
                return st.secrets[name]
        except Exception:
            pass

    return default


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        openai_api_key=_read_secret("OPENAI_API_KEY", ""),
        openai_organization=_read_secret("OPENAI_ORGANIZATION"),
        tavily_api_key=_read_secret("TAVILY_API_KEY"),
        redis_url=_read_secret("REDIS_URL", "redis://localhost:6379/0"),

        # routed generation
        model_easy=_read_secret("MODEL_EASY", "gpt-5.4-mini"),
        model_hard=_read_secret("MODEL_HARD", "gpt-5.4"),

        # agent-specific
        planner_model=_read_secret("PLANNER_MODEL", "gpt-5.4-mini"),
        verifier_model=_read_secret("VERIFIER_MODEL", "gpt-5.4-mini"),

        # cache / similarity
        embedding_model=_read_secret("EMBEDDING_MODEL", "text-embedding-3-large"),

        cache_similarity_threshold=float(_read_secret("CACHE_SIMILARITY_THRESHOLD", 0.90)),
        early_stop_similarity_threshold=float(_read_secret("EARLY_STOP_SIMILARITY_THRESHOLD", 0.95)),
        max_verification_loops=int(_read_secret("MAX_VERIFICATION_LOOPS", 2)),
        summary_token_threshold=int(_read_secret("SUMMARY_TOKEN_THRESHOLD", 900)),
        topic=_read_secret("DEBATE_TOPIC", DEFAULT_TOPIC),
    )
