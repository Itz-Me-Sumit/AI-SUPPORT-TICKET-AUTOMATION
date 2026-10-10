from functools import lru_cache

from langchain_openrouter import ChatOpenRouter

from app.config import settings


@lru_cache
def get_llm() -> ChatOpenRouter:
    """LLM client ek hi baar banta hai aur poore app mein reuse hota hai."""
    return ChatOpenRouter(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_retries=settings.llm_max_retries,
    )
