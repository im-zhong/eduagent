from __future__ import annotations

from langchain_community.chat_models import ChatZhipuAI
from langchain_community.embeddings import ZhipuAIEmbeddings

from eduagent.settings import settings


def get_chat_model(*, temperature: float = 0.0) -> ChatZhipuAI:
    """Return a configured ChatZhipuAI instance."""
    return ChatZhipuAI(
        api_key=settings.llm.api_key,
        model=settings.llm.model_name,
        temperature=temperature,
    )


def get_embedding_model() -> ZhipuAIEmbeddings:
    """Return a configured Zhipu embeddings model."""
    return ZhipuAIEmbeddings(
        api_key=settings.llm.api_key,
        model=settings.llm.embedding_model_name,
    )
