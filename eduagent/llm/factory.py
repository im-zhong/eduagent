from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.chat_models import ChatZhipuAI
from langchain_community.embeddings import ZhipuAIEmbeddings
from langchain_core.language_models import BaseChatModel
from langchain_deepseek import ChatDeepSeek
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

# def to_secret_str(s: str) -> SecretStr:
#     """Convert the configured API key into a SecretStr for LangChain models."""
#     api_key = settings.llm.api_key
#     if not api_key:
#         return None
#     return SecretStr(api_key)


def get_api_key() -> str:
    """Load the ZhipuAI API key from the project's `.env` file."""
    env_path = Path(".env")
    # Load environment variables once at import time; keeps secrets out of code.
    load_dotenv(dotenv_path=env_path)
    api_key = os.getenv("BIGMODEL_API_KEY")
    assert api_key is not None
    return api_key


def get_deepseek_api_key() -> str:
    env_path = Path(".env")
    # Load environment variables once at import time; keeps secrets out of code.
    load_dotenv(dotenv_path=env_path)
    api_key = os.getenv("DEEPSEEK_API_KEY")
    assert api_key is not None
    return api_key


def get_zhipu_chat_model() -> ChatZhipuAI:
    """Create a ChatOpenAI-compatible client pointed at Zhipu's API."""
    # Use the OpenAI-compatible wrapper so we can talk to Zhipu with the same interface.
    # Commented block shows the native client if you prefer the direct integration.
    return ChatZhipuAI(
        model="glm-4.6",
        temperature=0.5,
        api_key=get_api_key(),
    )

    # return ChatOpenAI(
    #     model="glm-4.6",
    #     temperature=0.5,
    #     api_key=get_api_key(),
    #     # Zhipu exposes an OpenAI-compatible endpoint; point the wrapper there.
    #     base_url="https://open.bigmodel.cn/api/paas/v4/",
    # )


def get_qwen_local_model() -> ChatOpenAI:
    """Create a ChatOpenAI-compatible client pointed at Qwen's local API."""
    return ChatOpenAI(
        model="Qwen3-235B-A22B",
        temperature=0.5,
        api_key="NOKEY",  # type: ignore
        # api_key=None,
        # Qwen local deployment endpoint
        base_url="http://222.30.145.85:8001/v1",
    )


def get_embedding_model() -> ZhipuAIEmbeddings:
    """Create a ZhipuAIEmbeddings client for semantic embedding generation."""
    return ZhipuAIEmbeddings(model="embedding-3", api_key=get_api_key())


# https://docs.langchain.com/oss/python/integrations/chat/deepseek
def get_deepseek_chat_model() -> ChatDeepSeek:
    return ChatDeepSeek(
        model="deepseek-chat",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
        api_key=SecretStr(get_deepseek_api_key()),
    )


def get_chat_model() -> BaseChatModel:
    return get_deepseek_chat_model()
    # return get_zhipu_chat_model()
    # return get_qwen_local_model()


# def get_chat_model(*, temperature: float | None = None) -> ChatOpenAI:
#     """Return a configured ChatOpenAI instance."""
#     resolved_temperature = (
#         temperature if temperature is not None else settings.llm.temperature
#     )
#     return ChatOpenAI(
#         temperature=resolved_temperature,
#         model=settings.llm.model_name,
#         api_key=_secret_api_key(),
#         base_url=settings.llm.api_base,
#     )


# def get_embedding_model() -> OpenAIEmbeddings:
#     """Return a configured OpenAI embeddings model for the Zhipu endpoint."""
#     return OpenAIEmbeddings(
#         model=settings.llm.embedding_model_name,
#         api_key=_secret_api_key(),
#         base_url=settings.llm.api_base,
#     )
