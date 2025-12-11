from __future__ import annotations

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pydantic import SecretStr

from eduagent.settings import settings


def _secret_api_key() -> SecretStr | None:
    """Convert the configured API key into a SecretStr for LangChain models."""
    api_key = settings.llm.api_key
    if not api_key:
        return None
    return SecretStr(api_key)


def get_chat_model(*, temperature: float | None = None) -> ChatOpenAI:
    """Return a configured ChatOpenAI instance."""
    resolved_temperature = (
        temperature if temperature is not None else settings.llm.temperature
    )
    return ChatOpenAI(
        temperature=resolved_temperature,
        model=settings.llm.model_name,
        api_key=_secret_api_key(),
        base_url=settings.llm.api_base,
    )


def get_embedding_model() -> OpenAIEmbeddings:
    """Return a configured OpenAI embeddings model for the Zhipu endpoint."""
    return OpenAIEmbeddings(
        model=settings.llm.embedding_model_name,
        api_key=_secret_api_key(),
        base_url=settings.llm.api_base,
    )
