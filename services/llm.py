from __future__ import annotations

from functools import lru_cache
from typing import Optional

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from config import get_settings


@lru_cache(maxsize=16)
def get_chat_model(model_name: str, temperature: float = 0.3) -> ChatOpenAI:
    settings = get_settings()
    kwargs = {
        "model": model_name,
        "temperature": temperature,
        "api_key": settings.openai_api_key,
    }
    if settings.openai_organization:
        kwargs["organization"] = settings.openai_organization
    return ChatOpenAI(**kwargs)


@lru_cache(maxsize=1)
def get_embedding_model() -> OpenAIEmbeddings:
    settings = get_settings()
    kwargs = {
        "model": settings.embedding_model,
        "api_key": settings.openai_api_key,
    }
    if settings.openai_organization:
        kwargs["organization"] = settings.openai_organization
    return OpenAIEmbeddings(**kwargs)


def require_openai_key() -> Optional[str]:
    settings = get_settings()
    if not settings.openai_api_key:
        return "OPENAI_API_KEY가 설정되지 않았습니다. Streamlit secrets 또는 환경변수에 키를 넣어주세요."
    return None
