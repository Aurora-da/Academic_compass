from __future__ import annotations

from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.core.config import settings


@lru_cache
def get_llm() -> ChatOpenAI | None:
    """LLM 只出现在“理解”和“表达”两端；未配置 API Key 时整图仍可离线运行。"""
    if not settings.llm_enabled:
        return None
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=settings.llm_temperature,
        timeout=60,
    )
