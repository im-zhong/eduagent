from __future__ import annotations

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from eduagent.llm.factory import get_chat_model, get_embedding_model
from eduagent.settings import settings


def test_chat_model_configuration() -> None:
    custom_temperature = 0.2
    chat = get_chat_model(temperature=custom_temperature)
    assert isinstance(chat, ChatOpenAI)
    assert chat.temperature == custom_temperature
    assert chat.model_name == settings.llm.model_name
    assert chat.openai_api_base == settings.llm.api_base
    assert chat.openai_api_key is not None
    assert chat.openai_api_key.get_secret_value() == settings.llm.api_key


def test_embedding_model_configuration() -> None:
    embedding = get_embedding_model()
    assert isinstance(embedding, OpenAIEmbeddings)
    assert embedding.model == settings.llm.embedding_model_name
    assert embedding.openai_api_base == settings.llm.api_base
    assert embedding.openai_api_key is not None
    assert embedding.openai_api_key.get_secret_value() == settings.llm.api_key
